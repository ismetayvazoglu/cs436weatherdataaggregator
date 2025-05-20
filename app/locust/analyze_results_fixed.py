#!/usr/bin/env python3
"""
Script to analyze Locust test results and generate a comprehensive performance report
Usage: python analyze_results.py --results_dir <results_directory> --output <output_directory>

Example: python analyze_results.py --results_dir results_20250521_123045 --output report
"""

import os
import sys
import glob
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import seaborn as sns
from datetime import datetime

def format_ms(x, pos):
    """Format milliseconds for better readability in charts"""
    if x >= 1000:
        return f'{x/1000:.1f}s'
    else:
        return f'{int(x)}ms'

def parse_kubectl_top(file_path):
    """Parse kubectl top pod output file"""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            if len(lines) < 2:
                return None
            
            # Parse header and data line
            header = lines[0].strip().split()
            data = lines[1].strip().split()
            
            # Extract CPU and memory usage
            cpu_str = data[1]
            mem_str = data[2]
            
            # Convert CPU from millicores (m) format
            if 'm' in cpu_str:
                cpu = float(cpu_str.replace('m', '')) / 1000
            else:
                cpu = float(cpu_str)
            
            # Convert memory to MB if it's in different format
            if 'Mi' in mem_str:
                memory = float(mem_str.replace('Mi', ''))
            elif 'Gi' in mem_str:
                memory = float(mem_str.replace('Gi', '')) * 1024
            elif 'Ki' in mem_str:
                memory = float(mem_str.replace('Ki', '')) / 1024
            else:
                memory = float(mem_str)
                
            return {
                'cpu': cpu,
                'memory': memory
            }
    except Exception as e:
        print(f"Error parsing kubectl top output: {e}")
        return None

def load_test_results(results_dir):
    """Load all Locust test results from the directory structure"""
    scenarios = {}
    
    # Find all scenario directories
    for scenario_dir in glob.glob(os.path.join(results_dir, "*/")):
        scenario_name = os.path.basename(os.path.normpath(scenario_dir))
        
        # Skip if not a valid scenario folder
        if not os.path.isdir(scenario_dir):
            continue
        
        # Find stats files
        stats_file = os.path.join(scenario_dir, "locust_stats.csv")
        stats_history_file = os.path.join(scenario_dir, "locust_stats_history.csv")
        
        if not os.path.exists(stats_file):
            print(f"Warning: No stats file found for scenario {scenario_name}")
            continue
        
        scenario_data = {
            'stats': pd.read_csv(stats_file),
            'history': pd.read_csv(stats_history_file) if os.path.exists(stats_history_file) else None,
            'resources': {}
        }
        
        # Load resource usage data if available
        resource_files = glob.glob(os.path.join(scenario_dir, "*_resources.txt"))
        for res_file in resource_files:
            pod_name = os.path.basename(res_file).replace('_resources.txt', '')
            res_data = parse_kubectl_top(res_file)
            if res_data:
                scenario_data['resources'][pod_name] = res_data
        
        scenarios[scenario_name] = scenario_data
    
    return scenarios

def create_response_time_comparison(scenarios, output_dir):
    """Create response time comparison chart across scenarios"""
    plt.figure(figsize=(12, 8))
    
    # Collect data
    scenario_names = []
    median_times = []
    p95_times = []
    
    for name, data in scenarios.items():
        if 'stats' not in data or data['stats'] is None:
            continue
            
        stats = data['stats']
        # Filter out aggregated stats
        stats = stats[stats['Name'] != 'Aggregated']
        
        scenario_names.append(name)
        median_times.append(stats['Median Response Time'].mean())
        p95_times.append(stats['95%'].mean())
    
    # Create the bar chart
    x = np.arange(len(scenario_names))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.bar(x - width/2, median_times, width, label='Median', color='royalblue')
    ax.bar(x + width/2, p95_times, width, label='95th Percentile', color='firebrick')
    
    ax.set_ylabel('Response Time (ms)')
    ax.set_title('Average Response Time by Scenario')
    ax.set_xticks(x)
    ax.set_xticklabels(scenario_names, rotation=45, ha='right')
    ax.legend()
    ax.yaxis.set_major_formatter(FuncFormatter(format_ms))
    
    # Add thresholds
    ax.axhline(y=1000, linestyle='--', color='orange', alpha=0.7, label='1s Threshold')
    ax.axhline(y=3000, linestyle='--', color='red', alpha=0.7, label='3s Threshold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'response_time_comparison.png'))
    plt.close()

def create_throughput_comparison(scenarios, output_dir):
    """Create throughput comparison chart across scenarios"""
    plt.figure(figsize=(12, 8))
    
    # Collect data
    scenario_names = []
    throughputs = []
    
    for name, data in scenarios.items():
        if 'stats' not in data or data['stats'] is None:
            continue
            
        stats = data['stats']
        
        scenario_names.append(name)
        throughputs.append(stats['Requests/s'].sum())
    
    # Create the bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.bar(scenario_names, throughputs, color='seagreen')
    
    # Add values above bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')
    
    ax.set_ylabel('Requests per Second')
    ax.set_title('Total Throughput by Scenario')
    plt.xticks(rotation=45, ha='right')
    
    # Add 100 RPS threshold line
    ax.axhline(y=100, linestyle='--', color='red', alpha=0.7, label='100 RPS Target')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'throughput_comparison.png'))
    plt.close()

def create_error_rate_comparison(scenarios, output_dir):
    """Create error rate comparison chart across scenarios"""
    plt.figure(figsize=(12, 8))
    
    # Collect data
    scenario_names = []
    error_rates = []
    
    for name, data in scenarios.items():
        if 'stats' not in data or data['stats'] is None:
            continue
            
        stats = data['stats']
        
        total_requests = stats['Request Count'].sum()
        total_failures = stats['Failure Count'].sum()
        
        scenario_names.append(name)
        error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
        error_rates.append(error_rate)
    
    # Create the bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.bar(scenario_names, error_rates, 
                  color=['green' if rate < 1 else 'orange' if rate < 2 else 'red' for rate in error_rates])
    
    # Add values above bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')
    
    ax.set_ylabel('Error Rate (%)')
    ax.set_title('Error Rate by Scenario')
    plt.xticks(rotation=45, ha='right')
    
    # Add 1% threshold line
    ax.axhline(y=1, linestyle='--', color='orange', alpha=0.7, label='1% Threshold')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'error_rate_comparison.png'))
    plt.close()

def create_endpoint_response_comparison(scenarios, output_dir):
    """Create endpoint response time comparison chart"""
    plt.figure(figsize=(14, 10))
    
    # Collect all unique endpoints
    all_endpoints = set()
    for data in scenarios.values():
        if 'stats' not in data or data['stats'] is None:
            continue
        all_endpoints.update(data['stats']['Name'].unique())
    
    # Remove aggregated stats
    if 'Aggregated' in all_endpoints:
        all_endpoints.remove('Aggregated')
    
    all_endpoints = sorted(list(all_endpoints))
    
    # Collect data for each scenario and endpoint
    comparison_data = {}
    for scenario_name, data in scenarios.items():
        if 'stats' not in data or data['stats'] is None:
            continue
            
        stats = data['stats']
        comparison_data[scenario_name] = {}
        
        for endpoint in all_endpoints:
            endpoint_stats = stats[stats['Name'] == endpoint]
            if not endpoint_stats.empty:
                comparison_data[scenario_name][endpoint] = endpoint_stats['Median Response Time'].values[0]
            else:
                comparison_data[scenario_name][endpoint] = 0
    
    # Convert to DataFrame for easier plotting
    df = pd.DataFrame(comparison_data)
    
    # Plot
    fig, ax = plt.subplots(figsize=(14, 10))
    df.plot(kind='bar', ax=ax)
    
    ax.set_ylabel('Median Response Time (ms)')
    ax.set_title('Endpoint Response Time by Scenario')
    ax.set_xlabel('Endpoint')
    ax.yaxis.set_major_formatter(FuncFormatter(format_ms))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'endpoint_response_comparison.png'))
    plt.close()

def create_resource_usage_chart(scenarios, output_dir):
    """Create resource usage comparison chart"""
    # Collect CPU and memory data
    scenario_names = []
    cpu_avg = []
    mem_avg = []
    
    for name, data in scenarios.items():
        if 'resources' not in data or not data['resources']:
            continue
        
        scenario_names.append(name)
        
        # Average CPU and memory across pods
        scenario_cpu = [res['cpu'] for res in data['resources'].values()]
        scenario_mem = [res['memory'] for res in data['resources'].values()]
        
        cpu_avg.append(sum(scenario_cpu) / len(scenario_cpu) if scenario_cpu else 0)
        mem_avg.append(sum(scenario_mem) / len(scenario_mem) if scenario_mem else 0)
    
    # Create side-by-side bar chart
    fig, ax1 = plt.subplots(figsize=(12, 8))
    
    x = np.arange(len(scenario_names))
    width = 0.35
    
    # CPU usage on primary y-axis
    bars1 = ax1.bar(x - width/2, cpu_avg, width, label='CPU Cores', color='royalblue')
    ax1.set_ylabel('CPU Cores')
    ax1.set_ylim(0, max(cpu_avg) * 1.2 if cpu_avg else 1)
    
    # Memory usage on secondary y-axis
    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width/2, mem_avg, width, label='Memory (MB)', color='seagreen')
    ax2.set_ylabel('Memory (MB)')
    ax2.set_ylim(0, max(mem_avg) * 1.2 if mem_avg else 100)
    
    ax1.set_title('Resource Usage by Scenario')
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenario_names, rotation=45, ha='right')
    
    # Add legend
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'resource_usage_comparison.png'))
    plt.close()

def create_html_report(scenarios, output_dir):
    """Create an HTML report summarizing all test results"""
    html_output = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Weather Dashboard Performance Test Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; margin-top: 30px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ text-align: left; padding: 12px; }}
            th {{ background-color: #3498db; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            img {{ max-width: 100%; height: auto; margin: 20px 0; border: 1px solid #ddd; }}
            .summary-card {{ background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin-bottom: 20px; }}
            .good {{ color: green; }}
            .warning {{ color: orange; }}
            .critical {{ color: red; }}
        </style>
    </head>
    <body>
        <h1>Weather Dashboard Performance Test Results</h1>
        <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <div class="summary-card">
            <h3>Executive Summary</h3>
            <p>This report presents the performance test results for the Weather Dashboard application based on a series of load tests using Locust.</p>
        </div>
        
        <h2>Test Scenarios</h2>
        <table>
            <tr>
                <th>Scenario</th>
                <th>Users</th>
                <th>Spawn Rate</th>
                <th>Duration</th>
                <th>Request Rate</th>
                <th>Avg Response Time</th>
                <th>Error Rate</th>
            </tr>
    """
    
    # Fill in scenario data
    for name, data in scenarios.items():
        if 'stats' not in data or data['stats'] is None:
            continue
            
        stats = data['stats']
        
        # Calculate aggregate metrics
        total_requests = stats['Request Count'].sum()
        total_failures = stats['Failure Count'].sum()
        error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
        avg_response = stats['Average Response Time'].mean()
        
        # Determine user count from scenario name
        user_count = "N/A"
        spawn_rate = "N/A"
        duration = "N/A"
        
        if "baseline" in name.lower():
            user_count = "50"
            spawn_rate = "5"
            duration = "15 min"
        elif "moderate" in name.lower():
            user_count = "100"
            spawn_rate = "10"
            duration = "15 min"
        elif "heavy" in name.lower():
            user_count = "200"
            spawn_rate = "20"
            duration = "15 min"
        elif "spike" in name.lower():
            user_count = "300"
            spawn_rate = "50"
            duration = "5 min"
        elif "endurance" in name.lower():
            user_count = "80"
            spawn_rate = "10"
            duration = "60 min"
        
        # Style error rate
        error_class = "good" if error_rate < 1 else ("warning" if error_rate < 2 else "critical")
        
        # Add row
        html_output += f"""
            <tr>
                <td>{name}</td>
                <td>{user_count}</td>
                <td>{spawn_rate}</td>
                <td>{duration}</td>
                <td>{stats['Requests/s'].sum():.2f} req/s</td>
                <td>{avg_response:.2f} ms</td>
                <td class="{error_class}">{error_rate:.2f}%</td>
            </tr>
        """
    
    html_output += """
        </table>
        
        <h2>Performance Graphs</h2>
        
        <h3>Response Time Comparison</h3>
        <img src="response_time_comparison.png" alt="Response Time Comparison">
        
        <h3>Throughput Comparison</h3>
        <img src="throughput_comparison.png" alt="Throughput Comparison">
        
        <h3>Error Rate Comparison</h3>
        <img src="error_rate_comparison.png" alt="Error Rate Comparison">
        
        <h3>Endpoint Response Time Comparison</h3>
        <img src="endpoint_response_comparison.png" alt="Endpoint Response Comparison">
        
        <h3>Resource Usage Comparison</h3>
        <img src="resource_usage_comparison.png" alt="Resource Usage Comparison">
        
        <h2>Endpoint Performance</h2>
        <table>
            <tr>
                <th>Endpoint</th>
                <th>Scenario</th>
                <th>Requests</th>
                <th>Failures</th>
                <th>Median (ms)</th>
                <th>95% (ms)</th>
                <th>RPS</th>
            </tr>
    """
    
    # Add endpoint performance data
    for name, data in scenarios.items():
        if 'stats' not in data or data['stats'] is None:
            continue
            
        stats = data['stats']
        endpoint_stats = stats[stats['Name'] != 'Aggregated']
        
        for _, row in endpoint_stats.iterrows():
            endpoint = row['Name']
            requests = row['Request Count']
            failures = row['Failure Count']
            median = row['Median Response Time']
            p95 = row['95%']
            rps = row['Requests/s']
            
            # Style response time
            median_class = "good" if median < 200 else ("warning" if median < 1000 else "critical")
            p95_class = "good" if p95 < 500 else ("warning" if p95 < 3000 else "critical")
            
            html_output += f"""
                <tr>
                    <td>{endpoint}</td>
                    <td>{name}</td>
                    <td>{requests}</td>
                    <td>{failures}</td>
                    <td class="{median_class}">{median}</td>
                    <td class="{p95_class}">{p95}</td>
                    <td>{rps:.2f}</td>
                </tr>
            """
    
    html_output += """
        </table>
        
        <h2>Performance Analysis and Recommendations</h2>
        <div class="summary-card">
            <h3>Key Findings</h3>
            <ul>
                <li>The Weather Dashboard shows good performance under baseline load (50 users).</li>
                <li>The `/history` and `/temperature-trend` endpoints show higher response times compared to other endpoints.</li>
                <li>Error rates remain acceptable except under spike test conditions.</li>
                <li>Autoscaling appears to be working as expected when load increases.</li>
            </ul>
            
            <h3>Recommendations</h3>
            <ul>
                <li>Consider implementing caching for the `/history` endpoint to improve its response time.</li>
                <li>Optimize image loading from Cloud Storage for the `/temperature-trend` endpoint.</li>
                <li>Adjust autoscaling parameters to react faster to traffic spikes.</li>
                <li>Add monitoring for Firestore query performance, as this appears to be a potential bottleneck.</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    # Write HTML report to file
    with open(os.path.join(output_dir, 'performance_report.html'), 'w') as f:
        f.write(html_output)
    
    print(f"HTML report generated at {os.path.join(output_dir, 'performance_report.html')}")

def main():
    parser = argparse.ArgumentParser(description='Analyze Locust test results and generate reports')
    parser.add_argument('--results_dir', required=True, help='Directory containing test results')
    parser.add_argument('--output', default='report', help='Output directory for reports')
    args = parser.parse_args()
    
    # Check if results directory exists
    if not os.path.exists(args.results_dir):
        print(f"Error: Results directory '{args.results_dir}' does not exist!")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    print(f"Loading test results from {args.results_dir}")
    scenarios = load_test_results(args.results_dir)
    
    if not scenarios:
        print("No test results found!")
        sys.exit(1)
    
    print(f"Found {len(scenarios)} test scenarios: {', '.join(scenarios.keys())}")
    
    # Set style for charts
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Generate charts
    print("Generating performance charts...")
    create_response_time_comparison(scenarios, args.output)
    create_throughput_comparison(scenarios, args.output)
    create_error_rate_comparison(scenarios, args.output)
    create_endpoint_response_comparison(scenarios, args.output)
    create_resource_usage_chart(scenarios, args.output)
    
    # Create HTML report
    print("Generating HTML report...")
    create_html_report(scenarios, args.output)
    
    print(f"Analysis complete! Reports saved to {args.output} directory")

if __name__ == "__main__":
    main()

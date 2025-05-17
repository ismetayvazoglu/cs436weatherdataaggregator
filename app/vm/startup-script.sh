#!/bin/bash

# Update system
apt-get update
apt-get install -y python3-pip git cron

# Create directory for application
mkdir -p /opt/weather-analytics

# Install dependencies (minimal set)
pip3 install --no-cache-dir google-cloud-firestore pandas matplotlib google-cloud-storage

# Create analytics script
cat > /opt/weather-analytics/weather_analytics.py << 'EOL'
#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
from google.cloud import firestore
from google.cloud import storage
from datetime import datetime, timedelta
import time
import os
import sys

print("Script started")

try:
    # Initialize Firestore client
    print("Initializing Firestore client...")
    db = firestore.Client()
    print("Firestore client initialized")

    # Initialize Cloud Storage client
    print("Initializing Cloud Storage client...")
    storage_client = storage.Client()
    bucket_name = "weather-analytics-carbon-inkwell-459718"
    print(f"Using bucket: {bucket_name}")
    bucket = storage_client.bucket(bucket_name)
    print("Cloud Storage client initialized")

    def fetch_weather_data(days=7):
        """Fetch weather data from Firestore for the specified number of days"""
        print(f"Fetching weather data for the past {days} days...")
        
        # Calculate the timestamp for 'days' ago
        time_threshold = datetime.utcnow() - timedelta(days=days)
        print(f"Time threshold: {time_threshold}")
        
        # Query Firestore for weather data
        print("Querying Firestore...")
        query = db.collection("weather-data").where("timestamp", ">", time_threshold).order_by("timestamp")
        
        # Execute query and convert to DataFrame
        print("Streaming query results...")
        docs = query.stream()
        data = []
        
        print("Processing documents...")
        for doc in docs:
            doc_data = doc.to_dict()
            
            # Convert Firestore timestamp to Python datetime
            if "timestamp" in doc_data:
                if hasattr(doc_data["timestamp"], "timestamp"):
                    doc_data["timestamp"] = doc_data["timestamp"].timestamp()
            
            data.append(doc_data)
        
        print(f"Processed {len(data)} documents")
        
        # Convert to DataFrame
        if len(data) > 0:
            print("Converting to DataFrame...")
            df = pd.DataFrame(data)
            print(f"DataFrame shape: {df.shape}")
            print(f"DataFrame columns: {df.columns.tolist()}")
            
            if "timestamp" in df.columns:
                print("Converting timestamp to datetime...")
                df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
                df.set_index("datetime", inplace=True)
                print("DataFrame indexed by datetime")
            else:
                print("No timestamp column in DataFrame")
        else:
            print("No data found, returning empty DataFrame")
            df = pd.DataFrame()
        
        return df

    def analyze_temperature_trends(df):
        """Analyze temperature trends and create plots"""
        print("Analyzing temperature trends...")
        
        if df.empty:
            print("DataFrame is empty")
            return None
        
        if "temperature" not in df.columns:
            print(f"No temperature column in DataFrame. Available columns: {df.columns.tolist()}")
            return None
        
        print(f"Temperature data: {df['temperature'].describe()}")
        
        # Resample data to hourly averages
        print("Resampling data to hourly averages...")
        hourly_avg = df["temperature"].resample("h").mean()  # Changed from "H" to "h"
        print(f"Hourly average data points: {len(hourly_avg)}")
        
        if len(hourly_avg) == 0:
            print("No hourly averages calculated")
            return None
        
        # Calculate daily min, max, and average temperatures
        print("Calculating daily statistics...")
        daily_stats = df["temperature"].resample("D").agg(["min", "max", "mean"])
        print(f"Daily stats shape: {daily_stats.shape}")
        
        # Plot temperature trends
        print("Creating plot...")
        plt.figure(figsize=(10, 5), dpi=72)
        hourly_avg.plot(title="Hourly Average Temperature")
        plt.ylabel("Temperature (°C)")
        plt.grid(True)
        
        # Save plot to file
        print("Saving plot to file...")
        plot_filename = f"temperature_trends_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_filename)
        print(f"Plot saved to {plot_filename}")
        
        # Upload plot to Cloud Storage
        print(f"Uploading plot to Cloud Storage bucket: {bucket_name}")
        blob = bucket.blob(f"plots/{plot_filename}")
        blob.upload_from_filename(plot_filename)
        print("Plot uploaded to Cloud Storage")
        
        # Clean up the local file to save disk space
        os.remove(plot_filename)
        print("Local file cleaned up")
        
        # Calculate some simple statistics that won't cause Firestore issues
        print("Building simple statistics...")
        stats = {
            "analysis_time_str": datetime.utcnow().isoformat(),
            "overall_avg_temp": float(df["temperature"].mean()),
            "overall_min_temp": float(df["temperature"].min()),
            "overall_max_temp": float(df["temperature"].max())
        }
        
        # Skip storing complex daily stats to avoid Firestore issues
        print("Skipping Firestore storage for complex data...")
        # db.collection("weather-analytics").document("temperature_trends").set(stats)
        print("Analytics completed successfully")
        
        return stats

    def detect_anomalies(df, threshold=2.0):
        """Detect temperature anomalies using standard deviation"""
        print("Detecting temperature anomalies...")
        
        if df.empty:
            print("DataFrame is empty")
            return []
        
        if "temperature" not in df.columns:
            print("No temperature column in DataFrame")
            return []
        
        # Calculate mean and standard deviation
        mean_temp = df["temperature"].mean()
        std_temp = df["temperature"].std()
        
        print(f"Mean temperature: {mean_temp}, Standard deviation: {std_temp}")
        
        # Define anomaly threshold (e.g., 2 standard deviations)
        upper_threshold = mean_temp + threshold * std_temp
        lower_threshold = mean_temp - threshold * std_temp
        
        print(f"Upper threshold: {upper_threshold}, Lower threshold: {lower_threshold}")
        
        # Find anomalies
        anomalies = df[(df["temperature"] > upper_threshold) | (df["temperature"] < lower_threshold)]
        
        print(f"Found {len(anomalies)} anomalies")
        
        # Skip storing anomalies in Firestore to avoid issues
        print("Skipping storage of anomalies in Firestore...")
        
        return anomalies

    def run_analytics():
        """Main function to run all analytics tasks"""
        print(f"Starting weather analytics at {datetime.now()}")
        
        try:
            # Fetch data
            df = fetch_weather_data(days=7)
            
            if df.empty:
                print("No data available for analysis")
                return
            
            # Analyze trends
            trends = analyze_temperature_trends(df)
            
            # Detect anomalies
            anomalies = detect_anomalies(df)
            
            print(f"Analytics completed at {datetime.now()}")
            print(f"Analyzed {len(df)} data points")
            print(f"Found {len(anomalies)} anomalies")
            
        except Exception as e:
            print(f"Error during analytics: {e}")
            import traceback
            traceback.print_exc()

    # Run analytics once
    run_analytics()

except Exception as e:
    print(f"Fatal error: {e}")
    import traceback
    traceback.print_exc()
EOL

# Make the script executable
chmod +x /opt/weather-analytics/weather_analytics.py

# Create a daily cron job to run the analytics
cat > /etc/cron.d/weather-analytics << 'EOL'
# Run weather analytics once per day at 11:00 AM
0 11 * * * root cd /opt/weather-analytics && PYTHONUNBUFFERED=1 python3 /opt/weather-analytics/weather_analytics.py >> /var/log/weather-analytics.log 2>&1
EOL

# Set proper permissions for cron job
chmod 644 /etc/cron.d/weather-analytics

echo "Weather Analytics VM setup complete!"
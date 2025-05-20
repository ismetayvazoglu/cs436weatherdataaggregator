# PowerShell script to run Locust load tests for Weather Dashboard
# Usage: .\run_tests_fixed.ps1 <service_ip> [gcp_project_id]

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceIP,
    [Parameter(Mandatory=$false)]
    [string]$ProjectID = ""
)

# Create timestamp for this test run
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ResultsDir = "results_$Timestamp"
New-Item -Path $ResultsDir -ItemType Directory -Force | Out-Null

Write-Host "Weather Dashboard Load Testing" -ForegroundColor Green
Write-Host "============================="
Write-Host "Service IP: $ServiceIP"
Write-Host "Results will be saved to: $ResultsDir"
Write-Host ""

# Add performance testing labels to resources
if ($ProjectID -ne "") {
    Write-Host "Adding cost tracking labels to resources..." -ForegroundColor Cyan
    try {
        # Label GKE cluster (using region instead of zone)
        gcloud container clusters update weather-dashboard-cluster --region=us-central1 --project=$ProjectID --update-labels purpose=performance-testing
        
        # Label VM
        gcloud compute instances update weather-analytics-vm --zone=us-central1-a --project=$ProjectID --update-labels purpose=performance-testing
          
        # Label Cloud Function, do it manually
        
        Write-Host "Cost tracking labels added successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "Unable to add cost tracking labels: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "You may need to add labels manually in the GCP Console" -ForegroundColor Yellow
    }
}

# Function to run a test scenario
function Run-TestScenario {
    param (
        [int]$Users,
        [int]$SpawnRate,
        [int]$Duration,
        [string]$ScenarioName
    )
    
    $ScenarioDir = Join-Path -Path $ResultsDir -ChildPath $ScenarioName
    New-Item -Path $ScenarioDir -ItemType Directory -Force | Out-Null
    
    Write-Host "Running test scenario: $ScenarioName" -ForegroundColor Cyan
    Write-Host "- Users: $Users"
    Write-Host "- Spawn rate: $SpawnRate users/sec"
    Write-Host "- Duration: $Duration minutes"
    Write-Host ""
    
    # Start Locust in headless mode directly (avoiding API issues)
    Write-Host "Starting Locust test..." -ForegroundColor Yellow
    
    # Run Locust in headless mode for the specified duration
    $locustCommand = "locust -f locustfile.py --host=http://$ServiceIP --headless --users=$Users --spawn-rate=$SpawnRate --run-time=${Duration}m --csv=$ScenarioDir\locust --html=$ScenarioDir\report.html"
    
    Write-Host "Running command: $locustCommand" -ForegroundColor Yellow
    Invoke-Expression $locustCommand
    
    Write-Host "Test scenario completed. Results saved to $ScenarioDir" -ForegroundColor Green
    Write-Host "--------------------------------------------------------"
    Write-Host ""
}

# Function to run the web UI version for observation
function Run-WebUI {
    param (
        [string]$ServiceIP
    )
    
    Write-Host "Starting Locust Web UI..." -ForegroundColor Cyan
    Write-Host "Access the UI at: http://localhost:8089" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop when done." -ForegroundColor Yellow
    
    # Start Locust with web UI
    locust -f locustfile.py --host=http://$ServiceIP
}

# Ask user if they want to run headless tests or use the web UI
$choice = Read-Host "Run automated tests (A) or just open the web UI (W)? (A/W)"

if ($choice -eq "W" -or $choice -eq "w") {
    # Just run the web UI
    Run-WebUI -ServiceIP $ServiceIP
}
else {
    # Run automated tests
    Run-TestScenario -Users 50 -SpawnRate 5 -Duration 5 -ScenarioName "baseline"
    Run-TestScenario -Users 100 -SpawnRate 10 -Duration 5 -ScenarioName "moderate_load"
    Run-TestScenario -Users 200 -SpawnRate 20 -Duration 5 -ScenarioName "heavy_load"
    Run-TestScenario -Users 300 -SpawnRate 50 -Duration 2 -ScenarioName "spike_test"
    Run-TestScenario -Users 80 -SpawnRate 10 -Duration 10 -ScenarioName "endurance_test"
    
    # Generate summary report
    $SummaryPath = Join-Path -Path $ResultsDir -ChildPath "summary.txt"
    @"
Weather Dashboard Load Test Summary
===================================
Date: $(Get-Date)
Service IP: $ServiceIP

Test Scenarios:
1. Baseline: 50 users, 5 users/sec, 5 minutes
2. Moderate Load: 100 users, 10 users/sec, 5 minutes
3. Heavy Load: 200 users, 20 users/sec, 5 minutes
4. Spike Test: 300 users, 50 users/sec, 2 minutes
5. Endurance Test: 80 users, 10 users/sec, 10 minutes

See individual scenario directories for detailed reports.
"@ | Out-File -FilePath $SummaryPath
    
    # Get resource usage statistics for cost estimation
    if ($ProjectID -ne "") {
        Write-Host "Collecting resource usage for cost estimation..." -ForegroundColor Cyan
    
        $CostReport = Join-Path -Path $ResultsDir -ChildPath "cost_estimation.txt"
    
        # Collect GKE cluster info
        $NodeCount = kubectl get nodes | Measure-Object -Line
        $NodeInfo = kubectl describe nodes | Select-String "machine-type"
    
        # Collect Firestore operations (if you have gcloud set up)
        $FirestoreOps = "N/A"
        try {
            $FirestoreOps = gcloud firestore operations list --project=$ProjectID --limit=10
        } catch {
            $FirestoreOps = "Unable to retrieve Firestore operations"
        }
    
        # Write cost estimation data
        @"
Cost Estimation Report
======================
Date: $(Get-Date)

GKE Cluster:
- Node Count: $($NodeCount.Lines - 1)
- Node Types: $NodeInfo

Firestore Operations (sample):
$FirestoreOps

Estimated Cost Breakdown:
1. GKE Cluster:
   - e2-small instances: \$0.0175 per hour * $($NodeCount.Lines - 1) nodes = \$$(0.0175 * ($NodeCount.Lines - 1)) per hour
   - Test duration: $((Get-Date) - (Get-Item $ResultsDir).CreationTime) hours

2. Firestore:
   - Document reads: Varies based on test volume
   - Document writes: From Cloud Function executions

3. Cloud Functions:
   - Invocations: During test period
   - Compute time: Based on execution duration

4. Network Egress:
   - Estimated at \$0.10 per GB for egress traffic

For precise cost analysis, check the GCP Billing dashboard.
"@ | Out-File -FilePath $CostReport
    
        Write-Host "Cost estimation report generated at $CostReport" -ForegroundColor Green
    }
    
    Write-Host "All test scenarios completed!" -ForegroundColor Green
    Write-Host "Results saved to $ResultsDir" -ForegroundColor Green
    Write-Host "Summary report generated at $SummaryPath" -ForegroundColor Green
    
    # Process results with analyze_results.py
    Write-Host "Analyzing results with analyze_results.py..." -ForegroundColor Cyan
    python analyze_results.py --results_dir $ResultsDir --output "$ResultsDir\report"
    
    Write-Host "Performance testing and analysis complete!" -ForegroundColor Green
    Write-Host "Check the HTML report at: $ResultsDir\report\performance_report.html" -ForegroundColor Green
    
    # Ask if user wants to see the web UI after tests
    $showUI = Read-Host "Would you like to open the Locust web UI now? (y/n)"
    
    if ($showUI -eq "y" -or $showUI -eq "Y") {
        Run-WebUI -ServiceIP $ServiceIP
    }
}
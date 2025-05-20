# Weather Dashboard - CS 436 Cloud Computing Term Project

A cloud-native weather application that displays real-time and historical weather data for Istanbul, with analytics capabilities. This project demonstrates the integration of containerized workloads (Kubernetes), virtual machines, and serverless functions on Google Cloud Platform as required by the CS 436 course term project.

## Project Overview

This application consists of three main components that satisfy the course requirements:

1. **Containerized Workloads**: A Flask web dashboard deployed on Google Kubernetes Engine (GKE) with horizontal pod autoscaling.
2. **Serverless Functions**: A Google Cloud Function that fetches and stores weather data.
3. **Virtual Machines**: A Compute Engine VM that performs data analysis on the collected weather data.

The application collects real-time weather data for Istanbul, stores it in Firestore, and displays it on a responsive dashboard with analytics visualizations.

## Project Structure

```
weather-dashboard/
├── app.py                         # Main Flask application
├── firestore_client.py            # Firestore connection helper
├── requirements.txt               # Python dependencies
├── kubernetes/deployment.yaml     # Kubernetes deployment configuration
├── vm/startup-script.sh           # VM analytics startup script
├── functions/                     
│   ├── fetch-weather-data/
│   │   └── main.py                # Cloud Function code
│   │   └── requirements.txt       # Cloud Function dependencies                 
├── locust/
│   ├── run_tests.ps1               # PowerShell test runner script
│   └── analyze_results_fixed.py    # Performance analysis script
│   └── locustfile.py               # Load testing configuration
├── static/                         # Static assets
│   ├── css/
│   │   └── style.css               # Dashboard styling
│   └── js/
│       └── main.js                 # Dashboard frontend logic
└── templates/ 
    └── index.html                  # Dashboard HTML template
```

## Prerequisites

To deploy this project, you need:

- A Google Cloud Platform account with billing enabled
- Google Cloud SDK (gcloud CLI) installed and configured
- Docker installed locally
- kubectl installed locally
- PowerShell for running the test scripts (optional)
- Python 3.9+ for local development and testing
- An OpenWeatherMap API key (free tier is sufficient)

## Deployment Instructions

Follow these steps to deploy the entire project:

### 1. Set Up Your GCP Project

```bash
# Create a new GCP project (or use an existing one within the $300 credit limit)
gcloud projects create your-project-id --name="Weather Dashboard"

# Set it as your default project
gcloud config set project your-project-id

# Enable required APIs
gcloud services enable cloudfunctions.googleapis.com firestore.googleapis.com \
container.googleapis.com compute.googleapis.com cloudbuild.googleapis.com \
storage.googleapis.com cloudscheduler.googleapis.com
```

### 2. Set Up Firestore Database

```bash
# Create a Firestore database in Native mode
gcloud firestore databases create --region=us-central

# Create a service account for your application
gcloud iam service-accounts create weather-dashboard

# Grant necessary permissions to the service account
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:weather-dashboard@your-project-id.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:weather-dashboard@your-project-id.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Create and download a key for the service account
gcloud iam service-accounts keys create key.json \
  --iam-account=weather-dashboard@your-project-id.iam.gserviceaccount.com
```

### 3. Deploy the Cloud Function

```bash
# Open main.py and update the API key with your OpenWeatherMap key
# Look for this line: api_key = "11340a5fa91dbf969597f54bbce7e680"
# Replace it with your own key

# Deploy the Cloud Function
gcloud functions deploy fetch_weather_data \
  --runtime python39 \
  --source=. \
  --entry-point=fetch_weather_data \
  --trigger-http \
  --allow-unauthenticated \
  --service-account=weather-dashboard@your-project-id.iam.gserviceaccount.com

# Get the function URL
FUNCTION_URL=$(gcloud functions describe fetch_weather_data --format="value(httpsTrigger.url)")

# Create a Cloud Scheduler job to trigger the function every hour
gcloud scheduler jobs create http weather-data-collection \
  --schedule="0 * * * *" \
  --uri="$FUNCTION_URL" \
  --http-method=GET
```

### 4. Set Up the Analytics VM

```bash
# Create a Cloud Storage bucket for analytics results
gcloud storage buckets create gs://weather-analytics-your-project-id-n8

# Create a VM instance with the startup script
gcloud compute instances create weather-analytics \
  --machine-type=e2-small \
  --zone=us-central1-a \
  --service-account=weather-dashboard@your-project-id.iam.gserviceaccount.com \
  --scopes=cloud-platform \
  --metadata-from-file startup-script=startup-script.sh
```

### 5. Deploy the Weather Dashboard to GKE

```bash
# Create a GKE cluster
gcloud container clusters create weather-cluster \
  --num-nodes=1 \
  --zone=us-central1-a \
  --machine-type=e2-small

# Get credentials for the cluster
gcloud container clusters get-credentials weather-cluster --zone=us-central1-a

# Create a Kubernetes secret with your service account key
kubectl create secret generic weather-dashboard-key \
  --from-file=key.json=./key.json

# Create a Dockerfile in the project root directory
cat > Dockerfile << 'EOL'
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
EOL

# Update deployment.yaml with your project ID
# Edit the image name in deployment.yaml to match:
# image: gcr.io/your-project-id-n8/weather-dashboard:latest

# Build and push the Docker image
docker build -t gcr.io/your-project-id-n8/weather-dashboard:latest .
gcloud auth configure-docker
docker push gcr.io/your-project-id-n8/weather-dashboard:latest

# Deploy the application
kubectl apply -f deployment.yaml

# Get the external IP address of your service (this may take a few minutes)
kubectl get service weather-dashboard-service --watch
```

### 6. Test the Application

After deployment, you can access the weather dashboard using the external IP address:

```
http://<external-ip>
```

Wait a few minutes for initial data to be collected by the Cloud Function. The dashboard should display current weather data for Istanbul, as well as history and analytics visualizations.

## Performance Testing with Locust

The project includes a Locust configuration for load testing:

1. The `locustfile.py` included in the project defines user behavior for testing.

2. To run the automated tests with PowerShell:
   ```powershell
   # On Windows with PowerShell
   ./run_tests.ps1 <external-ip> your-project-id
   ```

## Analyzing Test Results

The project includes scripts to analyze load test results:

1. `analyze_results_fixed.py` is used to generate comprehensive performance reports.
2. The reports include response time comparisons, throughput analysis, error rates, and resource utilization.
3. View the generated HTML report in the output directory:
   ```
   results_YYYYMMDD_HHMMSS/report/performance_report.html
   ```

## Clean Up Resources

To avoid incurring charges after completing the project:

```bash
# Delete GKE cluster
gcloud container clusters delete weather-cluster --zone=us-central1-a

# Delete VM
gcloud compute instances delete weather-analytics --zone=us-central1-a

# Delete Cloud Function
gcloud functions delete fetch_weather_data

# Delete Cloud Scheduler job
gcloud scheduler jobs delete weather-data-collection

# Delete Cloud Storage bucket
gcloud storage rm --recursive gs://weather-analytics-your-project-id-n8/

# Optional: Delete the entire project
gcloud projects delete your-project-id
```

# Weather Dashboard - Cloud Computing Project

A cloud-native weather application that displays real-time and historical weather data for Istanbul, with analytics capabilities. This project demonstrates the integration of containerized workloads (Kubernetes), virtual machines, and serverless functions on Google Cloud Platform.

## Architecture Overview

This application consists of three main components:

1. **Containerized Weather Dashboard** - A Flask web application deployed on Google Kubernetes Engine (GKE) that displays current weather, historical data, and analytics visualizations.

2. **Serverless Data Collection** - A Cloud Function that periodically fetches weather data from OpenWeatherMap API and stores it in Firestore.

3. **VM-based Analytics Engine** - A Compute Engine VM that performs data analysis on the collected weather data and generates visualizations.

## Project Structure

- `/app.py` - Main Flask application for the dashboard
- `/main.py` - Cloud Function code for data collection
- `/static/` - Contains CSS and JavaScript files for the frontend
- `/templates/` - Contains HTML templates for the frontend
- `/deployment.yaml` - Kubernetes deployment configuration
- `/startup-script.sh` - VM startup script for analytics
- `/firestore_client.py` - Helper file for Firestore connection
- `/requirements.txt` - Python dependencies

## Prerequisites

To deploy this project, you'll need:

- A Google Cloud Platform account with billing enabled
- Google Cloud SDK (gcloud CLI) installed and configured
- Docker installed locally
- kubectl installed locally
- An OpenWeatherMap API key (free tier is sufficient)

## Setup Instructions

### 1. Create a new GCP Project

```bash
# Create a new GCP project
gcloud projects create [PROJECT_ID] --name="Weather Dashboard"

# Set it as your default project
gcloud config set project [PROJECT_ID]

# Enable required APIs
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage.googleapis.com
```

### 2. Set up Firestore

```bash
# Create a Firestore database in Native mode
gcloud firestore databases create --region=us-central

# Create a service account for your application
gcloud iam service-accounts create weather-dashboard

# Grant necessary permissions to the service account
gcloud projects add-iam-policy-binding [PROJECT_ID] \
  --member="serviceAccount:weather-dashboard@[PROJECT_ID].iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding [PROJECT_ID] \
  --member="serviceAccount:weather-dashboard@[PROJECT_ID].iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Create and download a key for the service account
gcloud iam service-accounts keys create key.json \
  --iam-account=weather-dashboard@[PROJECT_ID].iam.gserviceaccount.com
```

### 3. Deploy the Cloud Function for Data Collection

```bash
# Navigate to the function directory
cd functions

# Replace the API key in main.py with your OpenWeatherMap API key
# Edit the main.py file to update:
# api_key = "YOUR_OPENWEATHERMAP_API_KEY"

# Deploy the Cloud Function
gcloud functions deploy fetch_weather_data \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --service-account=weather-dashboard@[PROJECT_ID].iam.gserviceaccount.com

# Set up a Cloud Scheduler job to trigger the function every hour
gcloud scheduler jobs create http weather-data-collection \
  --schedule="0 * * * *" \
  --uri="https://[REGION]-[PROJECT_ID].cloudfunctions.net/fetch_weather_data" \
  --http-method=GET
```

### 4. Set up the Analytics VM

```bash
# Create a storage bucket for analytics results
gcloud storage buckets create gs://weather-analytics-[PROJECT_ID]

# Create a VM instance with the startup script
gcloud compute instances create weather-analytics \
  --machine-type=e2-small \
  --zone=us-central1-a \
  --service-account=weather-dashboard@[PROJECT_ID].iam.gserviceaccount.com \
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

# Build and push the Docker image
docker build -t gcr.io/[PROJECT_ID]/weather-dashboard:latest .
gcloud auth configure-docker
docker push gcr.io/[PROJECT_ID]/weather-dashboard:latest

# Update the image name in deployment.yaml to match your project ID
# Edit the deployment.yaml file and update:
# image: gcr.io/[PROJECT_ID]/weather-dashboard:latest

# Deploy the application
kubectl apply -f deployment.yaml

# Get the external IP address of your service
kubectl get service weather-dashboard-service
```

## Troubleshooting

- **Dashboard not loading**: Check the external IP and ensure GKE services are running with `kubectl get pods`
- **Missing weather data**: Verify Cloud Function is executing via Cloud Scheduler logs
- **No analytics visualizations**: Check VM logs with `gcloud compute ssh weather-analytics --command="cat /var/log/weather-analytics.log"

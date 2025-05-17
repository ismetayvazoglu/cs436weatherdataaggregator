from flask import Flask, jsonify, render_template
from google.cloud import firestore, storage
from firestore_client import get_firestore_client
import re
from datetime import datetime, timedelta

app = Flask(__name__)
db = get_firestore_client()

@app.route("/")
def index():
    """Serve the main dashboard page"""
    return render_template("index.html")

@app.route("/current")
def get_current_weather():
    """Get the most recent weather data"""
    docs = db.collection("weather-data").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()
    latest = next(docs, None)
    if latest:
        data = latest.to_dict()
        # Ensure timestamp exists to prevent frontend errors
        if "timestamp" not in data or data["timestamp"] is None:
            data["timestamp"] = {"_seconds": int(datetime.now().timestamp())}
        return jsonify(data)
    return jsonify({"error": "No data found"}), 404

@app.route("/history")
def get_all_weather():
    """Get historical weather data (last 100 entries)"""
    docs = db.collection("weather-data").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
    history = []
    for doc in docs:
        data = doc.to_dict()
        # Ensure timestamp exists and is properly formatted
        if "timestamp" not in data or data["timestamp"] is None:
            data["timestamp"] = {"_seconds": int(datetime.now().timestamp())}
        elif not isinstance(data["timestamp"], dict):
            # Convert Firestore timestamp to dictionary format expected by frontend
            data["timestamp"] = {"_seconds": int(data["timestamp"].timestamp())}
        history.append(data)
    return jsonify(history)

@app.route("/average-temperature")
def get_average_temperature():
    """Calculate the average temperature from the past 24 hours"""
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    docs = db.collection("weather-data").where("timestamp", ">", time_threshold).stream()

    temps = [doc.to_dict()["temperature"] for doc in docs]
    if not temps:
        return jsonify({"error": "No data found"}), 404

    average_temp = sum(temps) / len(temps)
    return jsonify({"average_temperature": round(average_temp, 2)})

@app.route("/temperature-trend")
def get_temperature_trend():
    """Get the latest temperature trend image from Cloud Storage"""
    try:
        # Initialize the Storage client
        storage_client = storage.Client()
        
        # Get the bucket
        bucket = storage_client.bucket("weather-analytics-carbon-inkwell-459718")
        
        # List all blobs in the 'plots' folder
        blobs = list(bucket.list_blobs(prefix="plots/"))
        
        # Filter only PNG files
        png_blobs = [blob for blob in blobs if blob.name.endswith(".png")]
        
        if not png_blobs:
            return jsonify({"error": "No temperature trend images found"}), 404
        
        # Extract timestamps from filenames and find the most recent one
        latest_blob = None
        latest_timestamp = None
        
        for blob in png_blobs:
            # Extract timestamp from filename like "temperature_trends_20250515_203028.png"
            match = re.search(r'temperature_trends_(\d{8})_(\d{6})\.png', blob.name)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                timestamp_str = f"{date_str}_{time_str}"
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if latest_timestamp is None or timestamp > latest_timestamp:
                    latest_timestamp = timestamp
                    latest_blob = blob
        
        if latest_blob is None:
            return jsonify({"error": "No valid temperature trend images found"}), 404
        
        # Generate a signed URL for the latest blob
        # This URL can be used directly in an <img> tag
        signed_url = latest_blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="GET"
        )
        
        return jsonify({
            "image_url": signed_url,
            "image_name": latest_blob.name,
            "timestamp": latest_timestamp.isoformat() if latest_timestamp else None
        })
    
    except Exception as e:
        print(f"Error fetching temperature trend: {str(e)}")
        return jsonify({"error": f"Failed to fetch temperature trend: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
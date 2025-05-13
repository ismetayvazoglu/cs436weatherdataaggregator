from flask import Flask, jsonify, render_template
from google.cloud import firestore
from firestore_client import get_firestore_client
from datetime import datetime, timedelta

app = Flask(__name__)
db = get_firestore_client()

@app.route("/")
def index():
    """Serve the main dashboard page"""
    return render_template("index.html")

@app.route("/current")
def get_current_weather():
    docs = db.collection("weather-data").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()
    latest = next(docs, None)
    if latest:
        return jsonify(latest.to_dict())
    return jsonify({"error": "No data found"}), 404

@app.route("/history")
def get_all_weather():
    docs = db.collection("weather-data").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
    return jsonify([doc.to_dict() for doc in docs])

@app.route("/average-temperature")
def get_average_temperature():
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    docs = db.collection("weather-data").where("timestamp", ">", time_threshold).stream()

    temps = [doc.to_dict()["temperature"] for doc in docs]
    if not temps:
        return jsonify({"error": "No data found"}), 404

    average_temp = sum(temps) / len(temps)
    return jsonify({"average_temperature": round(average_temp, 2)})

if __name__ == "__main__":
    app.run(debug=True)
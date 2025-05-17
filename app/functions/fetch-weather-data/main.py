import requests
from google.cloud import firestore
from datetime import datetime

def fetch_weather_data(request):
    city = "Istanbul"
    api_key = "11340a5fa91dbf969597f54bbce7e680"  # my own api key

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    data = response.json()

    db = firestore.Client()
    weather_ref = db.collection("weather-data")

    weather_ref.add({
        "city": city,
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"],
        "pressure": data["main"]["pressure"],
        "conditions": data["weather"][0]["description"],
        "timestamp": firestore.SERVER_TIMESTAMP  # Use Firestore's server timestamp
    })

    return "Weather data fetched and stored."
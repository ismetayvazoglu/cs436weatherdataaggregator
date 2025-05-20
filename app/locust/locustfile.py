from locust import HttpUser, task, between
import random
import time

class WeatherDashboardUser(HttpUser):
    # Wait between 3 and 10 seconds between tasks
    wait_time = between(3, 10)
    
    def on_start(self):
        # Simulate a user visiting the dashboard
        self.client.get("/")
    
    @task(5)
    def view_dashboard(self):
        # Main dashboard view - highest frequency task
        self.client.get("/")
    
    @task(3)
    def get_current_weather(self):
        # Get current weather data
        self.client.get("/current")
    
    @task(2)
    def get_weather_history(self):
        # Get historical weather data
        self.client.get("/history")
    
    @task(2)
    def get_average_temperature(self):
        # Get average temperature
        self.client.get("/average-temperature")
    
    @task(1)
    def get_temperature_trend(self):
        # Get temperature trend image
        # This is the most resource-intensive operation
        self.client.get("/temperature-trend")
    
    @task
    def random_page_flow(self):
        # Simulate a user browsing through different endpoints in sequence
        self.client.get("/")
        time.sleep(2)
        self.client.get("/current")
        time.sleep(1)
        self.client.get("/history")
        time.sleep(2)
        self.client.get("/average-temperature")
        if random.random() > 0.5:  # 50% chance to view temperature trend
            time.sleep(3)
            self.client.get("/temperature-trend")
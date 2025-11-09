import requests
from datetime import datetime
from config import AQICN_URL, AQICN_TOKEN, CITIES
from backend.aqi_utils import get_aqi_category
import time

FLASK_API_URL = "http://127.0.0.1:5000" # The Flask server

def fetch_air_quality(city):
    """Fetch and store AQI data for a given city using the WAQI API"""
    
    if AQICN_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print(f"Error: API Token in config.py is not set. Please get a token from https://aqicn.org/feed/token/")
        time.sleep(60) # Wait a minute before retrying
        return None

    api_url = f"{AQICN_URL}/feed/{city}/?token={AQICN_TOKEN}"
    
    try:
        res = requests.get(api_url, timeout=10)
        res.raise_for_status()
        data = res.json()

        # --- WAQI API Error Checking ---
        if data.get("status") != "ok":
            print(f"Error: API returned status '{data.get('status')}' for {city}. Message: {data.get('data')}")
            return None

        aqi_data = data.get("data", {})
        aqi_value = aqi_data.get("aqi")
        
        if aqi_value is None or aqi_value == "-":
            print(f"Error: No AQI value found for {city}.")
            return None
        
        aqi_value = float(aqi_value)
        
        # --- Safely get individual pollutant values ---
        # The .get("v", 0.0) ensures that if a pollutant is missing, we log 0.0
        iaqi = aqi_data.get("iaqi", {})
        pm25 = iaqi.get("pm25", {}).get("v", 0.0)
        pm10 = iaqi.get("pm10", {}).get("v", 0.0)
        co_raw = iaqi.get("co", {}).get("v", 0.0) # WAQI CO is in ppm
        no2 = iaqi.get("no2", {}).get("v",0.0)
        o3 = iaqi.get("o3", {}).get("v", 0.0)
        so2 = iaqi.get("so2", {}).get("v", 0.0)

        category = get_aqi_category(aqi_value)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create the record for our database
        record = (timestamp, city, pm25, pm10, co_raw, no2, o3, so2, aqi_value, category)
        
        try:
            requests.post(f"{FLASK_API_URL}/add_data", json={"record": record}, timeout=5)
            print(f"[{timestamp}] {city} → AQI {round(aqi_value,1)} ({category}) [Logged via API]")
            return record
        except requests.exceptions.RequestException as e:
            print(f"Error: Could not log data to API for {city}: {e}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error in fetch_air_quality for {city} (API call): {e}")
        return None
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error parsing API data for {city}: {e}")
        return None


if __name__ == "__main__":
    print("Starting background fetcher...")
    print(f"Data will be sent to Flask API at {FLASK_API_URL}")
    while True:
        try:
            for city in CITIES:
                fetch_air_quality(city)
                time.sleep(2) # Small delay (2s) to avoid API rate-limiting
            print("✅ Cycle complete. Waiting for next run (15 minutes)...")
        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
        
        time.sleep(900)  # every 15 minutes
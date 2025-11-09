# AQI-Detector

## Clone the repo

git clone [https://github.com/PraneethUpadhya195/AQI-Detector](https://github.com/PraneethUpadhya195/AQI-Detector)<br>
cd your-repo-name

## Install requirements

pip install flask streamlit pandas numpy matplotlib requests

## Setup config.py

DB_NAME = "YOUR_DB_NAME.db"<br>
AQICN_TOKEN = "YOUR_TOKEN"<br>
AQICN_URL = "https://api.waqi.info"<br>
CITIES = ["Delhi", "Mumbai", "Chennai", "Kolkata", "Bengaluru", "London", "New York"]<br>

## Steps to run

1. python -m backend.app
2. python -m backend.aqi_fetcher
3. streamlit run frontend/dashboard.py

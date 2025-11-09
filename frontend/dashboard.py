import streamlit as st
import pandas as pd
import numpy as np
import requests # Used to call our Flask API
import matplotlib.pyplot as plt

# Add the parent directory (root of the project) to the Python path
# This allows us to import 'config' from the root folder
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CITIES # We only need the city list

# --- CONFIG ---
FLASK_API_URL = "http://127.0.0.1:5000/get_data"

# Setup
st.set_page_config(page_title="Global AQI Dashboard", page_icon="🌍", layout="wide")
st.title("☁️ Global Air Quality Monitoring Dashboard")
st.caption("Powered by the WAQI API (aqicn.org) • Python + Flask + SQLite + NumPy")

# Sidebar controls
city = st.sidebar.selectbox("🌆 Select City", CITIES)
refresh_rate = st.sidebar.slider("Auto-refresh every (seconds)", 30, 300, 120)

# Universal auto-refresh
st.markdown(
    f"""
    <meta http-equiv="refresh" content="{refresh_rate}">
    """,
    unsafe_allow_html=True
)

# --- DATA FETCHING ---
@st.cache_data(ttl=60) # Cache data for 60 seconds
def fetch_data_from_api(selected_city):
    """Fetches data from our Flask API, not the DB."""
    try:
        response = requests.get(FLASK_API_URL, params={"city": selected_city, "limit": 100}, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame.from_records(data)
        # Ensure all numeric columns are correctly typed
        for col in ['pm25', 'pm10', 'co', 'no2', 'o3', 'so2', 'aqi']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except requests.exceptions.ConnectionError:
        st.error(f"**Connection Error:** Could not connect to the Flask API at `{FLASK_API_URL}`. Is the backend server (`app.py`) running?")
        return pd.DataFrame() # Return empty DF
    except Exception as e:
        st.error(f"An error occurred while fetching data: {e}")
        return pd.DataFrame()

df = fetch_data_from_api(city)

if df.empty:
    st.warning(f"No AQI data found for {city}. Waiting for new data from the fetcher...")
    st.info("Note: This app uses real-time ground station data from aqicn.org.")
    st.stop()

# NumPy-based analysis
aqi_values = np.array(df["aqi"].dropna())
pm25_values = np.array(df["pm25"].dropna()) 
pm10_values = np.array(df["pm10"].dropna())

# Handle empty arrays after dropna()
if aqi_values.size == 0:
    st.warning(f"No valid AQI numbers found for {city} to analyze.")
    st.stop()

mean_aqi = np.mean(aqi_values)
max_aqi = np.max(aqi_values)
std_aqi = np.std(aqi_values)

# Check for correlation
corr_pm = np.nan
common_indices = df['pm25'].notna() & df['pm10'].notna()
if common_indices.sum() > 1:
    corr_pm = np.corrcoef(df.loc[common_indices, 'pm25'], df.loc[common_indices, 'pm10'])[0, 1]


latest = df.iloc[0]
aqi = round(latest["aqi"],1)
category = latest["category"]

# --- SIMPLIFIED COLOR MAP ---
# We now only need the US EPA categories
def get_aqi_color(category):
    return {
        "Good": "#00e400",
        "Moderate": "#ffde33",
        "Unhealthy (Sensitive)": "#ff9933",
        "Unhealthy": "#cc0033",
        "Very Unhealthy": "#660099",
        "Hazardous": "#7e0023"
    }.get(category, "#cccccc") # Default grey

aqi_color = get_aqi_color(category)

# Layout
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.markdown(
        f"<div style='padding:1.5rem;border-radius:1rem;background-color:{aqi_color};"
        f"text-align:center;color:white;font-size:1.5rem;'>"
        f"<b>{city}</b><br>AQI: <b style='font-size:2rem;'>{aqi}</b><br><i>{category}</i></div>",
        unsafe_allow_html=True)
with col2:
    st.metric("Mean AQI", round(mean_aqi,1))
    st.metric("Max AQI", int(max_aqi))
with col3:
    st.write("### 🧾 Last 5 Readings")
    st.dataframe(df.head(5)[["timestamp","pm25","pm10","aqi","category"]])

st.divider()

# NumPy Stats
st.write("### 📈 NumPy-based Analysis (Last 100 Readings)")
col4, col5, col6, col7 = st.columns(4)
col4.metric("Mean AQI", round(mean_aqi, 2))
col5.metric("Max AQI", int(max_aqi))
col6.metric("Std Dev", round(std_aqi, 2))
col7.metric("PM2.5↔PM10 Corr.", round(corr_pm, 2), help="Correlation between PM2.5 and PM10")

# Trend Plot
st.write(f"### 📊 AQI Trend for {city}")
fig, ax = plt.subplots()
# Reverse data for plotting (oldest to newest)
df_plot = df.iloc[::-1].reset_index()

ax.plot(df_plot["timestamp"], df_plot["aqi"], label="Raw AQI", alpha=0.4)
window = 5
if len(aqi_values) >= window:
    # Convolve expects newest data first, so use aqi_values (which is newest-to-oldest)
    # but then reverse the result for plotting
    smooth_aqi = np.convolve(aqi_values, np.ones(window)/window, mode='valid')[::-1]
    ax.plot(df_plot["timestamp"].iloc[window-1:], smooth_aqi, label=f"{window}-pt Smoothed AQI", color="blue", linewidth=2)
else:
    ax.plot(df_plot["timestamp"], df_plot["aqi"], label="Smoothed AQI", color="blue", linewidth=2)

ax.plot(df_plot["timestamp"], df_plot["pm25"], label="PM2.5", linestyle="--", alpha=0.7)
ax.plot(df_plot["timestamp"], df_plot["pm10"], label="PM10", linestyle="--", alpha=0.7)

# Improve x-axis readability
if len(df_plot) > 10:
    ax.set_xticks(ax.get_xticks()[::max(1, len(ax.get_xticks()) // 10)])
plt.xticks(rotation=45)
ax.legend()
st.pyplot(fig)

# Category Distribution
st.write("### 📊 AQI Category Distribution (Last 100)")
st.bar_chart(df["category"].value_counts())
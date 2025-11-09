# This file is now MUCH simpler.
# The WAQI API gives us the final AQI, so we only need to map it to a category.
# WAQI uses the standard US EPA breakpoints.

def get_aqi_category(aqi):
    """Gets the category based on the US EPA standard"""
    try:
        aqi = int(aqi)
    except (ValueError, TypeError):
        return "Unknown" # Handle cases where AQI might be None or non-numeric
        
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy (Sensitive)"
    elif aqi <= 200:
        return "Unhealthy"
    elif aqi <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"
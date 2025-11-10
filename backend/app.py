from flask import Flask, request, jsonify
# Updated import to get the new function
from backend.database import save_aqi_record, get_all_aqi_records
from backend.aqi_calculator import compute_final_aqi
import json

app = Flask(__name__)

# --- API Endpoints ---

@app.route('/api/calculate_manual', methods=['POST'])
def handle_manual_calculation():
    """
    Endpoint for the Manual Calculator.
    Receives raw pollutant data, calculates AQI,
    saves it, and returns the result.
    """
    data = request.json
    print(f"Received manual data: {data}")

    # Pass all 8 raw pollutant values to the calculator
    raw_values = {
        'pm25': data.get('pm25'),
        'pm10': data.get('pm10'),
        'no2': data.get('no2'),
        'o3': data.get('o3'),
        'co': data.get('co'),
        'so2': data.get('so2'),
        'nh3': data.get('nh3'),
        'pb': data.get('pb')
    }

    result = compute_final_aqi(raw_values)
    
    result['source'] = data.get('source', 'manual_entry')
    
    # --- THIS IS THE FIX ---
    # We pass a .copy() so the database function
    # doesn't add an '_id' to our 'result' variable.
    save_aqi_record(result.copy())
    # --- END OF FIX ---

    return jsonify(result)

@app.route('/api/get_all_data', methods=['GET'])
def get_all_data():
    """
    *** NEW ENDPOINT ***
    Endpoint for the Dash history table.
    Fetches all recent records from the database.
    """
    records = get_all_aqi_records(limit=100)
    return jsonify(records)


# This endpoint is ready for your IoT sensor in Phase 2
@app.route('/api/submit_sensor_data', methods=['POST'])
def handle_sensor_data():
    """
    Endpoint for Phase 2 (IoT Sensor).
    """
    data = request.json
    print(f"Received sensor data: {data}")
    
    # --- THIS IS THE FIX ---
    # That line was a placeholder. This is the real code.
    # It's identical to the manual calculation,
    # just with a different source name.
    raw_values = {
        'pm25': data.get('pm25'),
        'pm10': data.get('pm10'),
        'no2': data.get('no2'),
        'o3': data.get('o3'),
        'co': data.get('co'),
        'so2': data.get('so2'),
        'nh3': data.get('nh3'),
        'pb': data.get('pb')
    }
    # --- END OF FIX ---
    
    result = compute_final_aqi(raw_values)
    result['source'] = data.get('source', 'iot_sensor')
    
    save_aqi_record(result)
    
    return jsonify({"status": "success", "message": "Record saved"}), 200


# --- Main execution ---
if __name__ == '__main__':
    print(f"Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
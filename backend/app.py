from flask import Flask, jsonify, request
from backend.database import init_db, fetch_latest, insert_data

app = Flask(__name__)

@app.route("/get_data", methods=["GET"])
def get_data():
    """API endpoint to get the latest AQI data."""
    city = request.args.get("city")
    limit = request.args.get("limit", 100, type=int)
    data = fetch_latest(city, limit)
    return jsonify(data)

@app.route("/add_data", methods=["POST"])
def add_data():
    """API endpoint to add a new AQI record. Used by the fetcher."""
    data = request.get_json()
    record = data.get('record')
    
    if record and len(record) == 10:
        try:
            insert_data(record)
            return jsonify({"status": "success", "message": "Record added"}), 201
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "Invalid data format"}), 400

@app.route("/update_city", methods=["GET"])
def update_city():
    """
    DEPRECATED: This endpoint was for on-demand fetching.
    The background fetcher is preferred.
    """
    return jsonify({"status": "error", "message": "This endpoint is deprecated. Use the background fetcher."}), 404


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Starting Flask server on http://127.0.0.1:5000 ...")
    app.run(debug=True, host='127.0.0.1', port=5000)
import pymongo
from datetime import datetime
from .config import MONGO_URI

# Set up the database client
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client["aqi_project_db"] # Use a specific DB name
    aqi_collection = db["aqi_data"]  # Use a specific collection name
    
    # Test the connection
    client.server_info() 
    print(f"Connected to MongoDB. Using database: {db.name}")

except Exception as e:
    print(f"An unknown error occurred during DB initialization: {e}")
    exit(1)


def save_aqi_record(record_data):
    """
    Saves a single AQI record (a Python dict) to the database.
    """
    try:
        record_data['timestamp'] = datetime.utcnow()
        aqi_collection.insert_one(record_data)
        print(f"Record saved for source: {record_data.get('source')}")
        return True
    except Exception as e:
        print(f"Error saving record to MongoDB: {e}")
        return False

def get_all_aqi_records(limit=100):
    """
    *** NEW FUNCTION ***
    Fetches the latest 'limit' records from ALL sources.
    This is for the main history table.
    """
    try:
        # Find all records ({}), exclude "_id", sort by timestamp descending
        records = aqi_collection.find(
            {}, 
            {"_id": 0}
        ).sort("timestamp", pymongo.DESCENDING).limit(limit)
        
        return list(records)
    except Exception as e:
        print(f"Error fetching all records from MongoDB: {e}")
        return []

# This function is no longer used by the new frontend,
# but we can keep it for future use (e.g., if you want to filter by source again)
def get_latest_aqi_records(source, limit=100):
    """
    Fetches the latest 'limit' records for a specific 'source'.
    """
    try:
        records = aqi_collection.find(
            {"source": source},
            {"_id": 0}
        ).sort("timestamp", pymongo.DESCENDING).limit(limit)
        
        return list(records)
    except Exception as e:
        print(f"Error fetching records from MongoDB: {e}")
        return []
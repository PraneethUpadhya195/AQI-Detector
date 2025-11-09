import sqlite3
from config import DB_NAME

def get_db_connection():
    """Establishes a connection to the DB, waiting if it's locked."""
    conn = sqlite3.connect(DB_NAME, timeout=10.0)
    # This line makes the db return dicts instead of tuples,
    # which works much better with jsonify
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Initializes the database and creates the 'aqi' table if it doesn't exist."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS aqi (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 timestamp TEXT,
                 city TEXT,
                 pm25 REAL,
                 pm10 REAL,
                 co REAL,
                 no2 REAL,
                 o3 REAL,
                 so2 REAL,
                 aqi REAL,
                 category TEXT)''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def insert_data(record):
    """Inserts a single data record into the database."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO aqi (timestamp, city, pm25, pm10, co, no2, o3, so2, aqi, category)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', record)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Database insert error: {e}")

def fetch_latest(city=None, limit=100):
    """Fetches the latest data records, optionally filtered by city."""
    conn = get_db_connection()
    c = conn.cursor()
    if city:
        c.execute("SELECT * FROM aqi WHERE city=? ORDER BY id DESC LIMIT ?", (city, limit))
    else:
        c.execute("SELECT * FROM aqi ORDER BY id DESC LIMIT ?", (limit,))
    
    # .fetchall() will return a list of Row objects (like dicts)
    rows = c.fetchall() 
    conn.close()
    
    # Convert Row objects to standard dicts for jsonify
    return [dict(row) for row in rows]
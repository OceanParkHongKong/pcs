import sqlite3
from datetime import datetime, timedelta
import os


def cleanup_old_data(conn, days=10):
    """
    Delete data entries that are older than specified days from the current database
    Args:
        conn: Database connection
        days (int): Number of days to keep. Data older than this will be deleted
    """
    try:
        cursor = conn.cursor()
        # Calculate the cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Delete records older than the cutoff date
        cursor.execute('DELETE FROM traffic WHERE timestamp < ?', (cutoff_date,))
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"Deleted {deleted_count} records older than {cutoff_date}")
        
    except sqlite3.Error as e:
        print(f"Database error during cleanup: {str(e)}")
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
    finally:
        cursor.close()
        
# Replace the static db_file with a function call
db_file = "people_count_database.db"

# Function to connect to the SQLite database
def connect_db(db_file=db_file):
    conn = sqlite3.connect(db_file)
    return conn

# Function to create (if not exists) a table and to clean it if needed
def setup_or_clean_db(conn, clean=False):
    cursor = conn.cursor()
    # Create the table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS traffic (
        id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL,
        in_count INTEGER NOT NULL,
        out_count INTEGER NOT NULL,
        region_count INTEGER NULL,
        camera_name TEXT NOT NULL,
        ip TEXT NULL
    )
    ''')
    
    # Create index for better query performance
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_camera_name_timestamp 
    ON traffic (camera_name, timestamp)
    ''')
    
    # If the 'clean' parameter is True, clean the table
    if clean:
        cursor.execute('DELETE FROM traffic')
        conn.commit()
    
    cursor.close()

def insert_traffic_data(conn, in_count, out_count, region_count, camera_name, ip):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current time in ISO format
    insert_traffic_data_with_timestamp(conn, in_count, out_count, region_count, camera_name, ip, current_time)

def insert_traffic_data_with_timestamp(conn, in_count, out_count, region_count, camera_name, ip, timestamp):
    """
    Insert traffic data with a specific timestamp instead of current time.
    
    Args:
        conn: Database connection
        in_count: Number of people entering
        out_count: Number of people exiting  
        region_count: Current count in region
        camera_name: Name of the camera
        ip: IP address
        timestamp: Custom timestamp string in 'YYYY-MM-DD HH:MM:SS' format
    """
    def perform_insert():
        cursor.execute('''
        INSERT INTO traffic (timestamp, in_count, out_count, region_count, camera_name, ip)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, in_count, out_count, region_count, camera_name, ip))
        conn.commit()

    try:
        cursor = conn.cursor()
        perform_insert()
    except sqlite3.OperationalError as e:
        if "no such table: traffic" in str(e):
            setup_or_clean_db(conn)  # Call setup_db to create the table
            
            perform_insert()  # Retry the insert after setting up the database
        else:
            raise  # Re-raise the exception if it's not about a missing table
    finally:
        cursor.close()

def explain_query_plan(conn, query):
    """
    Explains the query execution plan for the given SQL query.

    :param conn: SQLite database connection object.
    :param query: SQL query to be explained.
    """
    cursor = conn.cursor()
    
    # Use EXPLAIN QUERY PLAN to get the query execution plan
    cursor.execute(f"EXPLAIN QUERY PLAN {query}")
    
    # Fetch and print the results
    plan = cursor.fetchall()
    for row in plan:
        print(row)
                
# def test_to_setup():

    # Set up the database and clean it if you pass True
    # setup_or_clean_db(conn, clean=True)  # Pass True if you want to clean the table

    # Insert a new row into the traffic table
    # insert_traffic_data(conn, in_count=5, out_count=3, region_count=0, camera_name='Camera 1', ip='192.168.1.1')

    # Don't forget to close the database connection when you're done
    # conn.close()

# Example usage
# conn = connect_db(db_file)
last_call_time = 0
import time

_last_in_count, _last_out_count = 0, 0

def insert_people_count_result_interval(in_count, out_count, region_count, camera_name, ip, interval=10):
    global last_call_time, _last_in_count, _last_out_count
    current_time = int(time.time())  # Convert to integer to ignore milliseconds
    
    # Extract seconds from the current time and check if it ends with 0
    if int(time.strftime('%S', time.localtime(current_time))) % 10 == 0:
        # Check if this is the first call or if the last call was at least 10 seconds ago
        if last_call_time is None or current_time - last_call_time >= 10:
            # for debug 
            # if last_call_time is not None and current_time - last_call_time >= 12:
            #     print(f"!!!!!!!!  bug? should be 10 seconds interval: {current_time - last_call_time}, {camera_name}")     
            conn = connect_db(db_file)
            insert_traffic_data(conn, (in_count - _last_in_count), (out_count - _last_out_count), region_count, camera_name, ip)
            print (f"insert_traffic_data: {in_count - _last_in_count}, {out_count - _last_out_count}, {region_count}, {camera_name}, {ip}")
            
            conn.close
            _last_in_count = in_count
            _last_out_count = out_count
            last_call_time = current_time
    
# test_to_setup()
# columns = ('camera_name', 'timestamp')
# create_index (conn, 'idx_camera_name_timestamp', columns = ('camera_name', 'timestamp'))

# query = "SELECT * FROM traffic WHERE camera_name = 'Camera1' AND timestamp >= '2024-06-26 12:00:00'"
# explain_query_plan (conn, query)



# Example usage:
  # Delete data older than 1 day
import sqlite3
from datetime import datetime

db_file = 'people_count_database.db'

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
    
    # If the 'clean' parameter is True, clean the table
    if clean:
        cursor.execute('DELETE FROM traffic')
        conn.commit()
    
    cursor.close()

# Function to insert a row into the traffic table
def insert_traffic_data(conn, in_count, out_count, region_count, camera_name, ip):
    cursor = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current time in ISO format
    cursor.execute('''
    INSERT INTO traffic (timestamp, in_count, out_count, region_count, camera_name, ip)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (current_time, in_count, out_count, region_count, camera_name, ip))
    
    conn.commit()  # Save (commit) the changes
    cursor.close()

def create_index(conn, index_name, columns):
    """
    Creates an index on the specified table and columns in a SQLite database.

    :param conn: SQLite database connection object.
    :param index_name: Name of the index to be created.
    :param table_name: Name of the table on which to create the index.
    :param columns: A tuple or list of column names to be included in the index.
    """
    # Join columns into a string separated by commas or use the string directly
    if isinstance(columns, str):
        columns_str = columns
    else:
        columns_str = ', '.join(columns)

    # Form the SQL command
    sql_command = f"CREATE INDEX {index_name} ON traffic ({columns_str});"
    
    cursor = conn.cursor()
    
    try:
        # Execute the SQL command to create the index
        cursor.execute(sql_command)
        print(f"Index {index_name} created successfully on table traffic.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        
def test_to_setup():

    # Set up the database and clean it if you pass True
    setup_or_clean_db(conn, clean=True)  # Pass True if you want to clean the table

    # Insert a new row into the traffic table
    insert_traffic_data(conn, in_count=5, out_count=3, region_count=0, camera_name='Camera 1', ip='192.168.1.1')

    # Don't forget to close the database connection when you're done
    conn.close()

# Example usage
conn = connect_db(db_file)
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
            insert_traffic_data(conn, (in_count - _last_in_count), (out_count - _last_out_count), region_count, camera_name, ip)
            _last_in_count = in_count
            _last_out_count = out_count
            last_call_time = current_time

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
            
#enable WAL (Write-Ahead Logging) mode in SQLite
#otherwise, running on mac mini database malformed error when get_last_result in web inspect:
# 2024-09-10 16:09:12 2024-09-10 08:09:12,222 - ERROR - Database error: database disk image is malformed
def enableWAL (conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    conn.commit()

# test_to_setup()
# columns = ('camera_name', 'timestamp')
# create_index (conn, 'idx_camera_name_timestamp', columns = ('camera_name', 'timestamp'))
# query = "SELECT * FROM traffic WHERE camera_name = 'Camera1' AND timestamp >= '2024-06-26 12:00:00'"

# create_index (conn, 'idx_timestamp', columns = ('timestamp'))
# query = "SELECT timestamp, in_count, out_count, region_count, camera_name FROM traffic ORDER BY timestamp DESC, camera_name ASC LIMIT 5"
# query = "SELECT timestamp, in_count, out_count, region_count, camera_name FROM traffic ORDER BY timestamp DESC LIMIT 5"
# explain_query_plan (conn, query)
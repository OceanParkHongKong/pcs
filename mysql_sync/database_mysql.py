import mysql.connector
from datetime import datetime
import time
import json

def load_config():
    with open('config_db.json', 'r') as file:
        return json.load(file)

db_config = load_config()

# Function to connect to the MySQL database
def connect_db():
    conn = mysql.connector.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database']
    )
    return conn

# Function to create (if not exists) a table and to clean it if needed
def setup_or_clean_db(conn, clean=False):
    cursor = conn.cursor()
    # Create the table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS traffic (
        id INT AUTO_INCREMENT PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL,
        in_count INT NOT NULL,
        out_count INT NOT NULL,
        region_count INT NULL,
        camera_name VARCHAR(255) NOT NULL,
        ip VARCHAR(255) NULL
    )
    ''')
    
    # insert_traffic_data (conn, 0, 0, 0, "first", "ip_url") # to let get_last_result work
    
    # If the 'clean' parameter is True, clean the table
    if clean:
        cursor.execute('DELETE FROM traffic')
        conn.commit()
    
    cursor.close()


def create_index_camera_name_timestamp(conn):
    try:
        # Creating a cursor object using the connection
        cursor = conn.cursor()
        # The SQL command to create the index
        sql = "CREATE INDEX idx_camera_name_timestamp ON traffic (camera_name, timestamp);"
        # Executing the SQL command
        cursor.execute(sql)
        # Committing the transaction
        conn.commit()
        print("Index created successfully.")
        
    except mysql.connector.Error as err:
        # Rolling back in case of error
        conn.rollback()
        print(f"Error: {err}")
    finally:
        # Closing the cursor
        cursor.close()

def create_index_timestamp(conn):
    try:
        # Creating a cursor object using the connection
        cursor = conn.cursor()
        # The SQL command to create the index on the timestamp column
        sql = "CREATE INDEX idx_timestamp ON traffic (timestamp);"
        # Executing the SQL command
        cursor.execute(sql)
        # Committing the transaction
        conn.commit()
        print("Index on timestamp created successfully.")
        
    except mysql.connector.Error as err:
        # Rolling back in case of error
        conn.rollback()
        print(f"Error: {err}")
    finally:
        # Closing the cursor
        cursor.close()

import mysql.connector

def drop_index_timestamp(conn):
    try:
        # Creating a cursor object using the connection
        cursor = conn.cursor()
        # The SQL command to drop the index on the timestamp column
        sql = "DROP INDEX idx_timestamp ON traffic;"
        # Executing the SQL command
        cursor.execute(sql)
        # Committing the transaction
        conn.commit()
        print("Index on timestamp dropped successfully.")
        
    except mysql.connector.Error as err:
        # Rolling back in case of error
        conn.rollback()
        print(f"Error: {err}")
    finally:
        # Closing the cursor
        cursor.close()

import mysql.connector
def explain_query(conn, query):
    try:
        # Creating a cursor object using the connection
        cursor = conn.cursor()
        # The SQL command to explain the query
        explain_sql = f"EXPLAIN {query}"
        # Executing the EXPLAIN command
        cursor.execute(explain_sql)
        # Fetching the results
        results = cursor.fetchall()
        # Getting column names
        columns = cursor.column_names
        # Printing the results
        print("Execution plan:")
        for column in columns:
            print(f"{column:20}", end="")
        print()
        
        for row in results:
            for value in row:
                print(f"{str(value):20}", end="")
            print()
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        
    finally:
        # Closing the cursor
        cursor.close()

# Function to insert a row into the traffic table
def insert_traffic_data(conn, in_count, out_count, region_count, camera_name, ip):
    cursor = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current time in ISO format
    cursor.execute('''
    INSERT INTO traffic (timestamp, in_count, out_count, region_count, camera_name, ip)
    VALUES (%s, %s, %s, %s, %s, %s)
    ''', (current_time, in_count, out_count, region_count, camera_name, ip))
    
    conn.commit()  # Save (commit) the changes
    cursor.close()

last_call_time = 0
_last_in_count, _last_out_count = 0, 0

def insert_people_count_result_interval(in_count, out_count, region_count, camera_name, ip, interval=10):
    global last_call_time, _last_in_count, _last_out_count
    current_time = time.time()
    
    # Extract seconds from the current time and check if it ends with 0
    if int(time.strftime('%S', time.localtime(current_time))) % 10 == 0:
        # Check if this is the first call or if the last call was at least 10 seconds ago
        if last_call_time == 0 or current_time - last_call_time >= interval:      
            insert_traffic_data(conn, (in_count - _last_in_count), (out_count - _last_out_count), region_count, camera_name, ip)
            _last_in_count = in_count
            _last_out_count = out_count
            last_call_time = current_time

conn = connect_db() # the 'conn' used by 'insert_people_count_result_interval' function
# setup_or_clean_db(conn)
# conn.close()
# Don't forget to close the database connection when you're done


# create_index_camera_name_timestamp (conn)

# query = "SELECT * FROM traffic WHERE camera_name = 'Camera1'"
# explain_query(conn, query)

# create_index_timestamp (conn)
# drop_index_timestamp(conn)
# query = "SELECT * FROM traffic ORDER BY timestamp DESC LIMIT 5"
# query = "SELECT timestamp, in_count, out_count, region_count, camera_name FROM traffic ORDER BY timestamp DESC LIMIT 5"
# query = "SELECT camera_name, SUM(in_count) AS total_in, SUM(out_count) AS total_out, SUM(region_count) AS total_region FROM traffic WHERE timestamp BETWEEN '2024-07-12T10:41:00.000' AND '2024-07-12T10:41:59.999' GROUP BY camera_name;"

# query = "SELECT timestamp, in_count, out_count, region_count, camera_name FROM traffic ORDER BY timestamp DESC, camera_name ASC LIMIT 5"
# query = "SELECT timestamp, in_count, out_count, region_count, camera_name FROM traffic ORDER BY timestamp DESC LIMIT 5"
#explain_query(conn, query)
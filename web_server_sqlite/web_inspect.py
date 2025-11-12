import time
import zlib
import json
import logging
from flask import Flask, Response, request, jsonify, render_template
from flask_httpauth import HTTPTokenAuth
from functools import wraps
from flask import redirect, url_for
import csv
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
import os
import subprocess
import signal
import sqlite3



# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
auth = HTTPTokenAuth(scheme='Bearer')

# Define the token verification spell
@auth.verify_token
def verify_token(token):
    if token == 'secret_token_example' or any(token == user_token for user_token in user_tokens.values()):
        return True
    return False

@auth.error_handler
def custom_unauthorized():
    response = jsonify({
        "error": "Unauthorized",
        "details": "The access token is missing or invalid."
    })
    response.status_code = 401
    return response

# Global dictionary to store user tokens
# for big projects, use redis to store tokens
user_tokens = {}

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.args.get('access_token')  # Assuming the token is sent as a query parameter
        
        if not token:
            # No token provided, return 401 Unauthorized
            return redirect(url_for('index'))
        
        if not verify_token(token):
            # Token is incorrect, return 403 Forbidden
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    
    return decorated_function

# Function to load users from a CSV file
def load_users_from_csv(filename):
    users = {}
    with open(filename, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            username = row['username']
            password = row['password']  # Assuming the password is already hashed
            users[username] = generate_password_hash(password)
    return users

# Load users into a dictionary
users = load_users_from_csv('users.csv')

app.config['SECRET_KEY'] = 'some_secret_token_here'

# Function to verify user and return token
def authenticate_user(username, password):
    if username in users and check_password_hash(users[username], password):
        s = Serializer(app.config['SECRET_KEY'])
        global access_token
        token = s.dumps({'username': username})
        # Store the token in the global dictionary
        user_tokens[username] = token
        return token
    return None

hostIP = "192.168.xxx.xxx"
def read_host_ip_from_config():
    filename = "config_video_feed.json"
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
        global hostIP
        hostIP = data['hostIP']
        logger.info(f"The Host IP retrieved is: {hostIP}")
        return hostIP
    except FileNotFoundError:
        logger.error(f"Alas! The tome '{filename}' cannot be found.")
    except json.JSONDecodeError:
        logger.error(f"Beware! The tome '{filename}' is corrupted and unreadable.")
    except KeyError:
        logger.error("The spell fails! There is no 'hostIP' within the ancient texts.")
    except Exception as e:
        logger.error(f"A pox! An unexpected specter has arisen: {e}")

cameras_group = []

# Add global variable for camera mapping
camera_name_to_id_mapping = {}

def generate_camera_urls(host_ip, config_file='config_cameras_web_inspect.json'):
    with open(config_file, 'r') as file:
        cameras_config = json.load(file)
    
    from collections import defaultdict
    grouped_cameras = defaultdict(list)
    camera_name_to_id = {}  # Add mapping dictionary
    
    for camera in cameras_config:
        # Assuming the prefix is separated by an underscore
        prefix = camera['name'].split('_')[0]
        url = f'http://{host_ip}:5001/video_feed?camera_id={camera["id"]}'
        grouped_cameras[prefix].append({
            'name': camera['name'], 
            'id': camera['id'],  # Include ID in camera data
            'url': url
        })
        camera_name_to_id[camera['name']] = camera['id']  # Build mapping
    
    # Convert defaultdict to a regular dict for JSON serialization
    return dict(grouped_cameras), camera_name_to_id

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.get_json()
        username = data['username']
        password = data['password']
        token = authenticate_user(username, password)
        if token:
            return jsonify({'access_token': token}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    return render_template('login.html')

@app.route('/inspect')
@token_required
# @auth.login_required
def inspect():
    return render_template('inspect.html', 
                         grouped_cameras=cameras_group, 
                         camera_mapping=camera_name_to_id_mapping,  # Pass mapping to template
                         hostIP=hostIP)

import database_sqlite as database


# Define the route and the sacred function
# curl -G "http://localhost:5000/get_last_result" -H "Authorization: Bearer secret_token_example"
@app.route('/get_last_result', methods=['GET'])
@auth.login_required
def get_last_result():
    camera_name = request.args.get('camera_name')
    conn = None
    try:
        conn = database.connect_db()
        cursor = conn.cursor()
        
        if camera_name:
            cursor.execute("""
                SELECT timestamp, in_count, out_count, region_count 
                FROM traffic  
                WHERE camera_name = ?
                ORDER BY timestamp DESC
                LIMIT 5
            """, (camera_name,))
        else:
            cursor.execute("""
                SELECT timestamp, in_count, out_count, region_count, camera_name 
                FROM traffic  
                ORDER BY timestamp DESC
                LIMIT 5
            """)
        
        rows = cursor.fetchall()
        
        if rows:
            results = [{
                "timestamp": row[0],
                "in_count": row[1],
                "out_count": row[2],
                "region_count": row[3],
                "camera_name": row[4] if not camera_name else camera_name
            } for row in rows]
            return jsonify(results)
        else:
            return jsonify({"error": "No results found"}), 404
            
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        return jsonify({"error": "Database error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
# Define the route and the sacred function to record the counting results
# curl -X POST http://localhost:5000/counting-results -H "Content-Type: application/json" -d '{"camera_id": "camera_123", "timestamp": "2024-02-29T09:00:00Z", "in_count": 50, "out_count": 45}'
@app.route('/counting-results', methods=['POST'])
@auth.login_required
def counting_results():
    data = request.get_json()
    camera_id = data.get('camera_id')
    timestamp = data.get('timestamp')
    in_count = data.get('in_count')
    out_count = data.get('out_count')
    
    if camera_id is None or timestamp is None or in_count is None or out_count is None:
        return jsonify({"error": "Missing required parameters"}), 400
    
    conn = database.connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO traffic (camera_name, timestamp, in_count, out_count) 
            VALUES (?, ?, ?, ?)
        """, (camera_id, timestamp, in_count, out_count))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        logger.error(f"Failed to record the counting results: {e}")
        return jsonify({"error": "Failed to record the counting results", "message": str(e)}), 500
    
    cursor.close()
    conn.close()
    logger.info("Counting results recorded successfully.")
    return jsonify({"message": "Counting results recorded successfully"}), 201

# curl -G "http://localhost:5000/counting-results" --data-urlencode "start_time=2024-02-28T00:00:00Z" --data-urlencode "end_time=2024-03-28T23:59:59Z" --data-urlencode "camera_id=CC_Out_Cam2"
# curl -G "http://localhost:5000/counting-results" --data-urlencode "start_time=2024-02-28T00:00:00Z" --data-urlencode "end_time=2024-03-28T23:59:59Z" 
@app.route('/counting-results', methods=['GET'])
@auth.login_required
def retrieve_counting_results():
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    camera_id = request.args.get('camera_id')

    if not start_time or not end_time:
        return jsonify({"error": "start_time and end_time parameters are required"}), 400

    conn = database.connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT * FROM traffic
        WHERE timestamp BETWEEN ? AND ?
    """
    params = [start_time, end_time]

    if camera_id:
        query += " AND camera_name = ?"
        params.append(camera_id)

    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        data = []
        for row in rows:
            data.append({
                "id": row['id'],
                "timestamp": row['timestamp'],
                "in": row['in_count'],
                "out": row['out_count'],
                "camera_id": row['camera_name']
            })

        logger.info("Counting results retrieved successfully.")
        return jsonify({
            "message": "Counting results retrieved successfully.",
            "data": data
        }), 200
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": "Database error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
        
# curl -G "http://localhost:5000/aggregated-counts" --data-urlencode "start_time=2024-02-28T00:00:00Z" --data-urlencode "end_time=2024-03-28T23:59:59Z" --data-urlencode "camera_id=CC_Out_Cam2"
# curl -G "http://localhost:5000/aggregated-counts" --data-urlencode "start_time=2024-02-28T00:00:00Z" --data-urlencode "end_time=2024-03-28T23:59:59Z" 
#   curl -G "http://localhost:5000/aggregated-counts" \
#   --data-urlencode "start_time=2024-04-28 00:00:00" \
#   --data-urlencode "end_time=2024-04-28 23:59:59" \
#   --data-urlencode "camera_id=COL_In_Cam1" \
#   -H "Authorization: Bearer some_secret_token_here"
@app.route('/aggregated-counts', methods=['GET'])
@auth.login_required
def get_aggregated_counts():
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    camera_id = request.args.get('camera_id')

    if not start_time or not end_time:
        return jsonify({"error": "Both start_time and end_time parameters are required."}), 400

    conn = database.connect_db()
    cursor = conn.cursor()

    query = """
        SELECT camera_name, SUM(in_count) as total_in, SUM(out_count) as total_out, SUM(region_count) as total_region
        FROM traffic
        WHERE timestamp BETWEEN ? AND ?
    """
    params = [start_time, end_time]

    if camera_id:
        query += " AND camera_name = ?"
        params.append(camera_id)
    
    query += " GROUP BY camera_name"

    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "camera_id": row[0],
                "total_in": row[1],
                "total_out": row[2],
                "total_region": row[3]
            })

        logger.info("Aggregated counts retrieved successfully.")
        return jsonify({
            "message": "Aggregated counts retrieved successfully.",
            "data": data
        })
    except sqlite3.Error as e:
        logger.error(f"A database error occurred: {e}")
        return jsonify({"error": "A database error occurred.", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/local')
def local():
    return render_template('inspect_local.html', hostIP=hostIP)

VIDEO_FILES_DIRECTORY = os.path.join(app.root_path, 'video_files')

@app.route('/api/video-files', methods=['GET'])
def list_video_files():
    try:
        video_files = [f for f in os.listdir(VIDEO_FILES_DIRECTORY) 
                       if os.path.isfile(os.path.join(VIDEO_FILES_DIRECTORY, f)) and f.endswith('.mp4')]
        return jsonify(video_files)
    except Exception as e:
        logger.error(f"Error listing video files: {e}")
        return jsonify({"error": str(e)}), 500

process = None

def preexec_function():
    os.setsid()

def invoke_main_py(video_filename):
    global process
    if process is not None:
        os.killpg(process.pid, signal.SIGTERM)
        time.sleep(2)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    process = subprocess.Popen([
        'python', 'main.py',
        '--source', "video_files/" + video_filename,
        '--device', 'mps',
        '--yolo-model', "yolov8nano-apr-3-2024-T4.mlmodel",
        '--tracking-method', 'bytetrack',
        '--line-width', '1',
        '--video-port', '6001',
        '--camera-name', video_filename,
        '--in-direction', "border",
        '--points', "[(539, 6),(392, 28),(278, 82),(224, 182),(251, 337),(446, 461),(788, 568),(1153, 605),(1207, 11)]"
    ], preexec_fn=preexec_function)

@app.route('/api/start-people-count', methods=['POST'])
def start_people_count():
    try:
        data = request.get_json()
        file_name = data.get('fileName')
        
        if not file_name:
            return jsonify({"error": "No file name provided"}), 400
        
        invoke_main_py(file_name)
        
        fake_results = {
            "results": [
                {"timestamp": "2023-04-01 10:00:00", "in_count": 5, "out_count": 3, "region_count": 2},
                {"timestamp": "2023-04-01 10:05:00", "in_count": 7, "out_count": 2, "region_count": 4},
            ]
        }
        
        return jsonify(fake_results)
    except json.JSONDecodeError:
        logger.error("Invalid JSON data")
        return jsonify({"error": "Invalid JSON data"}), 400
    except Exception as e:
        logger.error(f"Error starting people count: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/helper')
def manual_counter_helper():
    return render_template('manual_counter.html')

def setup_app():
    global hostIP, camera_name_to_id_mapping
    hostIP = read_host_ip_from_config()
    if hostIP:
        logger.info("Local IP with desired prefix found: %s", hostIP)
    else:
        logger.error("ERROR: No local IP with the desired prefix found.")
    lCameras, camera_name_to_id_mapping = generate_camera_urls(hostIP)  # Unpack both values
    logger.info(f"Grouped Cameras: {lCameras}")
    return lCameras

cameras_group = setup_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")
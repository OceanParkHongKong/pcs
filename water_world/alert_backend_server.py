from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import os
import time
import threading
import alert_monitor
from datetime import datetime, timedelta
import secrets
import hashlib
import jwt
from functools import wraps
from urllib.parse import quote
import traceback
import sqlite3
import requests
from logging_config import setup_logging
from kafka_consumer import AlertKafkaConsumer

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, logger=False, engineio_logger=False, cors_allowed_origins="*")

# Initialize logging
logger = setup_logging('alert_backend_server')

# Load configuration from file
def load_config():
    config_file = 'config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {
        "API_BASE_URL": "http://localhost:5000",
        "JWT_SECRET_KEY": os.environ.get('JWT_SECRET_KEY', 'jwt-key-for-api'),
        "TOKEN_EXPIRATION": 24 * 60 * 60
    }

# Load configuration
config = load_config()

# Use configuration values
API_BASE_URL = config['API_BASE_URL']
JWT_SECRET_KEY = config['JWT_SECRET_KEY']
TOKEN_EXPIRATION = config['TOKEN_EXPIRATION']

# File to store location settings
location_settings_file = 'location_settings.json'

# File to store user credentials
users_file = 'users.json'

# File to store user preferences
user_preferences_file = 'user_preferences.json'

# Load location settings from file if it exists
if os.path.exists(location_settings_file):
    with open(location_settings_file, 'r') as f:
        location_settings_store = json.load(f)
else:
    location_settings_store = {}

# Load users from file if it exists
if os.path.exists(users_file):
    with open(users_file, 'r') as f:
        users = json.load(f)
else:
    # Create default admin user if file doesn't exist
    users = {
        "admin": {
            "password_hash": hashlib.sha256("password".encode()).hexdigest(),
            "role": "admin"
        }
    }
    # Save to file
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=4)

# Load user preferences from file if it exists
if os.path.exists(user_preferences_file):
    with open(user_preferences_file, 'r') as f:
        user_preferences = json.load(f)
else:
    user_preferences = {}

# Token blacklist with expiration time
token_blacklist = {}  # Format: {token: expiry_time}

# Add this function to clean up expired tokens
def cleanup_token_blacklist():
    current_time = time.time()
    expired_tokens = [token for token, expiry in token_blacklist.items() if expiry < current_time]
    for token in expired_tokens:
        token_blacklist.pop(token)
    logger.info(f"Cleaned up {len(expired_tokens)} expired tokens from blacklist")
    return len(expired_tokens)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        if token in token_blacklist:
            return jsonify({'error': 'Token has been revoked'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def load_users():
    """Load users from file, create default admin if file doesn't exist"""
    global users
    
    # Load users from file if it exists
    if os.path.exists(users_file):
        with open(users_file, 'r') as f:
            users = json.load(f)
    else:
        # Create default admin user if file doesn't exist
        users = {
            "admin": {
                "password_hash": hashlib.sha256("password".encode()).hexdigest(),
                "role": "admin"
            }
        }
        # Save to file
        with open(users_file, 'w') as f:
            json.dump(users, f, indent=4)
    
    return users

# Load users initially when server starts
users = load_users()

# Add global variable for Kafka consumer (around line 40, after config loading)
kafka_consumer = None

@app.route('/login', methods=['POST'])
def login():
    # Refresh/load users every time login is called
    load_users()
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if username not in users:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if users[username]['password_hash'] != password_hash:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Generate JWT token
    token = jwt.encode({
        'username': username,
        'role': users[username].get('role', 'user'),
        'exp': int(time.time()) + TOKEN_EXPIRATION
    }, JWT_SECRET_KEY, algorithm='HS256')
    
    return jsonify({
        'token': token,
        'username': username,
        'role': users[username].get('role', 'user')
    })

@app.route('/validate_token', methods=['POST'])
@token_required
def validate_token(current_user):
    return jsonify({'valid': True, 'username': current_user})

@app.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    token = request.headers.get('Authorization').split(' ')[1]
    # Get token expiration from JWT
    try:
        data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'], options={"verify_signature": False})
        expiry = data.get('exp', int(time.time()) + 3600)  # Default to 1 hour if not found
    except:
        expiry = int(time.time()) + 3600  # Default to 1 hour if decode fails
    
    token_blacklist[token] = expiry
    cleanup_token_blacklist()  # Clean up expired tokens on each logout
    return jsonify({'message': 'Successfully logged out'})

@app.route('/change_password', methods=['POST'])
@token_required
def change_password(current_user):
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': 'Old and new passwords are required'}), 400
    
    old_password_hash = hashlib.sha256(old_password.encode()).hexdigest()
    
    if users[current_user]['password_hash'] != old_password_hash:
        return jsonify({'error': 'Invalid old password'}), 401
    
    # Update password
    users[current_user]['password_hash'] = hashlib.sha256(new_password.encode()).hexdigest()
    
    # Save to file
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=4)
    
    return jsonify({'message': 'Password changed successfully'})

@app.route('/users', methods=['GET'])
@token_required
def get_users(current_user):
    # Check if user is admin
    if users[current_user].get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Return user list without password hashes
    user_list = []
    for username, user_data in users.items():
        user_list.append({
            'username': username,
            'role': user_data.get('role', 'user')
        })
    
    return jsonify(user_list)

@app.route('/users', methods=['POST'])
@token_required
def create_user(current_user):
    # Check if user is admin
    if users[current_user].get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    if username in users:
        return jsonify({'error': 'Username already exists'}), 409
    
    # Create new user
    users[username] = {
        'password_hash': hashlib.sha256(password.encode()).hexdigest(),
        'role': role
    }
    
    # Save to file
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=4)
    
    return jsonify({'message': 'User created successfully'})

@app.route('/users/<username>', methods=['DELETE'])
@token_required
def delete_user(current_user, username):
    # Check if user is admin
    if users[current_user].get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if username not in users:
        return jsonify({'error': 'User not found'}), 404
    
    if username == current_user:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    
    # Delete user
    del users[username]
    
    # Save to file
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=4)
    
    return jsonify({'message': 'User deleted successfully'})

@app.route('/get_location_settings/<location>', methods=['GET'])
def get_location_settings(location):
    settings = location_settings_store.get(location, {})
    return jsonify(settings)

@app.route('/set_location_settings/<location>', methods=['POST'])
def set_location_settings(location):
    
    settings = request.json
    location_settings_store[location] = settings
    # Save settings to file with pretty printing
    with open(location_settings_file, 'w') as f:
        json.dump(location_settings_store, f, indent=4, sort_keys=True)
    
    # Refresh settings in alert_monitor module
    alert_monitor.refresh_settings(location_settings_store)
    
    return jsonify({"status": "success"})

def format_alert(alert):
    """Format an alert object for API response."""
    return {
        "location_id": alert[0] if len(alert) > 0 else None,
        "level": alert[1] if len(alert) > 1 else None,
        "level_threshold": alert[2] if len(alert) > 2 else None,
        "timestamp": alert[3] if len(alert) > 3 else None,
        "region_count": alert[4] if len(alert) > 4 else 0,
        "acknowledge": bool(alert[5]) if len(alert) > 5 else False,
        "acknowledge_time": alert[6] if len(alert) > 6 else None,
        "status": alert[7] if len(alert) > 7 else None
    }

@app.route('/recent_alerts', methods=['GET'])
# @token_required
def recent_alerts():
    # Parse optional time range parameters
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    
    # Parse location filter parameter
    location_id = request.args.get('location_id')
    
    # Parse search text parameter
    search_text = request.args.get('search_text')
    
    # Parse pagination parameters
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        
        # Validate pagination parameters
        if page < 1:
            return jsonify({"error": "Page number must be at least 1"}), 400
        if page_size < 1 or page_size > 100:
            return jsonify({"error": "Page size must be between 1 and 100"}), 400
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400
    
    start_time = None
    end_time = None
    
    # Convert string parameters to datetime objects if provided
    if start_time_str:
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"error": "Invalid start_time format. Use YYYY-MM-DD HH:MM:SS"}), 400
    
    if end_time_str:
        try:
            end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"error": "Invalid end_time format. Use YYYY-MM-DD HH:MM:SS"}), 400
    
    # Get alerts with optional time range, location filter, text search, and pagination
    result = alert_monitor.get_recent_alerts(
        start_time, end_time, page, page_size, location_id, search_text
    )
    
    # Process the alerts from the result dictionary
    alerts = result["alerts"]
    
    # Format the response with pagination metadata
    response = {
        "alerts": [format_alert(alert) for alert in alerts],
        "pagination": {
            "total_count": result["total_count"],
            "page": result["page"],
            "total_pages": result["total_pages"],
            "page_size": page_size
        }
    }
    
    return jsonify(response)

from flask import make_response
from flask_cors import cross_origin

@app.route('/acknowledge_alert', methods=['POST', 'OPTIONS'])
@cross_origin()
def acknowledge_alert():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    elif request.method == "POST":

        data = request.json
        location_id = data.get('location_id')
        timestamp = data.get('timestamp')
        
        logger.info(f'acknowledge_alert request - location_id: {location_id}, timestamp: {timestamp}')
        if not location_id or not timestamp:
            return jsonify({'error': 'Missing location_id or timestamp'}), 400
        
        # Get current timestamp for acknowledge_time
        acknowledge_time = time.strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect('alerts.db')
        c = conn.cursor()
        c.execute('''
            UPDATE alerts
            SET acknowledge = 1, acknowledge_time = ?
            WHERE location_id = ? AND timestamp = ?
        ''', (acknowledge_time, location_id, timestamp))
        conn.commit()
        
        if c.rowcount == 0:
            conn.close()
            logger.warning(f'No matching alert found for location_id: {location_id}, timestamp: {timestamp}')
            return jsonify({'error': 'No matching alert found'}), 404
        
        conn.close()
        logger.info(f'Alert acknowledged successfully - location_id: {location_id}, acknowledge_time: {acknowledge_time}')
        return jsonify({'message': 'Alert acknowledged successfully', 'acknowledge_time': acknowledge_time}), 200
    else:
        raise RuntimeError("Weird - don't know how to handle method {}".format(request.method))

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
    response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

from flask import Flask, send_from_directory
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# import time
# def send_alerts2():
#     alerts = [
#         {'camera': 'COL_In_Cam1', 'level': 'yellow'},
#         {'camera': 'WW_HC', 'level': 'red'},
#         {'camera': 'WW_BWB', 'level': 'black'}
#     ]
    
#     while True:
#         for alert in alerts:
#             socketio.emit('alert', alert)
#             time.sleep(10)  # Send an alert every 10 seconds

def check_send_alerts():
    # alert_monitor.create_db_if_not_exist()
    alert_monitor.restore_last_fired_alerts()

   
    # Create application context once outside the loop
    with app.app_context():
        logger.info("Starting check_send_alerts with app context")
        
        while True:
            try:
                locations = get_locations()
                cameras_by_location = get_cameras_by_location()
                
                # Modify the check_location_alerts function to accept direct data
                location_alerts = alert_monitor.check_location_alerts(
                    location_settings_store,
                    locations=locations,
                    cameras_by_location=cameras_by_location
                )
                
                logger.debug(f"check_location_alerts location_alerts: {location_alerts}")
                
                # Get the number of connected clients
                connected_clients = len(socketio.server.eio.sockets)
                logger.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}, Connected clients: {connected_clients}")
                
                # Clean up expired tokens periodically
                if int(time.time()) % 3600 == 0:  # Once per hour
                    cleanup_token_blacklist()
                
                # Send location alerts
                for location, alert_data in location_alerts.items():
                    alert = {'location': location, 'level': alert_data['level'], 'timestamp': alert_data['timestamp'], 
                            'count': alert_data['region_count'], 'status': alert_data['status']}
                    socketio.emit('location_alert', alert)
                    logger.debug(f"location_alert socketio.emit: {alert}")
                    
            except Exception as e:
                if 'alert_data' in locals():
                    logger.error(f"alert_data: {alert_data}")
                logger.error(f"Error in check_send_alerts: {e}")
                logger.error(traceback.format_exc())
                # Log the error but continue the loop
            
            time.sleep(10)  # Check every 10 seconds
        
@socketio.on('connect')
def handle_connect():
    client_ip = request.remote_addr
    logger.info(f'Client connected from IP: {client_ip}')

def get_locations():
    """Return a list of locations extracted from get_cameras_by_location."""
    cameras_by_location = get_cameras_by_location()
    locations = [
        {'id': location_id, 'name': location_id}
        for location_id in cameras_by_location.keys()
    ]
    return locations

@app.route('/locations', methods=['GET'])
def get_locations_api():
    """API endpoint to return locations as JSON."""
    return jsonify(get_locations())  # Use the function and jsonify for the API endpoint

def get_cameras_by_location(): #TODO: using cache? efficiency?
    """Return a mapping of location IDs to their associated cameras from config file."""
    config_path = os.path.join(os.path.dirname(__file__), 'config_locations.json')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('locations', {})
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        # Fallback to empty dict or you could return the hardcoded data as backup
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file {config_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error reading config file {config_path}: {e}")
        return {}

@app.route('/cameras', methods=['GET'])
def get_cameras():
    try:
        location_id = request.args.get('location_id')
        if not location_id:
            # Return all cameras grouped by location
            return jsonify(get_cameras_by_location())
            
        cameras_by_location = get_cameras_by_location()
        return jsonify(cameras_by_location.get(location_id, []))
    
    except Exception as e:
        print(f"Error fetching cameras: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/location_stats/<location_id>', methods=['GET'])
def get_location_stats(location_id):
    # Get start_time from location settings instead of query parameters
    location_settings = location_settings_store.get(location_id, {})
    start_time_setting = location_settings.get('startTime')
    
    # Parse the start_time from location settings if provided
    if start_time_setting:
        try:
            # Parse time string (format: HH:MM:SS)
            time_parts = start_time_setting.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            second = int(time_parts[2])
            
            # Create start_time with today's date but specified time
            now = datetime.now()
            start_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
            logger.info(f"Using location-specific start_time for {location_id}: {start_time_setting}")
        except (ValueError, IndexError):
            # If parsing fails, use default (start of day)
            logger.error(f"Error parsing start_time from location settings: {start_time_setting}")
            now = datetime.now()
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Default to start of day if no setting provided
        now = datetime.now()
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        logger.debug(f"No start_time setting found for {location_id}, using default (start of day)")
    
    try:
        if not location_id:
            return jsonify({'error': 'Missing location_id parameter'}), 400
            
        # Get recent alerts for this location
        latest_alert = None
        alert_counts = []
        
        # Use with statement to ensure connection is closed even if exception occurs
        with sqlite3.connect('alerts.db') as conn:
            c = conn.cursor()
            
            # Get the most recent alert for this location
            c.execute('''
                SELECT level, timestamp, region_count, acknowledge, acknowledge_time, status
                FROM alerts
                WHERE location_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (location_id,))
            
            latest_alert = c.fetchone()
            
            # Get alert counts by level for this location
            c.execute('''
                SELECT level, COUNT(*) as count
                FROM alerts
                WHERE location_id = ? AND status = 'firing'
                GROUP BY level
            ''', (location_id,))
            
            alert_counts = c.fetchall()
        
        # Format alert counts
        alert_stats = {
            'yellow': 0,
            'orange': 0,
            'red': 0,
            'black': 0
        }
        
        for level, count in alert_counts:
            if level in alert_stats:
                alert_stats[level] = count
        
        # Get the cameras for this location
        cameras_by_location = get_cameras_by_location()
        cameras = cameras_by_location.get(location_id, [])
        
        # Fetch all camera data in parallel
        print (f"get_location_stats: cameras:  =================================================")
        camera_data = get_camera_data_batch(cameras)
        
        # Process the results
        camera_counts_region = {}
        camera_counts_in = {}
        camera_counts_out = {}
        
        total_in = 0
        total_out = 0
        total_region = 0
        
        for camera in cameras:
            camera_id = camera['id']
            data = camera_data.get(camera_id, {})
            
            # Region count
            region_count = data.get('region_count', 0)
            camera_counts_region[camera_id] = region_count
            total_region += region_count
            
            # Aggregated count
            aggregated = data.get('aggregated', {'total_in': 0, 'total_out': 0})
            camera_counts_in[camera_id] = aggregated['total_in']
            camera_counts_out[camera_id] = aggregated['total_out']
            total_in += aggregated['total_in']
            total_out += aggregated['total_out']
        
        # Remove the separate total calculations
        # location_result = get_total_people_count_with_in_count(cameras)
        # total_in = location_result['total_in']
        # total_out = location_result['total_out']
        # total_region = get_total_people_count_with_region_sum(cameras)
   
        
        logger.debug(f'camera_counts_region: {camera_counts_region}')
        logger.debug(f'camera_counts_in: {camera_counts_in}')
        logger.debug(f'camera_counts_out: {camera_counts_out}')
        
        # Generate hourly attendance data using smart selector
        stats = {
            'alertCounts': alert_stats,
            'currentAlert': {
                'level': latest_alert[0] if latest_alert else None,
                'timestamp': latest_alert[1] if latest_alert else None,
                'count': latest_alert[2] if latest_alert else 0,
                'acknowledge': bool(latest_alert[3]) if latest_alert else False,
                'acknowledge_time': latest_alert[4] if latest_alert else None,
                'status': latest_alert[5] if latest_alert else None
            },
            'hourlyAttendance': get_hourly_attendance_function_cached(location_id),  # Cached hourly attendance
            'lengthOfStay': calculate_length_of_stay_cached_15min(location_id),  # 15-min interval cached LOS data
            'totalRegion': total_region,
            'totalIn': total_in,
            'totalOut': total_out,
            'cameraCountsRegion': camera_counts_region,
            'cameraCountsIn': camera_counts_in,
            'cameraCountsOut': camera_counts_out
        }
        
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error fetching location stats: {e}")
        return jsonify({'error': str(e)}), 500

# Add this as a global variable near the top of your file (after imports)
http_session = requests.Session()  # Reuse HTTP connections

def get_total_people_count_with_region_sum(cameras):
    """
    Calculate the total people count across all cameras in a location
    by getting the latest region counts for each camera.
    Uses local database access instead of HTTP requests for better performance.
    """
    if not cameras:
        return 0
    
    total_count = 0
    
    for camera in cameras:
        camera_id = camera['id']
        
        try:
            # Use local database access instead of HTTP API call
            data = get_last_results_local(camera_name=camera_id, limit=1)
            
            # Check if we got valid data (not an error)
            if isinstance(data, list) and len(data) > 0:
                # Take the first (most recent) result
                latest_data = data[0]
                if 'region_count' in latest_data:
                    region_count = latest_data['region_count'] or 0
                    total_count += region_count
                    logger.debug(f"Camera {camera_id}: region_count = {region_count}")
            elif isinstance(data, dict) and 'error' in data:
                logger.warning(f"Local database returned error for camera {camera_id}: {data['error']}")
                continue
            else:
                logger.warning(f"Unexpected data format for camera {camera_id}: {data}")
                
        except Exception as e:
            logger.error(f"Error getting region count for camera {camera_id}: {e}")
            continue
    
    logger.debug(f"Total people count across {len(cameras)} cameras: {total_count}")
    return total_count

def generate_hourly_attendance_data_batch_region(location_id):
    """
    Generate hourly attendance data by querying local database directly.
    For each hour in the past 24 hours, sample region_count at 4 time points:
    0, 15, 30, 45 minutes. Calculate average and multiply by 15 (assuming 15-minute stay).
    """
    from datetime import datetime, timedelta
    import sqlite3
    
    cameras_by_location = get_cameras_by_location()
    cameras = cameras_by_location.get(location_id, [])
    
    if not cameras:
        logger.warning(f"No cameras found for location: {location_id}")
        return [0] * 24
    
    # Use all cameras for this location and sum their region counts
    camera_ids = [camera['id'] for camera in cameras]
    
    # Get the past 24 hours range
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_time = now - timedelta(hours=24)
    
    logger.debug(f"Generating hourly attendance for {location_id} with cameras {camera_ids} from {start_time} to {now}")
    
    try:
        # Use the smart database connection
        conn = get_people_count_db_connection()
        cursor = conn.cursor()
        
        hourly_results = [0] * 24
        
        # For each hour in the past 24 hours
        for hour_offset in range(24):
            hour_start = start_time + timedelta(hours=hour_offset)
            hour_samples = []
            
            # Sample at 4 time points: 0, 15, 30, 45 minutes
            for minute_offset in [0, 15, 30, 45]:
                sample_time = hour_start + timedelta(minutes=minute_offset)
                sample_time_str = sample_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Query for region counts at this specific time (±2 minutes window for tolerance)
                window_start = (sample_time - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
                window_end = (sample_time + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
                
                # Create placeholders for camera IDs
                camera_placeholders = ','.join(['?' for _ in camera_ids])
                
                query = f"""
                    SELECT region_count
                    FROM traffic 
                    WHERE camera_name IN ({camera_placeholders})
                    AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                
                params = camera_ids + [window_start, window_end]
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                region_count = result[0] if result and result[0] else 0
                hour_samples.append(region_count)
                
                logger.debug(f"Sample at {sample_time_str}: {region_count} people")
            
            # Calculate average of the 4 samples
            if hour_samples and any(sample > 0 for sample in hour_samples):
                logger.debug(f"hour_samples: {hour_samples} camera_placeholders: {camera_ids} window_start: {window_start} window_end: {window_end}")
                average_count = sum(hour_samples) / len(hour_samples) * len(camera_ids)
                # Multiply by 4 (assuming 15-minute average stay duration, 60/15 = 4)
                hourly_attendance = average_count * 4
                hourly_results[hour_offset] = round(hourly_attendance)
            else:
                hourly_results[hour_offset] = 0
            
            logger.debug(f"Hour {hour_offset} ({hour_start.strftime('%H:%M')}): samples={hour_samples}, avg={sum(hour_samples)/len(hour_samples) if hour_samples else 0}, attendance={hourly_results[hour_offset]}")
        
        logger.debug(f"Hourly attendance results for {location_id}: {hourly_results}")
        return hourly_results
        
    except sqlite3.Error as e:
        logger.error(f"Database error while generating hourly attendance for {location_id}: {e}")
        return [0] * 24
    except FileNotFoundError as e:
        logger.error(f"Database file not found: {e}")
        return [0] * 24
    except Exception as e:
        logger.error(f"Error generating hourly attendance data for {location_id}: {e}")
        return [0] * 24
    finally:
        if 'conn' in locals():
            conn.close()

def generate_hourly_attendance_data_batch_in_out(location_id):
    """
    Generate hourly attendance data using in/out counts and Length of Stay.
    For each hour in the past 24 hours, calculate attendance as:
    (total_in - total_out at end of hour) * 60 / LOS_value
    
    Args:
        location_id (str): The location ID
    
    Returns:
        list: Hourly attendance data for past 24 hours
    """
    from datetime import datetime, timedelta
    import sqlite3
    
    cameras_by_location = get_cameras_by_location()
    cameras = cameras_by_location.get(location_id, [])
    
    if not cameras:
        logger.warning(f"No cameras found for location: {location_id}")
        return [0] * 24
    
    camera_ids = [camera['id'] for camera in cameras]
    
    # Get the past 24 hours range
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_time = now - timedelta(hours=24)
    
    logger.debug(f"Generating in/out-based hourly attendance for {location_id} with cameras {camera_ids} from {start_time} to {now}")
    
    try:
        # Get LOS value using cached function
        los_data = calculate_length_of_stay_cached(location_id)
        los_value = los_data.get('los', 0)
        
        if los_value <= 0:
            logger.warning(f"Invalid LOS value ({los_value}) for {location_id}, using default 15 minutes")
            los_value = 15  # Default 15 minutes if LOS is invalid
        
        # Use the smart database connection
        conn = get_people_count_db_connection()
        cursor = conn.cursor()
        
        camera_placeholders = ','.join(['?' for _ in camera_ids])
        hourly_results = [0] * 24
        
        # For each hour in the past 24 hours
        # TODO: do not need to do this for each hour, just do it once for the last hour?
        for hour_offset in range(24):
            hour_end = start_time + timedelta(hours=hour_offset + 1)
            hour_end_str = hour_end.strftime('%Y-%m-%d %H:%M:%S')
            
            # Get the start of the day for this hour (0:00:00 of that day)
            day_start = hour_end.replace(hour=0, minute=0, second=0, microsecond=0)
            day_start_str = day_start.strftime('%Y-%m-%d %H:%M:%S')
            
            # Get cumulative in/out counts from start of day up to the end of this hour
            query = f"""
                SELECT 
                    COALESCE(SUM(in_count), 0) as total_in,
                    COALESCE(SUM(out_count), 0) as total_out
                FROM traffic 
                WHERE camera_name IN ({camera_placeholders})
                AND timestamp >= ?
                AND timestamp <= ?
            """
            
            params = camera_ids + [day_start_str, hour_end_str]
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            if result:
                total_in = result[0] or 0
                total_out = result[1] or 0
                net_attendance = total_in - total_out
                
                # Ensure net_attendance is not negative
                net_attendance = max(0, net_attendance)
                
                # Calculate hourly attendance: net_attendance * 60 / LOS
                if los_value > 0:
                    hourly_attendance = (net_attendance * 60) / los_value
                else:
                    hourly_attendance = 0
                
                hourly_results[hour_offset] = round(hourly_attendance)
            else:
                hourly_results[hour_offset] = 0
            
            logger.debug(f"Hour {hour_offset} ({hour_end.strftime('%H:00')} on {hour_end.strftime('%Y-%m-%d')}): "
                        f"day_start={day_start_str}, hour_end={hour_end_str}, "
                        f"total_in={result[0] if result else 0}, "
                        f"total_out={result[1] if result else 0}, "
                        f"net={net_attendance if result else 0}, "
                        f"los={los_value}, "
                        f"attendance={hourly_results[hour_offset]}")
        
        logger.debug(f"In/Out-based hourly attendance results for {location_id}: {hourly_results}")
        return hourly_results
        
    except sqlite3.Error as e:
        logger.error(f"Database error while generating in/out-based hourly attendance for {location_id}: {e}")
        return [0] * 24
    except FileNotFoundError as e:
        logger.error(f"Database file not found: {e}")
        return [0] * 24
    except Exception as e:
        logger.error(f"Error generating in/out-based hourly attendance data for {location_id}: {e}")
        logger.error(traceback.format_exc())
        return [0] * 24
    finally:
        if 'conn' in locals():
            conn.close()

def get_hourly_attendance_function(location_id):
    """
    Select which hourly attendance function to use based on location ID.
    
    Args:
        location_id (str): The location ID
    
    Returns:
        function: The appropriate hourly attendance function
    """
    # Define which locations should use the new in/out-based calculation
    region_based_locations = [
        'Horizon Cove',
        'Big Wave Bay',
        'Doggie\'s Lagoon',
        # Add more locations as needed
    ]
    
    if location_id in region_based_locations:
        logger.debug(f"Using region-based hourly attendance calculation for {location_id}")
        return generate_hourly_attendance_data_batch_region
    else:
        logger.debug(f"Using in/out-based hourly attendance calculation for {location_id}")
        return generate_hourly_attendance_data_batch_in_out

@app.route('/get_location_by_camera/<camera_id>', methods=['GET'])
def get_location_by_camera(camera_id):
    try:
        if not camera_id:
            return jsonify({'error': 'Missing camera_id parameter'}), 400
            
        # Get the mapping of locations to cameras
        cameras_by_location = get_cameras_by_location()
        
        # Search through all locations to find the camera
        for location_id, cameras in cameras_by_location.items():
            for camera in cameras:
                if camera['id'] == camera_id:
                    return jsonify({'location_id': location_id})
        
        # If camera not found in any location
        logger.warning(f'No location found for camera: {camera_id}')
        return jsonify({'error': f'No location found for camera: {camera_id}'}), 404
    
    except Exception as e:
        logger.error(f"Error finding location for camera: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/user_preferences', methods=['POST'])
@token_required
def save_user_preference(current_user):
    data = request.json
    user_id = data.get('user_id')
    preference_type = data.get('preference_type')
    preference_value = data.get('preference_value')
    
    if not user_id or not preference_type or preference_value is None:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Initialize user preferences if not exists
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    
    # Save the preference
    user_preferences[user_id][preference_type] = preference_value
    
    # Save to file
    with open(user_preferences_file, 'w') as f:
        json.dump(user_preferences, f, indent=4)
    
    return jsonify({'message': 'Preference saved successfully'})

@app.route('/user_preferences/<preference_type>/<user_id>', methods=['GET'])
@token_required
def get_user_preference(current_user, preference_type, user_id):
    # Check if user exists in preferences
    if user_id not in user_preferences:
        return jsonify({'error': 'User preferences not found'}), 404
    
    # Check if preference type exists for user
    if preference_type not in user_preferences[user_id]:
        return jsonify({'error': f'Preference type {preference_type} not found for user'}), 404
    
    # Return the preference value
    return jsonify({
        'user_id': user_id,
        'preference_type': preference_type,
        'preference_value': user_preferences[user_id][preference_type]
    })

@app.route('/user_preferences/<user_id>', methods=['GET'])
@token_required
def get_all_user_preferences(current_user, user_id):
    # Check if user exists in preferences
    if user_id not in user_preferences:
        return jsonify({'error': 'User preferences not found'}), 404
    
    # Return all preferences for the user
    return jsonify(user_preferences[user_id])

@app.route('/user_preferences/<preference_type>/<user_id>', methods=['DELETE'])
@token_required
def delete_user_preference(current_user, preference_type, user_id):
    # Check if user exists in preferences
    if user_id not in user_preferences:
        return jsonify({'error': 'User preferences not found'}), 404
    
    # Check if preference type exists for user
    if preference_type not in user_preferences[user_id]:
        return jsonify({'error': f'Preference type {preference_type} not found for user'}), 404
    
    # Delete the preference
    del user_preferences[user_id][preference_type]
    
    # Save to file
    with open(user_preferences_file, 'w') as f:
        json.dump(user_preferences, f, indent=4)
    
    return jsonify({'message': 'Preference deleted successfully'})

@app.route('/all_locations_people_count', methods=['GET'])
def get_all_locations_people_count():
    try:
        locations = get_locations()
        cameras_by_location = get_cameras_by_location()
        
        # Collect all cameras from all locations
        all_cameras = []
        location_camera_map = {}
        
        for location in locations:
            location_id = location['id']
            cameras = cameras_by_location.get(location_id, [])
            all_cameras.extend(cameras)
            location_camera_map[location_id] = [camera['id'] for camera in cameras]
        
        # Fetch all camera data in one batch
        print (f"get_all_locations_people_count: all_cameras:  =================================================")
        camera_data = get_camera_data_batch(all_cameras)
        
        # Process results by location
        response = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'locations': {}
        }
        
        for location in locations:
            location_id = location['id']
            camera_ids = location_camera_map.get(location_id, [])
            
            # Aggregate data for this location
            camera_counts_region = {}
            camera_counts_in = {}
            camera_counts_out = {}
            
            total_in = 0
            total_out = 0
            total_region = 0
            
            for camera_id in camera_ids:
                data = camera_data.get(camera_id, {})
                
                region_count = data.get('region_count', 0)
                aggregated = data.get('aggregated', {'total_in': 0, 'total_out': 0})
                
                camera_counts_region[camera_id] = region_count
                camera_counts_in[camera_id] = aggregated['total_in']
                camera_counts_out[camera_id] = aggregated['total_out']
                
                total_region += region_count
                total_in += aggregated['total_in']
                total_out += aggregated['total_out']
            
            response['locations'][location_id] = {
                'name': location['name'],
                'total_region': total_region,
                'total_in': total_in,
                'total_out': total_out,
                'camera_counts_region': camera_counts_region,
                'camera_counts_in': camera_counts_in,
                'camera_counts_out': camera_counts_out
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error fetching all locations people count: {e}")
        return jsonify({'error': str(e)}), 500

# Add these global variables near the top of your file (after imports)
_db_path_cache = None
_db_path_checked = False

def get_people_count_core_db_path():
    """
    Smart database path detection - checks multiple locations and caches the result.
    Only executes the detection once, then uses cached path.
    
    Returns:
        str: Path to the people_count_database.db file
    """
    global _db_path_cache, _db_path_checked
    
    # Return cached path if already detected
    if _db_path_checked:
        if _db_path_cache is None:
            raise FileNotFoundError("people_count_database.db not found in any location")
        return _db_path_cache
    
    # List of possible database locations (in order of preference)
    possible_paths = [
        'people_count_database.db',              # Current directory
        './people_count_database.db',            # Explicit current directory
        '../swift/people_count_database.db',     # Swift directory
        '/app/people_count_database.db',         # Docker mounted path
    ]
    
    logger.info("🔍 Detecting people_count_database.db location...")
    
    for db_path in possible_paths:
        try:
            if os.path.exists(db_path):
                # Test if we can actually connect to it
                test_conn = sqlite3.connect(db_path)
                test_cursor = test_conn.cursor()
                # Try a simple query to verify it's a valid database
                test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                test_conn.close()
                
                # Cache the successful path
                _db_path_cache = db_path
                _db_path_checked = True
                logger.info(f"✅ Found people_count_database.db at: {db_path}")
                return db_path
                
        except (sqlite3.Error, OSError) as e:
            logger.debug(f"❌ Failed to access database at {db_path}: {e}")
            continue
    
    # Mark as checked but not found
    _db_path_checked = True
    _db_path_cache = None
    
    error_msg = f"people_count_database.db not found in any of these locations: {possible_paths}"
    logger.error(f"❌ {error_msg}")
    raise FileNotFoundError(error_msg)

def get_people_count_db_connection(readonly=True):
    """
    Get a connection to the people count database using smart path detection.
    
    Args:
        readonly (bool): If True, opens in read-only mode for better multi-process performance
    
    Returns:
        sqlite3.Connection: Database connection
    """
    db_path = get_people_count_core_db_path()
    if readonly:
        # Open in read-only mode using URI
        db_uri = f"file:{db_path}?mode=ro"
        # logger.info(f"Opening people count database in read-only mode: {db_uri}")
        return sqlite3.connect(db_uri, uri=True)
    else:
        return sqlite3.connect(db_path)

# Now update your aggregated counts function to use the smart connection
def get_aggregated_counts_local(camera_id=None, start_time=None, end_time=None):
    """
    Local version of aggregated-counts API - direct SQLite access with smart path detection.
    """
    if not start_time or not end_time:
        logger.error("Both start_time and end_time parameters are required for aggregated counts")
        return {"error": "Both start_time and end_time parameters are required."}

    try:
        # Use the smart database connection
        conn = get_people_count_db_connection()
        cursor = conn.cursor()

        # Same query as the original aggregated-counts API
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

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Format results exactly like the original API
        data = []
        for row in rows:
            data.append({
                "camera_id": row[0],
                "total_in": row[1] or 0,
                "total_out": row[2] or 0,
                "total_region": row[3] or 0
            })

        logger.debug(f"✅ Local aggregated counts query completed for {camera_id}: {data} start_time: {start_time} end_time: {end_time}") #TODO, why this line executed very frequently?
        
        # Return same format as original API
        return {
            "message": "Aggregated counts retrieved successfully.",
            "data": data
        }
        
    except sqlite3.Error as e:
        logger.error(f"❌ Local aggregated counts database error: {e}")
        return {"error": "A database error occurred.", "message": str(e)}
    except FileNotFoundError as e:
        logger.error(f"❌ Database file not found: {e}")
        return {"error": "Database file not found.", "message": str(e)}
    except Exception as e:
        logger.error(f"❌ Local aggregated counts error: {e}")
        return {"error": "An error occurred.", "message": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()
        logger.debug(f"get_aggregated_counts_local: Function execution completed")


def get_last_results_local(camera_name=None, limit=5):
    """
    Local version of get_last_result API - direct SQLite access with smart path detection.
    
    Args:
        camera_name (str, optional): Specific camera name to filter by
        limit (int): Number of recent results to return (default: 5)
    
    Returns:
        dict: Results in the same format as the original API
    """
    try:
        # Use the smart database connection with read-only mode for better performance
        conn = get_people_count_db_connection()
        cursor = conn.cursor()
        
        if camera_name:
            query = """
                SELECT timestamp, in_count, out_count, region_count 
                FROM traffic  
                WHERE camera_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params = [camera_name, limit]
        else:
            query = """
                SELECT timestamp, in_count, out_count, region_count, camera_name 
                FROM traffic  
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params = [limit]

        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if rows:
            # Format results exactly like the original API
            results = []
            for row in rows:
                if camera_name:
                    # When camera_name is specified, it's not in the SELECT
                    result = {
                        "timestamp": row[0],
                        "in_count": row[1] or 0,
                        "out_count": row[2] or 0,
                        "region_count": row[3] or 0,
                        "camera_name": camera_name
                    }
                else:
                    # When camera_name is not specified, it's the 5th column
                    result = {
                        "timestamp": row[0],
                        "in_count": row[1] or 0,
                        "out_count": row[2] or 0,
                        "region_count": row[3] or 0,
                        "camera_name": row[4]
                    }
                results.append(result)
            
            logger.debug(f"✅ Local last results query completed for camera '{camera_name}': found {len(results)} records")
            return results
        else:
            logger.debug(f"No results found for camera '{camera_name}'")
            return {"error": "No results found"}
        
    except sqlite3.Error as e:
        logger.error(f"❌ Local last results database error: {e}")
        return {"error": "Database error", "message": str(e)}
    except FileNotFoundError as e:
        logger.error(f"❌ Database file not found: {e}")
        return {"error": "Database file not found", "message": str(e)}
    except Exception as e:
        logger.error(f"❌ Local last results error: {e}")
        return {"error": "An error occurred", "message": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()
        logger.debug(f"get_last_results_local: Function execution completed")


# Add global variables for LOS database path detection
_alert_backend_server_db_path_cache = None
_alert_backend_server_db_path_checked = False

def get_backend_server_db_path():
    """
    Smart database path detection for Length of Stay database.
    Looks for location_los.db in multiple locations.
    
    Returns:
        str: Path to the location_los.db file
    """
    global _alert_backend_server_db_path_cache, _alert_backend_server_db_path_checked
    
    # Return cached path if already detected
    if _alert_backend_server_db_path_checked:
        if _alert_backend_server_db_path_cache is None:
            # Create default path if not found
            default_path = 'alert_backend_server.db'
            logger.info(f"🆕 Creating new LOS database at: {default_path}")
            return default_path
        return _alert_backend_server_db_path_cache
    
    # List of possible LOS database locations (in order of preference)
    possible_paths = [
        'alert_backend_server.db',                      # Current directory          # Swift directory
        '/app/alert_backend_server.db',                 # Docker mounted path
    ]
    
    logger.info("🔍 Detecting alert_backend_server.db location...")
    
    for db_path in possible_paths:
        try:
            if os.path.exists(db_path):
                # Test if we can actually connect to it
                test_conn = sqlite3.connect(db_path)
                test_cursor = test_conn.cursor()
                # Try a simple query to verify it's a valid database
                test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                test_conn.close()
                
                # Cache the successful path
                _alert_backend_server_db_path_cache = db_path
                _alert_backend_server_db_path_checked = True
                logger.info(f"✅ Found alert_backend_server.db at: {db_path}")
                return db_path
                
        except (sqlite3.Error, OSError) as e:
            logger.debug(f"❌ Failed to access alert_backend_server.db database at {db_path}: {e}")
            continue
    
    # Mark as checked but create default path
    _alert_backend_server_db_path_checked = True
    default_path = 'alert_backend_server.db'
    _alert_backend_server_db_path_cache = default_path
    
    logger.info(f"🆕 LOS database not found, will create at: {default_path}")
    return default_path

def get_backend_server_db_connection():
    """
    Get a connection to the Length of Stay database using smart path detection.
    
    Returns:
        sqlite3.Connection: Database connection
    """
    db_path = get_backend_server_db_path()
    return sqlite3.connect(db_path)

def calculate_length_of_stay(location_id, update_time=None):
    """
    Calculate Length of Stay for a location based on the logic from entity_managers.py.
    Now uses separate database for location_los table.
    
    Args:
        location_id (str): The location ID to calculate LOS for
        update_time (datetime, optional): The time to calculate LOS at. Defaults to now.
    
    Returns:
        dict: Contains 'los' (length of stay in minutes) and 'total_attendance'
    """
    if update_time is None:
        update_time = datetime.now()
    
    # Use separate connections for traffic data and LOS data
    traffic_conn = None
    los_conn = None
    
    try:
        # Get cameras for this location
        cameras_by_location = get_cameras_by_location()
        cameras = cameras_by_location.get(location_id, [])
        
        if not cameras:
            logger.warning(f"No cameras found for location: {location_id}")
            return {'los': 0, 'total_attendance': 0}
        
        camera_ids = [camera['id'] for camera in cameras]
        camera_placeholders = ','.join(['?' for _ in camera_ids])
        
        # Get the last LOS record for this location (from today)
        today_start = update_time.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
        update_time_str = update_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Connect to LOS database for LOS-specific operations
        los_conn = get_backend_server_db_connection()
        los_cursor = los_conn.cursor()
        
        # Create the LOS table if it doesn't exist (do this first)
        los_cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_los (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                los_value REAL NOT NULL,
                total_attendance INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        los_conn.commit()
        
        # Get last total stay time (if exists)
        last_total_stay_time = 0
        time_interval_mins = 1  # Default 1 minute interval
        
        # Try to get the last LOS calculation from LOS database
        try:
            los_cursor.execute("""
                SELECT los_value, total_attendance, timestamp
                FROM location_los 
                WHERE location_id = ? AND timestamp >= ? AND timestamp < ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (location_id, today_start_str, update_time_str))
            
            last_los_record = los_cursor.fetchone()
            
            if last_los_record:
                last_los_value = last_los_record[0]
                last_total_att = last_los_record[1]
                last_timestamp_str = last_los_record[2]
                
                # Calculate last total stay time
                last_total_stay_time = last_los_value * last_total_att
                
                # Calculate time interval since last update
                last_timestamp = datetime.strptime(last_timestamp_str, '%Y-%m-%d %H:%M:%S')
                time_interval = update_time - last_timestamp
                time_interval_mins = time_interval.total_seconds() / 60.0
                
                logger.debug(f"Found previous LOS for {location_id}: {last_los_value} mins, interval: {time_interval_mins} mins")
        
        except sqlite3.Error as e:
            logger.debug(f"Error reading LOS data: {e}")
        
        # Connect to traffic database for traffic data
        traffic_conn = get_people_count_db_connection()
        traffic_cursor = traffic_conn.cursor()
        
        # Get current attendance (today's total in - total out for all cameras in location)
        traffic_cursor.execute(f"""
            SELECT 
                COALESCE(SUM(in_count), 0) as total_in,
                COALESCE(SUM(out_count), 0) as total_out
            FROM traffic 
            WHERE camera_name IN ({camera_placeholders})
            AND timestamp >= ?
        """, camera_ids + [today_start_str])
        
        attendance_result = traffic_cursor.fetchone()
        if attendance_result:
            total_in = attendance_result[0] or 0
            total_out = attendance_result[1] or 0
            current_att = total_in - total_out
        else:
            current_att = 0
        
        # Get total attendance for today (cumulative in_count for all cameras)
        total_att = total_in if 'total_in' in locals() else 0
        
        # Calculate current total stay time
        # last_total_stay_time + (time_interval_mins * current_attendance)
        current_total_stay_time = last_total_stay_time + (time_interval_mins * current_att)
        
        # Calculate Length of Stay (avoid division by zero)
        if total_att > 0:
            current_los = current_total_stay_time / total_att
        else:
            current_los = 0
        
        # Store the new LOS calculation in LOS database
        los_cursor.execute("""
            INSERT INTO location_los (location_id, los_value, total_attendance, timestamp)
            VALUES (?, ?, ?, ?)
        """, (location_id, current_los, total_att, update_time_str))
        
        los_conn.commit()
        
        logger.debug(f"LOS calculation for {location_id}: {current_los:.2f} minutes (total_att: {total_att}, current_att: {current_att})")
        
        return {
            'los': round(current_los, 2),
            'total_attendance': total_att,
            'current_attendance': current_att,
            'total_stay_time': current_total_stay_time
        }
        
    except Exception as e:
        logger.error(f"Error calculating Length of Stay for {location_id}: {e}")
        logger.error(traceback.format_exc())
        return {'los': 0, 'total_attendance': 0}
    finally:
        # Close both connections
        if traffic_conn:
            traffic_conn.close()
        if los_conn:
            los_conn.close()

def get_camera_data_batch(cameras):
    """
    Fetch both region and aggregated count data for multiple cameras in parallel.
    Returns a dictionary with camera_id as key and both types of data.
    """
    print (f"get_camera_data_batch: {cameras} =================================================")
    import concurrent.futures
    import threading
    
    camera_data = {}
    token = "bearer_token_for_api"
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get the mapping to find location for each camera
    cameras_by_location = get_cameras_by_location()
    
    def get_camera_location(camera_id):
        """Find which location a camera belongs to"""
        for location_id, location_cameras in cameras_by_location.items():
            for cam in location_cameras:
                if cam['id'] == camera_id:
                    return location_id
        return None
    
    def get_start_time_for_camera(camera_id):
        """Get start_time from location settings for this camera"""
        location_id = get_camera_location(camera_id)
        if location_id:
            location_settings = location_settings_store.get(location_id, {})
            start_time_setting = location_settings.get('startTime')
            
            if start_time_setting:
                try:
                    time_parts = start_time_setting.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    second = int(time_parts[2])
                    
                    now = datetime.now()
                    return now.replace(hour=hour, minute=minute, second=second, microsecond=0)
                except (ValueError, IndexError):
                    logger.error(f"Error parsing start_time for camera {camera_id}: {start_time_setting}")
        
        # Default to start of day
        now = datetime.now()
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def fetch_camera_region_data(camera):
        camera_id = camera['id']
        try:
            # Use local database access instead of HTTP API call
            data = get_last_results_local(camera_name=camera_id, limit=1)
            region_count = 0
            
            if isinstance(data, list) and len(data) > 0:
                latest_data = data[0]
                region_count = latest_data.get('region_count', 0) or 0
            elif isinstance(data, dict) and 'region_count' in data:
                region_count = data['region_count'] or 0
            elif isinstance(data, dict) and 'regions' in data:
                region_count = sum(region.get('count', 0) for region in data['regions'])
            elif isinstance(data, dict) and 'error' in data:
                logger.debug(f"No region data available for camera {camera_id}: {data['error']}")
                region_count = 0
            
            return camera_id, 'region', region_count
            
        except Exception as e:
            logger.error(f"Error fetching region data for camera {camera_id}: {e}")
        return camera_id, 'region', 0
    
    def fetch_camera_aggregated_data(camera):
        camera_id = camera['id']
        try:
            # Get start_time from location settings for this specific camera
            start_time = get_start_time_for_camera(camera_id)
            
            now = datetime.now()
            start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
            end_time_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # Use local version instead of HTTP API call
            data = get_aggregated_counts_local(camera_id=camera_id, start_time=start_time_str, end_time=end_time_str)
            
            if data and 'data' in data and len(data['data']) > 0:
                total_in = sum(item.get('total_in', 0) for item in data['data'])
                total_out = sum(item.get('total_out', 0) for item in data['data'])
                return camera_id, 'aggregated', {'total_in': total_in, 'total_out': total_out}
        except Exception as e:
            logger.error(f"Error fetching aggregated data for camera {camera_id}: {e}")
        return camera_id, 'aggregated', {'total_in': 0, 'total_out': 0}
    
    # Use ThreadPoolExecutor to fetch data in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(cameras) * 2, 20)) as executor:
        # Submit all tasks
        future_to_camera = {}
        
        for camera in cameras:
            future_region = executor.submit(fetch_camera_region_data, camera)
            future_aggregated = executor.submit(fetch_camera_aggregated_data, camera)
            future_to_camera[future_region] = (camera['id'], 'region')
            future_to_camera[future_aggregated] = (camera['id'], 'aggregated')
        
        # Collect results
        for future in concurrent.futures.as_completed(future_to_camera):
            camera_id, data_type, result = future.result()
            
            if camera_id not in camera_data:
                camera_data[camera_id] = {}
            
            if data_type == 'region':
                camera_data[camera_id]['region_count'] = result
            else:
                camera_data[camera_id]['aggregated'] = result
    
    return camera_data

# Cache for LOS data with execution timestamps
los_cache = {}
CACHE_DURATION_SECONDS = 60  # 1 minute

def cache_with_interval(interval_seconds=60):
    """
    Decorator that caches function results and only re-executes when the interval has passed.
    
    Args:
        interval_seconds (int): Minimum seconds between function executions
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key based on function name and arguments
            cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            current_time = time.time()
            
            # Check if we have cached data and if it's still valid
            if cache_key in los_cache:
                cached_data = los_cache[cache_key]
                time_since_execution = current_time - cached_data['timestamp']
                
                if time_since_execution < interval_seconds:
                    logger.debug(f"Using cached LOS data for {args[0] if args else 'unknown'} (age: {time_since_execution:.1f}s)")
                    return cached_data['result']
            
            # Execute the function if cache is expired or doesn't exist
            logger.debug(f"Executing LOS calculation for {args[0] if args else 'unknown'}")
            result = func(*args, **kwargs)
            
            # Cache the result with current timestamp
            los_cache[cache_key] = {
                'result': result,
                'timestamp': current_time
            }
            
            return result
        
        return wrapper
    return decorator

# Apply the decorator to your LOS calculation function
@cache_with_interval(interval_seconds=60)  # 1 minute cache
def calculate_length_of_stay_cached(location_id, update_time=None):
    """
    Cached version of calculate_length_of_stay that only executes every 1 minute.
    """
    return calculate_length_of_stay(location_id, update_time)

# Add this new function after the existing LOS functions (around line 1783)

def get_length_of_stay_with_interval(location_id, interval_minutes=15):
    """
    Get Length of Stay for a location with database-backed interval caching.
    
    First checks the LOS database for recent calculations (within interval_minutes).
    If found, returns the cached value. Otherwise, calculates new LOS and stores it.
    
    Args:
        location_id (str): The location ID to get LOS for
        interval_minutes (int): Interval in minutes to consider data as fresh (default: 15)
    
    Returns:
        dict: Contains 'los' (length of stay in minutes) and 'total_attendance'
    """
    current_time = datetime.now()
    current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Calculate the cutoff time for "recent" data
    cutoff_time = current_time - timedelta(minutes=interval_minutes)
    cutoff_time_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
    
    los_conn = None
    
    try:
        # Connect to LOS database
        los_conn = get_backend_server_db_connection()
        los_cursor = los_conn.cursor()
        
        # Create the LOS table if it doesn't exist
        los_cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_los (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                los_value REAL NOT NULL,
                total_attendance INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        los_conn.commit()
        
        # Check for recent LOS data within the interval
        los_cursor.execute("""
            SELECT los_value, total_attendance, timestamp
            FROM location_los 
            WHERE location_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (location_id, cutoff_time_str))
        
        recent_los_record = los_cursor.fetchone()
        
        if recent_los_record:
            # Found recent data, return it
            los_value = recent_los_record[0]
            total_attendance = recent_los_record[1]
            timestamp = recent_los_record[2]
            
            logger.debug(f"Using cached LOS for {location_id}: {los_value:.2f} mins from {timestamp}")
            
            return {
                'los': round(los_value, 2),
                'total_attendance': total_attendance,
                'cached': True,
                'timestamp': timestamp
            }
        
        else:
            # No recent data found, calculate new LOS
            logger.debug(f"No recent LOS data for {location_id} within {interval_minutes} minutes, calculating new LOS")
            
            # Close LOS connection before calling calculate_length_of_stay
            # as it will open its own connections
            los_conn.close()
            los_conn = None
            
            # Calculate new LOS using the existing function
            result = calculate_length_of_stay(location_id, current_time)
            
            # Add metadata to indicate this was freshly calculated
            result['cached'] = False
            result['timestamp'] = current_time_str
            
            return result
            
    except Exception as e:
        logger.error(f"Error getting LOS with interval for {location_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Fallback to direct calculation if database operations fail
        try:
            result = calculate_length_of_stay(location_id, current_time)
            result['cached'] = False
            result['timestamp'] = current_time_str
            return result
        except Exception as calc_error:
            logger.error(f"Fallback LOS calculation also failed: {calc_error}")
            return {'los': 0, 'total_attendance': 0, 'cached': False, 'timestamp': current_time_str}
    
    finally:
        if los_conn:
            los_conn.close()

# Update the cached function to use the new interval-based function
def calculate_length_of_stay_cached_15min(location_id):
    """
    Cached version that uses 15-minute database-backed interval checking.
    This replaces the old in-memory cache with persistent database storage.
    """
    return get_length_of_stay_with_interval(location_id, interval_minutes=15)

# Add this function after the LOS caching functions (around line 1905)

def get_hourly_attendance_with_cache(location_id, interval_minutes=15):
    """
    Get hourly attendance data with database-backed caching.
    
    First checks the database for recent calculations (within interval_minutes).
    If found, returns the cached data. Otherwise, calculates new data and stores it.
    
    Args:
        location_id (str): The location ID to get hourly attendance for
        interval_minutes (int): Interval in minutes to consider data as fresh (default: 15)
    
    Returns:
        list: Hourly attendance data for past 24 hours
    """
    current_time = datetime.now()
    current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Calculate the cutoff time for "recent" data
    cutoff_time = current_time - timedelta(minutes=interval_minutes)
    cutoff_time_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
    
    los_conn = None
    
    try:
        # Connect to LOS database (reusing the same database for caching)
        los_conn = get_backend_server_db_connection()
        los_cursor = los_conn.cursor()
        
        # Create the hourly attendance cache table if it doesn't exist
        los_cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_hourly_attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                hourly_data TEXT NOT NULL,
                calculation_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        los_conn.commit()
        
        # Check for recent hourly attendance data within the interval
        los_cursor.execute("""
            SELECT hourly_data, calculation_type, timestamp
            FROM location_hourly_attendance 
            WHERE location_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (location_id, cutoff_time_str))
        
        recent_attendance_record = los_cursor.fetchone()
        
        if recent_attendance_record:
            # Found recent data, return it
            hourly_data_json = recent_attendance_record[0]
            calculation_type = recent_attendance_record[1]
            timestamp = recent_attendance_record[2]
            
            # Parse the JSON data back to list
            import json
            hourly_data = json.loads(hourly_data_json)
            
            logger.debug(f"Using cached hourly attendance for {location_id} ({calculation_type}): from {timestamp}")
            
            return hourly_data
        
        else:
            # No recent data found, calculate new hourly attendance
            logger.info(f"No recent hourly attendance data for {location_id} within {interval_minutes} minutes, calculating new data")
            
            # Get the appropriate calculation function
            attendance_function = get_hourly_attendance_function(location_id)
            
            # Determine calculation type for logging
            calculation_type = "region-based" if attendance_function.__name__ == "generate_hourly_attendance_data_batch_region" else "in_out-based"
            
            # Calculate new hourly attendance data
            hourly_data = attendance_function(location_id)
            
            # Convert to JSON for storage
            import json
            hourly_data_json = json.dumps(hourly_data)
            
            # Store the new calculation in database
            los_cursor.execute("""
                INSERT INTO location_hourly_attendance (location_id, hourly_data, calculation_type, timestamp)
                VALUES (?, ?, ?, ?)
            """, (location_id, hourly_data_json, calculation_type, current_time_str))
            
            los_conn.commit()
            
            logger.debug(f"Calculated and cached new hourly attendance for {location_id} ({calculation_type}): {len(hourly_data)} hours")
            
            return hourly_data
            
    except Exception as e:
        logger.error(f"Error getting hourly attendance with cache for {location_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Fallback to direct calculation if database operations fail
        try:
            attendance_function = get_hourly_attendance_function(location_id)
            result = attendance_function(location_id)
            logger.warning(f"Used fallback calculation for {location_id} hourly attendance")
            return result
        except Exception as calc_error:
            logger.error(f"Fallback hourly attendance calculation also failed: {calc_error}")
            return [0] * 24  # Return 24 hours of zeros as last resort
    
    finally:
        if los_conn:
            los_conn.close()

# Update the existing function to use caching by default
def get_hourly_attendance_function_cached(location_id, use_cache=True, interval_minutes=15):
    """
    Get hourly attendance data with optional caching.
    
    Args:
        location_id (str): The location ID
        use_cache (bool): Whether to use caching (default: True)
        interval_minutes (int): Cache interval in minutes (default: 15)
    
    Returns:
        list: Hourly attendance data for past 24 hours
    """
    if use_cache:
        return get_hourly_attendance_with_cache(location_id, interval_minutes)
    else:
        # Direct calculation without caching
        attendance_function = get_hourly_attendance_function(location_id)
        return attendance_function(location_id)



if __name__ == '__main__':
    logger.info("WW backend started")
    
    # Create location alerts table if it doesn't exist
    alert_monitor.create_location_alerts_table_if_not_exist()
    
    # Start alert monitoring thread
    threading.Thread(target=check_send_alerts).start()
    
    # Initialize and start Kafka consumer
    try:
        kafka_consumer = AlertKafkaConsumer(socketio)
        kafka_consumer.start()
        logger.info("✅ Kafka consumer initialized and started")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Kafka consumer: {e}")
        kafka_consumer = None
    
    # Start the SocketIO server
    socketio.run(app, host='0.0.0.0', port=8002)
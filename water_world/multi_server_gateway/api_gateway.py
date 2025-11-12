from flask import Flask, request, jsonify, make_response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import os
import time
import threading
import requests
from datetime import datetime, timedelta
import hashlib
import jwt
from functools import wraps
from urllib.parse import quote
import traceback
import sqlite3
import sys
# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import setup_logging
import concurrent.futures
from typing import List, Dict, Any, Optional
import socketio

# Add parent directory to Python path to access logging_config
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from logging_config import setup_logging

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio_server = SocketIO(app, logger=False, engineio_logger=False, cors_allowed_origins="*")

# Initialize logging
logger = setup_logging('api_gateway')

class APIGateway:
    def __init__(self):
        self.backend_servers = []
        self.load_config()
        self.session = requests.Session()  # Reuse HTTP connections
        
    def load_config(self):
        """Load API Gateway configuration"""
        config_file = 'api_gateway_config.json'
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            # Default configuration
            config = {
                "backend_servers": [
                    {"url": "http://localhost:8002", "name": "backend1"},
                    {"url": "http://localhost:8003", "name": "backend2"},
                    # {"url": "http://localhost:8004", "name": "backend3"}
                ],
                "JWT_SECRET_KEY": "jwt-key-for-api",
                "TOKEN_EXPIRATION": 86400,
                "TIMEOUT": 10,
                "MAX_WORKERS": 10
            }
            # Save default config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
        
        self.backend_servers = config['backend_servers']
        self.JWT_SECRET_KEY = config['JWT_SECRET_KEY']
        self.TOKEN_EXPIRATION = config['TOKEN_EXPIRATION']
        self.TIMEOUT = config.get('TIMEOUT', 10)
        self.MAX_WORKERS = config.get('MAX_WORKERS', 10)
        
        logger.info(f"Loaded {len(self.backend_servers)} backend servers: {[s['name'] for s in self.backend_servers]}")

    def forward_request_to_backends(self, endpoint: str, method: str = 'GET', 
                                  json_data: dict = None, params: dict = None, 
                                  headers: dict = None, aggregate: bool = True) -> Dict[str, Any]:
        """
        Forward request to all backend servers and aggregate responses.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            json_data: JSON payload for POST/PUT requests
            params: Query parameters
            headers: Request headers
            aggregate: Whether to aggregate responses or return all individual responses
        
        Returns:
            Aggregated response or list of individual responses
        """
        responses = {}
        
        def make_request(server: dict) -> tuple:
            """Make request to a single backend server"""
            try:
                url = f"{server['url']}{endpoint}"
                
                request_kwargs = {
                    'timeout': self.TIMEOUT,
                    'headers': headers or {},
                    'params': params or {}
                }
                
                if json_data:
                    request_kwargs['json'] = json_data
                
                if method.upper() == 'GET':
                    response = self.session.get(url, **request_kwargs)
                elif method.upper() == 'POST':
                    response = self.session.post(url, **request_kwargs)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, **request_kwargs)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, **request_kwargs)
                else:
                    return server['name'], {'error': f'Unsupported method: {method}', 'status_code': 405}
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        return server['name'], {'data': data, 'status_code': 200, 'success': True}
                    except ValueError:
                        return server['name'], {'data': response.text, 'status_code': 200, 'success': True}
                else:
                    try:
                        error_data = response.json()
                        return server['name'], {'error': error_data, 'status_code': response.status_code, 'success': False}
                    except ValueError:
                        return server['name'], {'error': response.text, 'status_code': response.status_code, 'success': False}
                        
            except requests.exceptions.Timeout:
                return server['name'], {'error': 'Request timeout', 'status_code': 408, 'success': False}
            except requests.exceptions.ConnectionError:
                return server['name'], {'error': 'Connection error', 'status_code': 503, 'success': False}
            except Exception as e:
                return server['name'], {'error': str(e), 'status_code': 500, 'success': False}
        
        # Make requests to all backend servers in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            future_to_server = {executor.submit(make_request, server): server for server in self.backend_servers}
            
            for future in concurrent.futures.as_completed(future_to_server):
                server_name, response = future.result()
                responses[server_name] = response
        
        # Log results
        successful_responses = [name for name, resp in responses.items() if resp.get('success', False)]
        failed_responses = [name for name, resp in responses.items() if not resp.get('success', False)]
        
        logger.info(f"{method} {endpoint}: Success: {successful_responses}, Failed: {failed_responses}")
        
        if not aggregate:
            return {'responses': responses}
        
        return self.aggregate_responses(responses, endpoint)

    def aggregate_responses(self, responses: Dict[str, Dict], endpoint: str) -> Dict[str, Any]:
        """Aggregate responses from multiple backend servers based on endpoint type"""
        
        successful_responses = {name: resp for name, resp in responses.items() if resp.get('success', False)}
        
        if not successful_responses:
            # No successful responses
            error_details = {name: resp.get('error', 'Unknown error') for name, resp in responses.items()}
            return {
                'error': 'All backend servers failed',
                'details': error_details,
                'status_code': 503
            }
        
        # For most endpoints, return the first successful response
        if len(successful_responses) == 1:
            first_response = list(successful_responses.values())[0]
            return first_response['data']
        
        # Special aggregation logic for specific endpoints
        if endpoint == '/all_locations_people_count':
            return self.aggregate_people_count_responses(successful_responses)
        elif endpoint.startswith('/location_stats/'):
            return self.aggregate_location_stats_responses(successful_responses)
        elif endpoint == '/recent_alerts':
            return self.aggregate_alerts_responses(successful_responses)
        elif endpoint == '/locations':
            return self.aggregate_locations_responses(successful_responses)
        elif endpoint == '/cameras':
            return self.aggregate_cameras_responses(successful_responses)
        else:
            # For other endpoints, return the first successful response
            first_response = list(successful_responses.values())[0]
            result = first_response['data']
            result['_gateway_info'] = {
                'successful_backends': list(successful_responses.keys()),
                'failed_backends': [name for name in responses.keys() if name not in successful_responses]
            }
            return result

    def aggregate_people_count_responses(self, responses: Dict[str, Dict]) -> Dict[str, Any]:
        """Aggregate people count data from multiple backends"""
        aggregated = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'locations': {},
            '_gateway_info': {
                'successful_backends': list(responses.keys()),
                'aggregation_method': 'sum'
            }
        }
        
        for server_name, response in responses.items():
            data = response['data']
            if 'locations' in data:
                for location_id, location_data in data['locations'].items():
                    if location_id not in aggregated['locations']:
                        aggregated['locations'][location_id] = {
                            'name': location_data.get('name', location_id),
                            'total_region': 0,
                            'total_in': 0,
                            'total_out': 0,
                            'camera_counts_region': {},
                            'camera_counts_in': {},
                            'camera_counts_out': {}
                        }
                    
                    # Sum the totals
                    aggregated['locations'][location_id]['total_region'] += location_data.get('total_region', 0)
                    aggregated['locations'][location_id]['total_in'] += location_data.get('total_in', 0)
                    aggregated['locations'][location_id]['total_out'] += location_data.get('total_out', 0)
                    
                    # Merge camera counts
                    for camera_id, count in location_data.get('camera_counts_region', {}).items():
                        aggregated['locations'][location_id]['camera_counts_region'][camera_id] = count
                    
                    for camera_id, count in location_data.get('camera_counts_in', {}).items():
                        aggregated['locations'][location_id]['camera_counts_in'][camera_id] = count
                    
                    for camera_id, count in location_data.get('camera_counts_out', {}).items():
                        aggregated['locations'][location_id]['camera_counts_out'][camera_id] = count
        
        return aggregated

    def aggregate_location_stats_responses(self, responses: Dict[str, Dict]) -> Dict[str, Any]:
        """Aggregate location stats from multiple backends"""
        # For location stats, merge data from all backends
        aggregated = {
            'alertCounts': {'yellow': 0, 'orange': 0, 'red': 0, 'black': 0},
            'currentAlert': None,
            'hourlyAttendance': [0] * 24,
            'lengthOfStay': {'los': 0, 'total_attendance': 0},
            'totalRegion': 0,
            'totalIn': 0,
            'totalOut': 0,
            'cameraCountsRegion': {},
            'cameraCountsIn': {},
            'cameraCountsOut': {},
            '_gateway_info': {
                'successful_backends': list(responses.keys()),
                'aggregation_method': 'merge'
            }
        }
        
        latest_alert_timestamp = None
        
        for server_name, response in responses.items():
            data = response['data']
            
            # Sum alert counts
            if 'alertCounts' in data:
                for level, count in data['alertCounts'].items():
                    if level in aggregated['alertCounts']:
                        aggregated['alertCounts'][level] += count
            
            # Keep the most recent alert
            if 'currentAlert' in data and data['currentAlert'] and data['currentAlert'].get('timestamp'):
                alert_timestamp = data['currentAlert']['timestamp']
                if latest_alert_timestamp is None or alert_timestamp > latest_alert_timestamp:
                    latest_alert_timestamp = alert_timestamp
                    aggregated['currentAlert'] = data['currentAlert']
            
            # Sum hourly attendance
            if 'hourlyAttendance' in data and isinstance(data['hourlyAttendance'], list):
                for i, count in enumerate(data['hourlyAttendance']):
                    if i < len(aggregated['hourlyAttendance']):
                        aggregated['hourlyAttendance'][i] += count
            
            # Average length of stay (weighted by total attendance)
            if 'lengthOfStay' in data:
                los_data = data['lengthOfStay']
                if isinstance(los_data, dict):
                    attendance = los_data.get('total_attendance', 0)
                    los_value = los_data.get('los', 0)
                    
                    if attendance > 0:
                        # Weighted average
                        current_total = aggregated['lengthOfStay']['total_attendance']
                        current_los = aggregated['lengthOfStay']['los']
                        
                        new_total = current_total + attendance
                        if new_total > 0:
                            aggregated['lengthOfStay']['los'] = (current_los * current_total + los_value * attendance) / new_total
                            aggregated['lengthOfStay']['total_attendance'] = new_total
            
            # Sum totals and merge camera counts
            aggregated['totalRegion'] += data.get('totalRegion', 0)
            aggregated['totalIn'] += data.get('totalIn', 0)
            aggregated['totalOut'] += data.get('totalOut', 0)
            
            for camera_id, count in data.get('cameraCountsRegion', {}).items():
                aggregated['cameraCountsRegion'][camera_id] = count
            
            for camera_id, count in data.get('cameraCountsIn', {}).items():
                aggregated['cameraCountsIn'][camera_id] = count
            
            for camera_id, count in data.get('cameraCountsOut', {}).items():
                aggregated['cameraCountsOut'][camera_id] = count
        
        return aggregated

    def aggregate_alerts_responses(self, responses: Dict[str, Dict]) -> Dict[str, Any]:
        """Aggregate recent alerts from multiple backends"""
        all_alerts = []
        total_count = 0
        
        for server_name, response in responses.items():
            data = response['data']
            if 'alerts' in data:
                all_alerts.extend(data['alerts'])
            
            if 'pagination' in data and 'total_count' in data['pagination']:
                total_count += data['pagination']['total_count']
        
        # Sort alerts by timestamp (most recent first)
        all_alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Get pagination info from first response as template
        first_response = list(responses.values())[0]['data']
        pagination = first_response.get('pagination', {})
        page_size = pagination.get('page_size', 50)
        page = pagination.get('page', 1)
        
        # Apply pagination to aggregated results
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_alerts = all_alerts[start_index:end_index]
        
        return {
            'alerts': paginated_alerts,
            'pagination': {
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size
            },
            '_gateway_info': {
                'successful_backends': list(responses.keys()),
                'total_alerts_before_pagination': len(all_alerts)
            }
        }

    def aggregate_locations_responses(self, responses: Dict[str, Dict]) -> List[Dict]:
        """Aggregate locations from multiple backends"""
        all_locations = {}
        
        for server_name, response in responses.items():
            data = response['data']
            if isinstance(data, list):
                for location in data:
                    location_id = location.get('id')
                    if location_id and location_id not in all_locations:
                        all_locations[location_id] = location
        
        return list(all_locations.values())

    def aggregate_cameras_responses(self, responses: Dict[str, Dict]) -> Dict[str, Any]:
        """Aggregate cameras from multiple backends"""
        if request.args.get('location_id'):
            # For specific location, merge camera lists
            all_cameras = []
            for server_name, response in responses.items():
                data = response['data']
                if isinstance(data, list):
                    all_cameras.extend(data)
            return all_cameras
        else:
            # For all cameras grouped by location
            all_cameras_by_location = {}
            for server_name, response in responses.items():
                data = response['data']
                if isinstance(data, dict):
                    for location_id, cameras in data.items():
                        if location_id not in all_cameras_by_location:
                            all_cameras_by_location[location_id] = []
                        all_cameras_by_location[location_id].extend(cameras)
            return all_cameras_by_location

# Store connected clients and their subscriptions
connected_clients = {}
client_subscriptions = {}

@socketio_server.on('connect')
def handle_connect():
    client_id = request.sid
    client_ip = request.remote_addr
    connected_clients[client_id] = {
        'ip': client_ip,
        'connected_at': datetime.now(),
        'subscriptions': set()
    }
    
    logger.info(f'Client {client_id} connected from IP: {client_ip}')
    emit('connected', {'client_id': client_id, 'message': 'Connected to API Gateway'})

@socketio_server.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    if client_id in connected_clients:
        del connected_clients[client_id]
    if client_id in client_subscriptions:
        del client_subscriptions[client_id]
    
    logger.info(f'Client {client_id} disconnected')

@socketio_server.on('subscribe')
def handle_subscribe(data):
    """Allow clients to subscribe to specific types of events"""
    client_id = request.sid
    event_types = data.get('events', [])
    
    if client_id not in client_subscriptions:
        client_subscriptions[client_id] = set()
    
    for event_type in event_types:
        client_subscriptions[client_id].add(event_type)
    
    logger.info(f'Client {client_id} subscribed to: {event_types}')
    emit('subscription_confirmed', {'events': list(client_subscriptions[client_id])})

class BackendSocketIOClient:
    """SocketIO client for connecting to backend servers"""
    
    def __init__(self, server_info, message_callback):
        self.server_info = server_info
        self.server_name = server_info['name']
        self.server_url = server_info['url']
        self.message_callback = message_callback
        self.client = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
    def connect(self):
        """Connect to backend SocketIO server"""
        try:
            self.client = socketio.Client(logger=False, engineio_logger=False)
            self.setup_handlers()
            
            logger.info(f"Attempting to connect to backend: {self.server_name} at {self.server_url}")
            self.client.connect(self.server_url, wait_timeout=10)
            
            self.connected = True
            self.reconnect_attempts = 0
            logger.info(f"✅ Connected to backend WebSocket: {self.server_name}")
            
        except Exception as e:
            self.connected = False
            logger.error(f"❌ Failed to connect to backend {self.server_name}: {e}")
            
    def setup_handlers(self):
        """Setup event handlers for the SocketIO client"""
        
        @self.client.event
        def connect():
            logger.info(f"✅ SocketIO connected to backend: {self.server_name}")
            self.connected = True
            self.reconnect_attempts = 0
            
        @self.client.event
        def disconnect():
            logger.warning(f"⚠️ SocketIO disconnected from backend: {self.server_name}")
            self.connected = False
            
        @self.client.event
        def connect_error(data):
            logger.error(f"❌ SocketIO connection error to {self.server_name}: {data}")
            self.connected = False
            
        # Handle specific events from backend
        @self.client.on('location_alert')
        def handle_location_alert(data):
            self.message_callback('location_alert', data, self.server_name)
            
        @self.client.on('alert')
        def handle_alert(data):
            self.message_callback('alert', data, self.server_name)
            
        # Generic handler for other events
        @self.client.on('*')
        def handle_any_event(event_name, *args):
            if event_name not in ['connect', 'disconnect', 'connect_error']:
                data = args[0] if args else {}
                self.message_callback(event_name, data, self.server_name)
                
    def disconnect(self):
        """Disconnect from backend server"""
        if self.client and self.connected:
            try:
                self.client.disconnect()
                logger.info(f"Disconnected from backend: {self.server_name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {self.server_name}: {e}")
        self.connected = False
        
    def reconnect(self):
        """Attempt to reconnect to backend server"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting to reconnect to {self.server_name} (attempt {self.reconnect_attempts})")
            
            try:
                if self.client:
                    self.client.disconnect()
            except:
                pass
                
            time.sleep(2 ** self.reconnect_attempts)  # Exponential backoff
            self.connect()
        else:
            logger.error(f"Max reconnection attempts reached for {self.server_name}")

class WebSocketAggregator:
    """Aggregates WebSocket messages from multiple backend servers"""
    
    def __init__(self, gateway_instance):
        self.gateway = gateway_instance
        self.backend_clients = {}
        self.message_buffer = {}
        self.last_emit_time = time.time()
        self.emit_interval = 1.0  # Aggregate messages for 1 second before emitting
        self.running = False
        
    def message_received(self, event_name, data, server_name):
        """Callback when a message is received from a backend server"""
        try:
            # Ensure data is a dictionary
            if isinstance(data, str):
                logger.debug(f"Converting string data to dict from {server_name}: {data}")
                data = {'message': data}
            elif not isinstance(data, dict):
                logger.debug(f"Converting non-dict data to dict from {server_name}: {type(data)}")
                data = {'data': data}
            
            # Add server information to the event
            data['_source_backend'] = server_name
            data['_timestamp'] = datetime.now().isoformat()
            
            # Buffer the message
            if event_name not in self.message_buffer:
                self.message_buffer[event_name] = []
            self.message_buffer[event_name].append(data)
            
            logger.debug(f"Buffered {event_name} from {server_name}: {len(self.message_buffer[event_name])} total")
            
        except Exception as e:
            logger.error(f"Error processing message from {server_name}: {e}")
            
    def start(self):
        """Start the WebSocket aggregator"""
        self.running = True
        
        # Connect to all backend servers
        for server in self.gateway.backend_servers:
            try:
                client = BackendSocketIOClient(server, self.message_received)
                client.connect()
                self.backend_clients[server['name']] = client
                logger.info(f"Connected to SocketIO backend: {server['name']}")
            except Exception as e:
                logger.error(f"Error creating client for {server['name']}: {e}")
        
        # Start the message processing loop
        self.process_messages()
        
    def process_messages(self):
        """Process and emit aggregated messages"""
        logger.info("🔄 Starting WebSocket message aggregation loop")
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check connection status and reconnect if needed
                self.check_connections()
                
                # Emit aggregated messages periodically
                if current_time - self.last_emit_time >= self.emit_interval and self.message_buffer:
                    self.emit_aggregated_messages()
                    self.message_buffer.clear()
                    self.last_emit_time = current_time
                
                time.sleep(0.1)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                logger.error(f"Error in WebSocket aggregation loop: {e}")
                time.sleep(1)
                
    def check_connections(self):
        """Check and maintain connections to backend servers"""
        for server_name, client in self.backend_clients.items():
            if not client.connected:
                logger.debug(f"Backend {server_name} not connected, attempting reconnect")
                threading.Thread(target=client.reconnect, daemon=True).start()
                
    def emit_aggregated_messages(self):
        """Emit aggregated messages to connected clients"""
        try:
            for event_name, messages in self.message_buffer.items():
                if not messages:
                    continue
                                
                # Send to subscribed clients
                sent_to_clients = False
                for client_id, subscriptions in client_subscriptions.items():
                    if not subscriptions or event_name in subscriptions:
                        for l_msg in messages:
                          socketio_server.emit(event_name, l_msg, room=client_id)
                        sent_to_clients = True
                
                # Also emit to all clients if no specific subscriptions
                if not sent_to_clients or not any(client_subscriptions.values()):
                    for l_msg in messages:
                      socketio_server.emit(event_name, l_msg)
                
                logger.debug(f"Emitted aggregated {event_name} with {len(messages)} messages: {messages}")
                
        except Exception as e:
            logger.error(f"Error emitting aggregated messages: {e}")
            
    def stop(self):
        """Stop the WebSocket aggregator"""
        self.running = False
        for client in self.backend_clients.values():
            client.disconnect()

# Initialize the gateway and WebSocket aggregator
gateway = APIGateway()
ws_aggregator = WebSocketAggregator(gateway)

# Token validation decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, gateway.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# ============================================================================
# API GATEWAY ROUTES - All 21 endpoints from the original backend
# ============================================================================

@app.route('/login', methods=['POST'])
def login():
    """Authenticate with the first available backend"""
    response = gateway.forward_request_to_backends('/login', 'POST', json_data=request.get_json())
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/validate_token', methods=['POST'])
@token_required
def validate_token(current_user):
    """Validate token - use local validation since we have the same JWT secret"""
    return jsonify({'valid': True, 'username': current_user})

@app.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """Logout from all backends"""
    headers = {'Authorization': request.headers.get('Authorization')}
    response = gateway.forward_request_to_backends('/logout', 'POST', headers=headers)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/change_password', methods=['POST'])
@token_required
def change_password(current_user):
    """Change password on all backends"""
    headers = {'Authorization': request.headers.get('Authorization')}
    response = gateway.forward_request_to_backends('/change_password', 'POST', 
                                                 json_data=request.get_json(), headers=headers)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/users', methods=['GET'])
@token_required
def get_users(current_user):
    """Get users from first available backend"""
    headers = {'Authorization': request.headers.get('Authorization')}
    response = gateway.forward_request_to_backends('/users', 'GET', headers=headers)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/users', methods=['POST'])
@token_required
def create_user(current_user):
    """Create user on all backends"""
    headers = {'Authorization': request.headers.get('Authorization')}
    response = gateway.forward_request_to_backends('/users', 'POST', 
                                                 json_data=request.get_json(), headers=headers)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/users/<username>', methods=['DELETE'])
@token_required
def delete_user(current_user, username):
    """Delete user from all backends"""
    headers = {'Authorization': request.headers.get('Authorization')}
    response = gateway.forward_request_to_backends(f'/users/{username}', 'DELETE', headers=headers)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/get_location_settings/<location>', methods=['GET'])
def get_location_settings(location):
    """Get location settings from first available backend"""
    response = gateway.forward_request_to_backends(f'/get_location_settings/{location}', 'GET')
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/set_location_settings/<location>', methods=['POST'])
def set_location_settings(location):
    """Set location settings on all backends"""
    response = gateway.forward_request_to_backends(f'/set_location_settings/{location}', 'POST', 
                                                 json_data=request.get_json())
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/recent_alerts', methods=['GET'])
def recent_alerts():
    """Get recent alerts from all backends and aggregate them"""
    params = request.args.to_dict()
    response = gateway.forward_request_to_backends('/recent_alerts', 'GET', params=params)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/acknowledge_alert', methods=['POST', 'OPTIONS'])
def acknowledge_alert():
    """Acknowledge alert on all backends"""
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    response = gateway.forward_request_to_backends('/acknowledge_alert', 'POST', 
                                                 json_data=request.get_json())
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from first available backend"""
    response = gateway.forward_request_to_backends(f'/static/{filename}', 'GET')
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return response

@app.route('/locations', methods=['GET'])
def get_locations_api():
    """Get locations from all backends and merge them"""
    response = gateway.forward_request_to_backends('/locations', 'GET')
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/cameras', methods=['GET'])
def get_cameras():
    """Get cameras from all backends and merge them"""
    params = request.args.to_dict()
    response = gateway.forward_request_to_backends('/cameras', 'GET', params=params)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/location_stats/<location_id>', methods=['GET'])
def get_location_stats(location_id):
    """Get location stats from all backends and aggregate them"""
    response = gateway.forward_request_to_backends(f'/location_stats/{location_id}', 'GET')
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/get_location_by_camera/<camera_id>', methods=['GET'])
def get_location_by_camera(camera_id):
    """Get location by camera from first available backend"""
    response = gateway.forward_request_to_backends(f'/get_location_by_camera/{camera_id}', 'GET')
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/user_preferences', methods=['POST'])
@token_required
def save_user_preference(current_user):
    """Save user preference on all backends"""
    headers = {'Authorization': request.headers.get('Authorization')}
    response = gateway.forward_request_to_backends('/user_preferences', 'POST', 
                                                 json_data=request.get_json(), headers=headers)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/user_preferences/<preference_type>/<user_id>', methods=['GET'])
@token_required
def get_user_preference(current_user, preference_type, user_id):
    """Get user preference from first available backend"""
    headers = {'Authorization': request.headers.get('Authorization')}
    response = gateway.forward_request_to_backends(f'/user_preferences/{preference_type}/{user_id}', 'GET', 
                                                 headers=headers)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/user_preferences/<user_id>', methods=['GET'])
@token_required
def get_all_user_preferences(current_user, user_id):
    """Get all user preferences from first available backend"""
    headers = {'Authorization': request.headers.get('Authorization')}
    response = gateway.forward_request_to_backends(f'/user_preferences/{user_id}', 'GET', headers=headers)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/user_preferences/<preference_type>/<user_id>', methods=['DELETE'])
@token_required
def delete_user_preference(current_user, preference_type, user_id):
    """Delete user preference from all backends"""
    headers = {'Authorization': request.headers.get('Authorization')}
    response = gateway.forward_request_to_backends(f'/user_preferences/{preference_type}/{user_id}', 'DELETE', 
                                                 headers=headers)
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

@app.route('/all_locations_people_count', methods=['GET'])
def get_all_locations_people_count():
    """Get people count from all backends and aggregate them"""
    response = gateway.forward_request_to_backends('/all_locations_people_count', 'GET')
    
    if 'error' in response:
        return jsonify(response), response.get('status_code', 500)
    
    return jsonify(response)

# ============================================================================
# WEBSOCKET/SOCKETIO FUNCTIONALITY
# ============================================================================

# Store connected clients and their subscriptions
connected_clients = {}
client_subscriptions = {}

# Initialize the gateway and WebSocket aggregator
gateway = APIGateway()
ws_aggregator = WebSocketAggregator(gateway)

# ============================================================================
# HEALTH CHECK AND STATUS ENDPOINTS
# ============================================================================

@app.route('/gateway/health', methods=['GET'])
def gateway_health():
    """Health check endpoint for the API Gateway"""
    backend_status = {}
    
    for server in gateway.backend_servers:
        try:
            response = gateway.session.get(f"{server['url']}/locations", timeout=5)
            
            # Check WebSocket connection status
            ws_client = ws_aggregator.backend_clients.get(server['name'])
            ws_status = ws_client.connected if ws_client else False
            
            backend_status[server['name']] = {
                'http_status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'http_status_code': response.status_code,
                'http_response_time_ms': response.elapsed.total_seconds() * 1000,
                'websocket_connected': ws_status
            }
        except Exception as e:
            backend_status[server['name']] = {
                'http_status': 'error',
                'http_error': str(e),
                'http_response_time_ms': None,
                'websocket_connected': False
            }
    
    healthy_backends = sum(1 for status in backend_status.values() 
                          if status.get('http_status') == 'healthy')
    total_backends = len(backend_status)
    
    return jsonify({
        'gateway_status': 'healthy' if healthy_backends > 0 else 'unhealthy',
        'backend_servers': backend_status,
        'healthy_backends': healthy_backends,
        'total_backends': total_backends,
        'connected_websocket_clients': len(connected_clients),
        'websocket_aggregator_running': ws_aggregator.running,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/gateway/config', methods=['GET'])
def gateway_config():
    """Get current gateway configuration"""
    return jsonify({
        'backend_servers': gateway.backend_servers,
        'timeout': gateway.TIMEOUT,
        'max_workers': gateway.MAX_WORKERS,
        'connected_clients': len(connected_clients)
    })

# ============================================================================
# MAIN APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    logger.info("🚀 API Gateway starting...")
    
    # Start WebSocket aggregation in background thread
    def start_websocket_aggregator():
        try:
            ws_aggregator.start()
        except Exception as e:
            logger.error(f"Error in WebSocket aggregator: {e}")
    
    websocket_thread = threading.Thread(target=start_websocket_aggregator, daemon=True)
    websocket_thread.start()
    logger.info("✅ WebSocket aggregation thread started")
    
    # Start the SocketIO server
    logger.info("🌐 Starting API Gateway on port 8001...")
    socketio_server.run(app, host='0.0.0.0', port=7002, debug=False)

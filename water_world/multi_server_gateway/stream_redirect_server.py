from flask import Flask, request, redirect, jsonify, Response
from flask_cors import CORS
import json
import os
import requests
from urllib.parse import urlparse, parse_qs, urlencode
import sys
# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import setup_logging

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize logging
logger = setup_logging('stream_redirect_server')

class StreamRedirectServer:
    def __init__(self):
        self.camera_to_backend = {}
        self.backend_servers = {}
        self.load_config()
        self.build_camera_mapping()
        
    def load_config(self):
        """Load stream redirect configuration"""
        config_file = 'stream_redirect_config.json'
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            # Default configuration
            config = {
                "backend_servers": {
                    "backend1": {
                        "base_url": "http://192.168.primary.ip:5001",
                        "name": "backend1",
                        "description": "Primary backend server",
                        "cameras": ["P1-Ride01", "P1-Ride01-2", "P2-Ride03"]
                    },
                    "backend2": {
                        "base_url": "http://192.168.secondary.ip:5001", 
                        "name": "backend2",
                        "description": "Secondary backend server",
                        "cameras": ["C-2045", "C-2045-2", "C-2022", "C-2023", "C-2023-2", "C-2023-3"]
                    }
                },
                "fallback_backend": "backend1",
                "enable_health_check": True,
                "redirect_method": "HTTP_REDIRECT"  # Options: HTTP_REDIRECT, PROXY
            }
            # Save default config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
        
        self.backend_servers = config['backend_servers']
        self.fallback_backend = config.get('fallback_backend', 'backend1')
        self.enable_health_check = config.get('enable_health_check', True)
        self.redirect_method = config.get('redirect_method', 'HTTP_REDIRECT')
        
        logger.info(f"Loaded {len(self.backend_servers)} backend servers")
        
    def build_camera_mapping(self):
        """Build mapping from camera ID to backend server"""
        self.camera_to_backend = {}
        
        for backend_id, backend_info in self.backend_servers.items():
            cameras = backend_info.get('cameras', [])
            for camera_id in cameras:
                self.camera_to_backend[camera_id] = backend_id
                
        logger.info(f"Built camera mapping for {len(self.camera_to_backend)} cameras")
        logger.debug(f"Camera mapping: {self.camera_to_backend}")
        
    def get_backend_for_camera(self, camera_id: str) -> str:
        """Get the backend server ID for a given camera"""
        backend_id = self.camera_to_backend.get(camera_id)
        
        if not backend_id:
            logger.warning(f"Camera {camera_id} not found in mapping, using fallback backend: {self.fallback_backend}")
            return self.fallback_backend
            
        return backend_id
        
    def get_backend_url(self, backend_id: str) -> str:
        """Get the base URL for a backend server"""
        backend_info = self.backend_servers.get(backend_id)
        if not backend_info:
            logger.error(f"Backend {backend_id} not found in configuration")
            # Use fallback
            fallback_info = self.backend_servers.get(self.fallback_backend)
            return fallback_info['base_url'] if fallback_info else "http://localhost:5001"
            
        return backend_info['base_url']
        
    def build_target_url(self, backend_id: str, path: str, query_params: dict = None) -> str:
        """Build the target URL for redirection"""
        base_url = self.get_backend_url(backend_id)
        
        # Remove leading slash from path if present
        if path.startswith('/'):
            path = path[1:]
            
        target_url = f"{base_url}/{path}"
        
        # Add query parameters if provided
        if query_params:
            query_string = urlencode(query_params)
            target_url = f"{target_url}?{query_string}"
            
        return target_url
        
    def check_backend_health(self, backend_id: str) -> bool:
        """Check if a backend server is healthy"""
        if not self.enable_health_check:
            return True
            
        try:
            backend_url = self.get_backend_url(backend_id)
            # Try a simple health check - you might want to customize this endpoint
            response = requests.get(f"{backend_url}/health", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for backend {backend_id}: {e}")
            return False

# Initialize the redirect server
redirect_server = StreamRedirectServer()

@app.route('/snapshot')
def redirect_snapshot():
    """Redirect snapshot requests to the appropriate backend"""
    camera_id = request.args.get('camera_id')
    
    if not camera_id:
        return jsonify({'error': 'camera_id parameter is required'}), 400
    
    # Get the backend for this camera
    backend_id = redirect_server.get_backend_for_camera(camera_id)
    
    # Check backend health if enabled
    if redirect_server.enable_health_check and not redirect_server.check_backend_health(backend_id):
        logger.warning(f"Backend {backend_id} is unhealthy for camera {camera_id}")
        return jsonify({'error': f'Backend server for camera {camera_id} is unavailable'}), 503
    
    # Build target URL
    query_params = request.args.to_dict()
    target_url = redirect_server.build_target_url(backend_id, 'snapshot', query_params)
    
    logger.info(f"Redirecting snapshot request for camera {camera_id} to {target_url}")
    
    if redirect_server.redirect_method == 'HTTP_REDIRECT':
        # HTTP 302 redirect - browser will make direct request to backend
        return redirect(target_url, code=302)
    else:
        # Proxy mode - fetch and return the image
        try:
            response = requests.get(target_url, timeout=10)
            return Response(
                response.content,
                status=response.status_code,
                headers={'Content-Type': response.headers.get('Content-Type', 'image/jpeg')}
            )
        except Exception as e:
            logger.error(f"Error proxying snapshot request: {e}")
            return jsonify({'error': 'Failed to fetch snapshot'}), 500

@app.route('/stream')
def redirect_stream():
    """Redirect live stream requests to the appropriate backend"""
    camera_id = request.args.get('camera_id')
    
    if not camera_id:
        return jsonify({'error': 'camera_id parameter is required'}), 400
    
    # Get the backend for this camera
    backend_id = redirect_server.get_backend_for_camera(camera_id)
    
    # Check backend health if enabled
    if redirect_server.enable_health_check and not redirect_server.check_backend_health(backend_id):
        logger.warning(f"Backend {backend_id} is unhealthy for camera {camera_id}")
        return jsonify({'error': f'Backend server for camera {camera_id} is unavailable'}), 503
    
    # Build target URL
    query_params = request.args.to_dict()
    target_url = redirect_server.build_target_url(backend_id, 'stream', query_params)
    
    logger.info(f"Redirecting stream request for camera {camera_id} to {target_url}")
    
    # For live streams, always use HTTP redirect to allow direct browser connection
    return redirect(target_url, code=302)

@app.route('/video_feed')
def redirect_video_feed():
    """Redirect video feed requests to the appropriate backend"""
    camera_id = request.args.get('camera_id')
    
    if not camera_id:
        return jsonify({'error': 'camera_id parameter is required'}), 400
    
    # Get the backend for this camera
    backend_id = redirect_server.get_backend_for_camera(camera_id)
    
    # Check backend health if enabled
    if redirect_server.enable_health_check and not redirect_server.check_backend_health(backend_id):
        logger.warning(f"Backend {backend_id} is unhealthy for camera {camera_id}")
        return jsonify({'error': f'Backend server for camera {camera_id} is unavailable'}), 503
    
    # Build target URL
    query_params = request.args.to_dict()
    target_url = redirect_server.build_target_url(backend_id, 'video_feed', query_params)
    
    logger.info(f"Redirecting video feed request for camera {camera_id} to {target_url}")
    
    # For video feeds, always use HTTP redirect
    return redirect(target_url, code=302)

@app.route('/get_stream_url')
def get_stream_url():
    """Get the direct stream URL for a camera (for client-side usage)"""
    camera_id = request.args.get('camera_id')
    stream_type = request.args.get('type', 'stream')  # stream, snapshot, video_feed
    
    if not camera_id:
        return jsonify({'error': 'camera_id parameter is required'}), 400
    
    # Get the backend for this camera
    backend_id = redirect_server.get_backend_for_camera(camera_id)
    
    # Check backend health if enabled
    if redirect_server.enable_health_check and not redirect_server.check_backend_health(backend_id):
        logger.warning(f"Backend {backend_id} is unhealthy for camera {camera_id}")
        return jsonify({'error': f'Backend server for camera {camera_id} is unavailable'}), 503
    
    # Build target URL
    query_params = {'camera_id': camera_id}
    target_url = redirect_server.build_target_url(backend_id, stream_type, query_params)
    
    return jsonify({
        'camera_id': camera_id,
        'stream_url': target_url,
        'backend': backend_id,
        'stream_type': stream_type
    })

@app.route('/camera_mapping')
def get_camera_mapping():
    """Get the camera to backend mapping"""
    return jsonify({
        'camera_mapping': redirect_server.camera_to_backend,
        'backend_servers': {
            backend_id: {
                'base_url': info['base_url'],
                'name': info['name'],
                'cameras': info.get('cameras', [])
            }
            for backend_id, info in redirect_server.backend_servers.items()
        }
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    backend_health = {}
    
    for backend_id in redirect_server.backend_servers.keys():
        backend_health[backend_id] = redirect_server.check_backend_health(backend_id)
    
    overall_health = any(backend_health.values())
    
    return jsonify({
        'status': 'healthy' if overall_health else 'unhealthy',
        'backend_health': backend_health,
        'total_cameras': len(redirect_server.camera_to_backend),
        'redirect_method': redirect_server.redirect_method
    })

@app.route('/reload_config', methods=['POST'])
def reload_config():
    """Reload configuration"""
    try:
        redirect_server.load_config()
        redirect_server.build_camera_mapping()
        logger.info("Configuration reloaded successfully")
        return jsonify({'message': 'Configuration reloaded successfully'})
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("🚀 Stream Redirect Server starting...")
    logger.info("📹 Handling camera stream redirections")
    
    # Start the server
    logger.info("🌐 Starting Stream Redirect Server on port 4001...")
    app.run(host='0.0.0.0', port=4001, debug=False)

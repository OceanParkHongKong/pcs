#!/usr/bin/env python3

import socket
import time
import argparse
import netifaces
import json
import hashlib
import threading
import queue
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from collections import deque
import signal
import sys

class Config:
    def __init__(self, multicast_addr, bind_addr=None, nic=None, interval=0.1, http_port=8008):
        self.multicast_addr = multicast_addr
        self.bind_addr = bind_addr
        self.nic = nic
        self.interval = interval  # Minimum interval between messages
        self.http_port = http_port

class MessageQueue:
    """Thread-safe message queue with priority support"""
    
    def __init__(self, max_size=1000):
        self.high_priority = queue.Queue(maxsize=max_size)
        self.normal_priority = queue.Queue(maxsize=max_size)
        self.stats = {
            'total_queued': 0,
            'total_sent': 0,
            'queue_full_drops': 0,
            'high_priority_count': 0,
            'normal_priority_count': 0
        }
        self.lock = threading.Lock()
    
    def put(self, message, priority='normal'):
        """Add message to queue with priority"""
        try:
            with self.lock:
                if priority == 'high':
                    self.high_priority.put(message, block=False)
                    self.stats['high_priority_count'] += 1
                else:
                    self.normal_priority.put(message, block=False)
                    self.stats['normal_priority_count'] += 1
                
                self.stats['total_queued'] += 1
                return True
        except queue.Full:
            with self.lock:
                self.stats['queue_full_drops'] += 1
            return False
    
    def get(self, timeout=1):
        """Get next message (high priority first)"""
        # Try high priority first
        try:
            message = self.high_priority.get(block=False)
            with self.lock:
                self.stats['high_priority_count'] -= 1
            return message
        except queue.Empty:
            pass
        
        # Then try normal priority
        try:
            message = self.normal_priority.get(timeout=timeout)
            with self.lock:
                self.stats['normal_priority_count'] -= 1
            return message
        except queue.Empty:
            return None
    
    def get_stats(self):
        """Get queue statistics"""
        with self.lock:
            return self.stats.copy()
    
    def size(self):
        """Get current queue sizes"""
        return {
            'high_priority': self.high_priority.qsize(),
            'normal_priority': self.normal_priority.qsize(),
            'total': self.high_priority.qsize() + self.normal_priority.qsize()
        }

# Global variables
message_queue = None
sender_stats = {
    'messages_sent': 0,
    'bytes_sent': 0,
    'errors': 0,
    'start_time': None
}
shutdown_event = threading.Event()

def list_interfaces():
    """List all available network interfaces with their IPs"""
    interfaces = netifaces.interfaces()
    print("Available network interfaces:")
    for iface in interfaces:
        try:
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                ip = addrs[netifaces.AF_INET][0]['addr']
                print(f"- {iface}: {ip}")
            else:
                print(f"- {iface}: (no IPv4)")
        except:
            print(f"- {iface}: (error reading)")
    print()
    return interfaces

def get_interface_ip(interface_name):
    """Get the IP address of a specific interface"""
    try:
        addrs = netifaces.ifaddresses(interface_name)
        if netifaces.AF_INET in addrs:
            return addrs[netifaces.AF_INET][0]['addr']
    except:
        pass
    return None

def create_flask_app():
    """Create Flask app for HTTP API"""
    app = Flask(__name__)
    
    @app.route('/send', methods=['POST'])
    def send_message():
        """Endpoint to queue messages for transmission"""
        try:
            # Get JSON data from request
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            
            # Validate required fields
            if 'data' not in data:
                return jsonify({'error': 'Missing required field: data'}), 400
            
            # Extract message details
            message_data = data['data']
            priority = data.get('priority', 'normal')
            message_type = data.get('type', 'general')
            source = data.get('source', 'unknown')
            
            # Create message for queue
            queued_message = {
                'data': message_data,
                'type': message_type,
                'source': source,
                'received_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'client_ip': request.remote_addr
            }
            
            # Add to queue
            success = message_queue.put(queued_message, priority)
            
            if success:
                queue_stats = message_queue.size()
                return jsonify({
                    'status': 'queued',
                    'priority': priority,
                    'queue_size': queue_stats['total'],
                    'high_priority_queue': queue_stats['high_priority'],
                    'normal_priority_queue': queue_stats['normal_priority']
                }), 200
            else:
                return jsonify({'error': 'Queue is full, message dropped'}), 503
                
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
    @app.route('/status', methods=['GET'])
    def get_status():
        """Get sender status and statistics"""
        queue_stats = message_queue.get_stats()
        queue_size = message_queue.size()
        
        uptime = None
        if sender_stats['start_time']:
            uptime = (datetime.now() - sender_stats['start_time']).total_seconds()
        
        return jsonify({
            'status': 'running',
            'uptime_seconds': uptime,
            'sender_stats': sender_stats,
            'queue_stats': queue_stats,
            'queue_size': queue_size
        })
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Simple health check endpoint"""
        return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
    
    return app

def multicast_sender_thread(conf):
    """Thread function that sends queued messages via multicast"""
    global message_queue, sender_stats, shutdown_event
    
    print("=== MULTICAST SENDER THREAD STARTING ===")
    
    # Parse multicast address and port
    multicast_ip, port = conf.multicast_addr.split(':')
    port = int(port)
    print(f"maddr: {multicast_ip}:{port}")
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Set write buffer size
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 10 * 1024)
        print("Write buffer set to", 10 * 1024)
    except Exception as e:
        print(f"Warning: Could not set write buffer: {e}")
    
    # Configure multicast TTL
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
    
    # Handle bind address
    if conf.bind_addr:
        try:
            bind_ip, bind_port = conf.bind_addr.split(':')
            bind_port = int(bind_port)
            print(f"baddr: {bind_ip}:{bind_port}")
            sock.bind((bind_ip, bind_port))
            print(f"Successfully bound to local address: {conf.bind_addr}")
        except Exception as e:
            print(f"ERROR: Failed to bind to {conf.bind_addr}: {e}")
            return
    
    # Configure specific interface if specified
    if conf.nic:
        available_interfaces = netifaces.interfaces()
        if conf.nic not in available_interfaces:
            print(f"Error: Interface '{conf.nic}' not found.")
            return
        
        interface_ip = get_interface_ip(conf.nic)
        if interface_ip:
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, 
                              socket.inet_aton(interface_ip))
                print(f"Using network interface: {conf.nic} (IP: {interface_ip})")
            except Exception as e:
                print(f"Failed to set multicast interface: {e}")
    
    print(f"Sending queued messages to {conf.multicast_addr}")
    print(f"Minimum interval: {conf.interval} seconds")
    print("===============================================\n")
    
    message_id = 1
    sender_stats['start_time'] = datetime.now()
    
    try:
        while not shutdown_event.is_set():
            # Get message from queue
            queued_message = message_queue.get(timeout=1)
            
            if queued_message is None:
                continue  # Timeout, check shutdown event
            
            # Create final message with sequence ID
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
            final_message = {
                "id": message_id,
                "timestamp": timestamp,
                "sender": "data_diode_sender",
                "sequence_info": {
                    "total_sent": message_id,
                    "queue_size": message_queue.size()['total']
                },
                "payload": queued_message
            }
            
            # Add checksum for data integrity
            message_json = json.dumps(final_message, separators=(',', ':'))
            checksum = hashlib.md5(message_json.encode('utf-8')).hexdigest()
            final_message["checksum"] = checksum
            
            # Create final JSON
            final_json = json.dumps(final_message, separators=(',', ':'))
            
            # Send message
            try:
                sock.sendto(final_json.encode('utf-8'), (multicast_ip, port))
                
                # Update stats
                sender_stats['messages_sent'] += 1
                sender_stats['bytes_sent'] += len(final_json)
                message_queue.stats['total_sent'] += 1
                
                print(f"✅ Sent ID {message_id}: {len(final_json)} bytes [Type: {queued_message.get('type', 'general')}] [Source: {queued_message.get('source', 'unknown')}]")
                message_id += 1
                
            except Exception as e:
                print(f"❌ Error sending message ID {message_id}: {e}")
                sender_stats['errors'] += 1
                # Put message back in queue for retry (with normal priority)
                message_queue.put(queued_message, 'normal')
            
            # Rate limiting
            time.sleep(conf.interval)
            
    except Exception as e:
        print(f"❌ Sender thread error: {e}")
        sender_stats['errors'] += 1
    finally:
        sock.close()
        print("🛑 Multicast sender thread stopped")

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {sig}, shutting down...")
    shutdown_event.set()
    sys.exit(0)

def main():
    global message_queue
    
    parser = argparse.ArgumentParser(description='Data Diode Sender with HTTP API and Message Queuing')
    parser.add_argument('--nic', type=str, help='Network interface name (e.g., eth0, en0)')
    parser.add_argument('--bind', type=str, default='192.168.192.8:1234',
                       help='Local bind address:port (default: 192.168.192.8:1234)')
    parser.add_argument('--interval', type=float, default=0.001, 
                       help='Minimum interval between messages in seconds (default: 0.1)')
    parser.add_argument('--addr', type=str, default='239.252.28.12:5432',
                       help='Multicast address:port (default: 239.252.28.12:5432)')
    parser.add_argument('--http-port', type=int, default=8008,
                       help='HTTP API port (default: 8008)')
    parser.add_argument('--queue-size', type=int, default=1000,
                       help='Maximum queue size (default: 1000)')
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize message queue
    message_queue = MessageQueue(max_size=args.queue_size)
    
    # Create configuration
    conf = Config(
        multicast_addr=args.addr,
        bind_addr=args.bind,
        nic=args.nic,
        interval=args.interval,
        http_port=args.http_port
    )
    
    print("🚀 Starting Data Diode Sender with HTTP API")
    print(f"📡 Multicast: {args.addr}")
    print(f"🌐 HTTP API: http://localhost:{args.http_port}")
    print(f"📦 Queue size: {args.queue_size}")
    print(f"⏱️  Min interval: {args.interval}s")
    print("=" * 50)
    
    # Start multicast sender thread
    sender_thread = threading.Thread(
        target=multicast_sender_thread, 
        args=(conf,),
        daemon=True
    )
    sender_thread.start()
    
    # Create and start Flask app
    app = create_flask_app()
    
    try:
        print(f"🌐 Starting HTTP API on port {conf.http_port}...")
        app.run(host='0.0.0.0', port=conf.http_port, debug=False, threaded=True)
    except Exception as e:
        print(f"❌ HTTP server error: {e}")
        shutdown_event.set()

if __name__ == "__main__":
    main()
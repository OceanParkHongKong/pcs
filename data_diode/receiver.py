#!/usr/bin/env python3
import socket
import struct
import netifaces
import argparse
import json
import hashlib
from collections import deque
from datetime import datetime
from kafka import KafkaProducer
import logging

def get_interface_ip(interface_name):
    """Get the IP address of a specific interface"""
    try:
        addrs = netifaces.ifaddresses(interface_name)
        if netifaces.AF_INET in addrs:
            return addrs[netifaces.AF_INET][0]['addr']
    except:
        pass
    return None

class KafkaForwarder:
    """Handle Kafka message forwarding with error handling and retries"""
    
    def __init__(self, bootstrap_servers=['localhost:9092'], topic='data_diode_messages'):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        self.stats = {
            'messages_sent': 0,
            'send_errors': 0,
            'connection_errors': 0,
            'last_error': None
        }
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self._create_producer()
    
    def _create_producer(self):
        """Create Kafka producer with retry logic"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                # Configuration for reliability
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,   # Retry failed sends
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                # Add timeout settings
                request_timeout_ms=30000,
                # Add this line to fix version compatibility if needed
                # api_version=(0, 10, 1)
            )
            print(f"✅ Connected to Kafka at {self.bootstrap_servers}")
            return True
        except Exception as e:
            self.stats['connection_errors'] += 1
            self.stats['last_error'] = str(e)
            print(f"❌ Failed to create Kafka producer: {e}")
            self.producer = None
            return False
    
    def send_message(self, message_data, message_id=None):
        """Send message to Kafka topic"""
        if not self.producer:
            # Try to reconnect
            if not self._create_producer():
                return False
        
        try:
            # Create Kafka message
            kafka_message = {
                'received_at': datetime.now().isoformat(),
                'data_diode_metadata': {
                    'message_id': message_id,
                    'original_timestamp': message_data.get('timestamp'),
                    'sender': message_data.get('sender'),
                    'sequence_info': message_data.get('sequence_info'),
                    'checksum_verified': True
                },
                'payload': message_data.get('payload', {}),
                'forwarded_by': 'data_diode_receiver'
            }
            
            # Generate key for partitioning (use message_id or sender)
            key = None
            if message_id:
                key = f"msg_{message_id}"
            elif message_data.get('sender'):
                key = message_data.get('sender')
            
            # Send to Kafka
            future = self.producer.send(
                self.topic, 
                value=kafka_message, 
                key=key
            )
            
            # Wait for confirmation (with timeout)
            record_metadata = future.get(timeout=10)
            
            self.stats['messages_sent'] += 1
            
            print(f"📤 Forwarded to Kafka - Topic: {record_metadata.topic}, Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
            return True
            
        except Exception as e:
            self.stats['send_errors'] += 1
            self.stats['last_error'] = str(e)
            print(f"❌ Failed to send to Kafka: {e}")
            
            # Reset producer on connection errors
            if "Connection" in str(e) or "Timeout" in str(e):
                self.producer = None
            
            return False
    
    def get_stats(self):
        """Get Kafka forwarding statistics"""
        return self.stats.copy()
    
    def close(self):
        """Close Kafka producer"""
        if self.producer:
            try:
                self.producer.flush()  # Ensure all messages are sent
                self.producer.close()
                print("🔌 Kafka producer closed")
            except Exception as e:
                print(f"⚠️  Error closing Kafka producer: {e}")

class MessageTracker:
    """Track received messages and detect missing ones"""
    
    def __init__(self, buffer_size=100):
        self.last_id = 0
        self.received_ids = set()
        self.missing_ids = set()
        self.total_received = 0
        self.total_missing = 0
        self.buffer_size = buffer_size
        self.recent_messages = deque(maxlen=buffer_size)
        self.out_of_order_count = 0
        
    def process_message(self, message_id):
        """Process a received message ID and detect missing messages"""
        self.total_received += 1
        self.received_ids.add(message_id)
        self.recent_messages.append(message_id)
        
        # Check for missing messages
        if self.last_id > 0:  # Skip first message
            expected_id = self.last_id + 1
            
            if message_id == expected_id:
                # Perfect sequence
                self.last_id = message_id
            elif message_id > expected_id:
                # Gap detected - mark missing IDs
                for missing_id in range(expected_id, message_id):
                    if missing_id not in self.received_ids:
                        self.missing_ids.add(missing_id)
                        self.total_missing += 1
                        print(f"⚠️  MISSING MESSAGE: ID {missing_id}")
                
                self.last_id = message_id
            else:
                # Out of order or duplicate
                if message_id in self.received_ids:
                    print(f"🔄 DUPLICATE MESSAGE: ID {message_id}")
                else:
                    print(f"📦 OUT-OF-ORDER MESSAGE: ID {message_id} (expected >= {expected_id})")
                    self.out_of_order_count += 1
                    
                    # Remove from missing if it was marked as missing
                    if message_id in self.missing_ids:
                        self.missing_ids.remove(message_id)
                        self.total_missing -= 1
                        print(f"✅ RECOVERED MISSING MESSAGE: ID {message_id}")
        else:
            # First message
            self.last_id = message_id
            print(f"🚀 FIRST MESSAGE: ID {message_id}")
    
    def get_statistics(self):
        """Get current statistics"""
        if self.total_received == 0:
            loss_rate = 0.0
        else:
            total_expected = self.last_id if self.last_id > 0 else 1
            loss_rate = (self.total_missing / total_expected) * 100
        
        return {
            "total_received": self.total_received,
            "total_missing": self.total_missing,
            "out_of_order": self.out_of_order_count,
            "last_id": self.last_id,
            "loss_rate": loss_rate,
            "missing_ids": sorted(list(self.missing_ids))[:10]  # Show first 10 missing
        }

def verify_checksum(message_data):
    """Verify message integrity using checksum"""
    if "checksum" not in message_data:
        return False, "No checksum provided"
    
    received_checksum = message_data.pop("checksum")
    calculated_checksum = hashlib.md5(
        json.dumps(message_data, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    
    # Put checksum back
    message_data["checksum"] = received_checksum
    
    if received_checksum == calculated_checksum:
        return True, "OK"
    else:
        return False, f"Checksum mismatch: expected {calculated_checksum}, got {received_checksum}"

def receive_multicast(mcast_group='239.252.28.12', mcast_port=5432, interface=None, 
                     kafka_enabled=True, kafka_servers=['localhost:9092'], kafka_topic='data_diode_messages'):
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to port (not to multicast address!)
    sock.bind(('', mcast_port))
    
    # Determine interface IP
    if interface:
        interface_ip = get_interface_ip(interface)
        if not interface_ip:
            print(f"Error: Could not get IP for interface {interface}")
            return
        print(f"Using interface {interface} with IP {interface_ip}")
    else:
        interface_ip = '0.0.0.0'  # INADDR_ANY
        print("Using default interface")
    
    # Join multicast group
    mreq = struct.pack('4s4s', 
                      socket.inet_aton(mcast_group), 
                      socket.inet_aton(interface_ip))
    
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        print(f"Successfully joined multicast group {mcast_group}:{mcast_port}")
    except Exception as e:
        print(f"Failed to join multicast group: {e}")
        return
    
    # Initialize Kafka forwarder
    kafka_forwarder = None
    if kafka_enabled:
        kafka_forwarder = KafkaForwarder(kafka_servers, kafka_topic)
        print(f"📡 Kafka forwarding enabled - Topic: {kafka_topic}")
    else:
        print("📡 Kafka forwarding disabled")
    
    print("Waiting for JSON multicast messages...")
    print("===========================================")
    
    tracker = MessageTracker()
    last_stats_time = datetime.now()
    
    try:
        while True:
            data, addr = sock.recvfrom(10240)
            
            try:
                # Parse JSON message
                message_str = data.decode('utf-8')
                message_data = json.loads(message_str)
                
                # Verify required fields
                if "id" not in message_data:
                    print(f"❌ INVALID MESSAGE: Missing ID field")
                    continue
                
                message_id = message_data["id"]
                timestamp = message_data.get("timestamp", "unknown")
                
                # Verify checksum
                is_valid, checksum_msg = verify_checksum(message_data)
                if not is_valid:
                    print(f"❌ CORRUPTED MESSAGE ID {message_id}: {checksum_msg}")
                    continue
                
                # Process message
                tracker.process_message(message_id)
                
                print(f"✅ Received ID {message_id} from {addr} at {timestamp}")
                
                # Forward to Kafka if enabled
                if kafka_forwarder:
                    kafka_success = kafka_forwarder.send_message(message_data, message_id)
                    if not kafka_success:
                        print(f"⚠️  Failed to forward message {message_id} to Kafka")
                
                # Print statistics every 10 seconds
                now = datetime.now()
                if (now - last_stats_time).seconds >= 10:
                    stats = tracker.get_statistics()
                    print(f"\n📊 MULTICAST STATISTICS:")
                    print(f"   Received: {stats['total_received']}")
                    print(f"   Missing: {stats['total_missing']}")
                    print(f"   Out of order: {stats['out_of_order']}")
                    print(f"   Loss rate: {stats['loss_rate']:.2f}%")
                    print(f"   Last ID: {stats['last_id']}")
                    if stats['missing_ids']:
                        print(f"   Missing IDs (sample): {stats['missing_ids']}")
                    
                    # Kafka statistics
                    if kafka_forwarder:
                        kafka_stats = kafka_forwarder.get_stats()
                        print(f"\n📤 KAFKA STATISTICS:")
                        print(f"   Messages sent: {kafka_stats['messages_sent']}")
                        print(f"   Send errors: {kafka_stats['send_errors']}")
                        print(f"   Connection errors: {kafka_stats['connection_errors']}")
                        if kafka_stats['last_error']:
                            print(f"   Last error: {kafka_stats['last_error']}")
                    
                    print("===========================================")
                    last_stats_time = now
                
            except json.JSONDecodeError:
                print(f"❌ INVALID JSON from {addr}: {data[:100]}...")
            except Exception as e:
                print(f"❌ ERROR processing message from {addr}: {e}")
    
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping receiver...")
        
        # Final statistics
        stats = tracker.get_statistics()
        print(f"\n📊 FINAL MULTICAST STATISTICS:")
        print(f"   Total received: {stats['total_received']}")
        print(f"   Total missing: {stats['total_missing']}")
        print(f"   Out of order: {stats['out_of_order']}")
        print(f"   Final loss rate: {stats['loss_rate']:.2f}%")
        print(f"   Last ID: {stats['last_id']}")
        if stats['missing_ids']:
            print(f"   Missing IDs: {stats['missing_ids']}")
        
        # Kafka final statistics
        if kafka_forwarder:
            kafka_stats = kafka_forwarder.get_stats()
            print(f"\n📤 FINAL KAFKA STATISTICS:")
            print(f"   Total sent: {kafka_stats['messages_sent']}")
            print(f"   Send errors: {kafka_stats['send_errors']}")
            print(f"   Connection errors: {kafka_stats['connection_errors']}")
            
    finally:
        # Cleanup
        if kafka_forwarder:
            kafka_forwarder.close()
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Multicast UDP Receiver with Kafka Forwarding')
    parser.add_argument('--interface', type=str, help='Network interface name')
    parser.add_argument('--group', type=str, default='239.252.28.12', help='Multicast group')
    parser.add_argument('--port', type=int, default=5432, help='Multicast port')
    
    # Kafka configuration
    parser.add_argument('--kafka-enabled', action='store_true', default=True, 
                       help='Enable Kafka forwarding (default: enabled)')
    parser.add_argument('--no-kafka', action='store_true', 
                       help='Disable Kafka forwarding')
    parser.add_argument('--kafka-servers', type=str, default='localhost:9092',
                       help='Kafka bootstrap servers (comma-separated)')
    parser.add_argument('--kafka-topic', type=str, default='data_diode_messages',
                       help='Kafka topic name')
    
    args = parser.parse_args()
    
    # Parse Kafka servers
    kafka_servers = [server.strip() for server in args.kafka_servers.split(',')]
    
    # Determine if Kafka should be enabled
    kafka_enabled = args.kafka_enabled and not args.no_kafka
    
    print(f"🚀 Starting Data Diode Receiver")
    print(f"📡 Multicast: {args.group}:{args.port}")
    if kafka_enabled:
        print(f"📤 Kafka: {kafka_servers} -> {args.kafka_topic}")
    else:
        print(f"📤 Kafka: Disabled")
    print("=" * 50)
    
    receive_multicast(
        mcast_group=args.group, 
        mcast_port=args.port, 
        interface=args.interface,
        kafka_enabled=kafka_enabled,
        kafka_servers=kafka_servers,
        kafka_topic=args.kafka_topic
    )
  
  
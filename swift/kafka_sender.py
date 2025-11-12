#!/usr/bin/env python3

import json
import time
import logging
import threading
import queue
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError, NoBrokersAvailable, KafkaConnectionError
import atexit

class AsyncKafkaSender:
    """
    Asynchronous Kafka sender for sending people counting results with retry logic
    """
    
    def __init__(self, bootstrap_servers=['localhost:9092'], topic='people_count_results', 
                 reconnect_delay=60, max_queue_size=1000):
        """
        Initialize AsyncKafka sender
        
        Args:
            bootstrap_servers: List of Kafka bootstrap servers
            topic: Kafka topic name
            reconnect_delay: Delay in seconds before reconnection attempts
            max_queue_size: Maximum number of messages to queue
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.reconnect_delay = reconnect_delay
        self.max_queue_size = max_queue_size
        
        self.producer = None
        self.logger = logging.getLogger(f'async_kafka_sender_{topic}')
        
        # Message queue and threading
        self.message_queue = queue.Queue(maxsize=max_queue_size)
        self.sender_thread = None
        self.running = False
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_queued': 0,
            'messages_dropped': 0,
            'send_errors': 0,
            'connection_errors': 0,
            'reconnection_attempts': 0,
            'last_error': None,
            'last_send_time': None,
            'queue_size': 0,
            'connected': False
        }
        self.stats_lock = threading.Lock()
        
        # Connection management
        self.last_reconnect_time = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        # Register cleanup on exit
        atexit.register(self.stop)
    
    def _create_producer_with_retry(self):
        """Create Kafka producer with retry logic"""
        attempt = 0
        max_attempts = 999999999
        
        while self.running and attempt < max_attempts:
            try:
                self.logger.info(f"🔄 Attempting to connect to Kafka (attempt {attempt + 1})")
                
                producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    # Configuration for reliability and reconnection
                    acks='all',
                    retries=3,
                    max_in_flight_requests_per_connection=1,
                    request_timeout_ms=5000,
                    batch_size=16384,
                    linger_ms=10,
                    buffer_memory=33554432,
                    # Connection settings for better failure detection
                    connections_max_idle_ms=60000,
                    metadata_max_age_ms=30000
                )
                
                # Test the connection
                producer.bootstrap_connected()
                
                with self.stats_lock:
                    self.stats['connected'] = True
                    self.stats['connection_errors'] = 0
                    
                self.consecutive_errors = 0
                self.logger.info(f"✅ Connected to Kafka at {self.bootstrap_servers}")
                return producer
                
            except (NoBrokersAvailable, KafkaConnectionError, KafkaTimeoutError) as e:
                attempt += 1
                with self.stats_lock:
                    self.stats['connection_errors'] += 1
                    self.stats['reconnection_attempts'] += 1
                    self.stats['last_error'] = str(e)
                    self.stats['connected'] = False
                
                self.logger.warning(f"❌ Kafka connection failed (attempt {attempt}): {e}")
                
                if attempt < max_attempts and self.running:
                    self.logger.info(f"⏳ Retrying in 5 seconds...")
                    time.sleep(5)
                    
            except Exception as e:
                self.logger.error(f"❌ Unexpected error creating producer: {e}")
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(2)
        
        with self.stats_lock:
            self.stats['connected'] = False
        return None
    
    def _sender_loop(self):
        """Main sender loop running in separate thread"""
        self.logger.info("🚀 Starting async Kafka sender loop")
        
        while self.running:
            try:
                # Try to create/recreate producer if needed
                if not self.producer:
                    self.producer = self._create_producer_with_retry()
                    if not self.producer:
                        self.logger.error(f"❌ Failed to create producer, retrying in {self.reconnect_delay} seconds")
                        time.sleep(self.reconnect_delay)
                        continue
                
                # Process messages from queue
                try:
                    # Wait for message with timeout
                    message_data = self.message_queue.get(timeout=1.0)
                    
                    if message_data is None:  # Shutdown signal
                        break
                    
                    # Send the message
                    success = self._send_message_sync(message_data)
                    
                    if success:
                        self.consecutive_errors = 0
                        with self.stats_lock:
                            self.stats['messages_sent'] += 1
                            self.stats['last_send_time'] = datetime.now().isoformat()
                            
                    else:
                        self.consecutive_errors += 1
                        with self.stats_lock:
                            self.stats['send_errors'] += 1
                        
                        # Trigger reconnection if too many errors
                        if self.consecutive_errors >= self.max_consecutive_errors:
                            self.logger.error(f"❌ Too many consecutive errors ({self.consecutive_errors}), reconnecting")
                            self._handle_connection_loss()
                    
                    # Update queue size stats
                    with self.stats_lock:
                        self.stats['queue_size'] = self.message_queue.qsize()
                    
                    self.message_queue.task_done()
                    
                except queue.Empty:
                    continue  # Timeout, check if still running
                    
            except (KafkaConnectionError, NoBrokersAvailable, KafkaTimeoutError) as e:
                self.logger.error(f"🔌 Connection error in sender loop: {e}")
                self._handle_connection_loss()
                
            except Exception as e:
                self.logger.error(f"❌ Unexpected error in sender loop: {e}")
                time.sleep(1)
        
        self.logger.info("🛑 Kafka sender loop stopped")
    
    def _send_message_sync(self, message_data):
        """Send message synchronously"""
        try:
            message, key = message_data
            
            future = self.producer.send(
                self.topic,
                value=message,
                key=key
            )
            
            # Wait for result with timeout
            record_metadata = future.get(timeout=5)
            
            self.logger.debug(
                f"📤 Sent to Kafka - Topic: {record_metadata.topic}, "
                f"Partition: {record_metadata.partition}, "
                f"Offset: {record_metadata.offset}, "
                f"Camera: {message.get('camera_name', 'unknown')}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error sending message: {e}")
            with self.stats_lock:
                self.stats['last_error'] = str(e)
            return False
    
    def _handle_connection_loss(self):
        """Handle connection loss"""
        if self.producer:
            try:
                self.producer.close(timeout=5)
            except:
                pass
            self.producer = None
        
        with self.stats_lock:
            self.stats['connected'] = False
        
        self.last_reconnect_time = datetime.now()
        time.sleep(self.reconnect_delay)
    
    def start(self):
        """Start the async sender thread"""
        if self.running:
            self.logger.warning("Async Kafka sender is already running")
            return
        
        self.running = True
        self.sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self.sender_thread.start()
        self.logger.info("✅ Async Kafka sender thread started")
    
    def stop(self):
        """Stop the async sender"""
        if not self.running:
            return
        
        self.logger.info("🛑 Stopping async Kafka sender")
        self.running = False
        
        # Signal shutdown
        try:
            self.message_queue.put(None, timeout=1)
        except queue.Full:
            pass
        
        # Wait for thread to finish
        if self.sender_thread and self.sender_thread.is_alive():
            self.sender_thread.join(timeout=5)
        
        # Close producer
        if self.producer:
            try:
                self.producer.flush(timeout=5)
                self.producer.close(timeout=5)
            except:
                pass
            self.producer = None
        
        self.logger.info("✅ Async Kafka sender stopped")
    
    def send_count_result_async(self, in_count, out_count, region_count, camera_name, timestamp=None):
        """
        Queue a people counting result to be sent to Kafka asynchronously
        
        Args:
            in_count: Number of people entering
            out_count: Number of people exiting  
            region_count: Number of people in region
            camera_name: Name/ID of the camera
            timestamp: Optional timestamp, uses current time if None
        
        Returns:
            bool: True if queued successfully, False if queue is full
        """
        if not self.running:
            self.logger.warning("Async sender not running, cannot queue message")
            return False
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # Create message payload
        message = {
            'camera_name': camera_name,
            'in_count': int(in_count),
            'out_count': int(out_count),
            'region_count': int(region_count),
            'timestamp': timestamp,
            'message_type': 'people_count_result',
            'source': 'swift_people_counter'
        }
        
        try:
            # Try to queue the message (non-blocking)
            self.message_queue.put((message, camera_name), block=False)
            
            with self.stats_lock:
                self.stats['messages_queued'] += 1
                self.stats['queue_size'] = self.message_queue.qsize()
            
            self.logger.debug(f"📥 Queued Kafka message for camera: {camera_name}")
            return True
            
        except queue.Full:
            # Queue is full, drop the message
            with self.stats_lock:
                self.stats['messages_dropped'] += 1
                
            self.logger.warning(f"⚠️ Kafka message queue full, dropping message for camera: {camera_name}")
            return False
    
    def get_stats(self):
        """Get sender statistics"""
        with self.stats_lock:
            stats = self.stats.copy()
            stats['queue_size'] = self.message_queue.qsize()
            return stats
    
    def get_connection_status(self):
        """Get current connection status"""
        with self.stats_lock:
            return {
                'connected': self.stats['connected'],
                'running': self.running,
                'queue_size': self.message_queue.qsize(),
                'connection_errors': self.stats['connection_errors'],
                'reconnection_attempts': self.stats['reconnection_attempts'],
                'last_error': self.stats['last_error'],
                'last_reconnect_time': self.last_reconnect_time.isoformat() if self.last_reconnect_time else None
            }

# Global async Kafka sender instance
_async_kafka_sender = None

def get_async_kafka_sender(bootstrap_servers=['localhost:9092'], topic='people_count_results'):
    """
    Get or create global async Kafka sender instance (singleton pattern)
    
    Args:
        bootstrap_servers: List of Kafka bootstrap servers
        topic: Kafka topic name
        
    Returns:
        AsyncKafkaSender instance
    """
    global _async_kafka_sender
    if _async_kafka_sender is None:
        _async_kafka_sender = AsyncKafkaSender(bootstrap_servers, topic)
        _async_kafka_sender.start()
    return _async_kafka_sender

def send_count_to_kafka_async(in_count, out_count, region_count, camera_name, 
                             bootstrap_servers=['localhost:9092'], topic='people_count_results'):
    """
    Convenience function to send count result to Kafka asynchronously
    
    Args:
        in_count: Number of people entering
        out_count: Number of people exiting
        region_count: Number of people in region
        camera_name: Name/ID of the camera
        bootstrap_servers: List of Kafka bootstrap servers
        topic: Kafka topic name
        
    Returns:
        bool: True if queued successfully, False otherwise
    """
    sender = get_async_kafka_sender(bootstrap_servers, topic)
    return sender.send_count_result_async(in_count, out_count, region_count, camera_name)

def close_async_kafka_sender():
    """Close the global async Kafka sender"""
    global _async_kafka_sender
    if _async_kafka_sender:
        _async_kafka_sender.stop()
        _async_kafka_sender = None

def get_async_kafka_stats():
    """Get async Kafka sender statistics"""
    global _async_kafka_sender
    if _async_kafka_sender:
        return _async_kafka_sender.get_stats()
    return None

# Example usage and testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Kafka sender')
    parser.add_argument('--servers', type=str, default='localhost:9092',
                       help='Kafka bootstrap servers (comma-separated)')
    parser.add_argument('--topic', type=str, default='people_count_results',
                       help='Kafka topic name')
    parser.add_argument('--test-messages', type=int, default=5,
                       help='Number of test messages to send')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Parse servers
    servers = [server.strip() for server in args.servers.split(',')]
    
    print(f"🧪 Testing Kafka sender with {servers} -> {args.topic}")
    
    # Create sender
    sender = get_async_kafka_sender(servers, args.topic)
    
    # Test connection
    status = sender.get_connection_status()
    print(f"Connection status: {status}")
    
    if status['connected']:
        # Send test messages
        print(f"Sending {args.test_messages} test messages...")
        for i in range(args.test_messages):
            success = send_count_to_kafka_async(
                in_count=i,
                out_count=i * 2,
                region_count=i * 3,
                camera_name=f"TEST_CAM_{i % 3 + 1}"
            )
            print(f"Message {i + 1}: {'✅' if success else '❌'}")
            time.sleep(0.5)
        
        # Print statistics
        stats = sender.get_stats()
        print(f"\n📊 Statistics:")
        print(f"   Messages sent: {stats['messages_sent']}")
        print(f"   Send errors: {stats['send_errors']}")
        print(f"   Connection errors: {stats['connection_errors']}")
        print(f"   Messages queued: {stats['messages_queued']}")
        print(f"   Messages dropped: {stats['messages_dropped']}")
        print(f"   Queue size: {stats['queue_size']}")
        if stats['last_error']:
            print(f"   Last error: {stats['last_error']}")
    
    # Close sender
    close_async_kafka_sender()
    print(" Test completed") 
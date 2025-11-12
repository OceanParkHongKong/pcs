#!/usr/bin/env python3

import json
import time
import logging
import threading
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import KafkaError, KafkaTimeoutError, NoBrokersAvailable, KafkaConnectionError
from logging_config import setup_logging

class AlertKafkaConsumer:
    """
    Kafka consumer for people counting results that integrates with alert backend server
    """
    
    def __init__(self, socketio, config_file="config_kafka.json"):
        """
        Initialize Kafka consumer
        
        Args:
            socketio: SocketIO instance from alert backend server
            config_file: Path to Kafka configuration file
        """
        self.socketio = socketio
        
        # Setup logging using shared configuration
        self.logger = setup_logging('kafka_consumer')
        
        # Now load configuration (which uses logger)
        self.config = self._load_config(config_file)
        self.consumer = None
        self.running = False
        self.consumer_thread = None
        
        # Connection management
        self.reconnect_delay = 60  # 1 minute reconnect delay
        self.max_reconnect_attempts = None  # Infinite retries
        self.reconnect_attempts = 0
        self.last_reconnect_time = None
        
        # Statistics
        self.stats = {
            'messages_consumed': 0,
            'messages_sent': 0,
            'kafka_errors': 0,
            'websocket_errors': 0,
            'connection_attempts': 0,
            'reconnect_attempts': 0,
            'start_time': None,
            'last_message_time': None,
            'connected_clients': 0,
            'last_connection_error': None
        }
        
        # Camera data cache (latest values per camera)
        self.camera_cache = {}
        
        # Previous values cache for calculating offsets
        self.camera_previous_values = {}
        
        # Thread lock for thread-safe access
        # self.cache_lock = threading.Lock()
    
    def _load_config(self, config_file):
        """Load Kafka configuration from file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = ['bootstrap_servers', 'topic']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required config field: {field}")
            
            self.logger.info(f"Loaded Kafka config - servers: {config['bootstrap_servers']}, topic: {config['topic']}")
            return config
            
        except FileNotFoundError:
            self.logger.warning(f"Kafka config file '{config_file}' not found, using defaults")
            return {
                "bootstrap_servers": ["localhost:9092"],
                "topic": "people_count_results",
                "group_id": "alert_backend_consumer",
                "auto_offset_reset": "latest"
            }
        except Exception as e:
            self.logger.error(f"Error loading Kafka config: {e}")
            return None
    
    def _create_consumer_with_retry(self):
        """Create Kafka consumer with retry logic"""
        if not self.config:
            self.logger.error("No valid Kafka configuration")
            return None
        
        attempt = 0
        while self.running and (self.max_reconnect_attempts is None or attempt < self.max_reconnect_attempts):
            try:
                self.stats['connection_attempts'] += 1
                self.logger.info(f"🔄 Attempting to connect to Kafka (attempt {attempt + 1})")
                
                consumer = KafkaConsumer(
                    self.config['topic'],
                    bootstrap_servers=self._get_all_servers(),
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                    group_id=self.config.get('group_id', 'alert_backend_consumer'),
                    auto_offset_reset=self.config.get('auto_offset_reset', 'latest'),
                    enable_auto_commit=True,
                    consumer_timeout_ms=1000,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=10000,
                    max_poll_records=100,
                    fetch_min_bytes=1,
                    fetch_max_wait_ms=500,
                    # Connection settings for better failure detection
                    connections_max_idle_ms=60000,
                    request_timeout_ms=31000,
                    metadata_max_age_ms=30000
                )
                
                # Test the connection by getting topic metadata instead
                # This will raise an exception if connection fails
                consumer.topics()  # This method exists and tests connectivity
                
                self.logger.info(f"✅ Kafka consumer connected successfully")
                self.reconnect_attempts = 0
                self.stats['last_connection_error'] = None
                return consumer
                
            except (NoBrokersAvailable, KafkaConnectionError, KafkaTimeoutError) as e:
                attempt += 1
                self.reconnect_attempts += 1
                self.stats['reconnect_attempts'] += 1
                self.stats['last_connection_error'] = str(e)
                self.last_reconnect_time = datetime.now()
                
                self.logger.warning(f"❌ Kafka connection failed (attempt {attempt}): {e}")
                
                if self.running and (self.max_reconnect_attempts is None or attempt < self.max_reconnect_attempts):
                    self.logger.info(f"⏳ Retrying in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)
                else:
                    self.logger.error(f"❌ Max reconnection attempts reached or consumer stopped")
                    break
                    
            except Exception as e:
                self.logger.error(f"❌ Unexpected error creating consumer: {e}")
                attempt += 1
                if self.running and attempt < 3:  # Only retry 3 times for unexpected errors
                    time.sleep(5)
                else:
                    break
        
        return None
    
    def _get_all_servers(self):
        """Get all bootstrap servers from config"""
        all_servers = []
        if isinstance(self.config['bootstrap_servers'], list):
            all_servers.extend(self.config['bootstrap_servers'])
        else:
            all_servers.append(self.config['bootstrap_servers'])
        
        # Add additional servers if configured
        additional_servers = self.config.get('additional_servers', [])
        all_servers.extend(additional_servers)
        
        return all_servers
    
    def _consumer_loop_with_reconnection(self):
        """Main Kafka consumer loop with automatic reconnection"""
        self.logger.info("🚀 Starting Kafka consumer loop with reconnection support")
        
        while self.running:
            try:
                # Create consumer with retry logic
                self.consumer = self._create_consumer_with_retry()
                if not self.consumer:
                    if self.running:
                        self.logger.error(f"❌ Failed to create Kafka consumer, retrying in {self.reconnect_delay} seconds")
                        time.sleep(self.reconnect_delay)
                    continue
                
                # Run the main consumption loop
                self._run_consumption_loop()
                
            except (KafkaConnectionError, NoBrokersAvailable, KafkaTimeoutError) as e:
                self.logger.error(f"🔌 Kafka connection lost: {e}")
                self._handle_connection_loss()
                
            except Exception as e:
                self.logger.error(f"❌ Unexpected error in consumer loop: {e}")
                self._handle_connection_loss()
            
            finally:
                if self.consumer:
                    try:
                        self.consumer.close()
                    except:
                        pass
                    self.consumer = None
    
    def _run_consumption_loop(self):
        """Run the actual message consumption loop"""
        self.logger.info(f"📡 Consuming from topic: {self.config['topic']}")
        
        # Wait for partition assignment
        partition_assigned = False
        assignment_attempts = 0
        max_assignment_attempts = 30
        
        while self.running and not partition_assigned and assignment_attempts < max_assignment_attempts:
            try:
                message_batch = self.consumer.poll(timeout_ms=1000)
                assignment = self.consumer.assignment()
                
                if assignment:
                    partition_assigned = True
                    self.logger.info(f"✅ Partition assignment successful: {assignment}")
                else:
                    assignment_attempts += 1
                    if assignment_attempts % 5 == 0:
                        self.logger.info(f"⏳ Waiting for partition assignment... ({assignment_attempts}/{max_assignment_attempts})")
                
                # Process any messages during assignment
                if message_batch:
                    self._process_message_batch(message_batch)
            
            except Exception as e:
                self.stats['kafka_errors'] += 1
                self.logger.error(f"Error during partition assignment: {e}")
                raise  # Re-raise to trigger reconnection
        
        if not partition_assigned:
            raise Exception("Failed to get partition assignment")
        
        # Main consumption loop
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                if message_batch:
                    self._process_message_batch(message_batch)
                    consecutive_errors = 0  # Reset error counter on successful processing
                    
                time.sleep(0.1)
                
            except (KafkaConnectionError, NoBrokersAvailable, KafkaTimeoutError) as e:
                self.logger.error(f"🔌 Connection error during polling: {e}")
                raise  # Re-raise to trigger reconnection
                
            except Exception as e:
                consecutive_errors += 1
                self.stats['kafka_errors'] += 1
                self.logger.error(f"Error in consumer loop (consecutive: {consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.error(f"❌ Too many consecutive errors ({consecutive_errors}), triggering reconnection")
                    raise
                
                time.sleep(1)
    
    def _handle_connection_loss(self):
        """Handle connection loss and prepare for reconnection"""
        if self.running:
            self.logger.info(f"🔄 Connection lost, will reconnect in {self.reconnect_delay} seconds")
            time.sleep(self.reconnect_delay)
    
    def _create_multi_server_consumer(self):
        """Create consumer that connects to multiple servers"""
        if not self.config:
            self.logger.error("No valid Kafka configuration")
            return None
        
        # Combine all bootstrap servers
        all_servers = []
        if isinstance(self.config['bootstrap_servers'], list):
            all_servers.extend(self.config['bootstrap_servers'])
        else:
            all_servers.append(self.config['bootstrap_servers'])
        
        # Add additional servers if configured
        additional_servers = self.config.get('additional_servers', [])
        all_servers.extend(additional_servers)
        
        try:
            consumer = KafkaConsumer(
                self.config['topic'],
                bootstrap_servers=all_servers,  # Multiple servers here
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                group_id=self.config.get('group_id', 'alert_backend_consumer'),
                auto_offset_reset=self.config.get('auto_offset_reset', 'latest'),
                enable_auto_commit=True,
                consumer_timeout_ms=1000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                max_poll_records=10
            )
            
            self.logger.info(f"✅ Created multi-server consumer connecting to: {all_servers}")
            return consumer
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create multi-server consumer: {e}")
            return None
    
    def _calculate_offsets(self, camera_name, new_in_count, new_out_count, new_region_count):
        """
        Calculate offset values (change since last message) for a camera
        
        Args:
            camera_name: Name of the camera
            new_in_count: New in_count value
            new_out_count: New out_count value
            new_region_count: New region_count value
            
        Returns:
            tuple: (in_count_offset, out_count_offset, region_count_offset, is_first_message)
        """
        # with self.cache_lock:
        # Check if we have previous values for this camera
        if camera_name not in self.camera_previous_values:
            # First message from this camera
            self.camera_previous_values[camera_name] = {
                'in_count': new_in_count,
                'out_count': new_out_count,
                'region_count': new_region_count,
                'first_seen': datetime.now().isoformat()
            }
            # For first message, offsets are 0 or the current values (depending on your preference)
            return 0, 0, 0, True
        
        # Calculate offsets
        prev_values = self.camera_previous_values[camera_name]
        in_count_offset = new_in_count - prev_values['in_count']
        out_count_offset = new_out_count - prev_values['out_count']
        region_count_offset = new_region_count - prev_values['region_count']
        
        # Update previous values
        self.camera_previous_values[camera_name] = {
            'in_count': new_in_count,
            'out_count': new_out_count,
            'region_count': new_region_count,
            'last_updated': datetime.now().isoformat()
        }
        
        return in_count_offset, out_count_offset, region_count_offset, False
    
    def _process_people_count_message(self, message):
        """
        Process a people count message from Kafka
        
        Args:
            message: Kafka message containing people count data
            
        Returns:
            dict: Processed message data or None if invalid
        """
        try:
            value = message.value
            
            # Validate message structure
            required_fields = ['camera_name', 'in_count', 'out_count', 'region_count', 'timestamp']
            for field in required_fields:
                if field not in value:
                    self.logger.warning(f"Missing required field '{field}' in message")
                    return None
            
            camera_name = value['camera_name']
            new_in_count = value['in_count']
            new_out_count = value['out_count']
            new_region_count = value['region_count']
            
            # Calculate offsets
            in_count_offset, out_count_offset, region_count_offset, is_first_message = self._calculate_offsets(
                camera_name, new_in_count, new_out_count, new_region_count
            )
            
            # Create processed message with offset information
            processed_message = {
                'type': 'people_count_update',
                'camera_name': camera_name,
                'counts': {
                    'in_count': new_in_count,
                    'out_count': new_out_count,
                    'region_count': new_region_count
                },
                'offsets': {
                    'in_count_offset': in_count_offset,
                    'out_count_offset': out_count_offset,
                    'region_count_offset': region_count_offset
                },
                'timestamp': value['timestamp'],
                'source': value.get('source', 'unknown'),
                'is_first_message': is_first_message,
                'kafka_metadata': {
                    'partition': message.partition,
                    'offset': message.offset,
                    'kafka_timestamp': message.timestamp,
                    'key': message.key
                },
                'processed_at': datetime.now().isoformat()
            }
            
            # Update camera cache with both current values and offsets
            # with self.cache_lock:
            self.camera_cache[camera_name] = {
                'in_count': new_in_count,
                'out_count': new_out_count,
                'region_count': new_region_count,
                'in_count_offset': in_count_offset,
                'out_count_offset': out_count_offset,
                'region_count_offset': region_count_offset,
                'timestamp': value['timestamp'],
                'is_first_message': is_first_message,
                'last_updated': datetime.now().isoformat()
            }
            
            # Log offset information for debugging
            if not is_first_message:
                self.logger.debug(f"Camera {camera_name} offsets - In: {in_count_offset:+d}, Out: {out_count_offset:+d}, Region: {region_count_offset:+d}")
            
            return processed_message
            
        except Exception as e:
            self.logger.error(f"Error processing Kafka message: {e}")
            return None
    
    def _send_to_websocket(self, message_data):
        """
        Send processed message to WebSocket clients
        
        Args:
            message_data: Processed message data
        """
        try:
            # Send to all connected clients
            self.socketio.emit('people_count_update', message_data)
            
            # Send camera-specific updates
            # camera_name = message_data.get('camera_name')
            # if camera_name:
            #     self.socketio.emit(f'camera_update_{camera_name}', message_data)
            
            # Send location-specific updates (if camera belongs to a location)
            # location_id = self._get_location_by_camera(camera_name)
            # if location_id:
            #     self.socketio.emit(f'location_update', message_data)
            
            self.stats['messages_sent'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            self.logger.debug(f"Sent WebSocket message for camera: {message_data.get('camera_name')}")
            
        except Exception as e:
            self.stats['websocket_errors'] += 1
            self.logger.error(f"Error sending WebSocket message: {e}")
    
    def _get_location_by_camera(self, camera_name):
        """
        Get location ID for a camera (integrate with your existing camera mapping)
        
        Args:
            camera_name: Name of the camera
            
        Returns:
            str: Location ID or None if not found
        """
        # Import the camera mapping from alert_backend_server
        try:
            from alert_backend_server import get_cameras_by_location
            cameras_by_location = get_cameras_by_location()
            
            for location_id, cameras in cameras_by_location.items():
                for camera in cameras:
                    if camera['id'] == camera_name:
                        return location_id
        except ImportError:
            pass
        
        return None
    
    def _process_message_batch(self, message_batch):
        """Process a batch of Kafka messages"""
        for topic_partition, messages in message_batch.items():
            for message in messages:
                if not self.running:
                    break
                
                self.stats['messages_consumed'] += 1
                
                self.logger.debug(f"Received Kafka message - Key: {message.key}, Camera: {message.value.get('camera_name', 'unknown')}")
                
                # Process and send the message
                processed_message = self._process_people_count_message(message)
                if processed_message:
                    self._send_to_websocket(processed_message)
    
    def start(self):
        """Start the Kafka consumer in a separate thread"""
        if self.running:
            self.logger.warning("Kafka consumer is already running")
            return
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Use the new consumer loop with reconnection
        self.consumer_thread = threading.Thread(target=self._consumer_loop_with_reconnection, daemon=True)
        self.consumer_thread.start()
        
        self.logger.info("✅ Kafka consumer thread started with reconnection support")
    
    def stop(self):
        """Stop the Kafka consumer"""
        if not self.running:
            return
        
        self.logger.info("🛑 Stopping Kafka consumer")
        self.running = False
        
        if self.consumer_thread and self.consumer_thread.is_alive():
            self.consumer_thread.join(timeout=5)
        
        self.logger.info("✅ Kafka consumer stopped")
    
    def get_camera_offsets(self, camera_name=None):
        """
        Get offset information for cameras
        
        Args:
            camera_name: Specific camera name, or None for all cameras
            
        Returns:
            dict: Camera offset data
        """
        # with self.cache_lock:
        if camera_name:
            cache_data = self.camera_cache.get(camera_name, {})
            return {
                'camera_name': camera_name,
                'in_count_offset': cache_data.get('in_count_offset', 0),
                'out_count_offset': cache_data.get('out_count_offset', 0),
                'region_count_offset': cache_data.get('region_count_offset', 0),
                'last_updated': cache_data.get('last_updated')
            }
        else:
            offset_data = {}
            for cam_name, cache_data in self.camera_cache.items():
                offset_data[cam_name] = {
                    'in_count_offset': cache_data.get('in_count_offset', 0),
                    'out_count_offset': cache_data.get('out_count_offset', 0),
                    'region_count_offset': cache_data.get('region_count_offset', 0),
                    'last_updated': cache_data.get('last_updated')
                }
            return offset_data
    
    def reset_camera_offsets(self, camera_name=None):
        """
        Reset offset tracking for cameras (useful for resetting the baseline)
        
        Args:
            camera_name: Specific camera name, or None for all cameras
        """
        # with self.cache_lock:
        if camera_name:
            if camera_name in self.camera_previous_values:
                del self.camera_previous_values[camera_name]
                self.logger.info(f"Reset offset tracking for camera: {camera_name}")
        else:
            self.camera_previous_values.clear()
            self.logger.info("Reset offset tracking for all cameras")
    
    def get_location_summary(self, location_id):
        """
        Get aggregated data for a location (including offset totals)
        
        Args:
            location_id: Location identifier
            
        Returns:
            dict: Aggregated location data with offsets
        """
        try:
            from alert_backend_server import get_cameras_by_location
            cameras_by_location = get_cameras_by_location()
            location_cameras = cameras_by_location.get(location_id, [])
            
            total_in = 0
            total_out = 0
            total_region = 0
            total_in_offset = 0
            total_out_offset = 0
            total_region_offset = 0
            camera_data = {}
            
            # with self.cache_lock:
            for camera in location_cameras:
                camera_id = camera['id']
                cache_data = self.camera_cache.get(camera_id, {})
                
                if cache_data:
                    total_in += cache_data.get('in_count', 0)
                    total_out += cache_data.get('out_count', 0)
                    total_region += cache_data.get('region_count', 0)
                    total_in_offset += cache_data.get('in_count_offset', 0)
                    total_out_offset += cache_data.get('out_count_offset', 0)
                    total_region_offset += cache_data.get('region_count_offset', 0)
                    camera_data[camera_id] = cache_data
            
            return {
                'location_id': location_id,
                'totals': {
                    'total_in': total_in,
                    'total_out': total_out,
                    'total_region': total_region
                },
                'offsets': {
                    'total_in_offset': total_in_offset,
                    'total_out_offset': total_out_offset,
                    'total_region_offset': total_region_offset
                },
                'camera_count': len(location_cameras),
                'active_cameras': len(camera_data),
                'camera_data': camera_data,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting location summary: {e}")
            return {} 

    def get_connection_status(self):
        """Get current connection status and statistics"""
        return {
            'connected': self.consumer is not None,
            'running': self.running,
            'connection_attempts': self.stats['connection_attempts'],
            'reconnect_attempts': self.stats['reconnect_attempts'],
            'last_reconnect_time': self.last_reconnect_time.isoformat() if self.last_reconnect_time else None,
            'last_connection_error': self.stats['last_connection_error'],
            'kafka_errors': self.stats['kafka_errors'],
            'messages_consumed': self.stats['messages_consumed'],
            'uptime': (datetime.now() - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
        } 
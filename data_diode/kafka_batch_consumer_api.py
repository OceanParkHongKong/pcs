#!/usr/bin/env python3

from kafka import KafkaConsumer
import json
import sys
import os
import requests
from datetime import datetime
import time

def load_api_config():
    """
    Load API configuration from config_api.json file
    """
    # Default configuration
    default_config = {
        "api_base_url": "http://localhost:5000",
        "secret_token": "bearer_token_for_api",
        "timeout": 30,
        "retry_attempts": 3,
        "retry_delay": 2
    }
    
    # Try to load from local config_api.json file
    config_file = os.path.join(os.path.dirname(__file__), 'config_api.json')
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                
            # Map config file keys to our internal keys
            config = default_config.copy()
            config["api_base_url"] = file_config.get("api_base_url", file_config.get("api_url", default_config["api_base_url"]))
            config["secret_token"] = file_config.get("secret_token", file_config.get("auth_token", default_config["secret_token"]))
            config["timeout"] = file_config.get("timeout", default_config["timeout"])
            config["retry_attempts"] = file_config.get("retry_attempts", default_config["retry_attempts"])
            config["retry_delay"] = file_config.get("retry_delay", default_config["retry_delay"])
            
            print(f"✅ Loaded configuration from {config_file}")
            return config
        else:
            print(f"⚠️ Config file {config_file} not found, using defaults")
            print(f"💡 Create {config_file} with the following structure:")
            print(json.dumps({
                "api_base_url": "http://your.server.ip:5000",
                "secret_token": "your_actual_secret_token_here",
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 2
            }, indent=2))
            
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing {config_file}: {e}")
        print(f"🔧 Using default configuration")
    except Exception as e:
        print(f"❌ Error loading {config_file}: {e}")
        print(f"🔧 Using default configuration")
    
    return default_config

def post_to_api(record_data, api_config):
    """
    Post a single record to the remote counting-results API
    
    Args:
        record_data (dict): Individual camera record data
        api_config (dict): API configuration
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Ensure the API base URL doesn't end with /counting-results already
    base_url = api_config['api_base_url'].rstrip('/')
    if base_url.endswith('/counting-results'):
        url = base_url
    else:
        url = f"{base_url}/counting-results"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_config['secret_token']}"
    }
    
    # Prepare the payload according to the API format
    payload = {
        "camera_id": record_data.get('camera_name', 'Unknown'),
        "timestamp": record_data.get('timestamp'),
        "in_count": record_data.get('in_count', 0),
        "out_count": record_data.get('out_count', 0),
        "region_count": record_data.get('region_count', 0)
    }
    
    # Retry logic
    for attempt in range(api_config['retry_attempts']):
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=api_config['timeout']
            )
            
            if response.status_code == 201:
                print(f"✅ API Success: {payload['camera_id']} @ {payload['timestamp']} - In:{payload['in_count']} Out:{payload['out_count']} Region:{payload['region_count']}")
                return True
            elif response.status_code == 401:
                print(f"❌ API Authentication failed - check token")
                return False
            elif response.status_code == 400:
                print(f"❌ API Bad Request: {response.text}")
                return False
            else:
                print(f"⚠️ API Error {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"⚠️ API Timeout (attempt {attempt + 1}/{api_config['retry_attempts']})")
        except requests.exceptions.ConnectionError:
            print(f"⚠️ API Connection Error (attempt {attempt + 1}/{api_config['retry_attempts']})")
        except Exception as e:
            print(f"⚠️ API Unexpected Error: {e} (attempt {attempt + 1}/{api_config['retry_attempts']})")
        
        # Wait before retry (except for last attempt)
        if attempt < api_config['retry_attempts'] - 1:
            time.sleep(api_config['retry_delay'])
    
    print(f"❌ API Failed after {api_config['retry_attempts']} attempts: {payload}")
    return False

def process_batch_records(batch_data, api_config):
    """
    Process batch data and post individual camera records to remote API
    
    Args:
        batch_data (dict): Batch data containing multiple camera records
        api_config (dict): API configuration
    
    Returns:
        tuple: (success_count, error_count)
    """
    success_count = 0
    error_count = 0
    
    # Extract records from batch data
    records = batch_data.get('data', {}).get('records', [])
    
    if not records:
        print("⚠️ No records found in batch data")
        return success_count, error_count
    
    # Process each camera record in the batch
    for record in records:
        try:
            # Extract data for each camera
            timestamp = record.get('timestamp')
            in_count = record.get('in_count', 0)
            out_count = record.get('out_count', 0)
            region_count = record.get('region_count', 0)
            camera_name = record.get('camera_name', 'Unknown')
            ip = record.get('ip', '')
            
            # Validate required fields
            if not timestamp or not camera_name:
                print(f"⚠️ Missing required fields in record: {record}")
                error_count += 1
                continue
            
            # Post to remote API
            record_data = {
                'timestamp': timestamp,
                'in_count': in_count,
                'out_count': out_count,
                'region_count': region_count,
                'camera_name': camera_name,
                'ip': ip
            }
            
            if post_to_api(record_data, api_config):
                success_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            print(f"❌ Error processing record: {e}")
            print(f"   Record: {record}")
            error_count += 1
    
    return success_count, error_count

def consume_batch_messages():
    """
    Consume Kafka messages containing batch traffic data and post to remote API
    """
    # Load API configuration
    api_config = load_api_config()
    print(f"🔗 API Configuration:")
    print(f"   Base URL: {api_config['api_base_url']}")
    print(f"   Token: {'*' * (len(api_config['secret_token']) - 4) + api_config['secret_token'][-4:]}")
    print(f"   Timeout: {api_config['timeout']}s")
    print(f"   Retry attempts: {api_config['retry_attempts']}")
    
    consumer = KafkaConsumer(
        'data_diode_messages',
        bootstrap_servers=['localhost:9092'],
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='latest',  # Start from latest messages
        enable_auto_commit=True
    )
    
    print("🎯 Consuming batch traffic data from Kafka...")
    print("📡 Will post individual camera records to remote API")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    total_batches = 0
    total_records_processed = 0
    total_records_success = 0
    total_records_errors = 0
    
    try:
        for message in consumer:
            data = message.value
            
            # Extract metadata
            metadata = data.get('data_diode_metadata', {})
            payload = data.get('payload', {})
            
            print(f"\n📨 Received batch from Kafka:")
            print(f"   Partition: {message.partition}, Offset: {message.offset}")
            print(f"   Message ID: {metadata.get('message_id', 'unknown')}")
            print(f"   Original Sender: {metadata.get('sender', 'unknown')}")
            print(f"   Payload Type: {payload.get('type', 'unknown')}")
            print(f"   Payload Source: {payload.get('source', 'unknown')}")
            
            # Check if this is a traffic data batch
            if payload.get('type') == 'traffic_data_batch':
                batch_info = payload.get('data', {})
                batch_number = batch_info.get('batch_number', 'unknown')
                total_batches_in_set = batch_info.get('total_batches', 'unknown')
                records_count = len(batch_info.get('records', []))
                
                print(f"   Batch: {batch_number}/{total_batches_in_set}")
                print(f"   Records in batch: {records_count}")
                
                # Process the batch
                success_count, error_count = process_batch_records(payload, api_config)
                
                # Update counters
                total_batches += 1
                total_records_processed += records_count
                total_records_success += success_count
                total_records_errors += error_count
                
                print(f"   ✅ Successfully posted: {success_count}/{records_count} records")
                if error_count > 0:
                    print(f"   ❌ Errors: {error_count} records")
                
                # Show running totals every 5 batches
                if total_batches % 5 == 0:
                    print(f"\n📈 Running totals:")
                    print(f"   Batches processed: {total_batches}")
                    print(f"   Total records: {total_records_processed}")
                    print(f"   Successful: {total_records_success}")
                    print(f"   Errors: {total_records_errors}")
            else:
                print(f"   ⚠️ Skipping non-batch message type: {payload.get('type')}")
            
            print("-" * 60)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Consumer stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        consumer.close()
        print(f"\n📊 Final Statistics:")
        print(f"   Total batches processed: {total_batches}")
        print(f"   Total records processed: {total_records_processed}")
        print(f"   Successful records: {total_records_success}")
        print(f"   Failed records: {total_records_errors}")
        if total_records_processed > 0:
            success_rate = (total_records_success / total_records_processed) * 100
            print(f"   Success rate: {success_rate:.1f}%")

def test_api_connection():
    """Test API connection and authentication"""
    print("🧪 Testing API connection...")
    api_config = load_api_config()
    
    # Test with a sample record
    test_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'in_count': 1,
        'out_count': 2,
        'region_count': 3,
        'camera_name': 'TestCamera-Kafka-API',
        'ip': '192.168.1.100'
    }
    
    if post_to_api(test_data, api_config):
        print("✅ API test successful")
        return True
    else:
        print("❌ API test failed")
        return False

def create_sample_config():
    """Create a sample config_api.json file"""
    config_file = os.path.join(os.path.dirname(__file__), 'config_api.json')
    
    if os.path.exists(config_file):
        print(f"⚠️ Config file {config_file} already exists")
        return
    
    sample_config = {
        "api_base_url": "http://192.168.1.100:5000",
        "secret_token": "bearer_token_for_api",
        "timeout": 30,
        "retry_attempts": 3,
        "retry_delay": 2
    }
    
    try:
        with open(config_file, 'w') as f:
            json.dump(sample_config, f, indent=2)
        print(f"✅ Created sample config file: {config_file}")
        print("🔧 Please edit the file with your actual API settings")
    except Exception as e:
        print(f"❌ Error creating config file: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Kafka Consumer for Batch Traffic Data - API Version')
    parser.add_argument('--test-api', action='store_true',
                       help='Test API connection and exit')
    parser.add_argument('--create-config', action='store_true',
                       help='Create a sample config_api.json file')
    parser.add_argument('--api-url', type=str,
                       help='Override API base URL (e.g., http://192.168.1.100:5000)')
    parser.add_argument('--token', type=str,
                       help='Override authentication token')
    
    args = parser.parse_args()
    
    if args.create_config:
        create_sample_config()
        sys.exit(0)
    
    # Override configuration if provided via command line
    if args.api_url or args.token:
        original_load_config = load_api_config
        def load_api_config():
            config = original_load_config()
            if args.api_url:
                config['api_base_url'] = args.api_url
            if args.token:
                config['secret_token'] = args.token
            return config
    
    if args.test_api:
        test_api_connection()
    else:
        consume_batch_messages()

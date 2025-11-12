#!/usr/bin/env python3

import json
import os
import sys
import time
import argparse
import requests
from datetime import datetime, timezone

# Add the swift directory to the path to import database_sqlite
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'swift'))
import database_sqlite as database

TIMESTAMP_FILE = "last_timestamp.json"

def load_last_timestamps():
    """
    Load the last timestamps per camera from JSON file.
    Returns a dictionary: {camera_name: last_timestamp}
    If file doesn't exist, return empty dict (will use today 00:00:00 for each camera)
    """
    if os.path.exists(TIMESTAMP_FILE):
        try:
            with open(TIMESTAMP_FILE, 'r') as f:
                data = json.load(f)
                # Handle both old format (single timestamp) and new format (per-camera)
                if 'last_timestamp' in data:
                    # Old format - convert to new format
                    old_timestamp = data['last_timestamp']
                    print(f"Converting old timestamp format: {old_timestamp}")
                    return {'_global': old_timestamp}  # Use global key for migration
                elif 'cameras' in data:
                    # New format
                    timestamps = data['cameras']
                    print(f"Loaded timestamps for {len(timestamps)} cameras")
                    for camera, timestamp in timestamps.items():
                        print(f"  {camera}: {timestamp}")
                    return timestamps
        except Exception as e:
            print(f"Error reading timestamp file: {e}")
    
    print("No existing timestamp file found, will start from today 00:00:00 for each camera")
    return {}

def save_last_timestamps(camera_timestamps):
    """
    Save the last processed timestamp per camera to JSON file
    camera_timestamps: dict {camera_name: timestamp_str}
    """
    try:
        data = {
            'cameras': camera_timestamps,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(TIMESTAMP_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved timestamps for {len(camera_timestamps)} cameras")
        for camera, timestamp in camera_timestamps.items():
            print(f"  {camera}: {timestamp}")
    except Exception as e:
        print(f"Error saving timestamps: {e}")

def get_default_start_time():
    """Get today at 00:00:00 as default start time"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start.strftime('%Y-%m-%d %H:%M:%S')

def get_data_since_timestamps(camera_timestamps):
    """
    Get all traffic data from database since the given timestamps per camera.
    camera_timestamps: dict {camera_name: last_timestamp}
    Returns list of records ordered by timestamp, camera_name
    """
    try:
        conn = database.connect_db()
        cursor = conn.cursor()
        
        # First, get all unique cameras if we don't have any timestamps yet
        if not camera_timestamps:
            cursor.execute('SELECT DISTINCT camera_name FROM traffic ORDER BY camera_name')
            cameras = [row[0] for row in cursor.fetchall()]
            default_time = get_default_start_time()
            camera_timestamps = {camera: default_time for camera in cameras}
            print(f"Initialized timestamps for {len(cameras)} cameras to {default_time}")
        
        # Handle migration from old global timestamp
        if '_global' in camera_timestamps:
            global_timestamp = camera_timestamps['_global']
            cursor.execute('SELECT DISTINCT camera_name FROM traffic ORDER BY camera_name')
            cameras = [row[0] for row in cursor.fetchall()]
            camera_timestamps = {camera: global_timestamp for camera in cameras}
            print(f"Migrated global timestamp {global_timestamp} to {len(cameras)} cameras")
        
        all_data = []
        
        # Query data for each camera individually
        for camera_name, last_timestamp in camera_timestamps.items():
            query = '''
            SELECT timestamp, in_count, out_count, region_count, camera_name, ip
            FROM traffic 
            WHERE camera_name = ? AND timestamp > ? 
            ORDER BY timestamp ASC
            '''
            
            cursor.execute(query, (camera_name, last_timestamp))
            rows = cursor.fetchall()
            
            for row in rows:
                all_data.append({
                    'timestamp': row[0],
                    'in_count': row[1],
                    'out_count': row[2],
                    'region_count': row[3],
                    'camera_name': row[4],
                    'ip': row[5]
                })
            
            print(f"Found {len(rows)} new records for camera {camera_name} since {last_timestamp}")
        
        # Sort all data by timestamp, then by camera_name for consistent ordering
        all_data.sort(key=lambda x: (x['timestamp'], x['camera_name']))
        
        cursor.close()
        conn.close()
        
        print(f"Total: {len(all_data)} new records across all cameras")
        return all_data, camera_timestamps
        
    except Exception as e:
        print(f"Error querying database: {e}")
        return [], camera_timestamps

def send_to_data_diode(data, message_type="database_record", source="database_sender", priority="normal", sender_url="http://localhost:8008"):
    """
    Send data to the data diode sender via HTTP POST
    
    Args:
        data: The data to send
        message_type: Type of message
        source: Source identifier
        priority: Message priority ('normal' or 'high')
        sender_url: URL of the sender API
    
    Returns:
        (success: bool, response_data: dict or error_message: str)
    """
    payload = {
        "data": data,
        "type": message_type,
        "source": source,
        "priority": priority
    }
    
    try:
        response = requests.post(
            f"{sender_url}/send",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5  # 5 second timeout
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"

def check_sender_status(sender_url="http://localhost:8008"):
    """Check if the sender API is available and get its status"""
    try:
        response = requests.get(f"{sender_url}/health", timeout=2)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"

def send_database_data(sender_url="http://localhost:8008", interval=0.1, batch_size=1):
    """
    Main function to read database data and send via HTTP POST to sender API
    
    Args:
        sender_url (str): URL of the sender API
        interval (float): Interval between messages in seconds
        batch_size (int): Number of records to send at once (1 = individual records)
    """
    print("=== Database to Data Diode Sender (HTTP API) ===")
    print(f"Sender API URL: {sender_url}")
    print(f"Message interval: {interval} seconds")
    print(f"Batch size: {batch_size}")
    print("=" * 50)
    
    # Check if sender API is available
    print("Checking sender API availability...")
    available, status = check_sender_status(sender_url)
    if available:
        print(f"✅ Sender API is available: {status}")
    else:
        print(f"❌ Sender API is not available: {status}")
        print("Make sure sender.py is running and accessible")
        return
    
    # Load last timestamps per camera
    camera_timestamps = load_last_timestamps()
    
    # Get data from database
    data_records, updated_timestamps = get_data_since_timestamps(camera_timestamps)
    
    if not data_records:
        print("No new data to send.")
        return
    
    print(f"Sending {len(data_records)} records...")
    print("Press Ctrl+C to stop...")
    
    sent_count = 0
    error_count = 0
    # Track the latest timestamp per camera
    latest_timestamps = updated_timestamps.copy()
    
    try:
        # Send records individually or in batches
        if batch_size == 1:
            # Send individual records
            for i, record in enumerate(data_records):
                # Add metadata to the record
                enhanced_record = {
                    **record,
                    'sent_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    'sequence_number': i + 1,
                    'total_records': len(data_records)
                }
                
                # Send to data diode
                success, result = send_to_data_diode(
                    enhanced_record, 
                    message_type="traffic_data",
                    source="database_sender",
                    priority="normal",
                    sender_url=sender_url
                )
                
                if success:
                    sent_count += 1
                    queue_size = result.get('queue_size', 'unknown')
                    print(f"✅ Sent [{sent_count}/{len(data_records)}]: {record['camera_name']} @ {record['timestamp']} - In:{record['in_count']} Out:{record['out_count']} Region:{record['region_count']} CameraID: {record['camera_name']} [Queue: {queue_size}]")
                    
                    # Update the latest timestamp for this camera
                    latest_timestamps[record['camera_name']] = record['timestamp']
                else:
                    error_count += 1
                    print(f"❌ Failed to send record {sent_count + error_count}: {result}")
                    # Optionally break on too many errors
                    if error_count > 10:
                        print("Too many errors, stopping...")
                        break
                
                # Wait between messages
                if interval > 0:
                    time.sleep(interval)
        
        else:
            # Send in batches
            for i in range(0, len(data_records), batch_size):
                batch = data_records[i:i + batch_size]
                
                # Create batch payload
                batch_data = {
                    'batch_number': (i // batch_size) + 1,
                    'total_batches': (len(data_records) + batch_size - 1) // batch_size,
                    'records': batch,
                    'sent_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
                
                # Send batch to data diode
                success, result = send_to_data_diode(
                    batch_data,
                    message_type="traffic_data_batch",
                    source="database_sender",
                    priority="normal",
                    sender_url=sender_url
                )
                
                if success:
                    sent_count += len(batch)
                    queue_size = result.get('queue_size', 'unknown')
                    print(f"✅ Sent batch [{batch_data['batch_number']}/{batch_data['total_batches']}]: {len(batch)} records [Queue: {queue_size}]")
                    
                    # Update latest timestamps for all cameras in this batch
                    for record in batch:
                        latest_timestamps[record['camera_name']] = record['timestamp']
                else:
                    error_count += len(batch)
                    print(f"❌ Failed to send batch {batch_data['batch_number']}: {result}")
                
                # Wait between batches
                if interval > 0:
                    time.sleep(interval)
    
    except KeyboardInterrupt:
        print(f"\nStopped by user. Sent {sent_count} messages, {error_count} errors.")
    
    # Save the latest timestamps per camera
    if sent_count > 0:
        save_last_timestamps(latest_timestamps)
        print(f"Updated timestamps for all cameras")
    
    print(f"Completed. Sent {sent_count}/{len(data_records)} records, {error_count} errors.")
    
    # Get final sender status
    try:
        available, status_data = check_sender_status(sender_url)
        if available:
            response = requests.get(f"{sender_url}/status", timeout=2)
            if response.status_code == 200:
                final_stats = response.json()
                sender_stats = final_stats.get('sender_stats', {})
                queue_stats = final_stats.get('queue_stats', {})
                
                print(f"\n📊 Final Sender Statistics:")
                print(f"   Messages sent: {sender_stats.get('messages_sent', 'unknown')}")
                print(f"   Bytes sent: {sender_stats.get('bytes_sent', 'unknown')}")
                print(f"   Queue drops: {queue_stats.get('queue_full_drops', 0)}")
    except:
        pass  # Don't fail if we can't get final stats

def main():
    parser = argparse.ArgumentParser(description='Send database records via HTTP POST to data diode sender API')
    parser.add_argument('--sender-url', type=str, default='http://localhost:8008',
                       help='Data diode sender API URL (default: http://localhost:8008)')
    parser.add_argument('--interval', type=float, default=0.1,
                       help='Interval between messages in seconds (default: 0.1)')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of records to send per message (default: 1)')
    parser.add_argument('--reset-timestamp', action='store_true',
                       help='Reset all camera timestamps to today 00:00:00')
    parser.add_argument('--show-timestamp', action='store_true',
                       help='Show current saved timestamps per camera and exit')
    parser.add_argument('--check-sender', action='store_true',
                       help='Check sender API status and exit')
    
    args = parser.parse_args()
    
    if args.check_sender:
        print(f"Checking sender API at {args.sender_url}...")
        available, result = check_sender_status(args.sender_url)
        if available:
            print(f"✅ Sender API is available: {result}")
            
            # Get detailed status
            try:
                response = requests.get(f"{args.sender_url}/status", timeout=2)
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"📊 Sender Status:")
                    print(f"   Uptime: {status_data.get('uptime_seconds', 'unknown')} seconds")
                    print(f"   Messages sent: {status_data.get('sender_stats', {}).get('messages_sent', 'unknown')}")
                    print(f"   Queue size: {status_data.get('queue_size', {}).get('total', 'unknown')}")
            except:
                pass
        else:
            print(f"❌ Sender API is not available: {result}")
        return
    
    if args.show_timestamp:
        timestamps = load_last_timestamps()
        if timestamps:
            print("Current saved timestamps per camera:")
            for camera, timestamp in timestamps.items():
                print(f"  {camera}: {timestamp}")
        else:
            print("No saved timestamps found")
        return
    
    if args.reset_timestamp:
        default_time = get_default_start_time()
        
        # Get all cameras from database to reset
        try:
            conn = database.connect_db()
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT camera_name FROM traffic ORDER BY camera_name')
            cameras = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            reset_timestamps = {camera: default_time for camera in cameras}
            save_last_timestamps(reset_timestamps)
            print(f"Reset timestamps for {len(cameras)} cameras to: {default_time}")
            for camera in cameras:
                print(f"  {camera}: {default_time}")
        except Exception as e:
            print(f"Error resetting timestamps: {e}")
        return
    
    # Loop forever - continuously check for new data and send
    print(f"🚀 Starting Database to Data Diode Sender")
    print(f"📡 Sender API: {args.sender_url}")
    print(f"⏱️  Interval: {args.interval}s")
    print(f"📦 Batch size: {args.batch_size}")
    print("=" * 50)
    
    while True:
        try:
            send_database_data(
                sender_url=args.sender_url,
                interval=args.interval,
                batch_size=args.batch_size
            )
        except Exception as e:
            print(f"Encountered an error: {e}")
            print("Retrying in 5 seconds...")
        
        # Sleep 5 seconds before next check
        print("Waiting 5 seconds before checking for new data...")
        time.sleep(5)

if __name__ == "__main__":
    main() 
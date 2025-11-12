#!/usr/bin/env python3
import time
import random
import threading
import sys
import os

# Add the swift directory to the path to import database_sqlite
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'swift'))
import database_sqlite as database

def wait_for_next_10_second_mark():
    """
    Wait until the next 10-second mark (when seconds end with 0)
    """
    current_time = time.time()
    current_seconds = int(time.strftime('%S', time.localtime(current_time)))
    
    # Calculate how many seconds to wait until next 10-second mark
    seconds_to_wait = 10 - (current_seconds % 10)
    if seconds_to_wait == 10:
        seconds_to_wait = 0  # Already at a 10-second mark
    
    if seconds_to_wait > 0:
        print(f"Waiting {seconds_to_wait} seconds to sync with 10-second intervals...")
        time.sleep(seconds_to_wait)

def generate_camera_data(camera_name, duration_minutes=5):
    """
    Generate dummy data for a single camera.
    
    Args:
        camera_name (str): Name of the camera
        duration_minutes (int): How long to run the simulation
    """
    print(f"Starting data generation for {camera_name}")
    
    total_in_count = 0
    total_out_count = 0
    ip_address = f"192.168.1.{random.randint(100, 200)}"
    
    # Track when we last inserted data to avoid duplicates
    last_insert_time = None
    
    # Calculate end time
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    while time.time() < end_time:
        # Get current time
        current_time = time.time()
        current_seconds = int(time.strftime('%S', time.localtime(current_time)))
        current_time_str = time.strftime('%H:%M:%S', time.localtime(current_time))
        
        # Check if current seconds end with 0 (i.e., :00, :10, :20, :30, :40, :50)
        if current_seconds % 10 == 0:
            # Make sure we haven't already inserted data for this 10-second mark
            current_minute_second = time.strftime('%H:%M:%S', time.localtime(current_time))[:7]  # HH:MM:S (first digit of seconds)
            
            if last_insert_time != current_minute_second:
                # Generate random increments
                in_increment = random.randint(0, 3)
                out_increment = random.randint(0, 3)
                
                total_in_count += in_increment
                total_out_count += out_increment
                region_count = max(0, total_in_count - total_out_count)
                
                # Insert data using the same function as main.py
                # This will only actually insert when seconds end with 0
                database.insert_people_count_result_interval(
                    total_in_count, 
                    total_out_count, 
                    region_count, 
                    camera_name, 
                    ip_address
                )
                
                print(f"{camera_name} [{current_time_str}]: In={total_in_count}, Out={total_out_count}, Region={region_count}")
                
                # Update last insert time to prevent duplicate inserts
                last_insert_time = current_minute_second
        
        # Sleep for a short interval to avoid busy waiting
        time.sleep(0.1)
    
    print(f"Completed: {camera_name} - Final In={total_in_count}, Out={total_out_count}")

def simulate_multiple_cameras(duration_minutes=5):
    """
    Simulate multiple cameras sending data simultaneously.
    """
    # Default camera list
    cameras = [
        'Camera_Entrance_A',
        'Camera_Entrance_B', 
        'Camera_Exit_C',
        'Camera_Exit_D',
        'Camera_Main_Hall'
    ]
    
    print(f"🎬 Starting multi-camera simulation with {len(cameras)} cameras for {duration_minutes} minutes")
    print("⏰ Syncing with 10-second intervals (data inserts at :00, :10, :20, :30, :40, :50)")
    print("=" * 80)
    
    # Setup database
    conn = database.connect_db()
    database.setup_or_clean_db(conn, clean=False)
    conn.close()
    
    # Start threads for each camera
    threads = []
    for i, camera in enumerate(cameras):
        thread = threading.Thread(target=generate_camera_data, args=(camera, duration_minutes))
        thread.start()
        threads.append(thread)
        # Small stagger to avoid all cameras starting at exactly the same microsecond
        time.sleep(0.1)
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print("=" * 80)
    print("✅ Multi-camera simulation completed!")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-camera SQLite data emulator")
    parser.add_argument('--duration', type=int, default=365*24*60, 
                       help='Duration in minutes (default: 525600 = 1 year)')
    
    args = parser.parse_args()
    
    # Run multi-camera simulation by default
    simulate_multiple_cameras(args.duration)

if __name__ == "__main__":
    main()
    
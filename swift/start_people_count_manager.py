import atexit
import os
import subprocess
import signal
import sys
import time
from database_sqlite import connect_db, cleanup_old_data
import datetime
import shutil

# The location of your PID file
PIDFILE = '/tmp/all_pids_swift.pid'

def cleanup():
    """Terminate all subprocesses"""
    if os.path.isfile(PIDFILE):
        with open(PIDFILE, 'r') as pidfile:
            for line in pidfile:
                parts = line.strip().split()
                if len(parts) == 2:
                    pid, camera_name = parts
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"Successfully terminated PID: {pid} (Camera: {camera_name})")
                    except ProcessLookupError:
                        print(f"No process found with PID: {pid} (Camera: {camera_name})")
                else:
                    print(f"Invalid line format: {line.strip()}")
        os.remove(PIDFILE)
        print(f"Removed PID file: {PIDFILE}")

def cleanup_old_logs(days=5):
    """Clean up log files older than specified days in the logs directory and its subdirectories"""
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        print(f"Logs directory '{logs_dir}' does not exist")
        return
        
    current_time = datetime.datetime.now()
    cutoff_time = current_time - datetime.timedelta(days=days)
    
    for root, dirs, files in os.walk(logs_dir, topdown=False):
        if root == logs_dir:
            continue
            
        dir_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(root))
        if dir_mtime < cutoff_time:
            try:
                shutil.rmtree(root)
                print(f"Removed directory: {root}")
            except Exception as e:
                print(f"Error removing directory {root}: {e}")

def start_people_count_system(cameras_config):
    """Start the people counting system with the provided camera configuration"""
    
    # Register the cleanup function to be called on exit
    atexit.register(cleanup)
    
    # Clear out any old PIDs
    cleanup()
    
    # Clean up old database records
    conn = connect_db()
    cleanup_old_data(conn, days=5)
    conn.close()
    
    # Clean up old log files
    cleanup_old_logs(days=5)
    
    time.sleep(2)
    
    # Write the current process PID to the PID file
    with open(PIDFILE, 'a') as pidfile:
        pidfile.write(f"{os.getpid()}\n")
    
    # Start all processes and store their PIDs and camera names
    with open(PIDFILE, 'a') as pidfile:
        for config_line in cameras_config:
            parts = config_line.split()
            if len(parts) >= 5:
                video_url, model_name, redis_key, region_points, in_direction = parts[:5]
                crop_param = parts[5] if len(parts) > 5 else ""
                
                region_points = region_points.replace("'", "")
                in_direction = in_direction.replace("'", "")
                process = subprocess.Popen(["python", "main_and_swift.py", "--video", video_url, "--model_name", model_name, "--camera_name", redis_key, "--region", region_points, "--in_direction", in_direction, "--crop-param", crop_param])
                
                pidfile.write(f"{process.pid} {redis_key}\n")
            else:
                print(f"Invalid config line (needs at least 5 parameters): {config_line}")
    
    # Keep the main script running
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass 
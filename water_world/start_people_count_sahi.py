import atexit
import os
import subprocess
import signal
import sys
import time
# from database_sqlite import connect_db, cleanup_old_data
import datetime
import shutil

# The location of your PID file
PIDFILE = '/tmp/all_pids_sahi_swift.pid'

# Function to terminate all subprocesses
def cleanup():
    if os.path.isfile(PIDFILE):
        with open(PIDFILE, 'r') as pidfile:
            for line in pidfile:
                # Split the line to get the PID and camera name
                parts = line.strip().split()
                # Ensure the line contains both pid and camera_name
                if len(parts) == 2:
                    pid, camera_name = parts
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"Successfully terminated PID: {pid} (Camera: {camera_name})")
                    except ProcessLookupError:
                        print(f"No process found with PID: {pid} (Camera: {camera_name})")
                else:
                    print(f"Invalid line format: {line.strip()}")
        # Remove the PID file after processing
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
    
    # Process directories from deepest first
    for root, dirs, files in os.walk(logs_dir, topdown=False):
        # Skip the main logs directory
        if root == logs_dir:
            continue
            
        dir_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(root))
        if dir_mtime < cutoff_time:
            try:
                shutil.rmtree(root)
                print(f"Removed directory: {root}")
            except Exception as e:
                print(f"Error removing directory {root}: {e}") 


# Register the cleanup function to be called on exit
atexit.register(cleanup)

# Clear out any old PIDs
cleanup()

# Clean up old database records
# conn = connect_db()
# cleanup_old_data(conn, days=5)
# conn.close()

# Clean up old log files
cleanup_old_logs(days=5)

time.sleep(2)

# Write the current process PID to the PID file
with open(PIDFILE, 'a') as pidfile:
    pidfile.write(f"{os.getpid()}\n")

# Read user pass from Environment Variable
env_vars = {
    # "CC_PASS": os.getenv("PEOPLE_COUNT_CC_PASS"),
    # "CROCO_PASS": os.getenv("PEOPLE_COUNT_CROCO_PASS"),
    "PASSO": os.getenv("PASSO")
}

# List of commands to run
cameras_config = [
    f"rtsp://username1:{env_vars['PASSO']}@192.168.camera.ip1:554/axis-media/media.amp ww_pool C-2001 '[(10,1072),(1908,459),(1912,402),(1562,259),(963,212),(400,231),(396,205),(4,266)]'",
    f"rtsp://username2:{env_vars['PASSO']}@192.168.camera.ip2:554/axis-media/media.amp ww_pool C-2004 '[(36,590),(293,717),(616,798),(1164,810),(1618,727),(1814,567),(1735,404),(1594,291),(1386,192),(643,144),(248,324)]'",

    # f"http://localhost:3001/video_feed ww_pool C-3024 '[(1142,892),(1426,450),(496,407),(428,836)]'",

    # "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-29_19-25-25.mp4 crocoland CC_In_Cam1 '' ''"
]

# Start all processes and store their PIDs and camera names
with open(PIDFILE, 'a') as pidfile:
    for config_line in cameras_config:
        video_url, model_name, redis_key, region_points = config_line.split()
        region_points = region_points.replace("'", "")
        process = subprocess.Popen(["python", "main_sahi_and_swift.py", "--video", video_url, "--model_name", model_name, "--camera_name", redis_key, "--region", region_points])
        
        
        pidfile.write(f"{process.pid} {redis_key}\n")

# Keep the main script running
try:
    while True:
        pass
except KeyboardInterrupt:
    pass
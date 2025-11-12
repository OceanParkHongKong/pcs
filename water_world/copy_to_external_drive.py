#!/usr/bin/env python3
import os
import time
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path


#  using rsync directly would be simpler and more reliable ?
# rsync -avz --progress --remove-source-files /path/to/source/files username@192.168.a.ip:/Volumes/4T/script_copy/

# Configuration
SOURCE_DIR = "/path/to/source/videos"
DEST_DIR = "/Volumes/ExternalDrive/videos"
LOG_FILE = "transfer.log"
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi']
AGE_THRESHOLD_MINUTES = 20
CHECK_INTERVAL_SECONDS = 60

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def is_file_in_use(file_path):
    """Check if a file is currently being accessed by another process"""
    try:
        # Using lsof to check if file is in use
        result = subprocess.run(['lsof', file_path], capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking if file is in use: {e}")
        # If we can't determine, assume it's in use to be safe
        return True

def get_file_age_minutes(file_path):
    """Get file age in minutes"""
    mtime = os.path.getmtime(file_path)
    age_seconds = time.time() - mtime
    return age_seconds / 60

def copy_file_with_verification(source, destination):
    """Copy file and verify the copy is identical"""
    try:
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Copy the file
        shutil.copy2(source, destination)
        
        # Verify file sizes match
        source_size = os.path.getsize(source)
        dest_size = os.path.getsize(destination)
        
        if source_size == dest_size:
            return True
        else:
            logger.error(f"Size mismatch after copying: source={source_size}, dest={dest_size}")
            return False
    except Exception as e:
        logger.error(f"Error during copy: {e}")
        return False

def main():
    logger.info(f"Starting continuous monitoring of {SOURCE_DIR}")
    
    while True:
        # Check if destination exists and is mounted
        if not os.path.exists(DEST_DIR):
            logger.info("Destination directory doesn't exist. Waiting for drive...")
            time.sleep(30)
            continue
        
        # Find video files
        for root, _, files in os.walk(SOURCE_DIR):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                # Check if it's a video file
                if any(file_path.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                    # Check file age
                    age_minutes = get_file_age_minutes(file_path)
                    
                    if age_minutes < AGE_THRESHOLD_MINUTES:
                        continue
                    
                    # Skip files that are currently being written to
                    # if is_file_in_use(file_path):
                    #     logger.info(f"{filename} is still being written to. Skipping.")
                    #     continue
                    
                    logger.info(f"Copying {filename}...")
                    
                    # Determine destination path (preserving directory structure)
                    rel_path = os.path.relpath(file_path, SOURCE_DIR)
                    dest_path = os.path.join(DEST_DIR, rel_path)
                    
                    # Copy with verification
                    if copy_file_with_verification(file_path, dest_path):
                        logger.info(f"Successfully copied {filename}, removing original.")
                        os.remove(file_path)
                    else:
                        logger.info(f"Error copying {filename}, original file preserved.")
        
        # Wait before checking for new files
        logger.info("Waiting for new files...")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
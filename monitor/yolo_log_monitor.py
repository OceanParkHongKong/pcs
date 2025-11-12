import time
import os
from datetime import datetime
from smtp import send_email
import threading
import logging
import sys

class LogWatcher:
    def __init__(self):
        self.last_position = {}  # Store file positions
        self.logger = logging.getLogger(__name__)
        # Add rate limiting attributes
        self.email_timestamps = []
        self.max_emails_per_minute = 5
        self.start_time = time.time()  # Add start time tracking
        self.known_files = set()  # Track known files
        self.last_scan_time = 0
        self.scan_interval = 1  # Scan every 1 second
        # Add buffer for collecting errors
        self.error_buffer = []
        self.last_email_time = 0
        self.email_interval = 60  # Send summarized email every 60 seconds

    def can_send_email(self):
        current_time = time.time()
        # Check if enough time has passed since the last email
        return current_time - self.last_email_time >= self.email_interval

    def send_email_async(self, error_msg):
        # This method now handles a single error message to be added to the buffer
        if error_msg:  # Only add non-empty messages
            self.error_buffer.append(error_msg)
        
        # Check if it's time to send the summarized email
        if self.can_send_email() and self.error_buffer:
            self.last_email_time = time.time()
            
            # Group errors by camera log file
            errors_by_camera = {}
            for error in self.error_buffer:
                # Extract camera name from the error message
                parts = error.split(': ', 1)
                if len(parts) == 2:
                    camera_name = parts[0].split(' in ')[1]
                    error_content = parts[1]
                    
                    if camera_name not in errors_by_camera:
                        errors_by_camera[camera_name] = []
                    errors_by_camera[camera_name].append(error_content)
            
            # Create a summarized message with grouped errors
            summary = f"YOLO Log Monitor Alert Summary - {datetime.now()}\n\n"
            summary += f"Issues detected in {len(errors_by_camera)} camera logs:\n\n"
            
            # Add camera names summary
            summary += f"{', '.join(sorted(errors_by_camera.keys()))}\n\n"
            summary += "Details:\n"
            
            for camera, messages in sorted(errors_by_camera.items()):
                summary += f"## {camera} ({len(messages)} issues)\n"
                # Count occurrences of each unique message
                message_counts = {}
                for msg in messages:
                    if msg in message_counts:
                        message_counts[msg] += 1
                    else:
                        message_counts[msg] = 1
                
                # Display each unique message with count if repeated
                for msg, count in message_counts.items():
                    if count > 1:
                        summary += f"- {msg} (repeated {count} times)\n"
                    else:
                        summary += f"- {msg}\n"
                summary += "\n"
            
            # Send the email with the summary
            email_thread = threading.Thread(target=send_email, args=(summary,))
            email_thread.daemon = True
            email_thread.start()
            self.logger.info(f"Summarized email sent with issues from {len(errors_by_camera)} cameras")
            
            # Clear the buffer after sending
            self.error_buffer = []

    def check_for_errors(self, filepath):
        # Get the last known position or start from beginning
        last_pos = self.last_position.get(filepath, 0)
        
        try:
            with open(filepath, 'r') as file:
                # Move to last known position
                file.seek(last_pos)
                
                # Read new lines
                new_lines = file.readlines()
                
                # Update last position
                self.last_position[filepath] = file.tell()
                
                # Check for errors in new lines
                for line in new_lines:
                    if "ERROR" in line.upper() or "WARNING" in line.upper():
                        error_level = "ERROR" if "ERROR" in line.upper() else "WARNING"
                        error_msg = f"{error_level} in {os.path.basename(filepath)}: {line.strip()}"
                        self.send_email_async(error_msg)
                        self.logger.error(f"{error_level} found and added to summary: {error_msg}")
                        
        except Exception as e:
            self.logger.error(f"Error reading file {filepath}: {e}")

    def force_scan_directory(self, path):
        current_time = time.time()
        if current_time - self.last_scan_time < self.scan_interval:
            return
            
        self.last_scan_time = current_time
        current_files = set()
        
        # Check if it's time to send a summary email even if no new errors
        if self.error_buffer and self.can_send_email():
            self.send_email_async("")  # This will trigger sending the buffered errors
        
        # Scan directory for .log files
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.log'):
                    full_path = os.path.join(root, file)
                    try:
                        # Get file's modification time
                        file_mtime = os.path.getmtime(full_path)
                        # Only process files modified after script start
                        if file_mtime > self.start_time:
                            current_files.add(full_path)
                            if full_path not in self.known_files:
                                # New file detected
                                self.logger.info(f"Found new log file: {full_path}")
                                self.check_for_errors(full_path)
                            else:
                                # Existing file - check if it was modified since last scan
                                last_pos = self.last_position.get(full_path, 0)
                                current_size = os.path.getsize(full_path)
                                if current_size > last_pos:
                                    # self.logger.info(f"Detected changes: {full_path}")
                                    self.check_for_errors(full_path)
                    except Exception as e:
                        self.logger.error(f"Error checking file {full_path}: {e}")
        
        # Update known_files to only contain currently existing files
        self.known_files = current_files

def start_monitoring(path="./logs"):
    # Configure logging once at startup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)

    # Create logs directory if it doesn't exist
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Created directory: {path}")

    # Initialize the event handler - no more Observer needed
    event_handler = LogWatcher()
    
    # Get absolute path
    abs_path = os.path.abspath(path)
    logger.info(f"Starting to monitor logs in: {abs_path}")

    try:
        while True:
            event_handler.force_scan_directory(path)  # Actively scan directory
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nLog monitoring stopped")

if __name__ == "__main__":
    # Check for command line argument
    if len(sys.argv) > 1:
        monitor_path = sys.argv[1]
        print(f"Monitoring custom path: {monitor_path}")
        start_monitoring(monitor_path)
    else:
        print("Monitoring default path: ./logs")
        start_monitoring() 
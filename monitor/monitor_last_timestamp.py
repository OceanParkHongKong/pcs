import requests
import time
import json
import logging
from datetime import datetime, timedelta

# Configuration
config_file = 'config_api.json'
check_interval = 5  # in seconds
time_threshold = 30  # in seconds

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(file_path):
    with open(file_path, 'r') as config_file:
        return json.load(config_file)

def fetch_data(api_url, auth_token):
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()

import smtp

def check_timestamps(data, time_threshold):
    current_time = datetime.now()
    for entry in data:
        timestamp = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
        if (current_time - timestamp).total_seconds() > time_threshold:
            errorStr = f"Error: Timestamp for {entry['camera_name']} is older than {time_threshold} seconds."
            logging.ERROR(errorStr)
            smtp.send_email (errorStr)
    logging.info('.')

def monitor_api(api_url, auth_token):
    while True:
        try:
            data = fetch_data(api_url, auth_token)
            check_timestamps(data, time_threshold)
        except Exception as e:
            errorStr = f"Error fetching data: {e}"
            logging.ERROR(errorStr)
            smtp.send_email (errorStr)
        time.sleep(check_interval)

if __name__ == '__main__':
    logging.info ("started.")
    config = load_config(config_file)
    api_url = config.get('api_url')
    auth_token = config.get('auth_token')
    
    monitor_api(api_url, auth_token)
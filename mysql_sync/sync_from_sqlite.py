import requests
import json
import logging
from datetime import datetime, timedelta
import time
from functools import wraps
# from monitor.smtp import send_email

# Configuration
with open("config_db_sync.json", "r") as config_file:
    config = json.load(config_file)

sqlite_api_url = config["sqlite_api_url"]
counting_results_api_url = config["counting_results_api_url"]
headers_sqlite = config["headers_sqlite"]

# backup
# TODO: maybe hot backup not need
is_backup = False
sqlite_api_url_backup = config["sqlite_api_url_backup"]
counting_results_api_url_backup = config["counting_results_api_url_backup"]

mysql_api_url = config["mysql_api_url"]
insert_api_url = config["insert_api_url"]
headers_mysql = config["headers_mysql"]

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables to track current URLs
current_sqlite_api_url = sqlite_api_url
current_counting_results_api_url = counting_results_api_url

# Global variables to track failure counts
FAILURE_THRESHOLD = 5
# Global variables to track failure counts
api_failures = 0

# import backup_ssh_start
def failover_mechanism(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global current_sqlite_api_url, current_counting_results_api_url
        global api_failures

        primary_sqlite_url = sqlite_api_url
        primary_counting_results_url = counting_results_api_url
        backup_sqlite_url = sqlite_api_url_backup
        backup_counting_results_url = counting_results_api_url_backup

        current_sqlite_url = current_sqlite_api_url
        current_counting_results_url = current_counting_results_api_url

        try:
            result = func(*args, **kwargs)
            # Reset failure count on success
            api_failures = 0
            return result
        except Exception as e:
            api_failures += 1
            logging.warning(f"Failed to access {kwargs['api_url']}. Failure count: {api_failures}/{FAILURE_THRESHOLD}")
            
            if api_failures >= FAILURE_THRESHOLD:
                if current_sqlite_url == primary_sqlite_url and current_counting_results_url == primary_counting_results_url:
                    logging.warning("Switching to backup URLs.")
                    current_sqlite_api_url = backup_sqlite_url
                    current_counting_results_api_url = backup_counting_results_url
                    # send_email(f"Failover Alert: Switched to Backup URLs at {datetime.datetime.now()}")
                    #start backup mac studio
                    #backup_ssh_start.start_backup("start")
                else:
                    logging.warning("Switching back to primary URLs.")
                    current_sqlite_api_url = primary_sqlite_url
                    current_counting_results_api_url = primary_counting_results_url
                    # send_email(f"Failover Alert: Switched back to Primary URLs at {datetime.datetime.now()}")
                    #restart primary mac studio?

                # Reset failure count after switching
                api_failures = 0
            
            raise

    return wrapper

@failover_mechanism
def get_latest_timestamp(api_url, headers):
    response = requests.get(api_url, headers=headers, verify=False)
    response.raise_for_status()
    data = response.json()

    def parse_timestamp(timestamp):
        for fmt in ('%Y-%m-%d %H:%M:%S', '%a, %d %b %Y %H:%M:%S %Z'):
            try:
                return datetime.strptime(timestamp, fmt)
            except ValueError:
                continue
        raise ValueError(f"Timestamp format for {timestamp} is not supported")

    # Check if the response contains the error message
    if isinstance(data, dict) and data.get("error") == "No results found":
        # If "No results found" error is detected, return today's date at 00:00:00
        today_start = datetime.combine(datetime.today(), datetime.min.time())
        formatted_timestamp = today_start.strftime('%Y-%m-%d %H:%M:%S')
        return formatted_timestamp, data

    latest_timestamp = max(data, key=lambda item: parse_timestamp(item["timestamp"]))["timestamp"]
    parsed_timestamp = parse_timestamp(latest_timestamp)
    formatted_timestamp = parsed_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_timestamp, data

@failover_mechanism
def get_counting_results(api_url, start_time, end_time, headers):
    params = {
        "start_time": start_time,
        "end_time": end_time
    }
    response = requests.get(api_url, headers=headers, params=params, verify=False)
    response.raise_for_status()
    return response.json()

def insert_data(data):
    for record in data:
        timestamp = record["timestamp"]
        camera_id = record["camera_id"]
        payload = {
            "camera_id": camera_id,
            "timestamp": timestamp,
            "in_count": record["in"],
            "out_count": record["out"]
        }

        logging.debug(f"Payload: {json.dumps(payload)}")
        try:
            response = requests.post(insert_api_url, json=payload, headers=headers_mysql, verify=False)
            logging.info(f"Inserted data - Camera: {camera_id}, Time: {timestamp}, In: {record['in']}, Out: {record['out']}, Response: {response.status_code}")
            response.raise_for_status()
        except Exception as e:
            logging.error(f"Failed to insert data {camera_id}: {e}")
            raise

def main():
    try:
        global current_sqlite_api_url, current_counting_results_api_url
        
        sqlite_timestamp, sqlite_data = get_latest_timestamp(api_url=current_sqlite_api_url, headers=headers_sqlite)
        logging.debug("sqlite timestamp done")
        mysql_timestamp, mysql_data = get_latest_timestamp(api_url=mysql_api_url, headers=headers_mysql)
        logging.debug("mysql timestamp done")

        if mysql_timestamp != sqlite_timestamp:
            date_object = datetime.strptime(mysql_timestamp, '%Y-%m-%d %H:%M:%S')
            start_time = date_object + timedelta(milliseconds=1000)
            start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            
            end_time = sqlite_timestamp
            all_data = get_counting_results(api_url=current_counting_results_api_url, start_time=start_time, end_time=end_time, headers=headers_sqlite)["data"]
            logging.info(f"============ {start_time} -> {end_time}, data count {len(all_data)} ============")
            insert_data(all_data)
            logging.info(f"============ {len(all_data)} records synchronized. {start_time} -> {end_time}, data count {len(all_data)} ============")
        else:
            logging.info("same timestamp not expected")
    except Exception as e:
        logging.error(f"An error occurred while fetching timestamps: {e}")
        return

def should_run_now():
    current_seconds = datetime.now().second
    return current_seconds in {5, 15, 25, 35, 45, 55}

if __name__ == "__main__":
    while True:
        if should_run_now():
            logging.info (f"start sync at {datetime.now()}")
            main()
            time.sleep(1)
        else:
            time.sleep(0.5)
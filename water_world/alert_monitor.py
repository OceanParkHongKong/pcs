import requests
import time
import sqlite3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from logging_config import setup_logging

app = Flask(__name__)

# Initialize logging
logger = setup_logging('alert_monitor')

# Track alert states
alert_states = {}
resolution_timers = {}
# Track the last fired alert for each location
last_fired_alerts = {}  # Format: {location_id: {'level': level, 'timestamp': timestamp}}

# Global variable to store settings
current_settings = {}

def create_db_if_not_exist():
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 location_id TEXT,
                 level TEXT,
                 timestamp TEXT,
                 region_count INTEGER,
                 acknowledge BOOLEAN DEFAULT 0,
                 acknowledge_time TEXT,
                 status TEXT
                 )''')
    
    # # Check if acknowledge_time column exists, add it if it doesn't
    # try:
    #     c.execute("SELECT acknowledge_time FROM alerts LIMIT 1")
    # except sqlite3.OperationalError:
    #     # Column doesn't exist, add it
    #     c.execute("ALTER TABLE alerts ADD COLUMN acknowledge_time TEXT")
    #     print("Added acknowledge_time column to alerts table")
    
    conn.commit()
    conn.close()
    logger.info("Database table 'alerts' created or verified")

def store_alert(location_id, level, timestamp, region_count, status):
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('INSERT INTO alerts (location_id, level, timestamp, region_count, status) VALUES (?, ?, ?, ?, ?)',
              (location_id, level, timestamp, region_count, status))
    conn.commit()
    conn.close()
    logger.debug(f"Stored alert: {location_id}, {level}, {status}")

def get_recent_alerts(start_time=None, end_time=None, page=1, page_size=50, location_id=None, search_text=None):
    """
    Get recent alerts with optional time range filtering and pagination
    
    Parameters:
    - start_time: Optional datetime object for start of time range (default: today at midnight)
    - end_time: Optional datetime object for end of time range (default: current time)
    - page: Page number to return (default: 1)
    - page_size: Number of results per page (default: 50)
    
    Returns:
    - Dictionary containing:
      - alerts: List of alert records
      - total_count: Total number of alerts matching the criteria
      - page: Current page number
      - total_pages: Total number of pages
    """
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    
    # Set default time range if not provided
    if start_time is None:
        # Default to today at midnight
        start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if end_time is None:
        # Default to current time
        end_time = datetime.now()
    
    # Format datetime objects to strings for SQLite
    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
    
    sql_string = '''
        WITH FilteredAlerts AS (
            SELECT 
                id,
                location_id, 
                level, 
                level_threshold,
                timestamp, 
                region_count, 
                acknowledge, 
                acknowledge_time,
                status
            FROM alerts
            WHERE status != 'reminder'
            AND timestamp BETWEEN ? AND ?
        '''
    params = [start_time_str, end_time_str]
    
    if location_id:
        sql_string = sql_string + '''
            AND location_id = ?
        '''
        params.append(location_id)
    
    if search_text:
        # Create a LIKE clause for each searchable column
        search_term = f"%{search_text}%"
        search_clauses = [
            "location_id LIKE ?",
            "level LIKE ?",
            "level_threshold LIKE ?",
            "timestamp LIKE ?",
            "status LIKE ?"
            # Add other text columns you want to search
        ]
        
        sql_string = sql_string + '''
            AND (''' + " OR ".join(search_clauses) + ''')
        '''
        # Add search parameters for each clause
        params.extend([search_term] * len(search_clauses))
    
    sql_string = sql_string + '''
        ),
        AlertsWithPrevious AS (
            SELECT 
                id,
                location_id, 
                level, 
                level_threshold,
                timestamp, 
                region_count, 
                acknowledge, 
                acknowledge_time,
                status,
                LAG(status) OVER (PARTITION BY location_id ORDER BY timestamp) as previous_status
            FROM FilteredAlerts
            ORDER BY location_id, timestamp
        )'''
        
    sql_string_count = sql_string + '''
        SELECT COUNT(*)
        FROM AlertsWithPrevious
    '''
    # First, get the total count of matching alerts
    c.execute(sql_string_count, params)
    
    total_count = c.fetchone()[0]
    total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
    
    # Calculate offset for pagination
    offset = (page - 1) * page_size
    
    # Add hard limit to maximum page size to prevent excessive memory usage
    page_size = min(page_size, 100)  # Cap at 100 items per page
    
    # Add a maximum time range to prevent querying the entire database
    if start_time and end_time and (end_time - start_time).days > 31:
        # Limit to 31 days maximum
        start_time = end_time - timedelta(days=31)
    
    sql_string_data = sql_string + ''' 
        SELECT 
            location_id, 
            level, 
            level_threshold,
            timestamp, 
            region_count, 
            acknowledge, 
            acknowledge_time,
            status
        FROM AlertsWithPrevious
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    '''
    
    # Add pagination parameters
    params.extend([page_size, offset])
    
    # Get paginated alert history with time range filter
    c.execute(sql_string_data, params)
    
    alerts = c.fetchall()
    conn.close()
    
    return {
        "alerts": alerts,
        "total_count": total_count,
        "page": page,
        "total_pages": total_pages,
        "page_size": page_size
    }

def get_threshold_for_level(location_config, level, is_resolve=False):
    """
    Helper function to get the threshold value for a specific alert level
    
    Parameters:
    - location_config: Dictionary containing location configuration
    - level: Alert level ('yellow', 'orange', or 'red')
    - is_resolve: If True, get the resolve threshold instead of firing threshold
    
    Returns:
    - Threshold value as integer, or 0 if not found or invalid
    """
    if is_resolve:
        threshold_key = f'{level}ResolveThreshold'
    else:
        threshold_key = f'{level}Threshold'
        
    threshold_str = location_config.get(threshold_key, '0')
    
    try:
        return int(threshold_str) if threshold_str else 0
    except ValueError:
        logger.warning(f"Invalid threshold value for {threshold_key}: {threshold_str}")
        return 0

current_alerts = {}#merge with alert_states? alert_states[location_id]['level'] never NONE ?
    
def check_location_alerts(location_settings, alert_interval=300, locations=None, cameras_by_location=None):
    """
    Check for alerts based on total occupancy of locations rather than individual cameras
    
    Parameters:
    - location_settings: Location settings with thresholds
    - alert_interval: Time in seconds before re-alerting (default: 5 minutes)
    - locations: List of location objects
    - cameras_by_location: Dictionary mapping location IDs to camera lists
    
    Returns:
    - Dictionary with alert status information by location
    """
    # Move the import here to avoid circular import
    from alert_backend_server import get_location_stats
    
    global last_fired_alerts
    
    # Periodically clean up old alert states (every 6 hours)
    if int(time.time()) % (6 * 3600) < 10:  # Run within a 10-second window every 6 hours
        cleaned = cleanup_alert_states()
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old alert entries")
        
    current_time = datetime.now()
    alert_status_results = {}
    
    # Get all locations and their cameras
    if locations is None or cameras_by_location is None:
        raise ValueError("Locations or cameras_by_location is None")
    
    try:
        # Group camera data by location
        location_counts = {}
        
        # Initialize counts for all locations to 0
        logger.debug(f"Locations type: {type(locations)}, count: {len(locations)}")
        
        for location in locations:
            location_id = location['id']
            location_counts[location_id] = {
                'total_count': 0,
                'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                'cameras': [],
                'processed_cameras': set()
            }
        
        # Instead of manually calculating location_counts, reuse the existing function
        for location_id in cameras_by_location.keys():
            try:
                # Check if location_id exists in location_counts before accessing it
                if location_id not in location_counts:
                    logger.warning(f"Location ID '{location_id}' found in cameras_by_location but not in locations list. Skipping stats retrieval.")
                    continue
                    
                stats_response = get_location_stats(location_id)
                if stats_response.status_code == 200:
                    stats_data = stats_response.get_json()
                    total_region = stats_data.get('totalRegion', 0)
                    total_in = stats_data.get('totalIn', 0)
                    total_out = stats_data.get('totalOut', 0)
                    if location_id == 'Riptide':
                        total_count = total_region - total_in + total_out
                    else:
                        total_count = total_region + total_in - total_out
                    
                    location_counts[location_id]['total_count'] = total_count
                    logger.debug(f"Location {location_id} total count from get_location_stats: {total_count} total_region: {total_region} total_in: {total_in} total_out: {total_out}")
                else:
                    logger.warning(f"Failed to get stats for location {location_id}")
                    location_counts[location_id]['total_count'] = 0
                    
            except Exception as e:
                logger.error(f"Error getting stats for location {location_id}: {e}")
                # Only set to 0 if location_id exists in location_counts
                if location_id in location_counts:
                    location_counts[location_id]['total_count'] = 0
        
        # Now check thresholds for each location
        for location_id, count_data in location_counts.items():
            total_count = count_data['total_count']
            timestamp = count_data['timestamp']
            
            if location_id in location_settings:
                location_config = location_settings[location_id]
                
                try:
                    # Get thresholds for each level
                    yellow_threshold = get_threshold_for_level(location_config, 'yellow')
                    orange_threshold = get_threshold_for_level(location_config, 'orange')
                    red_threshold = get_threshold_for_level(location_config, 'red')
                    
                    # Get resolve thresholds for each level
                    yellow_resolve_threshold = get_threshold_for_level(location_config, 'yellow', True)
                    orange_resolve_threshold = get_threshold_for_level(location_config, 'orange', True)
                    red_resolve_threshold = get_threshold_for_level(location_config, 'red', True)
                    
                    # Check if each level is enabled
                    yellow_enabled = location_config.get('yellowOccupancyDetectEnabled', False)
                    orange_enabled = location_config.get('orangeOccupancyDetectEnabled', False)
                    red_enabled = location_config.get('redOccupancyDetectEnabled', False)
                    
                    # Determine current alert level based on thresholds and enabled settings
                    level = None
                    if red_enabled and total_count >= red_threshold and red_threshold > 0:
                        level = 'red'
                    elif orange_enabled and total_count >= orange_threshold and orange_threshold > 0:
                        level = 'orange'
                        if location_id in current_alerts and current_alerts[location_id]['level'] == 'red' and total_count >= red_resolve_threshold:
                            level = 'red' #keep red level if it is still above the resolve threshold
                    elif yellow_enabled and total_count >= yellow_threshold and yellow_threshold > 0:
                        level = 'yellow'
                        if location_id in current_alerts and current_alerts[location_id]['level'] == 'orange' and total_count >= orange_resolve_threshold:
                            level = 'orange' #keep orange level if it is still above the resolve threshold
                        elif location_id in current_alerts and current_alerts[location_id]['level'] == 'red' and total_count >= red_resolve_threshold:
                            level = 'red' #keep red level if it is still above the resolve threshold
                    
                    logger.debug(f'Alert level for {location_id}: {level}, count: {total_count}')
                    
                    if level == None:
                        current_alerts[location_id] = {
                            'level': 'none',
                            'timestamp': timestamp, 
                            'region_count': total_count
                        }
                        
                    # Handle alert state transitions
                    if level:  # Current reading is above a threshold and that level is enabled
                        current_alerts[location_id] = {
                            'level': level, 
                            'timestamp': timestamp, 
                            'region_count': total_count
                        }
                        
                        # Check if this is a new alert or a change in alert level
                        if location_id not in alert_states or alert_states[location_id]['level'] != level:
                            # If there was a previous alert for this location with a different level, mark it as resolved
                            if location_id in last_fired_alerts and last_fired_alerts[location_id]['level'] != level:
                                previous_level = last_fired_alerts[location_id]['level']
                                previous_timestamp = last_fired_alerts[location_id]['timestamp']
                                
                                # Store the auto-resolved alert
                                # store_location_alert(location_id, previous_level, 
                                #                     get_threshold_for_level(location_config, previous_level), 
                                #                     timestamp, total_count, "level-changed")
                                logger.info(f"LOCATION ALERT LEVEL CHANGED: {location_id} - previous level: {previous_level} - new level: {level}")
                            
                            # New alert or level change - fire immediately
                            alert_states[location_id] = {
                                'level': level,
                                'last_alert_time': current_time,
                                'status': 'firing'
                            }
                            
                            # Store the alert in the database with "firing" status
                            store_location_alert(location_id, level, get_threshold_for_level(location_config, level), timestamp, total_count, "firing")
                            logger.warning(f"LOCATION ALERT FIRED: {location_id} - {level} level - count: {total_count}")
                            
                            # Update the last fired alert for this location
                            last_fired_alerts[location_id] = {
                                'level': level,
                                'timestamp': timestamp
                            }
                            
                            # Add to status results
                            alert_status_results[location_id] = {
                                'status': 'firing',
                                'level': level,
                                'region_count': total_count,
                                'timestamp': timestamp,
                                'location_id': location_id,
                                'threshold': get_threshold_for_level(location_config, level)
                            }
                        
                        elif (current_time.timestamp() - alert_states[location_id]['last_alert_time'].timestamp()) >= alert_interval:
                            # Re-alert after the specified interval
                            alert_states[location_id]['last_alert_time'] = current_time
                            
                            # Store the reminder alert
                            store_location_alert(location_id, level, get_threshold_for_level(location_config, level), timestamp, total_count, "reminder")
                            logger.info(f"LOCATION ALERT REMINDER: {location_id} - {level} level - count: {total_count}")
                            
                            # Add to status results
                            alert_status_results[location_id] = {
                                'status': 'reminder',
                                'level': level,
                                'region_count': total_count,
                                'timestamp': timestamp,
                                'location_id': location_id,
                                'threshold': get_threshold_for_level(location_config, level)
                            }
                    
                    else:  # Current reading is below all thresholds or no levels are enabled
                        # Check if there's an active alert that needs to be resolved
                        if location_id in alert_states and alert_states[location_id]['status'] == 'firing':
                            current_level = alert_states[location_id]['level']
                            resolve_threshold = get_threshold_for_level(location_config, current_level, True)
                            
                            # Check if count is below the resolve threshold for the current alert level
                            if total_count <= resolve_threshold:
                                # Alert is resolved
                                previous_level = alert_states[location_id]['level']
                                
                                # Store the resolved alert
                                store_location_alert(location_id, previous_level, get_threshold_for_level(location_config, previous_level), timestamp, total_count, "resolved")
                                logger.info(f"LOCATION ALERT RESOLVED: {location_id} - previous level: {previous_level} - count: {total_count} below resolve threshold: {resolve_threshold}")
                                
                                # Add to status results
                                alert_status_results[location_id] = {
                                    'status': 'resolved',
                                    'previous_level': previous_level,
                                    'region_count': total_count,
                                    'timestamp': timestamp,
                                    'location_id': location_id,
                                    'threshold': get_threshold_for_level(location_config, previous_level)
                                }
                                
                                # Clean up state
                                del alert_states[location_id]
                                # Also remove from last_fired_alerts when fully resolved
                                if location_id in last_fired_alerts:
                                    del last_fired_alerts[location_id]
                    
                except ValueError as e:
                    logger.error(f"Invalid threshold value for location: {location_id} - {e}")
        
        logger.debug(f'Location alerts result: {alert_status_results}')
        return alert_status_results
    
    except requests.exceptions.RequestException as e:
        logger.error(f'Error querying API: {e}')
        return {'Error': str(e)}

def store_location_alert(location_id, level, level_threshold, timestamp, region_count, status):
    """Store a location-based alert in the database with proper exception handling"""
    try:
        with sqlite3.connect('alerts.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO alerts (location_id, level, level_threshold, timestamp, region_count, status) VALUES (?, ?, ?, ?, ?, ?)',
                    (location_id, level, level_threshold, timestamp, region_count, status))
            conn.commit()
            logger.debug(f"Stored location alert: {location_id}, {level}, {status}")
    except Exception as e:
        logger.error(f"Error storing alert in database: {e}")

def create_location_alerts_table_if_not_exist():
    """Create the alerts table if it doesn't exist"""
    try:
        conn = sqlite3.connect('alerts.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS alerts (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     location_id TEXT,
                     level TEXT,
                     level_threshold INTEGER,
                     timestamp TEXT,
                     region_count INTEGER,
                     acknowledge BOOLEAN DEFAULT 0,
                     acknowledge_time TEXT,
                     status TEXT
                     )''')
        conn.commit()
        conn.close()
        logger.info("Location alerts table created or verified")
    except Exception as e:
        logger.error(f"Error creating location alerts table: {e}")

def get_recent_location_alerts():
    """Get recent location alerts, filtering out reminders and consecutive alerts with the same status"""
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    
    c.execute('''
        WITH FilteredAlerts AS (
            SELECT 
                id,
                location_id, 
                level, 
                level_threshold,
                timestamp, 
                region_count, 
                acknowledge, 
                acknowledge_time,
                status
            FROM alerts
            WHERE status != 'reminder'
        ),
        AlertsWithPrevious AS (
            SELECT 
                id,
                location_id, 
                level, 
                level_threshold,
                timestamp, 
                region_count, 
                acknowledge, 
                acknowledge_time,
                status,
                LAG(status) OVER (PARTITION BY location_id ORDER BY timestamp) as previous_status
            FROM FilteredAlerts
            ORDER BY location_id, timestamp
        )
        SELECT 
            location_id, 
            level, 
            level_threshold,
            timestamp, 
            region_count, 
            acknowledge, 
            acknowledge_time,
            status
        FROM AlertsWithPrevious
        WHERE previous_status IS NULL OR status != previous_status
        ORDER BY timestamp DESC
        LIMIT 50
    ''')
    
    alerts = c.fetchall()
    conn.close()
    return alerts

def refresh_settings(new_settings):
    """
    Update the current settings with new values.
    
    Parameters:
    - new_settings: Dictionary containing the updated location settings
    
    Returns:
    - None
    """
    global current_settings
    current_settings = new_settings.copy()
    logger.info(f"Alert settings refreshed. Now monitoring {len(current_settings)} locations.")
    
    # Log the thresholds for each location
    for location_id, settings in current_settings.items():
        yellow_enabled = settings.get('yellowOccupancyDetectEnabled', False)
        orange_enabled = settings.get('orangeOccupancyDetectEnabled', False)
        red_enabled = settings.get('redOccupancyDetectEnabled', False)
        
        yellow_threshold = get_threshold_for_level(settings, 'yellow')
        orange_threshold = get_threshold_for_level(settings, 'orange')
        red_threshold = get_threshold_for_level(settings, 'red')
        
        logger.info(f"Location {location_id} thresholds:")
        logger.info(f"  Yellow: {yellow_threshold} (enabled: {yellow_enabled})")
        logger.info(f"  Orange: {orange_threshold} (enabled: {orange_enabled})")
        logger.info(f"  Red: {red_threshold} (enabled: {red_enabled})")

def restore_last_fired_alerts():
    """
    Restore the last_fired_alerts dictionary from the database after application restart.
    Only considers active alerts from the last 24 hours.
    """
    # Get a timestamp for 24 hours ago
    one_day_ago = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with sqlite3.connect('alerts.db') as conn:
            c = conn.cursor()
            
            # Add time constraint to only restore recent alerts
            c.execute('''
                WITH RankedAlerts AS (
                    SELECT 
                        location_id,
                        level,
                        timestamp,
                        status,
                        ROW_NUMBER() OVER (PARTITION BY location_id ORDER BY id DESC) as row_num
                    FROM alerts
                    WHERE status != 'reminder'
                    AND timestamp > ?
                )
                SELECT location_id, level, timestamp, status
                FROM RankedAlerts
                WHERE row_num = 1
            ''', (one_day_ago,))
            
            results = c.fetchall()
    except Exception as e:
        logger.error(f"Error restoring alerts: {e}")
        return {}
        
    # Rebuild the last_fired_alerts dictionary - only include locations with active alerts
    restored_alerts = {}
    for location_id, level, timestamp, status in results:
        # Only include locations where the most recent non-reminder alert is 'firing'
        if status == 'firing':
            # Convert string timestamp to datetime object
            last_alert_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            restored_alerts[location_id] = {
                'level': level,
                'timestamp': timestamp,
                'status': status,
                'last_alert_time': last_alert_time  # Store as datetime object
            }
            logger.info(f"Restored active alert for {location_id}: {level} level at {timestamp}")
    
    logger.info(f"Restored {len(restored_alerts)} active alerts from database")
    global alert_states
    alert_states = restored_alerts

def cleanup_alert_states(max_age_hours=24):
    """Clean up old entries from alert states dictionaries"""
    global alert_states, resolution_timers
    
    current_time = datetime.now()
    max_age = timedelta(hours=max_age_hours)
    
    # Clean up alert_states - remove entries older than max_age
    to_remove = []
    for location_id, state in alert_states.items():
        last_alert_time = state['last_alert_time']
        if isinstance(last_alert_time, str):
            last_alert_time = datetime.strptime(last_alert_time, '%Y-%m-%d %H:%M:%S')
        if current_time - last_alert_time > max_age:
            to_remove.append(location_id)
    
    for location_id in to_remove:
        del alert_states[location_id]
        logger.debug(f"Cleaned up old alert state for {location_id}")
    
    # Clean up resolution_timers
    to_remove = []
    for key in resolution_timers:
        if current_time - resolution_timers[key]['start_time'] > max_age:
            to_remove.append(key)
    
    for key in to_remove:
        del resolution_timers[key]
        
    total_removed = len(to_remove) + len(to_remove)
    if total_removed > 0:
        logger.info(f"Cleaned up {total_removed} old alert entries")
        
    return total_removed

def main():
    logger.info("Starting alert monitor main loop")
    create_db_if_not_exist()
    # Restore last fired alerts from database

    
    api_url = "http://localhost:5000/get_last_result"
    token = "bearer_token_for_api"
    settings = {
        "COL_In_Cam1": {"yellowThreshold": "1", "yellowResolveThreshold": "0", "orangeThreshold": "2", "orangeResolveThreshold": "1", "redThreshold": "5", "redResolveThreshold": "3"},
        "WW_HC": {"yellowThreshold": "211", "yellowResolveThreshold": "200", "orangeThreshold": "", "orangeResolveThreshold": "", "redThreshold": "", "redResolveThreshold": ""},
        "OE_In_Cam4": {"yellowThreshold": "2", "yellowResolveThreshold": "1", "orangeThreshold": "5", "orangeResolveThreshold": "3", "redThreshold": "10", "redResolveThreshold": "7"}
    }
    
    # Alert settings (in seconds)
    alert_interval = 300  # 5 minutes between reminder alerts
    
    while True:
        try:
            alerts = check_location_alerts(api_url, token, settings, alert_interval)
            logger.debug(f"Current alert state: {alerts}")
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == '__main__':
    main()
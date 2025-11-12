import redis
import cv2
import json

# The spell to summon the configuration from the mystical scrolls
def load_redis_config():
    with open('config_redis.json', 'r') as config_file:
        config = json.load(config_file)
    return config

# The global variable to hold the configuration so it need only be summoned once
redis_config = load_redis_config()

# Create a Redis connection
def get_redis_connection():
    return redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'])

# The shared Redis connection
redisShare = get_redis_connection()

import zlib
def update_web_inspect_frame(aFrame, camera_name):
    # Encode frame to JPEG format
    ret, buffer = cv2.imencode('.jpg', aFrame)
    if not ret:
        print("Failed to encode frame.")
        return

    # Compress the JPEG buffer
    compressed_buffer = zlib.compress(buffer.tobytes())
    
    global redisShare
    # Try to set the value in Redis
    try:
        redisShare.set(camera_name.lower(), compressed_buffer)
    except redis.exceptions.ConnectionError as e:
        print(f"Failed with error: {e}")
        print("Trying to reconnect to Redis...")
        # Attempt to reconnect once
        try:
 
            redisShare = get_redis_connection() # prepare for next call, this 'aFrame' ignored
            # redisShare.set(camera_name.lower(), buffer.tobytes())  # Try to set again after reconnecting
        except Exception as e:
            print(f"Reconnection failed with error: {e}")


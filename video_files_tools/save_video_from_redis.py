import redis
import cv2
import numpy as np
import time
from datetime import datetime
import json
import zlib
import os

# Path to the Redis configuration JSON file
REDIS_CONFIG_PATH = '../shared/config_redis.json'

# Function to read Redis configuration from a JSON file
def read_redis_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config

# Set the frames per second and the duration for each video (10 minutes)
FPS = 25
VIDEO_DURATION = 11 * 60 + 30 # 10 minutes in seconds

def get_image_from_redis(r, camera_name):
    # Retrieve the compressed image from Redis using the provided camera_name
    compressed_image_data = r.get(camera_name.lower())
    if compressed_image_data:
        # Decompress the image data
        image_data = zlib.decompress(compressed_image_data)
        # Convert the image data to a numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        # Decode the numpy array to an image
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    return None

def check_folder_size_and_cleanup(output_folder, max_size_tb=2):
    try:
        # Convert terabytes to bytes
        max_size_bytes = max_size_tb * 1024**4

        # Calculate the total size of the directory
        total_size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in os.walk(output_folder) for filename in filenames)

        # If the total size exceeds the maximum size, delete the oldest files
        while total_size > max_size_bytes:
            oldest_file = min((os.path.join(dirpath, filename) for dirpath, dirnames, filenames in os.walk(output_folder) for filename in filenames), key=os.path.getctime)
            os.remove(oldest_file)
            print(f"Deleted old video parchment: {oldest_file}")
            total_size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in os.walk(output_folder) for filename in filenames)
    
    except Exception as e:
        print(f"An error occurred: {e}")
        
def main(camera_name, original_file_name):
    # Initialize out as None at the beginning
    out = None
    
    try:
        # Read Redis configuration
        redis_config = read_redis_config(REDIS_CONFIG_PATH)
        
        # Connect to Redis
        r = redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'])

        output_folder = 'video_records'
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
                
        while True:
            # Get the start time for the video
            start_time = time.time()
            # Define the filename with a timestamp and camera_name
            destfilename = f"___{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.avi"
            if original_file_name:
                destfilename = original_file_name + destfilename
            destfilename = os.path.join(output_folder, destfilename)

            print(f"record video to file: {destfilename}", flush=True)
            
            # Define the codec and create VideoWriter object
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

            # First frame - get actual dimensions and initialize VideoWriter
            frame = get_image_from_redis(r, camera_name)
            if frame is not None:
                height, width = frame.shape[:2]
                print(f"Actual frame dimensions: {width}x{height}", flush=True)
                out = cv2.VideoWriter(destfilename, fourcc, FPS, (width, height))
                
                # Process the first frame
                out.write(frame)
                cv2.imshow(camera_name, frame)

                # Then continue with your loop for remaining frames
                while True:
                    # Calculate elapsed time
                    elapsed_time = time.time() - start_time
                    if elapsed_time > VIDEO_DURATION:
                        break
                    
                    frame = get_image_from_redis(r, camera_name)
                    if frame is not None:
                        # Write the frame
                        out.write(frame)
                        cv2.imshow(camera_name, frame)
                        
                        # Exit if the user presses 'q'
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
            else:
                print(f"No frame from {camera_name}", flush=True)

            # Release the VideoWriter object
            if out is not None:
                out.release()
            # Output a hint that the video has been saved
            check_folder_size_and_cleanup(output_folder)
            print(f"Video saved to {destfilename}", flush=True)
            
            # Close the display window
            cv2.destroyAllWindows()
            sys.exit() #only save one video

    finally:
        # Safely release resources
        if out is not None:
            out.release()
        # Other cleanup code if needed

def remove_file_extension(file_path):
    # Use os.path.splitext to separate the file name from the extension
    base_name = os.path.splitext(file_path)[0]
    return base_name

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python save_video_from_redis.py <redis_channel> [file_name]")
        sys.exit(1)
    
    redis_channel_name = sys.argv[1]
    src_file_name = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Start redis video recording {redis_channel_name}", flush=True)
    
    if src_file_name:
        src_file_name = remove_file_extension(src_file_name)
        print(f"Saving with file name: {src_file_name}", flush=True)
        main(redis_channel_name, src_file_name)
    else:
        main(redis_channel_name)
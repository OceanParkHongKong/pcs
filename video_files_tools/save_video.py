import cv2
import datetime
import os
import shutil
import argparse
import fcntl
import time
import threading
from collections import namedtuple
import heapq
import subprocess
from urllib.parse import quote

# At the top of your script
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;10000000|buffer_size;1024000"

# Environment variable configuration with defaults
DEFAULT_FPS = 15
DEFAULT_MAX_SIZE_TB = 4
DEFAULT_VIDEO_LENGTH_MINUTES = 10

FPS = int(os.getenv('VIDEO_FPS', DEFAULT_FPS))
MAX_SIZE_TB = float(os.getenv('MAX_SIZE_TB', DEFAULT_MAX_SIZE_TB))
VIDEO_LENGTH_MINUTES = int(os.getenv('VIDEO_LENGTH_MINUTES', DEFAULT_VIDEO_LENGTH_MINUTES))

def flushed_print(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

def save_rtsp_stream(rtsp_url, output_file, video_length_minutes, camera_name=None):
    """
    Save RTSP stream using FFmpeg without re-encoding to preserve original quality
    """
    try:
        print(f"[INFO] Starting RTSP recording to: {output_file}")
        
        # FFmpeg command to save the stream without re-encoding
        ffmpeg_cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-rtsp_transport', 'tcp',  # Use TCP for RTSP
            '-i', rtsp_url,  # Input URL
            '-c:v', 'copy',  # Copy video stream without re-encoding
            '-c:a', 'copy',  # Copy audio stream if present
            '-t', str(video_length_minutes * 60),  # Duration in seconds
            output_file
        ]
        
        # Start FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        flushed_print(f"Recording RTSPstarted at: {datetime.datetime.now().strftime('%H:%M:%S')}")
        flushed_print(f"Will record for {video_length_minutes} minutes")
        
        # Wait for the process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            flushed_print("Recording completed successfully")
            flushed_print(f"Video saved to: {output_file}")
        else:
            flushed_print(f"FFmpeg process failed with return code: {process.returncode}")
            flushed_print(f"FFmpeg error output: {stderr.decode()}")
            raise Exception("FFmpeg recording failed")
            
    except Exception as e:
        flushed_print(f"An error occurred during RTSP recording: {e}")
        raise

def save_camera_video(aCameraURL, output_file, video_length_minutes, fps, camera_name):
    """
    Save non-RTSP camera stream using OpenCV
    """
    try:
        cap = cv2.VideoCapture(aCameraURL)
        
        if not cap.isOpened():
            raise Exception("Cannot open camera stream")

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_file, fourcc, fps, (frame_width, frame_height))

        if not out.isOpened():
            raise Exception("Cannot open output file for writing")

        end_time = datetime.datetime.now() + datetime.timedelta(minutes=video_length_minutes)
        window_name = camera_name if camera_name else 'frame'

        while datetime.datetime.now() < end_time:
            ret, frame = cap.read()
            if not ret:
                flushed_print("Frame capture failed, ending recording.")
                break

            out.write(frame)

#cannot display in docker, env variable to config?
            # Display the resulting frame
            # cv2.imshow(window_name, frame)

            # Process GUI events to avoid window freeze
            # if cv2.waitKey(1) & 0xFF == ord('q'):
                # print("Recording stopped by user.")
                # break

    except Exception as e:
        flushed_print(f"An error occurred: {e}")
        raise

    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if 'out' in locals() and out.isOpened():
            out.release()
        cv2.destroyAllWindows()
        
        # Compress the recorded video
        # if os.path.exists(output_file):
        #     flushed_print("Compressing video...")
        #     compress_video(output_file)
        #     flushed_print("Video compression completed!")
        flushed_print("Resources released, partner! Check your corral for the video.")

FileInfo = namedtuple('FileInfo', ['ctime', 'path', 'size'])

def check_folder_size_and_cleanup(output_folder, max_size_tb=MAX_SIZE_TB):
    lock_file = os.path.join(output_folder, '.cleanup_lock')
    
    try:
        with open(lock_file, 'w') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                flushed_print("Another cleanup process is already running. Skipping.")
                return

            max_size_bytes = max_size_tb * 1024**4
            total_size = 0
            file_list = []

            for dirpath, dirnames, filenames in os.walk(output_folder):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    file_size = os.path.getsize(file_path)
                    file_ctime = os.path.getctime(file_path)
                    total_size += file_size
                    heapq.heappush(file_list, FileInfo(file_ctime, file_path, file_size))

            files_deleted = 0
            try:
                while total_size > max_size_bytes and file_list:
                    oldest_file = heapq.heappop(file_list)
                    os.remove(oldest_file.path)
                    total_size -= oldest_file.size
                    files_deleted += 1
                    flushed_print(f"Deleted old video parchment: {oldest_file.path}")
            except OSError as e:
                flushed_print(f"Error deleting file {oldest_file.path}: {e}")
                flushed_print("Stopping deletion process due to error.")

            flushed_print(f"Deleted {files_deleted} files. Current total size of the output folder: {total_size / (1024**3):.2f} GB")

            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        flushed_print(f"An error occurred during cleanup: {e}")
    finally:
        if os.path.exists(lock_file):
            os.remove(lock_file)

def is_recording_paused():
    current_time = datetime.datetime.now()
    night_pause = current_time.replace(hour=23, minute=0, second=0, microsecond=0)
    morning_pause = current_time.replace(hour=7, minute=0, second=0, microsecond=0)
    
    return current_time >= night_pause or current_time < morning_pause

def start_video_loop(aCameraURL, video_length_minutes=VIDEO_LENGTH_MINUTES, fps=FPS, camera_name=None):
    output_folder = os.path.abspath('video_records')
    print(output_folder)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    flushed_print(f"Starting video loop with FPS: {fps}, Max Size: {MAX_SIZE_TB}TB, Video Length: {video_length_minutes}min")

    while True:
        if is_recording_paused():
            flushed_print(f"Skipping recording during pause time: {datetime.datetime.now()}")
            time.sleep(60)
            continue
        
        current_time = datetime.datetime.now()
        time_str = current_time.strftime('%Y-%m-%d_%H-%M-%S')
        if camera_name:
            output_file = os.path.join(output_folder, f'video_{camera_name}_{time_str}.mp4')
        else:
            output_file = os.path.join(output_folder, f'video_{time_str}.mp4')

        try:
            # Check if the URL is RTSP H264
            if aCameraURL.lower().startswith('rtsp://'):
                save_rtsp_stream(aCameraURL, output_file, video_length_minutes, camera_name)
            else:
                save_camera_video(aCameraURL, output_file, video_length_minutes, fps, camera_name)
            
            cleanup_thread = threading.Thread(target=check_folder_size_and_cleanup, args=(output_folder,))
            cleanup_thread.start()
            
            flushed_print(f"Saved video at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            flushed_print(f"Error during video recording: {e}")
            time.sleep(5)  # Wait a bit before retrying
            continue

parser = argparse.ArgumentParser(description="Start video loop with given URL or default to environment variable URL.")
parser.add_argument('--url', type=str, help='The URL to start the video loop.')
parser.add_argument('--camera_name', type=str, help='The name of the camera to append to the output file.')
parser.add_argument('--fps', type=int, help=f'Frames per second for the video. Default is {FPS}.')

args = parser.parse_args()

secret_key = os.getenv('PEOPLE_COUNT_CROCO_PASS')

if args.url:
    video_url = args.url
else:
    if secret_key:
        video_url = 'http://' + secret_key + '@192.168.camera.ip/mjpg/video.mjpg'
    else:
        video_url = None
        flushed_print("The secret key was not found in the environment.")

if video_url:
    flushed_print("start video loop")
    fps = args.fps if args.fps is not None else FPS
    start_video_loop(video_url, camera_name=args.camera_name, fps=fps)
else:
    flushed_print("Need url argument.")
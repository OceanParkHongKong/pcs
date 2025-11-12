import argparse
import cv2
import numpy as np
import redis
import base64
import ast
import re
from pathlib import Path
# from boxmot.trackers.bytetrack.byte_tracker import BYTETracker
from byte_tacker import BYTETracker
from empty_tracker import EmptyTracker
from boxmot.trackers.ocsort.ocsort import OCSort 
import time
import sys
import os
import json

# Set OpenCV FFMPEG options for RTSP before any cv2.VideoCapture usage
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;10000000|buffer_size;1024000"

from urllib.parse import urlparse
from collections import deque
import torch
import logging
# Import the pipe utilities
from pipe_utils import reset_pipe, DetectionPipeReader, FramePipeWriter, get_detection_string_from_pipe

# Add this import near the top of the file, around line 15
import kafka_sender

# Global logger variable
logger = logging.getLogger('people_counter')

# Initialize the logging
def setup_logging(camera_name):
    global logger  # Not strictly necessary but makes it explicit
    log_dir = f"logs/{time.strftime('%Y%m%d')}"
    os.makedirs(log_dir, exist_ok=True)
    log_file = f"{log_dir}/{camera_name}.log"
    
    # Create a file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Configure the logger
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add the file handler
    logger.addHandler(file_handler)

# Initialize the connection to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Note: get_detection_string_from_pipe is now imported from pipe_utils
    
label_map = {'person': 2, 'car': 3, 'bike': 4, 'head': 5}  # Example label map

from typing import List, Dict, Any
class DetectionResult:
    def __init__(self, image_path: str, orig_img: np.ndarray, label_map: Dict[str, int]):
        self.path = image_path
        self.orig_img = orig_img
        self.orig_shape = orig_img.shape
        self.label_map = label_map
        self.boxes = None  # To be filled after parsing
        self.masks = None  # Optional: to be implemented
        self.probs = None  # Optional: to be implemented
        self.keypoints = None  # Optional: to be implemented
        self.speed = {'preprocess': 0, 'inference': 0, 'postprocess': 0}
        self.names = {v: k for k, v in label_map.items()}

    def parse_detections(self, detection_str: str):
        """
        Parse string-encoded detection results and update the object attributes.

        Parameters:
        - detection_str (str): String containing detection results in a specific format.
        """
        detections_raw = re.findall(r'\{.*?\}', detection_str.replace(' ', ''))
        detections = []

        for det in detections_raw:
            det_dict = ast.literal_eval(det)
            bbox_str = det_dict['bbox']
            bbox = ast.literal_eval(bbox_str)
            x1_rel, y1_rel, width_rel, height_rel = bbox
            # Adjust y1 relative position
            y1_rel = 1 - y1_rel - height_rel

            # Convert relative positions to absolute pixel positions
            x1 = (x1_rel * self.orig_shape[1])
            y1 = (y1_rel * self.orig_shape[0])
            width = (width_rel * self.orig_shape[1])
            height = (height_rel * self.orig_shape[0])
            x2 = x1 + width
            y2 = y1 + height

            # Retrieve label ID using label map, default to -1 if not found
            label_id = self.label_map.get(det_dict['label'], -1)
            
            # Create a detection entry
            confidence = float(det_dict['confidence'])
            detections.append([x1, y1, x2, y2, confidence, label_id])

        self.boxes = np.array(detections, dtype=np.float64)

def trackerInit(aThresh=0.6, use_empty_tracker=False, tracker_type="byte"):
    """
    Initialize tracker based on type
    
    Args:
        aThresh: Tracking threshold
        use_empty_tracker: Whether to use empty tracker
        tracker_type: Type of tracker ("byte", "deepsort", "simple_deepsort")
    """
    if use_empty_tracker:
        tracker = EmptyTracker()
    elif tracker_type == "ocsort":
        tracker = OCSort(
            asso_func="centroid", # important for fast moving objects tracking
            per_class=False,
            det_thresh=0.5, # Minimum confidence score required for a detection to be considered for tracking
            max_age=10,
            min_hits=3,
            asso_threshold=0.9,# Minimum similarity score (IoU/GIoU/etc.) required to associate a detection with an existing track
            delta_t=3,
            inertia=0.2, #Weight for velocity direction consistency in the association cost. Higher values make the tracker more sensitive to direction changes and movement patterns.
            use_byte=False
        )
    else:  # default to ByteTrack
        tracker = BYTETracker(
            track_thresh=aThresh,
            match_thresh=0.8,
            track_buffer=30,
            frame_rate=30
        )
    return tracker

FPS = 15 * 5
TARGET_TIME_PER_FRAME = 1.0 / FPS

class VideoFrameFetcher:
    def __init__(self, url, quit_process, crop_params=None):
        self.url = url
        self.quit_process = quit_process
        self.crop_params = crop_params  # (y1, y2, x1, x2) or None
        self.cap = cv2.VideoCapture(url)
        if not self.cap.isOpened():
            logger.error("Error opening video stream or file")
        
    def fetch_frame(self):
        while True:
            if not self.cap.isOpened():
                logger.warning("Video capture not opened, retrying...")
                self.cap = cv2.VideoCapture(self.url)
                time.sleep(5)
                continue
            
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to retrieve the frame or end of video.")
                if self.quit_process:
                    logger.info("Quitting process as 'quit_process' is set to True.")
                    os._exit(0)  
                else:
                    logger.warning("Retrying...")
                    time.sleep(5)
                    if self.cap.isOpened():
                        self.cap.release()
                    self.cap = cv2.VideoCapture(self.url)  # Re-open the URL
                    continue
            
            # Apply cropping if crop_params are provided
            if self.crop_params is not None:
                y1, y2, x1, x2 = self.crop_params
                frame = np.ascontiguousarray(frame[y1:y2, x1:x2])
            
            return frame
    
    def release(self):
        if self.cap.isOpened():
            self.cap.release()
            logger.info("Video stream released")
            
frame_fetcher: VideoFrameFetcher

# Note: DetectionPipeReader is now imported from pipe_utils
        
frame_counter = 0

def save_image(im, camera_name, region_count_result, use_png=False):
    """
    Save image to verify_images folder with frame number in filename
    
    Args:
        im: The image/frame to save
        camera_name: Name of the camera for the filename
        region_count_result: Count result to append to CSV
        use_png: Whether to save as PNG (higher quality) or JPG (smaller size)
    """
    global frame_counter
    
    # Create verify_images directory if it doesn't exist
    verify_dir = f"verify_images_{camera_name}"
    os.makedirs(verify_dir, exist_ok=True)
    
    # Generate filename with frame number
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    file_extension = "png" if use_png else "jpg"
    filename = f"{camera_name}_frame_{frame_counter:06d}_{timestamp}.{file_extension}"
    filepath = os.path.join(verify_dir, filename)
    
    # Save the image with quality settings
    if use_png:
        # PNG: lossless compression
        cv2.imwrite(filepath, im, [cv2.IMWRITE_PNG_COMPRESSION, 6])  # 0-9, 6 is good balance
    else:
        # JPG: high quality (95%)
        cv2.imwrite(filepath, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    logger.info(f"Saved frame {frame_counter} to {filepath}")
    
    # Append region count result to CSV file
    csv_filename = f"{camera_name}_region_count.csv"
    
    with open(csv_filename, 'a', newline='') as csvfile:
        csvfile.write(f"{camera_name}\t{frame_counter}\t{region_count_result}\n")

def get_next_frame():
    global frame_fetcher, frame_counter
    frame = frame_fetcher.fetch_frame()
    if frame is not None:
        frame_counter += 1
    return frame

# Note: FramePipeWriter is now imported from pipe_utils

def prepare_video_source(video_url, quit_process, crop_param_str=None):
    global frame_fetcher
    
    # Parse crop parameters from string if provided
    crop_params = None
    # print(f"crop_param_str larry: {crop_param_str}", flush=True)
    if crop_param_str and len(crop_param_str.strip()) > 0:
        try:
            # Parse the string format "y1,y2,x1,x2"
            crop_values = [int(x.strip()) for x in crop_param_str.split(',')]
            if len(crop_values) == 4:
                crop_params = tuple(crop_values)  # (y1, y2, x1, x2)
                logger.info(f"Using crop parameters: {crop_params}")
            else:
                logger.error(f"Invalid crop parameter format: {crop_param_str}. Expected 4 values separated by commas.")
        except ValueError as e:
            logger.error(f"Failed to parse crop parameters '{crop_param_str}': {e}")
    
    frame_fetcher = VideoFrameFetcher(video_url, quit_process, crop_params)
    
    # Determine if the URL is a file path or a network URL
    if video_url.startswith("http://") or video_url.startswith("https://"):
        # Parse the URL to extract the hostname (IP address)
        parsed_url = urlparse(video_url)
        result = parsed_url.hostname
    else:
        # Extract the file name from the full path
        result = os.path.basename(video_url)
    
    # Return the result based on the type of video_url
    return result

import object_counter

def parse_points(points_str):
    if points_str == '' or points_str == None:
        return None
    
    try:
        points = ast.literal_eval(points_str)
        if isinstance(points, list) and all(isinstance(p, tuple) and len(p) == 2 for p in points):
            return points
        else:
            raise ValueError
    except:
        raise ValueError("Invalid format for points. Expected a list of tuples.")

class Box:
    def __init__(self, xyxy, box_id, aClass, confs):
        if not isinstance(xyxy, torch.Tensor):
            self.xyxy = torch.tensor(xyxy)
        else:
            self.xyxy = xyxy
        if not isinstance(aClass, torch.Tensor):
            self.cls = torch.tensor([int(aClass)], dtype=torch.int64)  # Explicit conversion to int
        else:
            self.cls = aClass
        if not isinstance(box_id, torch.Tensor):
            self.id = torch.tensor([box_id], dtype=torch.int64)  # Assuming class labels are integers
        else:
            self.id = box_id
        if not isinstance(confs, torch.Tensor):
            self.conf = torch.tensor([confs], dtype=torch.float64)
        else:
            self.conf = confs
            
    def __getitem__(self, index):
        return self.xyxy[index].item()  # Use .item() to convert from tensor to Python number

class WrappedSTrack:
    def __init__(self, boxes):
        self.boxes = boxes

class WrappedSTrackCollection:
    def __init__(self):
        self.ids = []
        self.classes = []
        self.xyxyList = []
        self.confs = []

    def add_box(self, box):
        self.ids.append(box.id.item())  # Assuming id is a tensor with a single value
        self.classes.append(box.cls.item())  # Assuming cls is a tensor with a single value
        self.xyxyList.append(box.xyxy.tolist())  # Convert tensor to list
        self.confs.append(box.conf)

    @property
    def id(self):
        return torch.tensor(self.ids)

    @property
    def cls(self):
        return torch.tensor(self.classes)

    @property
    def xyxy(self):
        return torch.tensor(self.xyxyList)
    
    @property
    def conf(self):
        return torch.tensor(self.confs)
    
def wrap_strack_objects(strack_list):
    collection = WrappedSTrackCollection()
    for strack in strack_list:
        if hasattr(strack, 'get_state'):
            state = strack.get_state()
            # print(f"get_state() returns: {state}")
            # print(f"State type: {type(state)}")
            # print(f"State shape/length: {len(state) if hasattr(state, '__len__') else 'no length'}")
            
            # Try to extract coordinates properly
            if hasattr(state, 'flatten'):  # numpy array
                xyxy = state.flatten()[:4].tolist()
            elif isinstance(state, (list, tuple)):
                if len(state) > 0 and isinstance(state[0], (list, tuple)):
                    xyxy = list(state[0][:4])  # Nested list
                else:
                    xyxy = list(state[:4])     # Flat list
            else:
                xyxy = [state[0], state[1], state[2], state[3]]
        else:        
            xyxy = strack.xyxy
            
        box = Box(xyxy=xyxy, box_id=strack.id, aClass=strack.cls, confs=strack.conf)
        collection.add_box(box)
    return collection

# Initialize the counter
iteration_counter = 0
    
def sleep_for_frame_rate (start_time, camera_name):
    global iteration_counter
    iteration_counter += 1

    end_time = time.time()  # End time of the loop
    elapsed_time = end_time - start_time  # Calculate the elapsed time of the loop
    elapsed_time_ms = int(elapsed_time * 1000)  # Convert to milliseconds        
    if iteration_counter % 10 == 0:
        if camera_name == "COL_In_Cam1":
            logger.info(f"{elapsed_time_ms:03d}ms {camera_name}")  # Print elapsed time in '000ms' format
        # for handler in logging.handlers:
        #     handler.flush()  # Flush the handler to ensure immediate log writing
    sleep_time = TARGET_TIME_PER_FRAME - elapsed_time
    if sleep_time > 0:
        time.sleep(sleep_time)

last_print_in, last_print_out = 0, 0
# Add new global variables for Kafka tracking
last_kafka_in, last_kafka_out, last_kafka_region = 0, 0, 0
last_region_only_send_time = {}  # Add this
region_only_throttle_interval = 3.0  # Add this

import database_sqlite as database
def load_kafka_config(config_file="../shared/config_kafka.json"):
    """
    Load Kafka configuration from JSON file
    
    Returns:
        dict: Kafka configuration or None if disabled/not found
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        if not config.get('enabled', False):
            logger.info("Kafka sending is disabled in config")
            return None
            
        required_fields = ['bootstrap_servers', 'topic']
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required Kafka config field: {field}")
                return None
        
        logger.info(f"Loaded Kafka config - servers: {config['bootstrap_servers']}, topic: {config['topic']}")
        return config
        
    except FileNotFoundError:
        logger.warning(f"Kafka config file '{config_file}' not found. Kafka sending disabled.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in Kafka config file: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading Kafka config: {e}")
        return None

# Load Kafka config at module level
kafka_config = load_kafka_config()

def should_send_kafka_message(camera_name, in_count, out_count, region_count):
    """
    Determine if a Kafka message should be sent based on throttling rules.
    
    Rules:
    - Always send if in_count or out_count changed
    - If only region_count changed, throttle to ? message per second
    
    Returns:
        bool: True if message should be sent, False if throttled
    """
    global last_kafka_in, last_kafka_out, last_kafka_region
    global last_region_only_send_time, region_only_throttle_interval  # Add this line
    
    # Check what changed
    in_count_changed = last_kafka_in != in_count
    out_count_changed = last_kafka_out != out_count
    region_count_changed = last_kafka_region != region_count
    
    # If nothing changed, don't send
    if not (in_count_changed or out_count_changed or region_count_changed):
        return False
    
    # Always send if in_count or out_count changed
    if in_count_changed or out_count_changed:
        logger.debug(f"📤 Sending immediate update for {camera_name} - in/out count changed")
        return True
    
    # Only region_count changed - apply throttling
    if region_count_changed:
        current_time = time.time()
        
        if camera_name in last_region_only_send_time:
            time_since_last_send = current_time - last_region_only_send_time[camera_name]
            
            if time_since_last_send < region_only_throttle_interval:
                remaining_time = region_only_throttle_interval - time_since_last_send
                logger.debug(f"⏳ Throttling region-only update for {camera_name} (next send in {remaining_time:.1f}s)")
                return False
        
        # Send the throttled region update
        last_region_only_send_time[camera_name] = current_time
        logger.debug(f"📤 Sending throttled region-only update for {camera_name}")
        return True
    
    return False

def record_count_result (in_count, out_count, region_count, url, args):
    # Define camera_name at the beginning of the function
    camera_name = args.camera_name
    # logger.info(f"in {in_count} out {out_count} name {args.camera_name}")
    database.insert_people_count_result_interval (in_count, out_count, region_count, args.camera_name, url)
    
    # Send to Kafka if enabled, configured, and should send based on throttling rules
    if args.send_count_kafka and kafka_config:
        if should_send_kafka_message(camera_name, in_count, out_count, region_count):
            try:
                # Send to Kafka asynchronously using the new async sender
                success = kafka_sender.send_count_to_kafka_async(
                    in_count=in_count,
                    out_count=out_count, 
                    region_count=region_count,
                    camera_name=camera_name,
                    bootstrap_servers=kafka_config['bootstrap_servers'],
                    topic=kafka_config['topic']
                )
                
                if success:
                    logger.debug(f"✅ Queued for Kafka - in:{in_count}, out:{out_count}, region:{region_count}, camera:{camera_name}")
                    # Update the last sent values when successfully queued
                    global last_kafka_in, last_kafka_out, last_kafka_region
                    last_kafka_in = in_count
                    last_kafka_out = out_count
                    last_kafka_region = region_count
                else:
                    logger.warning(f"❌ Failed to queue count result for Kafka (queue full) for camera {camera_name}")
                    
            except Exception as e:
                logger.error(f"❌ Error queuing message for Kafka for camera {camera_name}: {e}")
        else:
            # Counts haven't changed, no need to send
            logger.debug(f"Counts unchanged for {camera_name}, skipping Kafka send")
            
    elif args.send_count_kafka and not kafka_config:
        logger.warning("Kafka sending requested but no valid config found")
    
    if args.show_count_test:
      global last_print_in, last_print_out
      if last_print_in != in_count or last_print_out != out_count:
            print(f"in_count:{in_count} out_count:{out_count} {args.camera_name}", flush=True)
            last_print_in = in_count
            last_print_out = out_count
            
import re
def mask_password_in_url(url):
    # This pattern will match the username and password in the URL (user:pass@)
    pattern = r'(?<=://)([^:@/]+):([^:@/]+)@'
    # Replace the found pattern with 'username:xxxxx@' to mask the password
    masked_url = re.sub(pattern, r'\1:xxxxx@', url)
    return masked_url
source_url_mask = ""

import concurrent.futures        
def main_loop(writer, reader, oCounter, args):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    def update_web_inspect_frame_in_thread(im, camera_name):
        redis_share.update_web_inspect_frame(im, camera_name)
        
    while True:
        loop_start_time = time.time()  # Start time of the loop
        
        im = get_next_frame()
        if im is None:
            continue
        
        writer.put_frame_to_pipe(im)

        detection_str = get_detection_string_from_pipe(reader)
            
        if detection_str is None: #no detections
            executor.submit(update_web_inspect_frame_in_thread, im, args.camera_name)

            # TODO: this is never executed???
            print ("some print here, never executed???", flush=True)
                    
            sleep_for_frame_rate(loop_start_time, args.camera_name)
            continue
        
        dets = DetectionResult("", im, label_map)
        dets.parse_detections(detection_str)

        # Ensure dets.boxes is a properly formatted 2D array even when empty
        if dets.boxes is None or len(dets.boxes) == 0:
            # Create an empty array with the correct shape (0, 6) for [x1, y1, x2, y2, confidence, class]
            dets.boxes = np.zeros((0, 6), dtype=np.float64)
        
        # Now call tracker.update with properly formatted input
        trackerResult = tracker.update(dets.boxes, im)
        
        if len(dets.boxes) == 0:
            oCounter.annotator_init(im)
            oCounter.draw_in_out_count_labels()
            
            executor.submit(update_web_inspect_frame_in_thread, im, args.camera_name)
            
            record_count_result(oCounter.in_counts, oCounter.out_counts, oCounter.region_count_result, source_url_mask, args)
            
                        # for empty detections, save the frame too.
            if args.test_save_frame:
                save_image(im, args.camera_name, oCounter.region_count_result, use_png=True)
                
            sleep_for_frame_rate(loop_start_time, args.camera_name)
            continue
        
        # Process active tracks
        lResults = WrappedSTrack(wrap_strack_objects(tracker.active_tracks))

        oCount_img = oCounter.start_counting(im, [lResults])

        #wait key spend 13ms?
        # start_time = time.time()
        # key = cv2.waitKey(1) & 0xFF
        # if key == ord(' ') or key == ord('q'):
        #     break
        # print_elapsed_time(start_time, "CV2 wait key")
        
        executor.submit(update_web_inspect_frame_in_thread, oCount_img, args.camera_name)
        
        if args.test_save_frame:
            save_image(im, args.camera_name, oCounter.region_count_result, use_png=True)
                    
        record_count_result(oCounter.in_counts, oCounter.out_counts, oCounter.region_count_result, source_url_mask, args)
        
        sleep_for_frame_rate(loop_start_time, args.camera_name)
    
    executor.shutdown()  # Clean up the thread pool
        
import redis_share     
@torch.no_grad()       # save memory, speed up, exact same result https://poe.com/s/cr1sfqTpZF3wYn7Csuxu             
def main():

    parser = argparse.ArgumentParser(description="Video Processing Script")
    parser.add_argument('--video_url', type=str, required=True, help='URL or path to the video stream')
    parser.add_argument('--camera_name', type=str, default='test1', help='Path to the pipe to retrieve detection results')
    parser.add_argument('--show-count-test', action='store_true', help='Output people count result to console for testing')
    parser.add_argument('--test-save-frame', action='store_true', help='Save frames to verify_images folder for testing')
    parser.add_argument('--model', type=str, default='cableCar', help='cableCar, crocoland or meerkat?')
    parser.add_argument('--region', type=str, default='', help='Specify the couting region, optional')
    parser.add_argument('--end-quit', action='store_true', help='Stop process if the end of the video is reached, optional')
    parser.add_argument('--in_direction', type=str, default='y+', help='Direction for in_count, default is "y+"')
    parser.add_argument('--crop-param', type=str, default='', help='Crop parameters in format "y1,y2,x1,x2" (e.g. "4,484,359,999")')
    
    # Keep only the enable flag for Kafka
    parser.add_argument('--send-count-kafka', action='store_true', help='Send counting results to Kafka (requires config_kafka.json)')
    
    args = parser.parse_args()

    setup_logging(args.camera_name)
    
    # Log Kafka configuration status
    if args.send_count_kafka:
        if kafka_config:
            logger.info(f"Kafka sending enabled - servers: {kafka_config['bootstrap_servers']}, topic: {kafka_config['topic']}")
        else:
            logger.warning("Kafka sending requested but no valid configuration found")
    
    global source_url_mask
    source_url_mask = mask_password_in_url(args.video_url)
    
    pipe_write_path = "/tmp/" + args.camera_name
    reset_pipe(pipe_write_path)
    reset_pipe(pipe_write_path + "_result")
    print("two pipes ready", flush=True)  # this is a signal to start Swift process
    
    winTitle = prepare_video_source(args.video_url, args.end_quit, args.crop_param)

    oCounter = object_counter.ObjectCounter(winTitle)
    region_points = ""
    in_direction = ""
    global tracker
    global FPS, TARGET_TIME_PER_FRAME
    
    if args.model == 'cableCar':
        region_points = "[(0, 200), (640, 200), (640, 250), (0, 250)]"
        in_direction = "y+"
        tracker = trackerInit(0.6, use_empty_tracker=False)
        FPS = 15
        TARGET_TIME_PER_FRAME = 1.0 / FPS
    elif args.model == 'crocoland':
        region_points = "[(539, 6),(392, 28),(278, 82),(224, 182),(251, 337),(446, 461),(788, 568),(1153, 605),(1207, 11)]"
        in_direction = "border"
        tracker = trackerInit(0.5, use_empty_tracker=False)
        FPS = 25
        TARGET_TIME_PER_FRAME = 1.0 / FPS
    elif args.model == 'meerkat':
        region_points = "[(0, 250), (640, 250), (640, 300), (0, 300)]"
        in_direction = "y+"
        tracker = trackerInit(0.5, use_empty_tracker=False)
        FPS = 15
        TARGET_TIME_PER_FRAME = 1.0 / FPS
    elif args.model == 'ww_pool_1920' or args.model == 'ww_riptide_1920' or args.model == 'ww_riptide_960':
        region_points = "[(663,269),(14,1072),(1908,1072),(1916,559),(1541,299)]"
        in_direction = "border"
        tracker = trackerInit(0.5, use_empty_tracker=True)
        FPS = 5
        TARGET_TIME_PER_FRAME = 1.0 / FPS
    elif args.model == 'ww_riptide' or args.model == 'ww_pool' or args.model == 'ww_ws_lc_small_head' or args.model == 'ww_7in1' or args.model == 'ww_9in1':
        region_points = "[(537,400),(466,451),(1076,458),(1030,401)]"
        in_direction = "y+"
        tracker = trackerInit(0.5, use_empty_tracker=False)
        FPS = 15
        TARGET_TIME_PER_FRAME = 1.0 / FPS
    elif args.model == 'ww_9in1_slides':
        region_points = "[(537,400),(466,451),(1076,458),(1030,401)]"
        in_direction = "y+"
        tracker = trackerInit(0.5, use_empty_tracker=False, tracker_type="ocsort")
        FPS = 15
        TARGET_TIME_PER_FRAME = 1.0 / FPS
    #use calbleCar model, but different region_point for NP_Out_Cam1 ?
    else:
        raise Exception("wrong model parameter, got: " + args.model)
    
    if len(args.in_direction) > 0:
        in_direction = args.in_direction
    
    if len(args.region) > 0:
        logger.info(f"set customized region {len(args.region)}  {args.region}")
        
        # Check if args.region contains '|' to split into main and additional regions
        if '|' in args.region:
            # Split into main region and additional region
            parts = args.region.split('|', 1)  # Split only on first '|' to keep all remaining parts together
            region_points = parts[0].strip()
            additional_region_points = parts[1]  # Keep all remaining parts including any additional '|' separators
            logger.info(f"Main region: {region_points}")
            logger.info(f"Additional region: {additional_region_points}")
        else:
            # No '|' found, use the entire string as main region
            region_points = args.region
            additional_region_points = None
        logger.info(f"region_points: {region_points} additional_region_points: {additional_region_points}")
    else:
        additional_region_points = None

    oCounter.set_args(view_img=True,
                      reg_pts=parse_points(region_points),
                      additional_reg_pts=(additional_region_points),  # New parameter
                      classes_names={5: 'head', 1: 'person', 2: 'type2', 3: 'type3', 4: 'type4', 0: 'type0', -1: 'type-1'},
                      line_thickness=1,
                      region_thickness=2 if args.model == 'ww_pool_1920' else 5,
                      track_thickness=1 if args.model == 'ww_pool_1920' else 2,
                      draw_tracks=True,
                      draw_head_box=False if args.model == 'ww_pool_1920' or args.model == 'ww_riptide' or args.model == 'ww_ws_lc_small_head' else True,
                      in_direction=in_direction)
    
    pipe_reader = DetectionPipeReader(pipe_write_path + "_result")
    pipe_writer = FramePipeWriter(pipe_write_path)

    main_loop(writer=pipe_writer, reader=pipe_reader, oCounter=oCounter, args=args)

    # Clean up Kafka sender before exit
    if args.send_count_kafka:
        kafka_sender.close_async_kafka_sender()

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
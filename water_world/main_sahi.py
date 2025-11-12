import argparse
from pathlib import Path
import cv2
from sahi import AutoDetectionModel
from sahi_predict import get_sliced_prediction
# from sahi.utils.yolov11 import download_yolov11s_model
from ultralytics.utils.files import increment_path

import sys
from pathlib import Path
# Add the parent directory to sys.path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
from shared import redis_share 

import time
import re

from swift import database_sqlite as database

import os
import logging
from logging.handlers import RotatingFileHandler

# Declare logger as a module-level variable
logger = None

def setup_logging(camera_name):
    """
    Setup logging configuration with camera-specific log file
    
    Args:
        camera_name (str): Name of the camera to use in log file name
    """
    global logger  # Use the global logger variable
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Configure the logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create log file name with camera name prefix
    log_file = os.path.join("logs", f'{camera_name}_sahi.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=100*1024*1024,  # 100MB
        backupCount=5
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def draw_region_on_frame(frame, region_points, color=(0, 255, 0), thickness=5):
    """
    Draw a region on the frame using the provided points.
    
    Args:
        frame (numpy.ndarray): The frame to draw on
        region_points (list): List of points defining the region
        color (tuple): Color of the region outline (BGR format)
        thickness (int): Thickness of the region outline
    """
    import numpy as np
    from swift.plotting import Annotator
    
    # Create an annotator object
    annotator = Annotator(frame, line_width=thickness)
    
    # Draw the region
    annotator.draw_region (region_points, color=color, thickness=thickness)
    
    return annotator.result()

def draw_boxes_count(frame, num_boxes, font_size=2.0):
    text = f"OCC: {num_boxes}"
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_size, 2)[0]
    text_x = (frame.shape[1] - text_size[0] - 120)- 100 #right 
    text_y = 100

    cv2.rectangle(frame, (text_x - 10, text_y - text_size[1] - 10), 
                  (text_x + text_size[0] + 10, text_y + 10), (255, 255, 255), cv2.FILLED)
    cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_size, (0, 0, 0), 2)
    logger.debug(f"Number of boxes detected: {num_boxes}")

class VideoCaptureFetcher:
    def __init__(self, source):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            logger.error("Error opening video stream or file")
            
    def get_frame(self):
        while True:
            if not self.cap.isOpened():
                logger.warning("Video capture not opened, retrying...")
                self.cap = cv2.VideoCapture(self.source)
                time.sleep(5)
                continue
            
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Failed to retrieve the frame or end of video.")
                logger.warning("Retrying...")
                time.sleep(5)
                if self.cap.isOpened():
                    self.cap.release()
                self.cap = cv2.VideoCapture(self.source)
                continue
            
            return frame, True
            
    def get_properties(self):
        return {
            'width': int(self.cap.get(3)),
            'height': int(self.cap.get(4)),
            'fps': int(self.cap.get(5)),
        }
    
    def release(self):
        if self.cap.isOpened():
            self.cap.release()
            logger.info("Video stream released")

def mask_password_in_url(url):
    # This pattern will match the username and password in the URL (user:pass@)
    pattern = r'(?<=://)([^:@/]+):([^:@/]+)@'
    # Replace the found pattern with 'username:xxxxx@' to mask the password
    masked_url = re.sub(pattern, r'\1:xxxxx@', url)
    return masked_url

source_url_mask = ""

def run(weights="yolov11n.pt", source="test.mp4", view_img=True, save_img=False, exist_ok=False, camera_name="camera", 
        region_points="", pipe_reader=None, pipe_writer=None):
    global source_url_mask
    source_url_mask = mask_password_in_url(source)
    
    yolov11_model_path = f"models/{weights}"

    logger.info("yolov11_model_path: " + yolov11_model_path,  os.path.exists(yolov11_model_path))
        
    # Replace direct VideoCapture with our new VideoCaptureFetcher
    video_fetcher = VideoCaptureFetcher(source)
    props = video_fetcher.get_properties()
    frame_width, frame_height = props['width'], props['height']
    fps, fourcc = props['fps'], cv2.VideoWriter_fourcc(*"mp4v")

    save_dir = increment_path(Path("ultralytics_results_with_sahi") / "exp", exist_ok)
    save_dir.mkdir(parents=True, exist_ok=True)
    video_writer = cv2.VideoWriter(str(save_dir / f"{Path(source).stem}.mp4"), fourcc, fps, (frame_width, frame_height))

    # Parse region points from string
    try:
        # Check if the input is in the format [(x,y),(x,y),...] 
        if region_points.strip().startswith('[') and region_points.strip().endswith(']'):
            # Extract the content between the square brackets
            content = region_points.strip()[1:-1]
            # Split by '),(' to get individual points
            point_strings = content.split('),(')
            # Clean up the first and last point
            point_strings[0] = point_strings[0].lstrip('(')
            point_strings[-1] = point_strings[-1].rstrip(')')
            
            # Parse each point
            region_points = []
            for point_str in point_strings:
                x, y = map(int, point_str.split(','))
                region_points.append((x, y))
        else:
            # Original comma-separated format
            coords = [int(x) for x in region_points.split(',')]
            region_points = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
    except Exception as e:
        logger.error(f"Error parsing region points: {e}. Using default region.")
        region_points = [(455, 267), (1531, 297), (1559, 1066), (144, 1068)]

    while True:
        try:
            frame, success = video_fetcher.get_frame()
            if not success:
                continue

            results = get_sliced_prediction(
                frame, None, slice_height=640, slice_width=640, 
                overlap_height_ratio=0.2, overlap_width_ratio=0.2, 
                pipe_reader=pipe_reader, pipe_writer=pipe_writer
            )
            object_prediction_list = results.object_prediction_list

            boxes_list = []
            clss_list = []
            for ind, _ in enumerate(object_prediction_list):
                boxes = (
                    object_prediction_list[ind].bbox.minx,
                    object_prediction_list[ind].bbox.miny,
                    object_prediction_list[ind].bbox.maxx,
                    object_prediction_list[ind].bbox.maxy,
                )
                clss = object_prediction_list[ind].category.name
                boxes_list.append(boxes)
                clss_list.append(clss)

            for box, cls in zip(boxes_list, clss_list):
                x1, y1, x2, y2 = box
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (56, 56, 255), 1)
                label = str(cls)
                t_size = cv2.getTextSize(label, 0, fontScale=0.3, thickness=1)[0]

            # Draw region on frame
            frame = draw_region_on_frame(frame, region_points, color=(255, 0, 255), thickness=5)
            
            if region_points:
                from shapely.geometry import Polygon, Point
                # Create polygon from region points
                region_polygon = Polygon(region_points)
                
                # Count boxes inside the region
                boxes_inside_region = 0
                for box in boxes_list:
                    # Get center point of the box
                    x1, y1, x2, y2 = box
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    
                    # Check if center point is inside polygon
                    if region_polygon.contains(Point(center_x, center_y)):
                        boxes_inside_region += 1
                
                draw_boxes_count(frame, boxes_inside_region)
                # Add database insertion here
                # need ln -s ../swift/people_count_database.db .    
                database.insert_people_count_result_interval(0, 0, boxes_inside_region, camera_name, source_url_mask)
            else:
                total_boxes = len(boxes_list)
                draw_boxes_count(frame, total_boxes)
                # Add database insertion here for non-region case
                database.insert_people_count_result_interval(0, 0, total_boxes, camera_name, source_url_mask)

            # Use the custom function to write frame to Redis
            redis_share.update_web_inspect_frame(frame, camera_name)

            if view_img:
                cv2.imshow(Path(source).stem, frame)
            if save_img:
                video_writer.write(frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(1)
            continue

    video_writer.release()
    video_fetcher.release()
    cv2.destroyAllWindows()

def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=str, default="yolov11n.pt", help="initial weights path")
    parser.add_argument("--source", type=str, required=True, help="video file path")
    parser.add_argument("--view-img", action="store_true", help="show results")
    parser.add_argument("--save-img", action="store_true", help="save results")
    parser.add_argument("--exist-ok", action="store_true", help="existing project/name ok, do not increment")
    parser.add_argument("--camera-name", type=str, default="camera", help="Redis key for camera name")
    parser.add_argument("--region-points", type=str, default="[(455,267),(1531,297),(1559,1066),(144,1068)]", 
                        help="Comma-separated list of x,y coordinates defining the region")
    return parser.parse_args()

from swift.pipe_utils import reset_pipe, DetectionPipeReader, FramePipeWriter

def main(opt, pipe_reader, pipe_writer):
    # Setup logging with camera name
    setup_logging(opt.camera_name)
    
    # Now you can use logger directly throughout the code
    logger.info(f"Starting SAHI detection for camera: {opt.camera_name}")
    
    run(**vars(opt), pipe_reader=pipe_reader, pipe_writer=pipe_writer)

pipe_reader = None
pipe_writer = None

if __name__ == "__main__":
    opt = parse_opt()
    
    pipe_write_path = "/tmp/" + opt.camera_name
    reset_pipe (pipe_write_path)
    reset_pipe (pipe_write_path + "_result")
    print ("two pipes ready", flush=True) # this is a singal to start Swift process
    
    pipe_reader = DetectionPipeReader(pipe_write_path + "_result")
    pipe_writer = FramePipeWriter(pipe_write_path)
    
    # logger.info ("pipe_reader and pipe_writer ready")
    
    main(opt, pipe_reader, pipe_writer)
    

    
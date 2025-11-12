import cv2
import time
import logging
from flask import Flask, Response
import argparse
import os
import threading

# Initialize the Flask app
app = Flask(__name__)

# Setup logging to save to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("video_streamer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Command-line argument parsing
parser = argparse.ArgumentParser(description="Video Streamer with FPS, Port, and Video Source control")
parser.add_argument('--fps', type=int, default=15, help='Frames per second for the video stream')
parser.add_argument('--port', type=int, default=3000, help='Port number to run the Flask app on')
parser.add_argument('--video', type=str, required=True, help='Path to the video source')
parser.add_argument('--loop', action='store_true', help='Loop the video when it reaches the end')
parser.add_argument('--quality', type=int, default=95, 
                   help='JPEG quality (0-100, higher means better quality)')
args = parser.parse_args()

video_source = args.video
fps = args.fps  # Set the desired FPS
loop = args.loop

# Add these global variables after the args parsing
current_frame = None
frame_lock = threading.Lock()
should_run = True

def update_frame_buffer():
    global current_frame, should_run
    cap = cv2.VideoCapture(video_source)
    
    # Get the quality parameter
    quality = min(max(args.quality, 0), 100)  # Ensure quality is between 0-100
    
    if not cap.isOpened():
        logger.error("Could not open video source")
        raise Exception("Could not open video source")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_delay = 1.0 / fps
    frame_count = 0

    while should_run:
        try:
            success, frame = cap.read()
            if not success or frame_count >= total_frames:
                logger.info("Reached end of video.")
                if loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_count = 0
                    continue
                else:
                    break

            # Use the specified quality
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not ret:
                logger.error("Failed to encode frame to JPEG")
                continue

            with frame_lock:
                current_frame = buffer.tobytes()

            time.sleep(frame_delay)
            frame_count += 1
        except Exception as e:
            logger.exception("Exception occurred during frame generation")
            break

    cap.release()
    should_run = False

def generate_frames():
    global current_frame
    while should_run:
        try:
            with frame_lock:
                if current_frame is None:
                    continue
                frame = current_frame

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

            time.sleep(1.0 / fps)
        except Exception as e:
            logger.exception("Exception occurred during frame streaming")
            break

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Open your web browser and navigate to http://localhost:<port>/video_feed to view the live stream.
if __name__ == '__main__':
    try:
        logger.info(f"Starting Flask app on port {args.port} with FPS {fps} and video source {video_source}")
        # Start frame update thread
        frame_thread = threading.Thread(target=update_frame_buffer)
        frame_thread.daemon = True
        frame_thread.start()

        from werkzeug.serving import WSGIRequestHandler
        WSGIRequestHandler.protocol_version = "HTTP/1.1"
        app.run(host='0.0.0.0', port=args.port)
    except Exception as e:
        logger.exception("Exception occurred while running Flask app")
    finally:
        should_run = False
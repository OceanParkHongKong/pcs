import time
import redis
import zlib
import json
import logging
from flask import Flask, Response, request, send_file
from gevent import monkey
from gevent.pywsgi import WSGIServer
import gevent
import io
from flask_cors import CORS  # Import the CORS library

# Monkey-patch the standard library to make it cooperative with gevent
monkey.patch_all()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Enable CORS for all routes
CORS(app, resources={
    r"/snapshot": {"origins": "*"},
    r"/video_feed": {"origins": "*"}
})

# Load Redis configuration
def load_redis_config():
    with open('config_redis.json', 'r') as config_file:
        config = json.load(config_file)
    return config

# Global variable for Redis configuration
redis_config = load_redis_config()

def gen_frames(camera_id, fps=20):
    r = redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'])
    frame_interval = 1 / fps  # Calculate the time interval between frames based on FPS
    last_frame_time = time.time()

    while True:
        try:
            frame_data_zip = r.get(camera_id.lower())
            current_time = time.time()
            elapsed_time = current_time - last_frame_time

            if elapsed_time >= frame_interval:
                if frame_data_zip:
                    frame_data = zlib.decompress(frame_data_zip)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n\r\n')
                    last_frame_time = current_time
                else:
                    logging.info(f"No frame available (gen_frames) for camera_id: {camera_id}")
            gevent.sleep(max(0, frame_interval - (time.time() - current_time)))

        except redis.ConnectionError:
            logging.error("Failed to connect to Redis. Retrying in 5 seconds...")
            gevent.sleep(5)
        except Exception as e:
            logging.exception(f"An error occurred: {e}")
            gevent.sleep(1)

def get_single_frame(camera_id):
    r = redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'])
    try:
        frame_data_zip = r.get(camera_id.lower())
        if frame_data_zip:
            frame_data = zlib.decompress(frame_data_zip)
            return frame_data
        else:
            logging.info(f"No frame available (get_single_frame) for camera_id: {camera_id}")
            return None
    except redis.ConnectionError:
        logging.error("Failed to connect to Redis.")
        return None
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        return None

@app.route('/snapshot')
def snapshot():
    camera_id = request.args.get('camera_id', default='default_id', type=str)
    frame_data = get_single_frame(camera_id)

    if frame_data:
        return Response(frame_data, mimetype='image/jpeg')
    else:
        return "No frame available", 404

@app.route('/video_feed')
def video_feed():
    camera_id = request.args.get('camera_id', default='default_id', type=str)
    fps = request.args.get('fps', default=20, type=int)
    if fps > 20:
        fps = 20
    return Response(gen_frames(camera_id, fps), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    logging.info("Starting the video feed server...")
    http_server = WSGIServer(('0.0.0.0', 5001), app)
    http_server.serve_forever()
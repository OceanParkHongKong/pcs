import os
import logging
import cv2
import numpy as np

# Create a logger for this module
logger = logging.getLogger('pipe_utils')

def reset_pipe(pipe_path):
    """
    Remove existing pipe and create a new one.
    
    Args:
        pipe_path (str): Path to the pipe file
    """
    # Remove the existing pipe if it exists
    if os.path.exists(pipe_path):
        try:
            os.remove(pipe_path)
            logger.info(f"Removed existing pipe at {pipe_path}")
        except OSError as e:
            logger.error(f"Error removing pipe: {e}")
    
    # Create a new pipe
    try:
        os.mkfifo(pipe_path)
        logger.info(f"Created new pipe at {pipe_path}")
    except OSError as e:
        logger.error(f"Error creating pipe: {e}")


class DetectionPipeReader:
    """
    Class for reading detection data from a named pipe.
    """
    def __init__(self, pipe_path):
        self.pipe_path = pipe_path
        if not os.path.exists(pipe_path):
            os.mkfifo(pipe_path)
        self.pipe = None
        self.open_pipe()

    def open_pipe(self):
        if self.pipe is None:
            self.pipe = open(self.pipe_path, 'rb')

    def close_pipe(self):
        if self.pipe is not None:
            self.pipe.close()
            self.pipe = None

    def read_from_pipe(self):
        if self.pipe is None:
            self.open_pipe()

        try:
            length_data = self.pipe.read(4)
            if len(length_data) < 4:
                return None
            length = int.from_bytes(length_data, byteorder='little')
            data = self.pipe.read(length)
            if len(data) < length:
                return None

            return data.decode('utf-8')
        except BrokenPipeError:
            logger.error("BrokenPipeError reader")
            self.close_pipe()
            self.open_pipe()
        except Exception as e:
            logger.error(f"An error occurred while reading from pipe: {e}")
            self.close_pipe()
            self.open_pipe()
        return None

    def __del__(self):
        self.close_pipe()


class FramePipeWriter:
    """
    Class for writing frame data to a named pipe.
    """
    def __init__(self, pipe_path):
        self.pipe_path = pipe_path
        if not os.path.exists(pipe_path):
            os.mkfifo(pipe_path)
        self.pipe = None
        self.open_pipe()

    def open_pipe(self):
        if self.pipe is None:
            self.pipe = open(self.pipe_path, 'wb')

    def close_pipe(self):
        if self.pipe is not None:
            self.pipe.close()
            self.pipe = None

    def put_frame_to_pipe(self, frame):
        if frame is not None:
            if self.pipe is None:
                self.open_pipe()
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width = int(frame.shape[0]), int(frame.shape[1])  # Explicit conversion to int
            num_channels = frame_rgb.shape[2] if len(frame_rgb.shape) > 2 else 1
            
            # Check the data type
            dtype = frame_rgb.dtype

            buffer = frame_rgb.tobytes()
            length = len(buffer)
            
            # Pack width, height, and data length
            header = width.to_bytes(4, 'big') + height.to_bytes(4, 'big') + length.to_bytes(4, 'big')
            payload = header + buffer

            try:
                self.pipe.write(payload)
                self.pipe.flush()
            except BrokenPipeError:
                logger.error("BrokenPipeError writer")
                self.close_pipe()
                self.open_pipe()
            except Exception as e:
                logger.error(f"An error occurred: {e}")
        else:
            logger.warning("Failed to retrieve the frame.")

    def __del__(self):
        self.close_pipe()


def get_detection_string_from_pipe(pipe_reader):
    """
    Get detection string from a pipe reader.
    
    Args:
        pipe_reader (DetectionPipeReader): The pipe reader object
        
    Returns:
        str or None: The detection string if available, None otherwise
    """
    detection_string = pipe_reader.read_from_pipe()
    if detection_string is not None:
        return detection_string
    return None 
import cv2
import time
import sys
import argparse
from urllib.parse import quote

# At the top of your script
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;10000000|buffer_size;1024000"

def get_codec_info(cap):
    """
    Get codec information from VideoCapture object
    """
    # Get FOURCC code
    fourcc = cap.get(cv2.CAP_PROP_FOURCC)
    
    # Convert FOURCC to string
    fourcc_str = "".join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)])
    
    # Common codec mappings
    codec_map = {
        'H264': 'H.264/AVC',
        'avc1': 'H.264/AVC', 
        'h264': 'H.264/AVC',
        'H265': 'H.265/HEVC',
        'hev1': 'H.265/HEVC',
        'hevc': 'H.265/HEVC',
        'hvc1': 'H.265/HEVC'
    }
    
    # Try to identify codec
    detected_codec = "Unknown"
    for codec_code, codec_name in codec_map.items():
        if codec_code.lower() in fourcc_str.lower():
            detected_codec = codec_name
            break
    
    return {
        'fourcc_code': fourcc,
        'fourcc_string': fourcc_str,
        'codec_name': detected_codec
    }

def test_rtsp_connection(ip, username, password, port=554, path="/axis-media/media.amp", verbose=True, display=False, resize_to_640x360=False, crop=False):
    # URL encode the password to handle special characters
    encoded_password = quote(password)
    
    # Construct the RTSP URL
    rtsp_url = f"rtsp://{username}:{encoded_password}@{ip}:{port}{path}"
    
    if verbose:
        print(f"[INFO] Attempting to connect to: rtsp://{username}:****@{ip}:{port}{path}")
        print(f"[INFO] Starting connection at: {time.strftime('%H:%M:%S')}")
        if resize_to_640x360:
            print("[INFO] Resize to 640x360 enabled")
        if crop:
            print("[INFO] Crop to top right 640x360 corner enabled")
    
    try:
        # Create a VideoCapture object
        cap = cv2.VideoCapture(rtsp_url)
        
        # Check if camera opened successfully
        if not cap.isOpened():
            print("[ERROR] Failed to open RTSP stream")
            return False
        
        # Read the first frame
        if verbose:
            print("[INFO] Connection established, attempting to read frames...")
        
        ret, frame = cap.read()
        
        if not ret:
            print("[ERROR] Could connect but failed to retrieve video frame")
            cap.release()
            return False
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print("[SUCCESS] RTSP stream is working!")
        print(f"[INFO] Original stream details - Resolution: {frame_width}x{frame_height}, FPS: {fps:.2f}")
        
        # Get codec information
        codec_info = get_codec_info(cap)
        print(f"[INFO] Codec Details - FOURCC: {codec_info['fourcc_string']} ({codec_info['fourcc_code']}), Detected: {codec_info['codec_name']}")
        
        if crop:
            print(f"[INFO] Cropping from {frame_width}x{frame_height} to 640x360 (top right corner)")
        elif resize_to_640x360:
            print(f"[INFO] Resizing from {frame_width}x{frame_height} to 640x360")
        
        # If display is True, show the video feed until 'q' is pressed
        if display:
            print("[INFO] Displaying video feed. Press 'q' to quit.")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("[ERROR] Failed to retrieve frame. Stream may have ended.")
                    break
                
                # Crop frame if requested (top right 640x360 corner)
                if crop:
                    # Crop coordinates: from (1280, 0) to (1920, 360)
                    # OpenCV format: frame[y1:y2, x1:x2]
                    frame = frame[50:410, 1230:1870]
                # Or resize frame if requested
                elif resize_to_640x360:
                    frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_LINEAR)
                
                # Display the frame
                if crop:
                    window_title = 'RTSP Stream (Cropped 640x360)'
                elif resize_to_640x360:
                    window_title = 'RTSP Stream (Resized 640x360)'
                else:
                    window_title = 'RTSP Stream'
                    
                cv2.imshow(window_title, frame)
                
                # Break the loop if 'q' is pressed
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("[INFO] Video display stopped by user")
                    break
            
            # Destroy the window
            cv2.destroyAllWindows()
        
        # Release the VideoCapture object
        cap.release()
        return True
    
    except Exception as e:
        print(f"[ERROR] An exception occurred: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test RTSP connection to a camera')
    parser.add_argument('--ip', required=True, help='Camera IP address')
    parser.add_argument('--username', required=True, help='Camera username')
    parser.add_argument('--password', required=True, help='Camera password')
    parser.add_argument('--port', type=int, default=554, help='RTSP port (default: 554)')
    parser.add_argument('--path', default='/axis-media/media.amp?fps=15', help='Stream path (default: /axis-media/media.amp)')
    parser.add_argument('--display', action='store_true', help='Display video feed until q is pressed')
    parser.add_argument('--resize', action='store_true', help='Resize video from 1920x1080 to 640x360 for better performance')
    parser.add_argument('--crop', action='store_true', default=False, help='Crop video to top right 640x360 corner (coordinates: 1280,0 to 1920,360)')
    
    args = parser.parse_args()
    
    # Test the connection and display if requested
    test_rtsp_connection(args.ip, args.username, args.password, args.port, args.path, display=args.display, resize_to_640x360=args.resize, crop=args.crop)

if __name__ == "__main__":
    main()
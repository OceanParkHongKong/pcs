import subprocess
import atexit
import os
import argparse
import signal
import threading
import sys

def run_swift_ane(redis_key, model_name):
    # swift_ane_dir = "/Users/username/Library/Developer/Xcode/DerivedData/swfit_yolo-gqqhyrfffctjifenpuypbuxoxzkh/Build/Products/Release"
    # Using a different folder led to forgetting to update on Mac Studio, causing an issue on 2024-Sep-09.
    # Now, prefer copying the `swift_yolo` to the `swift_compiled` folder instead of using it in the Xcode Release folder.
    swift_ane_dir = "./swift_compiled"
    command = ["./swift_yolo", redis_key, f"{redis_key}_result", model_name]
    process = subprocess.Popen(command, cwd=swift_ane_dir)
    return process

def kill_process(process):
    if process:
        if process.poll() is None:  # Check if the process is still running
            process.terminate()
            process.wait()
            print("Process terminated.")
        else:
            print("Process already terminated.")
        # process.wait()  # Ensure the process has terminated

def run_command(redis_key, video, model_name, region_points, in_direction, end_quit, test_save_frame, crop_param):
    command = ["python", "main.py", "--camera_name", redis_key, "--video_url", video, "--show-count-test", "--model", model_name, "--region", region_points, "--in_direction", in_direction]
    
    if end_quit:
        command.append("--end-quit")
    
    if test_save_frame:
        command.append("--test-save-frame")
        
    if crop_param:
        command.append("--crop-param")
        command.append(crop_param)
        
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(f"PID: {process.pid}")

    def print_output():
        swift_ane_process = None
        try:
            for line in iter(process.stdout.readline, ''):
                print(line, end='')  # Print output in real-time
                if "two pipes ready" in line:
                    if swift_ane_process is None:
                        swift_ane_process = run_swift_ane(redis_key, model_name)
                        # Register the kill function to be called when the script exits
                        atexit.register(kill_process, swift_ane_process)
        finally:
            process.stdout.close()
    
    # Start a thread to handle printing the output
    output_thread = threading.Thread(target=print_output)
    output_thread.start()

    return process

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run people count script with different parameters.')
    parser.add_argument('--video', required=True, help='URL or path to the video file')
    parser.add_argument('--camera_name', required=True, help='Redis key to use')
    parser.add_argument('--model_name', required=True, help='Model name to use')
    parser.add_argument('--region', type=str, default='', help='Specify the couting region, optional')
    parser.add_argument('--end-quit', action='store_true', help='Stop process if the end of the video is reached, optional')
    parser.add_argument('--in_direction', type=str, default='y+', help='Direction for processing, default is "y+"')
    parser.add_argument('--test-save-frame', action='store_true', help='Enable test save frame functionality, default is False')
    parser.add_argument('--crop-param', type=str, default='', help='Crop parameters in format "y1,y2,x1,x2" (e.g. "4,484,359,999")')
    
    args = parser.parse_args()

    # Run the command for the specified video file
    main_process = run_command(args.camera_name, args.video, args.model_name, args.region, args.in_direction, args.end_quit, args.test_save_frame, args.crop_param)
    
    # Define signal handler to terminate processes
    def signal_handler(sig, frame):
        print(f"Received signal {sig}, terminating processes...")
        kill_process(main_process)
        sys.exit(0)

    # Register signal handlers for termination signals
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
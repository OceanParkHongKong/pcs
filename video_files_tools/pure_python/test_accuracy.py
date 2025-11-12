import subprocess
import time
from datetime import datetime
import argparse
import socket
import os

def get_current_timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def find_unused_port(starting_port=3000):
    port = starting_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:  # Port is unused
                return port
        port += 1

def main():
    # Argument parsing
    parser = argparse.ArgumentParser(description="Run a process with optional arguments")
    parser.add_argument('--video', type=str, default="/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/video_CC_In_Cam2_2024-06-10_16-47-24.mp4", help='Path to the video file')
    parser.add_argument('--redis_name', type=str, default=get_current_timestamp(), help='Name for redis (default to current timestamp)')
    parser.add_argument('--model', type=str, default="cableCar", help='cableCar -> Cable Car, crocoland -> Crocoland Yolo model')
    args = parser.parse_args()

    fps = 15
    yolo_model = ""
    in_direction = ""
    points = ""
    if args.model == "cableCar":
        yolo_model = "yolov8n_CC_OE_9_july_2024_10_01.mlmodel"
        in_direction = "y-"
        fps = 15
    elif args.model == "crocoland":
        yolo_model = "yolov8n_crocoland_24_june_2024_10_11.mlmodel"
        in_direction = "border"
        points = "[(539, 6),(392, 28),(278, 82),(224, 182),(251, 337),(446, 461),(788, 568),(1153, 605),(1207, 11)]"
        fps = 25
    else:
        raise ValueError(f"Unsupported model type: {args.model}")

    # Define the command for the process
    second_process_cmd = [
        "python", "./main.py",
        "--source", args.video,
        "--device", "mps",
        "--show",
        "--yolo-model", yolo_model,
        "--tracking-method", "bytetrack",
        "--in-direction", in_direction,
        "--camera-name", args.redis_name,
        "--show-count"
    ]
    # Conditionally add the --points parameter
    if points:
        second_process_cmd.extend(["--points", points])

    # Start the process with the working directory set to the parent folder
    parent_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    second_process = subprocess.Popen(second_process_cmd, cwd=parent_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Started process with PID:", second_process.pid)

    try:
        # Function to read and process output from the process
        def read_process_output(process):
            for line in process.stdout:
                print(line, end='', flush=True)

        # Read outputs in real-time
        read_process_output(second_process)
    except KeyboardInterrupt:
        print("Interrupted. Terminating process.")

    second_process.wait()
    print("Process exited with code:", second_process.returncode)

if __name__ == "__main__":
    main()
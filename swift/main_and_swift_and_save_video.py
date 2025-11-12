import subprocess
import sys
import threading

def stream_output(process):
    # Function to read and print the output of a process
    def print_stream(stream):
        for line in iter(stream.readline, b''):
            print(line.decode(), end='')

    # Start threads to capture both stdout and stderr
    stdout_thread = threading.Thread(target=print_stream, args=(process.stdout,))
    stderr_thread = threading.Thread(target=print_stream, args=(process.stderr,))

    stdout_thread.start()
    stderr_thread.start()

    # Wait for both threads to finish
    stdout_thread.join()
    stderr_thread.join()

import os
def extract_file_name(file_path):
    # Use os.path.basename to extract the file name from the path
    file_name = os.path.basename(file_path)
    return file_name

def start_processes(video, camera_name, model_name, region_points, in_direction, crop_param=None):
    
    file_name = extract_file_name(video)
    try:
        # Start the second process first with a specific working directory
        second_process = subprocess.Popen(
            ["python", "save_video_from_redis.py", camera_name, file_name],
            cwd="../video_files_tools/",  # Set the working directory for the second process
            stdout=subprocess.PIPE,  # Capture the standard output
            stderr=subprocess.PIPE   # Capture the standard error
        )

        # Start a thread to stream the output from the second process
        threading.Thread(target=stream_output, args=(second_process,), daemon=True).start()

        # Start the first process with the default working directory
        command = [
            "python", "main_and_swift.py",
            "--video", video,
            "--camera_name", camera_name,
            "--model_name", model_name,
            "--region", region_points,
            "--in_direction", in_direction,
            "--end-quit"
        ]
        
        # Add crop-param if provided
        if crop_param:
            command.extend(["--crop-param", crop_param])
            
        first_process = subprocess.Popen(command)

        # Wait for the first process to finish
        first_process.wait()

        # Wait for the second process to terminate or terminate it if it's still running
        second_process.terminate()
        second_process.wait()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 6 or len(sys.argv) > 7:
        print("Usage: python script.py <video> <camera_name> <model_name> <region_points> <in_direction> [crop_param]")
        sys.exit(1)

    video = sys.argv[1]
    camera_name = sys.argv[2]
    model_name = sys.argv[3]
    region_points = sys.argv[4]
    in_direction = sys.argv[5]
    crop_param = sys.argv[6] if len(sys.argv) == 7 else None

    start_processes(video, camera_name, model_name, region_points, in_direction, crop_param)
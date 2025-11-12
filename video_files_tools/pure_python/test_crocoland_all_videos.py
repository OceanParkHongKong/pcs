import subprocess
from datetime import datetime

# List of video file paths
video_files = [
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-23_09-59-42.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-23_15-59-58.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-23_19-30-08.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-21_16-57-27.mp4",# infinite waiting?
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-22_09-28-26.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-24_17-11-18.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-29_09-24-55.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-29_18-25-21.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-29_19-25-25.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-31_09-47-42.mp4"
]

# Local file to store results
log_file = "results_log_crocoland.txt"

with open(log_file, "a") as f:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write(f"{timestamp} - start testing video count: {len(video_files)}\n")

for video in video_files:
    try:
        # Construct the command
        command = ["python", "test_accuracy.py", "--video", video, "--model", "crocoland"]

        # Execute the command
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Read the output in real-time
        in_count = None
        out_count = None
        for line in process.stdout:
            print(line, end='')  # Print the output line-by-line

            if "in_count:" in line:
                in_count = line.split("in_count:")[1].split()[0]
                print(f"Extracted in_count: {in_count}")

            if "out_count:" in line:
                out_count = line.split("out_count:")[1].split()[0]
                print(f"Extracted out_count: {out_count}")

        # Wait for the process to complete
        process.wait()

        if process.returncode == 0 and in_count is not None and out_count is not None:
            # Get the current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Append the results to the log file
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - video: {video}, in_count: {in_count}, out_count: {out_count}\n")

        else:
            print(f"Command failed for video: {video} with error: {process.stderr.read()}")

    except Exception as e:
        print(f"An error occurred while processing video: {video}")
        print(str(e))
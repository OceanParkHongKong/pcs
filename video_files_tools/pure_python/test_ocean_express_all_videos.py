import subprocess
from datetime import datetime

# List of video file paths

video_files = [
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam1_2024-06-24_10-18-09.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam1_2024-06-24_10-28-14.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam1_2024-06-24_11-58-50.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam1_2024-06-24_12-08-55.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam2_2024-06-24_10-18-09.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam2_2024-07-08_13-02-43.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam3_2024-06-23_10-57-57.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam3_2024-06-23_11-18-13.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam3_2024-06-23_11-28-19.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam3_2024-06-23_11-38-25.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam4_2024-06-19_10-01-40.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_In_Cam4_2024-06-19_10-11-44.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam2_2024-06-30_16-13-19.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam2_2024-06-30_16-23-23.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam3_2024-06-20_13-53-56.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam4_2024-06-23_17-02-18.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam4_2024-06-23_17-12-23.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam4_2024-06-23_17-32-32.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam5_2024-06-19_12-12-45.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam5_2024-06-19_12-32-54.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam6_2024-06-22_17-06-04.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountOceanExpress/video_OE_Out_Cam6_2024-06-30_16-23-23.mp4"
]

# Local file to store results
log_file = "results_log_ocean_express.txt"

for video in video_files:
    try:
        # Construct the command
        command = ["python", "test_accuracy.py", "--video", video]

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
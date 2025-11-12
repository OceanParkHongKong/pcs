import subprocess
from datetime import datetime

# List of video file paths
video_files = [
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_09-52-51.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_10-02-55.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_10-13-00.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_10-23-06.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_10-33-11.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_10-43-15.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_10-53-21.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_11-03-25.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_11-13-30.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_11-23-37.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_11-33-41.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_11-43-45.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_11-53-52.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_12-03-59.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_17-59-14.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_18-09-18.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_18-19-21.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_18-29-25.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_18-39-28.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_18-49-32.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_18-59-36.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_19-09-39.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_10-53-21.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_11-03-25.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_11-13-30.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_11-23-37.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_11-33-41.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_11-43-45.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_11-53-52.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_12-03-59.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_17-51-58.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_18-02-02.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_18-12-05.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_18-22-09.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_18-32-12.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_18-42-18.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_18-52-21.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_19-02-25.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_12-58-24.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_13-08-26.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_13-18-29.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_13-28-31.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_13-38-33.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_13-48-36.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_13-58-38.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_14-08-40.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_17-59-37.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_18-09-39.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_18-19-41.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_18-29-44.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_18-39-46.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_18-49-48.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_18-59-51.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_19-09-53.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_12-57-10.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_13-07-13.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_13-17-17.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_13-27-20.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_13-37-23.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_13-47-26.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_13-57-30.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_14-07-33.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_17-59-14.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_18-09-18.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_18-19-21.mp4",    
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_18-29-25.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_18-39-28.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_18-49-32.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_18-59-36.mp4",
    "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_19-09-39.mp4"
    

]


# Local file to store results
log_file = "results_log_cable_car.txt"

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
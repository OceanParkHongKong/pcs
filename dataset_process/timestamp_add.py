import cv2

def add_timestamps_to_video(input_file, output_file):
    # Open the video file
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    # Get video properties
    # fps = cap.get(cv2.CAP_PROP_FPS)
    fps = 15 #cableCar
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    # Create a VideoWriter object to save the output video
    out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

    frame_number = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Calculate the current timestamp in seconds
        timestamp = frame_number / fps
        minutes, seconds = divmod(timestamp, 60)
        time_str = f"{int(minutes):02}:{int(seconds):02}"

        # Add the timestamp to the frame
        cv2.putText(frame, time_str, (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Write the frame to the output video
        out.write(frame)

        frame_number += 1

    # Release resources
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Output video saved. {output_file}")


import os
# Example usage
input_file = '/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountAmazingAsiaAnimals/video_AAA_Out_Cam2_2024-08-09_14-52-43.mp4'
# input_file = '/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountAmazingAsiaAnimals/video_AAA_Out_Cam2_2024-08-09_17-03-01.mp4'
# input_file = '/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountAmazingAsiaAnimals/video_AAA_Out_Cam2_2024-08-10_19-06-54.mp4'
base, ext = os.path.splitext(input_file)
output_file = f"{base}_timestamp{ext}"
add_timestamps_to_video(input_file, output_file)

import cv2
import os

def extract_frames(video_path, output_folder='extracted_frames', frame_skip=1, image_format='png'):
    # Extract the video file name without the directory path and extension
    video_file_name = os.path.basename(video_path)
    video_file_name_without_ext = os.path.splitext(video_file_name)[0]
    
    # Append video filename to output folder
    output_folder = f"{output_folder}_{video_file_name_without_ext}"
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the video
    video = cv2.VideoCapture(video_path)

    # Initialize the frame count
    frame_count = 0
    extracted_count = 0

    # Determine file extension and quality settings
    if image_format.lower() in ['jpg', 'jpeg']:
        file_ext = 'jpg'
        # JPEG quality setting (0-100, higher is better quality)
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
    elif image_format.lower() == 'png':
        file_ext = 'png'
        # PNG compression level (0-9, higher is more compression)
        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 6]
    else:
        print(f"Warning: Unsupported format '{image_format}', defaulting to PNG")
        file_ext = 'png'
        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 6]

    # Loop through each frame in the video
    while True:
        # Read the next frame
        success, frame = video.read()
        if not success:
            break  # No more frames or error occurred

        # Check if this frame is to be skipped
        if frame_count % frame_skip == 0:
            # Save the frame to the output folder with chosen format
            frame_filename = os.path.join(output_folder, f'{video_file_name_without_ext}_frame_{extracted_count:04d}.{file_ext}')
            cv2.imwrite(frame_filename, frame, encode_params)
            extracted_count += 1
        frame_count += 1

    # Release the video capture object
    video.release()

    print(f'Yeehaw! Done extractin\' frames for {video_file_name}. Saved {extracted_count} {file_ext.upper()} frames to {output_folder}')

def process_multiple_videos(video_paths, frame_skip=50, image_format='png'):
    """
    Process multiple videos one by one
    
    Args:
        video_paths (list): List of video file paths
        frame_skip (int): Extract every Nth frame (default: 50)
        image_format (str): Output image format - 'png', 'jpg', or 'jpeg' (default: 'png')
    """
    total_videos = len(video_paths)
    
    print(f"Processing {total_videos} videos with frame_skip={frame_skip}, format={image_format.upper()}")
    
    for i, video_path in enumerate(video_paths, 1):
        print(f"\n[{i}/{total_videos}] Processing: {os.path.basename(video_path)}")
        
        # Check if video file exists
        if not os.path.exists(video_path):
            print(f"Warning: Video file not found: {video_path}")
            continue
            
        try:
            extract_frames(video_path, frame_skip=frame_skip, image_format=image_format)
        except Exception as e:
            print(f"Error processing {video_path}: {str(e)}")
            continue
    
    print(f"\n🎉 All done! Processed {total_videos} videos.")

# List of video paths
video_paths = [
    # '/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/WaterWorld/WiskerSplash/video_DL_WS_190_69_2025-06-08_13-31-06.mp4',
    # '/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/Videos/video_CC_Out_Cam1_2024-05-23_17-13-22.mp4',
    # Add more video paths here
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.07.08.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.08.08.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.08.59.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.10.56.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.11.27.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.11.51.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.12.26.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.12.59.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.13.31.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.18.41.mov'
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.19.17.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.21.40.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 10.24.03.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 11.05.54.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 11.06.45.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 11.10.41.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 11.11.34.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 11.21.02.mov',
    '/Users/username/Desktop/20250626104407-201/Screen Recording 2025-07-07 at 11.22.42.mov',
]

# Process all videos
# frame_skip = 5 suit for Yolo Pose Tracking
# frame_skip = 50 suit for Yolo Object Detection
process_multiple_videos(video_paths, frame_skip=3, image_format='jpg')
#!/usr/bin/env python3
import os
import argparse
import glob

def generate_commands(folder_path, camera_base="COL_In_Cam", model="crocoland", region="''"):
    """Generate commands for processing MP4 files in the specified folder"""
    # Get all MP4 files in the folder
    video_files = glob.glob(os.path.join(folder_path, "*.mp4"))
    
    if not video_files:
        print(f"No MP4 files found in {folder_path}")
        return
    
    # Generate commands for each file
    for i, video_file in enumerate(video_files):
        camera_index = i + 1  # Simply increment by 1 for each file
        camera_name = f"{camera_base}{camera_index}"
        
        # Create and print the command
        cmd = f"python main_and_swift_and_save_video.py {video_file} {camera_name} {model} {region}"
        print(cmd)
        print("sleep 5")

def main():
    parser = argparse.ArgumentParser(description="Generate video processing commands")
    parser.add_argument("folder", type=str, help="Folder containing MP4 files")
    parser.add_argument("--camera-base", type=str, default="COL_In_Cam", help="Base name for camera parameter")
    parser.add_argument("--model", type=str, default="crocoland", help="Model parameter")
    parser.add_argument("--region", type=str, default="''", help="Region parameter")
    
    args = parser.parse_args()
    
    generate_commands(args.folder, args.camera_base, args.model, args.region)

if __name__ == "__main__":
    main()
    
    
#  move video files from larry's windows
# rsync -avz --progress "xxxx@192.168.xx.xx:/cygdrive/d/OneDrive/OneDrive\ -\ Ocean\ Park\ Corporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/2025-May-3rd/" ./2025-May-3/
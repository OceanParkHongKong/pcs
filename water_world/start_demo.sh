#!/bin/bash

# Define the base video directory
# VIDEO_DIR="/Users/username/ww_demo_videos"
VIDEO_DIR="/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/WaterWorld"

# Check if the directory exists
if [ ! -d "$VIDEO_DIR" ]; then
    echo "Error: Video directory $VIDEO_DIR does not exist"
    exit 1
fi

# Start fake live video streams and record PIDs
# python ../video_files_tools/local_file_video_stream.py --video "$VIDEO_DIR/video_HC_190_26_2025-05-03_20-42-04.mp4" --fps 20--loop &
echo $! > pid1.txt

python ../video_files_tools/local_file_video_stream.py --video $VIDEO_DIR/video_HC_190_24_2025-05-03_21-06-56.mp4 --fps 20 --loop --port 3001 &
echo $! > pid2.txt


# python ../video_files_tools/local_file_video_stream.py --video $VIDEO_DIR/video_HC_190_22_2025-05-03_20-57-40.mp4 --fps 20 --loop --port 3002 &
# echo $! > pid3.txt

# #Big wave bay

# python  ../video_files_tools/local_file_video_stream.py --video $VIDEO_DIR/video_BWB_142_32_2025-04-14_17-29-49.mp4 --fps 20 --loop --port 3003 &
# echo $! > pid4.txt

# python  ../video_files_tools/local_file_video_stream.py --video $VIDEO_DIR/video_BWB_142_8_2025-04-17_14-31-55.mp4 --fps 20 --loop --port 3004 &
# echo $! > pid5.txt

# python  ../video_files_tools/local_file_video_stream.py --video $VIDEO_DIR/video_BWB_142_4_2025-05-02_11-33-48.mp4 --fps 20 --loop --port 3005 &
echo $! > pid6.txt

python  ../video_files_tools/local_file_video_stream.py --video $VIDEO_DIR/video_BWB_142_1_2025-04-15_10-30-52.mp4 --fps 20 --loop --port 3006 &
echo $! > pid7.txt

#need start start all OP docker containers
#need start original python start_people_count.py
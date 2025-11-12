#!/bin/bash

# Check if the user provided the base name
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 base_name"
    echo "Example: $0 video_CC_In_Cam2_2024-06-10_10-16-00"
    exit 1
fi

BASE_NAME=$1
VIDEO_PATH="/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCount CableCar/$BASE_NAME.mp4"
REDIS_NAME="$BASE_NAME"

# Run the first Python command
echo "Running test_accuracy with video: $VIDEO_PATH and redis_name: $REDIS_NAME"
python test_accuracy.py --video "$VIDEO_PATH" --redis_name "$REDIS_NAME" &

# Run the second Python command
echo "Running save_video_from_redis with redis_name: $REDIS_NAME"
python save_video_from_redis.py "$REDIS_NAME" &




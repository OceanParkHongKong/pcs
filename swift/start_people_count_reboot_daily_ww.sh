#!/bin/bash


# Configuration
CHECK_INTERVAL=10  # Interval in seconds to check the log file
SCRIPT="python start_people_count_ww.py"
OUTPUT_LOG="output_ww.log"


# Infinite loop
while true; do
    # Get the current time, but only hour and minute
    current_time=$(date +%H:%M)
    TARGET_TIME="03:30"

    # Check if it's the specific time to run the script
    if [[ "$current_time" == "$TARGET_TIME" ]]; then
        echo "Running the script at $(date '+%Y-%m-%d %H:%M:%S')..."
        # Kill any existing instances of the script
        pkill -f "start_people_count_ww.py"
        $SCRIPT >> $OUTPUT_LOG 2>&1 &
        sleep 60  # Sleep for 60 seconds to prevent multiple executions within the same minute
        continue  # Skip the rest of the loop this iteration
    fi

    # Sleep for the rest of the interval before checking again
    sleep $CHECK_INTERVAL
done

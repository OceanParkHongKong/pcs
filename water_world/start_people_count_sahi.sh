# Path to the output file to be monitored
OUTPUT_FILE="output_sahi.log"

# Command to be executed when the specific line is detected
COMMAND="python start_people_count_sahi.py >> output_sahi.log 2>&1"

# Kill any existing instances of start_people_count.py
pkill -f "python start_people_count_sahi.py"

# Wait a moment to ensure processes are cleaned up
sleep 1

# execute command at start.
eval $COMMAND
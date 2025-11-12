#!/bin/bash

# Define the path to the PID file
PIDFILE='/tmp/all_pids_swift.pid'

# Check if the PID file exists
if [[ ! -f "$PIDFILE" ]]; then
  echo "PID file not found: $PIDFILE"
  exit 1
fi

# Read the PIDs and camera names from the file and kill each process
while IFS= read -r line; do
  pid=$(echo "$line" | awk '{print $1}')
  camera_name=$(echo "$line" | awk '{print $2}')
  
  if [[ "$pid" =~ ^[0-9]+$ ]]; then
    echo "Killing process with PID: $pid (Camera: $camera_name)"
    kill "$pid" 2>/dev/null
    if [[ $? -eq 0 ]]; then
      echo "Successfully killed PID: $pid (Camera: $camera_name)"
    else
      echo "Failed to kill PID: $pid or process not found (Camera: $camera_name)"
    fi
  else
    echo "Invalid PID: $pid"
  fi
done < "$PIDFILE"
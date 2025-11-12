#!/bin/bash

# Kill processes based on recorded PIDs
# First try normal termination
echo "Attempting to terminate processes..."
for i in {1..8}; do
    kill $(cat pid${i}.txt 2>/dev/null) 2>/dev/null || echo "Process in pid${i}.txt already terminated"
done

# Wait a moment for processes to terminate gracefully
sleep 2

# Force kill any remaining processes by name
echo "Force killing any remaining processes..."
for i in {1..8}; do
    kill -9 $(cat pid${i}.txt 2>/dev/null) 2>/dev/null || true
done

# Wait for all processes to terminate
sleep 2

# Optionally, remove the PID files
echo "Cleaning up PID files..."
rm -f pid{1..8}.txt

echo "All processes terminated and files cleaned up."


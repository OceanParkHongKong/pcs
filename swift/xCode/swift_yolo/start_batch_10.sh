

#!/bin/bash

# File where PIDs will be stored
PID_FILE="./process_pids.txt"


# Start processes in the background and save their PIDs using a loop
for i in {1..10}
do
  ./swift_yolo test$i "test${i}_result" & echo $! >> $PID_FILE
done

echo "All processes started and PIDs saved to $PID_FILE."



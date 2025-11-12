#!/bin/bash
# monitor_and_sync.sh

SOURCE_DIR="/path/to/source/files"
REMOTE_USER="username"
REMOTE_HOST="192.168.a.ip"
REMOTE_DIR="/Volumes/4T/script_copy"
AGE_MINUTES=20

while true; do
    # Find files older than 20 minutes and sync them
    find "$SOURCE_DIR" -type f -mmin +$AGE_MINUTES -exec rsync -avz --progress --remove-source-files {} $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/ \;
    
    # Wait for 1 minute before next check
    sleep 60
done

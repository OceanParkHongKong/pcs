#!/bin/bash

# To kill the processes later, you can use:
while read pid; do
    kill $pid
done < process_pids.txt


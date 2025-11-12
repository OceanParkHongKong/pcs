#!/bin/bash

# ============================================================================
# CONFIGURATION - Customize these parameters as needed
# ============================================================================

# Speed multiplier (how many times faster the output should be)
SPEED_MULTIPLIER=2.5

# Output suffix for the processed files
OUTPUT_SUFFIX="${SPEED_MULTIPLIER}x"

# ============================================================================
# Script to process all .avi files in a folder with configurable speed conversion
# Usage: ./ffmpeg_speed_configurable_avi_files.sh [destination_folder]

# Check if destination folder is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <destination_folder>"
    echo "Example: $0 /path/to/your/video/folder"
    echo ""
    echo "Current configuration:"
    echo "  Speed multiplier: ${SPEED_MULTIPLIER}x"
    echo "  Output suffix: _${OUTPUT_SUFFIX}"
    exit 1
fi

DEST_FOLDER="$1"

# Check if destination folder exists
if [ ! -d "$DEST_FOLDER" ]; then
    echo "Error: Destination folder '$DEST_FOLDER' does not exist."
    exit 1
fi

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed or not in PATH."
    exit 1
fi

# Calculate the PTS (Presentation TimeStamp) value for video speed
# For 2.5x speed: setpts = 1/2.5 = 0.4
PTS_VALUE=$(echo "scale=6; 1 / $SPEED_MULTIPLIER" | bc -l)

# For audio tempo, we can use the speed multiplier directly
AUDIO_TEMPO="$SPEED_MULTIPLIER"

# However, atempo has limitations (0.5 to 100.0, and for values > 2.0, we need to chain filters)
# For speeds > 2.0, we need to use multiple atempo filters
AUDIO_FILTER=""
if (( $(echo "$SPEED_MULTIPLIER > 2.0" | bc -l) )); then
    # For speeds > 2.0, we need to chain atempo filters
    # Example: for 2.5x, we can use atempo=2.0,atempo=1.25
    # or atempo=1.6,atempo=1.5625 (1.6 * 1.5625 = 2.5)
    if (( $(echo "$SPEED_MULTIPLIER <= 4.0" | bc -l) )); then
        # For speeds between 2.0 and 4.0, use two atempo filters
        FIRST_TEMPO="2.0"
        SECOND_TEMPO=$(echo "scale=6; $SPEED_MULTIPLIER / 2.0" | bc -l)
        AUDIO_FILTER="atempo=${FIRST_TEMPO},atempo=${SECOND_TEMPO}"
    else
        # For speeds > 4.0, might need more complex chaining
        echo "Warning: Speed multiplier > 4.0 might require additional audio filter chaining"
        AUDIO_FILTER="atempo=2.0,atempo=2.0,atempo=$(echo "scale=6; $SPEED_MULTIPLIER / 4.0" | bc -l)"
    fi
else
    # For speeds <= 2.0, single atempo filter is sufficient
    AUDIO_FILTER="atempo=${AUDIO_TEMPO}"
fi

echo "Processing .avi files in: $DEST_FOLDER"
echo "========================================"
echo "Configuration:"
echo "  Speed multiplier: ${SPEED_MULTIPLIER}x"
echo "  Video PTS value: $PTS_VALUE"
echo "  Audio filter: $AUDIO_FILTER"
echo "  Output suffix: _${OUTPUT_SUFFIX}"
echo ""

# Counter for processed files
processed_count=0
total_count=0

# Count total .avi files first
for file in "$DEST_FOLDER"/*.avi; do
    if [ -f "$file" ]; then
        ((total_count++))
    fi
done

if [ $total_count -eq 0 ]; then
    echo "No .avi files found in $DEST_FOLDER"
    exit 0
fi

echo "Found $total_count .avi files to process"
echo ""

# Process each .avi file in the destination folder
for input_file in "$DEST_FOLDER"/*.avi; do
    # Check if file exists (handle case where no .avi files exist)
    if [ ! -f "$input_file" ]; then
        continue
    fi
    
    # Get the base filename without extension
    base_name=$(basename "$input_file" .avi)
    
    # Create output filename with configurable suffix
    output_file="$DEST_FOLDER/${base_name}_${OUTPUT_SUFFIX}.avi"
    
    # Check if output file already exists
    if [ -f "$output_file" ]; then
        echo "Skipping $base_name.avi - output file already exists"
        continue
    fi
    
    ((processed_count++))
    echo "Processing ($processed_count/$total_count): $base_name.avi"
    echo "  Speed: ${SPEED_MULTIPLIER}x faster"
    
    # Run ffmpeg command with configurable parameters
    ffmpeg -i "$input_file" \
           -filter:v "setpts=${PTS_VALUE}*PTS" \
           -filter:a "$AUDIO_FILTER" \
           -c:v libx264 \
           -crf 18 \
           -preset slow \
           -c:a aac \
           "$output_file"
    
    # Check if ffmpeg command was successful
    if [ $? -eq 0 ]; then
        echo "✓ Successfully processed: $base_name.avi -> ${base_name}_${OUTPUT_SUFFIX}.avi"
    else
        echo "✗ Error processing: $base_name.avi"
    fi
    
    echo ""
done

echo "========================================"
echo "Processing complete!"
echo "Processed $processed_count out of $total_count files"
echo "Speed multiplier used: ${SPEED_MULTIPLIER}x"

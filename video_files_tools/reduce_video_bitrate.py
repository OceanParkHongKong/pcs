import subprocess
import os

# Grab all the .mp4 files in the current directory
video_files = [f for f in os.listdir('.') if f.endswith('.mp4')]

# Set your desired bitrate and framerate
bitrate = '3260k'  # This here's the variable for your bitrate
framerate = '10'   # And this lil' fella's for your framerate

# Loop through each file
for video_file in video_files:
    # Create a new filename with the bitrate, framerate, and '_reduced' before the .mp4 extension
    output_file = video_file.rsplit('.', 1)[0] + f"_{bitrate}_{framerate}fps_reduced.mp4"

    # Set up your FFmpeg command
    command = [
        'ffmpeg',
        '-i', video_file,
        '-r', framerate,      # Add the framerate option here
        '-c:v', 'libx264',
        '-preset', 'slow',
        '-b:v', bitrate,
        '-c:a', 'aac',
        '-b:a', '128k',
        output_file
    ]

    # Run the FFmpeg command
    subprocess.run(command)

    # Print out a message to let you know the job's done
    print(f"Yeehaw! Finished wranglin' {video_file} to {output_file} at {framerate} FPS.")

print("All videos have been rounded up and compressed. Happy trails!")
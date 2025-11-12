import os
import time
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

def compress_video(input_file, output_file=None, crf=23):
    """
    Compress video using FFmpeg with H.264 codec.
    
    Args:
        input_file: Path to input video file
        output_file: Path to output video file (if None, will append '_compressed' to input filename)
        crf: Compression quality (18-28 is good, 23 is default, lower = better quality but larger file)
    """
    if output_file is None:
        filename, ext = os.path.splitext(input_file)
        output_file = f"{filename}_compressed{ext}"
        final_output = input_file
    else:
        final_output = output_file

    # Insert 'temp' before the extension
    filename, ext = os.path.splitext(output_file)
    temp_output = f"{filename}_temp{ext}"  # This ensures proper extension handling

    try:
        # FFmpeg command for high-quality compression
        command = [
            'ffmpeg',
            '-i', input_file,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', str(crf),
            '-c:a', 'aac',
            '-b:a', '128k',
            '-threads', '0', #M2 Ultra has 24 cores
            temp_output
        ]
        
        # Execute FFmpeg command
        subprocess.run(command, check=True)
        
        # Verify the compressed file exists and has size > 0
        if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
            # Print size comparison
            original_size = os.path.getsize(input_file) / (1024 * 1024)
            compressed_size = os.path.getsize(temp_output) / (1024 * 1024)
            print(f"Original size: {original_size:.2f}MB")
            print(f"Compressed size: {compressed_size:.2f}MB")
            print(f"Compression ratio: {compressed_size/original_size:.2%}")
            
            # Remove original and rename temp to final
            os.remove(input_file)
            os.rename(temp_output, final_output)
            print(f"Compression successful, original file deleted")
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"Compression failed: {e}")
        if os.path.exists(temp_output):
            os.remove(temp_output)
    except Exception as e:
        print(f"An error occurred: {e}")
        if os.path.exists(temp_output):
            os.remove(temp_output)
    
    return False

def load_processed_files(history_file):
    """Load the history of processed files"""
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            return json.load(f)
    return {}

def save_processed_files(history_file, processed_files):
    """Save the history of processed files"""
    with open(history_file, 'w') as f:
        json.dump(processed_files, f, indent=4)

def is_file_too_new(file_path, minutes=20):
    """Check if file was created within last 20 minutes"""
    file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
    return datetime.now() - file_creation_time < timedelta(minutes=minutes)

def monitor_and_compress(folder_path):
    """Monitor folder and compress videos"""
    history_file = 'processed_videos.json'
    processed_files = load_processed_files(history_file)
    
    print(f"Monitoring folder: {folder_path}")
    print(f"Using history file: {history_file}")
    
    while True:
        try:
            # Get all MP4 files in the folder
            mp4_files = [f for f in os.listdir(folder_path) 
                        if f.lower().endswith('.mp4')]
            
            for video_file in mp4_files:
                full_path = os.path.join(folder_path, video_file)
                
                # Skip if already processed
                if full_path in processed_files:
                    continue
                
                # Skip if file is too new (might be recording)
                if is_file_too_new(full_path, minutes=20):
                    print(f"Skipping {video_file} - too new (< 20 minutes old)")
                    continue
                
                print(f"\nProcessing: {video_file}")
                
                # Compress video
                if compress_video(full_path):
                    # Add to processed files with timestamp
                    processed_files[full_path] = {
                        'processed_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'original_size': os.path.getsize(full_path)
                    }
                    save_processed_files(history_file, processed_files)
                    print(f"Successfully processed: {video_file}")
                else:
                    # Add to processed files with timestamp
                    processed_files[full_path] = {
                        'processed_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'original_size': os.path.getsize(full_path)
                    }
                    save_processed_files(history_file, processed_files)
                    print(f"Failed to process: {video_file}")
                
                # Process one file at a time
                break
            
            # Sleep before next check
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(60)  # Wait before retrying

def main():
    parser = argparse.ArgumentParser(description='Monitor and compress video files in a folder')
    parser.add_argument('folder', help='Folder path to monitor')
    args = parser.parse_args()
    
    # Verify folder exists
    if not os.path.isdir(args.folder):
        print(f"Error: Folder '{args.folder}' does not exist")
        return
    
    monitor_and_compress(args.folder)

if __name__ == "__main__":
    main()
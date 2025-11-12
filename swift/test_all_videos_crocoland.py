import subprocess
import datetime
import atexit
import os
import shutil

video_files_crocoland = [
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-23_09-59-42.mp4", "", 187, 152),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-23_15-59-58.mp4", "", 47, 57),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-23_19-30-08.mp4", "", 27, 42),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-21_16-57-27.mp4", "", 0, 0),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-22_09-28-26.mp4", "", 0, 0),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-24_17-11-18.mp4", "", 64, 66),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-29_09-24-55.mp4", "", 106, 96),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-29_18-25-21.mp4", "", 81, 95),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-29_19-25-25.mp4", "", 78, 77),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountCrocoland/video_2024-03-31_09-47-42.mp4", "", 82, 82)
]

# Constants that remain the same across different tests
SWIFT_ANE_DIR = "./swift_compiled/"
# SWIFT_ANE_DIR = "/Users/username/Library/Developer/Xcode/DerivedData/swfit_yolo-gqqhyrfffctjifenpuypbuxoxzkh/Build/Products/Release"
PROCESS_NAME = "./swift_yolo"
PYTHON_SCRIPT = "main.py"

def run_swift_ane(redis_key, model_name):
    command = [PROCESS_NAME, redis_key, f"{redis_key}_result", model_name]
    process = subprocess.Popen(command, cwd=SWIFT_ANE_DIR)
    return process

def kill_swift_ane(process):
    if process:
        process.terminate()

def run_command(video_path, redis_key, model_name, region=None):
    if model_name == "crocoland":
        in_direction = "border"
    elif model_name == "cableCar":
        in_direction = "y+"
    elif model_name == "meerkat":
        in_direction = "y+"
    elif model_name == "ww_pool_1920" or model_name == "ww_riptide_1920":
        in_direction = "border"
    else:
        raise ValueError(f"Invalid model name: {model_name}")
    
    # Extract filename without extension from video_path
    camera_name = os.path.splitext(os.path.basename(video_path))[0]

    command = ["python", PYTHON_SCRIPT, "--camera_name", camera_name, "--video_url", video_path, "--show-count-test", "--model", model_name, "--end-quit", "--in_direction", in_direction]
    
    # Only add --test-save-frame for ww_pool_1920 model
    if model_name == "ww_pool_1920" or model_name == "ww_riptide_1920":
        command.append("--test-save-frame")
    
    if region:
        command.extend(["--region", region])
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    in_count = None
    out_count = None
    swift_ane_process = None
    for line in iter(process.stdout.readline, ''):
        print(line, end='')  # Print output in real-time
        if "two pipes ready" in line:
            # print("two pipes ready detected")
            swift_ane_process = run_swift_ane(camera_name, model_name)
            atexit.register(kill_swift_ane, swift_ane_process)
            
        if "in_count" in line and "out_count" in line:
            if "in_count:" in line:
                in_count = line.split("in_count:")[1].split()[0]
                print(f"Extracted in_count: {in_count}")

            if "out_count:" in line:
                out_count = line.split("out_count:")[1].split()[0]
                print(f"Extracted out_count: {out_count}")
    
    process.stdout.close()
    process.wait()
    
    if swift_ane_process:
        swift_ane_process.terminate()
    
    # Auto-run frame pickup for ww_pool_1920 model
    if model_name == "ww_pool_1920" or model_name == "ww_riptide_1920":
        print(f"\n{'='*50}")
        print(f"Auto-running frame images pickup for video: {os.path.basename(video_path)}")
        print(f"{'='*50}")
        
        # Create a single-item list for the current video
        current_video_list = [(video_path, region if region else "", 0, 0)]
        
        try:
            run_frame_images_pickup_for_all_videos(current_video_list)
        except Exception as e:
            print(f"Error running frame images pickup: {e}")
        
    return in_count, out_count

def append_to_file(result_file, video_path, in_count, out_count, expected_in=0, expected_out=0, video_index=None):
    with open(result_file, "a") as file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate percentages if expected values are provided and not zero
        in_percentage = "N/A"
        out_percentage = "N/A"
        
        if expected_in and in_count is not None:
            try:
                in_percentage = f"{(int(in_count) / expected_in) * 100:.2f}%"
            except (ValueError, ZeroDivisionError):
                in_percentage = "Error"
                
        if expected_out and out_count is not None:
            try:
                out_percentage = f"{(int(out_count) / expected_out) * 100:.2f}%"
            except (ValueError, ZeroDivisionError):
                out_percentage = "Error"
        
        file.write(f"{timestamp} - video #{video_index}: {video_path}, in_count: {in_count}, out_count: {out_count}, "
                  f"expected_in: {expected_in}, expected_out: {expected_out}, "
                  f"in_accuracy: {in_percentage}, out_accuracy: {out_percentage}\n")

def log_test_start(result_file, aFileCount):
    with open(result_file, "a") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - start testing video count: {aFileCount}\n")

import concurrent.futures

def run_tests(aVideo_files, redis_key, model_name, result_file, parallel=1):
    def unique_redis_key(base_key, index):
        return f"{base_key}{index}"

    def process_video(video_info, index):
        # Unpack the video info tuple with expected counts
        if len(video_info) >= 4:  # Check if expected counts are provided
            video_path, region, expected_in, expected_out = video_info
        elif len(video_info) == 2:  # Backward compatibility
            video_path, region = video_info
            expected_in, expected_out = 0, 0
        else:
            print(f"Invalid video info: {video_info}")
        unique_key = unique_redis_key(redis_key, index)
        in_count, out_count = run_command(video_path, unique_key, model_name, region)
        if in_count is not None and out_count is not None:
            append_to_file(result_file, video_path, in_count, out_count, expected_in, expected_out, index)

    log_test_start(result_file, len(aVideo_files))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = []
        for i in range(0, len(aVideo_files), parallel):
            batch = aVideo_files[i:i+parallel]
            for j, video in enumerate(batch):
                futures.append(executor.submit(process_video, video, i + j + 1))
        
        # Ensure all futures are completed
        concurrent.futures.wait(futures)

def delete_image_directory_csv_file(image_dir, csv_file):
    """Delete the image directory after successful processing"""
    if os.path.exists(image_dir):
        shutil.rmtree(image_dir)
        print(f"✓ Deleted image directory: {image_dir}")
    else:
        print(f"⚠ Image directory not found: {image_dir}")
    
    if os.path.exists(csv_file):
        os.remove(csv_file)
        print(f"✓ Deleted csv file: {csv_file}")
    else:
        print(f"⚠ Csv file not found: {csv_file}")

def run_frame_images_pickup_for_all_videos(video_files_list):
    """Run test_accuracy_frame_images_pickup.py for each video file after tests are completed"""
    print("\n" + "="*50)
    print("Running frame images pickup for all video files...")
    print("="*50)
    
    for video_file_tuple in video_files_list:
        video_path = video_file_tuple[0]  # First element is the video path
        
        # Extract filename without extension
        filename = os.path.basename(video_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # Generate parameters based on filename
        csv_file = f"{filename_without_ext}_region_count.csv"
        image_dir = f"verify_images_{filename_without_ext}"
        output_dir = f"{image_dir}_pickup30"
        total_samples = 30
        
        # Construct the command
        cmd = [
            "python", "test_accuracy_frame_images_pickup.py",
            "--csv_file", csv_file,
            "--image_dir", image_dir,
            "--output_dir", output_dir,
            "--total_samples", str(total_samples)
        ]
        
        print(f"\nProcessing video: {filename}")
        print(f"Command: {' '.join(cmd)}")
        
        try:
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✓ Successfully processed {filename}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            
            # Delete the image directory after successful processing
            delete_image_directory_csv_file(image_dir, csv_file)
                
        except subprocess.CalledProcessError as e:
            print(f"✗ Error processing {filename}: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr}")
            print(f"⚠ Keeping image directory due to processing error: {image_dir}")
        except Exception as e:
            print(f"✗ Unexpected error processing {filename}: {e}")
            print(f"⚠ Keeping image directory due to unexpected error: {image_dir}")

# Parameters for your first set of video files

redis_key_1 = "Meerkat"
model_name_1 = "crocoland"
#model_name_1 = "meerkat"
result_file_1 = "test_result_crocoland.txt"

# Run tests for the first set of video files
if __name__ == "__main__":
    run_tests(video_files_crocoland, redis_key_1, model_name_1, result_file_1, parallel=10)

# # Parameters for your second set of video files
# video_files_2 = [
#     # Add your second set of video files here
# ]
# redis_key_2 = "test30"
# model_name_2 = "cableCar"
# result_file_2 = "test_result_cable_car.txt"

# # Run tests for the second set of video files
# run_tests(video_files_2, redis_key_2, model_name_2, result_file_2)
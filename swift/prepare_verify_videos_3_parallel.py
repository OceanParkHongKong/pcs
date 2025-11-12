#!/usr/bin/env python3

import os
import sys
import subprocess
import glob
import re
import time
import psutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================================
# CONFIGURATION - Customize these parameters as needed
# ============================================================================

# Parallel processing batch size (how many files to process simultaneously)
BATCH_SIZE = 3

# Skyhigh Fall
# SHARED_PARAMS = {
#     'model': 'ww_9in1',
#     # 'coordinates': '[(566,153),(829,184),(825,223),(563,186)]',
#     'coordinates': '[(115,230),(670,299),(625,162),(153,102)]|[(115,216),(107,243),(669,310),(673,281)]',
#     'mode': 'border_plus',
#     'crop': '81,481,1134,1846'
# }

# Skyhigh Fall P5-Ride03
# SHARED_PARAMS = {
#     'model': 'ww_9in1_slides',
#     'coordinates': '[(76,0),(57,196),(649,214),(684,0)]|[(111,187),(614,201),(613,228),(106,212)]',
#     'mode': 'border_plus',
#     'crop': '661,1061,466,1177'
# }

# vrotex
# /Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/WaterWorld/Cavern_&_Vortex
# SHARED_PARAMS = {
#     'model': 'ww_9in1_slides',
#     'coordinates': '[(421,127),(420,245),(395,245),(395,123)]',
#     'mode': 'x-',
#     'crop': '60,380,676,1244'
# }

#Cavern
# SHARED_PARAMS = {
#     'model': 'ww_9in1_slides',
#     'coordinates': '[(1006,202),(1016,473),(968,472),(956,199)]',
#     'mode': 'x-',
#     'crop': '174,814,780,1917'
# }

#Thunder Loop, Daredevil Drop, Bravery Cliffs
# SHARED_PARAMS = {
#     'model': 'ww_9in1',
#     'coordinates': '[(164,0),(60,246),(170,254),(206,0)]|[(156,0),(46,253),(180,262),(213,0),(199,0),(162,247),(73,237),(173,0)]',
#     'mode': 'border_plus',
#     'crop': '0,400,589,1300'
# }

# SHARED_PARAMS = {
#     'model': 'ww_9in1',
#     'coordinates': '[(318,0),(572,278),(691,279),(354,0)]|[(310,0),(561,288),(710,283),(365,0),(347,0),(671,273),(580,272),(325,0)]',
#     'mode': 'border_plus',
#     'crop': '0,400,589,1300'
# }

# SHARED_PARAMS = {
#     'model': 'ww_9in1',
#     'coordinates': '[(318,0),(572,278),(691,279),(354,0)]|[(310,0),(561,288),(710,283),(365,0),(347,0),(671,273),(580,272),(325,0)]',
#     'mode': 'border_plus',
#     'crop': '0,400,589,1300'
# }

# Daredevil Drop C-3007
# SHARED_PARAMS = {
#     'model': 'ww_9in1_slides',
#     'coordinates': '[(151,16),(175,160),(229,156),(201,13)]|[(166,151),(169,168),(236,163),(232,148)]',
#     'mode': 'border_plus',
#     'crop': '108,428,892,1460'
# }

# Bravery Cliffs C-2024
# SHARED_PARAMS = {
#     'model': 'ww_9in1_slides',
#     'coordinates': '[(290,22),(281,180),(347,183),(341,23)]|[(290,177),(340,178),(341,190),(286,187)]',
#     'mode': 'border_plus',
#     'crop': '20,340,1075,1643'
# }

# SurfStriker C-2069
# SHARED_PARAMS = {
#     'model': 'ww_9in1',
#     'coordinates': '[(273,243),(288,440),(129,449),(92,253)]|[(295,396),(284,265),(268,263),(278,396)]',
#     'mode': 'border_plus',
#     'crop': ''
# }

# SurfStriker C-2125
SHARED_PARAMS = {
    'model': 'ww_9in1',
    'coordinates': '[(297,81),(287,343),(463,336),(470,74)]|[(278,356),(293,353),(308,71),(290,71)]',
    'mode': 'border_plus',
    'crop': '70,710,62,1199'
}

#RF_In_Cam1
# SHARED_PARAMS = {
#     'model': 'meerkat',
#     'coordinates': '[(88,218),(712,222),(707,4),(94,4)]|[(71,206),(72,225),(721,238),(723,210)]',
#     'mode': 'border_plus_reverse',
#     'crop': ''
# }

#MMB_In_Cam1
# SHARED_PARAMS = {
#     'model': 'meerkat',
#     'coordinates': '[(300,37),(686,36),(796,206),(795,512),(27,482)]|[(12,491),(31,497),(318,35),(290,26)]',
#     'mode': 'border_plus',
#     'crop': ''
# }

# MMB_In_Cam2
# SHARED_PARAMS = {
#     'model': 'meerkat',
#     'coordinates': '[(721,5),(683,53),(694,184),(783,281),(782,564),(45,548),(14,420),(380,9)]|[(702,6),(671,44),(680,191),(776,293),(795,280),(703,181),(695,46),(732,4)]',
#     'mode': 'border_plus',
#     'crop': ''
# }

#RF_Out_Cam1
# SHARED_PARAMS = {
#     'model': 'cableCar',
#     'coordinates': '[(21,5),(57,153),(692,174),(797,8)]|[(6,5),(43,167),(702,186),(799,26),(783,6),(683,161),(69,144),(31,6)]',
#     'mode': 'border_plus',
#     'crop': ''
# }



def extract_camera_id(video_path):
    """Extract camera ID from video filename"""
    filename = Path(video_path).stem
    # Remove 'video_' prefix and timestamp suffix to get camera ID
    match = re.search(r'video_([^_]+)', filename)
    if match:
        return match.group(1)
    else:
        return filename.replace('video_', '').split('_')[0]

def wait_for_process_tree_completion(process, timeout=3600):
    """
    Wait for a process and all its children to complete
    Returns True if successful, False if timeout
    """
    try:
        # Get the process tree
        try:
            main_process = psutil.Process(process.pid)
        except psutil.NoSuchProcess:
            # Process already finished
            return True
        
        start_time = time.time()
        check_interval = 1  # Check every second
        last_report_time = start_time
        
        while time.time() - start_time < timeout:
            try:
                # Check if main process is still running
                if not main_process.is_running():
                    break
                
                # Get all children processes
                children = main_process.children(recursive=True)
                
                # If no children and main process status is zombie or finished, we're done
                if not children:
                    try:
                        if main_process.status() in ['zombie', 'dead']:
                            break
                    except psutil.NoSuchProcess:
                        break
                
                # Report progress every 30 seconds
                current_time = time.time()
                if current_time - last_report_time >= 30:
                    print(f"      Still waiting for {main_process.pid}... ({int(current_time - start_time)}s, {len(children)} child processes)")
                    last_report_time = current_time
                
                time.sleep(check_interval)
                
            except psutil.NoSuchProcess:
                # Process finished
                break
        
        # Final check
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            print(f"      Warning: Process {main_process.pid} timed out after {timeout} seconds")
            # Try to terminate the process tree
            try:
                main_process.terminate()
                time.sleep(5)
                if main_process.is_running():
                    main_process.kill()
            except psutil.NoSuchProcess:
                pass
            return False
        
        # Wait for the subprocess to actually finish
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        
        return True
        
    except Exception as e:
        print(f"      Error waiting for process: {e}")
        return False

def run_single_process(video_file, camera_id, model, coordinates, mode, crop):
    """Run a single python process and return results"""
    cmd = [
        'python', 'main_and_swift_and_save_video.py',
        video_file, camera_id, model, coordinates, mode, crop
    ]
    
    video_name = Path(video_file).name
    print(f"    Starting processing: {video_name} -> {camera_id}")
    
    try:
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            # Create a new process group
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        
        # Wait for the process and all its children to complete
        success = wait_for_process_tree_completion(process, timeout=3600)
        
        # Get the output
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout, stderr = "Process timeout during communication", "Process timeout"
        
        return {
            'video_file': video_file,
            'video_name': video_name,
            'camera_id': camera_id,
            'success': success and process.returncode == 0,
            'stdout': stdout,
            'stderr': stderr,
            'returncode': process.returncode if process.returncode is not None else -1
        }
        
    except Exception as e:
        return {
            'video_file': video_file,
            'video_name': video_name,
            'camera_id': camera_id,
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def process_batch_of_files(video_files, batch_number, total_batches):
    """Process a batch of video files in parallel"""
    batch_size = len(video_files)
    print(f"Processing batch {batch_number}/{total_batches}: {batch_size} files")
    
    # Show the files being processed
    for i, video_file in enumerate(video_files, 1):
        base_camera_id = extract_camera_id(video_file)
        camera_id = f"{base_camera_id}-{i}" if batch_size > 1 else base_camera_id
        print(f"  File {i}: {Path(video_file).name} -> {camera_id}")
    
    print("  Starting parallel processing...")
    
    # Run all files in this batch in parallel
    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        futures = []
        for i, video_file in enumerate(video_files, 1):
            base_camera_id = extract_camera_id(video_file)
            # Create unique camera ID for each file in the batch
            camera_id = f"{base_camera_id}-{i}" if batch_size > 1 else base_camera_id
            
            future = executor.submit(
                run_single_process,
                video_file,
                camera_id,
                SHARED_PARAMS['model'],
                SHARED_PARAMS['coordinates'],
                SHARED_PARAMS['mode'],
                SHARED_PARAMS['crop']
            )
            futures.append(future)
        
        # Wait for all processes to complete and collect results
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                print(f"    ✓ Finished: {result['video_name']} -> {result['camera_id']}")
            except Exception as e:
                results.append({
                    'video_file': 'Unknown',
                    'video_name': 'Unknown',
                    'camera_id': 'Unknown',
                    'success': False,
                    'stdout': '',
                    'stderr': str(e),
                    'returncode': -1
                })
    
    # Display results for this batch
    print("  Batch results:")
    successful = 0
    for result in results:
        if result['success']:
            print(f"    ✓ {result['video_name']} ({result['camera_id']}) completed successfully")
            successful += 1
        else:
            print(f"    ✗ {result['video_name']} ({result['camera_id']}) failed")
            if result['stderr']:
                error_lines = result['stderr'].strip().split('\n')[-2:]
                error_summary = ' '.join(error_lines).strip()
                if error_summary:
                    print(f"      Error: {error_summary}")
    
    print(f"  Batch {batch_number} complete: {successful}/{len(results)} successful")
    print("")
    return results

def chunk_list(lst, chunk_size):
    """Split a list into chunks of specified size"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 prepare_verify_videos_3_parallel.py <destination_folder>")
        print("Example: python3 prepare_verify_videos_3_parallel.py /path/to/your/video/folder")
        print("")
        print("This script processes MP4 files in parallel batches with configurable batch size.")
        print(f"Current batch size: {BATCH_SIZE} files processed simultaneously")
        sys.exit(1)
    
    dest_folder = sys.argv[1]
    
    # Check if destination folder exists
    if not os.path.isdir(dest_folder):
        print(f"Error: Destination folder '{dest_folder}' does not exist.")
        sys.exit(1)
    
    # Check if main_and_swift_and_save_video.py exists
    if not os.path.isfile('main_and_swift_and_save_video.py'):
        print("Error: main_and_swift_and_save_video.py not found in current directory.")
        print("Please run this script from the directory containing main_and_swift_and_save_video.py")
        sys.exit(1)
    
    # Check if psutil is available
    try:
        import psutil
    except ImportError:
        print("Error: psutil is required for robust process management.")
        print("Install it with: pip install psutil")
        sys.exit(1)
    
    # Find all .mp4 files
    mp4_pattern = os.path.join(dest_folder, "*.mp4")
    mp4_files = glob.glob(mp4_pattern)
    
    if not mp4_files:
        print(f"No .mp4 files found in {dest_folder}")
        sys.exit(0)
    
    # Sort files for consistent processing order
    mp4_files.sort()
    
    total_files = len(mp4_files)
    print(f"Processing .mp4 files in: {dest_folder}")
    print("=" * 60)
    print(f"Found {total_files} .mp4 files to process")
    
    # Display configuration
    print(f"Configuration:")
    print(f"  Batch size: {BATCH_SIZE} files processed simultaneously")
    print(f"  Model: {SHARED_PARAMS['model']}")
    print(f"  Coordinates: {SHARED_PARAMS['coordinates']}")
    print(f"  Mode: {SHARED_PARAMS['mode']}")
    print(f"  Crop: {SHARED_PARAMS['crop']}")
    print("")
    
    # Split files into batches
    file_batches = list(chunk_list(mp4_files, BATCH_SIZE))
    total_batches = len(file_batches)
    
    print(f"Processing {total_files} files in {total_batches} batches of up to {BATCH_SIZE} files each")
    print("")
    
    # Process each batch
    all_results = []
    for batch_num, batch_files in enumerate(file_batches, 1):
        results = process_batch_of_files(batch_files, batch_num, total_batches)
        all_results.extend(results)
    
    # Final summary
    total_processes = len(all_results)
    successful_processes = sum(1 for r in all_results if r['success'])
    failed_processes = total_processes - successful_processes
    
    print("=" * 60)
    print("Processing complete!")
    print(f"Processed {total_files} video files in {total_batches} batches")
    print(f"Batch size: {BATCH_SIZE} files per batch")
    print(f"Total processes executed: {total_processes}")
    print(f"Successful: {successful_processes}")
    print(f"Failed: {failed_processes}")
    
    if failed_processes > 0:
        print(f"\nFailed processes:")
        for result in all_results:
            if not result['success']:
                print(f"  - {result['video_name']} ({result['camera_id']})")
    
    print(f"\nAll files processed with {BATCH_SIZE}-file parallel batches!")

if __name__ == "__main__":
    main()
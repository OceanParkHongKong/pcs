import os
import shutil

def merge_directories(target_parent_folder):
    # Define the top-level directories and the subdirectories of interest
    top_level_dirs = ['test', 'train', 'valid']
    sub_dirs = ['images', 'labels']
    destination_dir = os.path.join(target_parent_folder, 'merged')

    # Create the 'merged' directory if it doth not exist
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    # Traverse through each top-level directory
    for top_dir in top_level_dirs:
        for sub_dir in sub_dirs:
            # Construct the path to the current subdirectory
            current_sub_dir = os.path.join(target_parent_folder, top_dir, sub_dir)
            
            # Verify that the subdirectory doth exist
            if not os.path.exists(current_sub_dir):
                print(f"The directory {current_sub_dir} doth not exist!")
                continue
            
            # List all files in the current subdirectory
            for filename in os.listdir(current_sub_dir):
                # Construct the full file paths
                source_file = os.path.join(current_sub_dir, filename)
                destination_file = os.path.join(destination_dir, filename)

                # Check if the file already exists in the destination directory
                if os.path.exists(destination_file):
                    print(f"A file with the name {filename} already existeth in the destination. Thy script shall not overwrite it.")
                    continue

                # Copy the file to the destination directory
                shutil.copy(source_file, destination_file)

    print("The merging of files is complete. Thou mayest check the 'merged' directory.")

# Invoke the function with the path to the target parent folder
merge_directories('/Users/username/Oceanpark/top-bottom - top-view larry.v2i.yolov8-roboflow-backup')
import os
import shutil
from config import DATASET_PATH

def organize_files(target_folder):
    # Define the paths for the new sanctuaries
    labels_folder = os.path.join(target_folder, 'labels')
    images_folder = os.path.join(target_folder, 'images')

    # Create the sanctuaries if they dost not exist
    os.makedirs(labels_folder, exist_ok=True)
    os.makedirs(images_folder, exist_ok=True)

    # Traverse the directory
    for dirpath, dirnames, filenames in os.walk(target_folder):
        for file in filenames:
            # Skip if the file resides within "labels" or "images" folders
            if dirpath == labels_folder or dirpath == images_folder:
                continue

            # The full path to the current file
            file_path = os.path.join(dirpath, file)
            
            # Move each .txt file to the "labels" sanctuary
            if file.endswith('.txt'):
                shutil.move(file_path, os.path.join(labels_folder, file))
            
            # Move each .jpg image to the "images" abode
            elif file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.png'):
                shutil.move(file_path, os.path.join(images_folder, file))

    print("The files have been sorted, each to its rightful place.")

# Use the path from config
organize_files(DATASET_PATH + 'test')
organize_files(DATASET_PATH + 'train')
organize_files(DATASET_PATH + 'val')
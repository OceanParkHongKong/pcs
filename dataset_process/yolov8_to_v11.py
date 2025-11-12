import os
import shutil
from config import DATASET_PATH

def copy_contents(src_dir, dst_dir):
    """
    Copy all contents from src_dir to dst_dir without copying the src_dir itself
    """
    # Create destination directory if it doesn't exist
    os.makedirs(dst_dir, exist_ok=True)
    
    # List all items in source directory
    if os.path.exists(src_dir):
        for item in os.listdir(src_dir):
            src_item = os.path.join(src_dir, item)
            dst_item = os.path.join(dst_dir, item)
            
            if os.path.isfile(src_item):
                # Copy file
                print(f"Copying file: {src_item} -> {dst_item}")
                shutil.copy2(src_item, dst_item)
            elif os.path.isdir(src_item):
                # Copy directory and its contents
                print(f"Copying directory: {src_item} -> {dst_item}")
                shutil.copytree(src_item, dst_item, dirs_exist_ok=True)

def reorganize_folders(base_path):
    # Create new directory structure
    os.makedirs(os.path.join(base_path, 'images', 'test'), exist_ok=True)
    os.makedirs(os.path.join(base_path, 'images', 'train'), exist_ok=True)
    os.makedirs(os.path.join(base_path, 'images', 'val'), exist_ok=True)
    os.makedirs(os.path.join(base_path, 'labels', 'test'), exist_ok=True)
    os.makedirs(os.path.join(base_path, 'labels', 'train'), exist_ok=True)
    os.makedirs(os.path.join(base_path, 'labels', 'val'), exist_ok=True)

    # Copy folders
    for folder in ['test', 'train', 'val']:
        # Copy images
        src_images = os.path.join(base_path, folder, 'images')
        dst_images = os.path.join(base_path, 'images', folder)
        if os.path.exists(src_images):
            print(f"\nCopying contents from {src_images} to {dst_images}")
            copy_contents(src_images, dst_images)

        # Copy labels
        src_labels = os.path.join(base_path, folder, 'labels')
        dst_labels = os.path.join(base_path, 'labels', folder)
        if os.path.exists(src_labels):
            print(f"\nCopying contents from {src_labels} to {dst_labels}")
            copy_contents(src_labels, dst_labels)

    print("\nFolder reorganization complete!")


# Use the path from config
reorganize_folders(DATASET_PATH)

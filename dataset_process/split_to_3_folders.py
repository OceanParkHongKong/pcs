import os
import shutil
import random
from config import DATASET_PATH

def split_dataset(folder_path, train_ratio=0.7, val_ratio=0.2, test_ratio=0.1):
    # First, check if the ratios add up to 1
    # if train_ratio + val_ratio + test_ratio != 1:
        # raise ValueError("The sum of the ratios must equal 1!")

    # Create the destination folders if they don't exist
    train_folder = os.path.join(folder_path, 'train')
    val_folder = os.path.join(folder_path, 'val')
    test_folder = os.path.join(folder_path, 'test')
    for folder in [train_folder, val_folder, test_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Gather all unique file prefixes (assumes format 'xxxxxxx.ext')
    file_prefixes = set()
    for filename in os.listdir(folder_path):
        if filename.split('.')[-1].lower() in ['jpg', 'jpeg', 'png', 'txt']:
            file_prefixes.add(filename.rsplit('.', 1)[0])

    # Convert set to list and shuffle it
    file_prefixes = list(file_prefixes)
    random.shuffle(file_prefixes)

    # Split the prefixes into train/val/test according to the given ratios
    total_files = len(file_prefixes)
    train_end = int(total_files * train_ratio)
    val_end = train_end + int(total_files * val_ratio)

    train_prefixes = file_prefixes[:train_end]
    val_prefixes = file_prefixes[train_end:val_end]
    test_prefixes = file_prefixes[val_end:]

    # Function to move the files
    def move_files(prefixes, destination):
        for prefix in prefixes:
            for ext in ['jpg', 'jpeg', 'png', 'txt']:
                filename = f"{prefix}.{ext}"
                source_path = os.path.join(folder_path, filename)
                dest_path = os.path.join(destination, filename)
                if os.path.exists(source_path):
                    shutil.move(source_path, dest_path)

    # Move the files into their respective folders
    move_files(train_prefixes, train_folder)
    move_files(val_prefixes, val_folder)
    move_files(test_prefixes, test_folder)

    print(f"Files successfully wrangled into 'train', 'val', and 'test' folders, y'all!")

# Use the path from config
split_dataset(DATASET_PATH, train_ratio=0.7, val_ratio=0.2, test_ratio=0.1)

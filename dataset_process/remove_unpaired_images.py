import os
from config import DATASET_PATH

def remove_images_without_txt(directory):
    """
    Remove image files (jpg, jpeg, png) that don't have corresponding txt files.
    
    Args:
        directory (str): Path to the directory containing image and txt files
    """
    # Get all files in the directory
    all_files = os.listdir(directory)
    
    # Create sets of base filenames (without extensions)
    txt_basenames = set()
    image_files_to_check = []
    
    # First pass: collect all txt basenames and image files
    for filename in all_files:
        if filename.endswith('.txt'):
            # Get basename without extension (e.g., 'blar_1.txt' -> 'blar_1')
            basename = os.path.splitext(filename)[0]
            txt_basenames.add(basename)
        elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_files_to_check.append(filename)
    
    # Second pass: check each image file for corresponding txt
    removed_count = 0
    for image_filename in image_files_to_check:
        # Get basename without extension (e.g., 'blar_1.png' -> 'blar_1')
        image_basename = os.path.splitext(image_filename)[0]
        
        # Check if corresponding txt file exists
        if image_basename not in txt_basenames:
            # Remove the image file
            image_file_path = os.path.join(directory, image_filename)
            try:
                os.remove(image_file_path)
                print(f"Removed unpaired image file: {image_file_path}")
                removed_count += 1
            except OSError as e:
                print(f"Error removing {image_file_path}: {e}")
    
    print(f"\nSummary: Removed {removed_count} unpaired image files")
    print(f"Found {len(txt_basenames)} txt files to match against")
    print(f"Checked {len(image_files_to_check)} image files")

def preview_files_to_remove(directory):
    """
    Preview which image files would be removed without actually removing them.
    
    Args:
        directory (str): Path to the directory containing image and txt files
    """
    # Get all files in the directory
    all_files = os.listdir(directory)
    
    # Create sets of base filenames (without extensions)
    txt_basenames = set()
    image_files_to_check = []
    
    # First pass: collect all txt basenames and image files
    for filename in all_files:
        if filename.endswith('.txt'):
            basename = os.path.splitext(filename)[0]
            txt_basenames.add(basename)
        elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_files_to_check.append(filename)
    
    # Find unpaired images
    unpaired_images = []
    for image_filename in image_files_to_check:
        image_basename = os.path.splitext(image_filename)[0]
        if image_basename not in txt_basenames:
            unpaired_images.append(image_filename)
    
    print(f"Preview: Found {len(unpaired_images)} unpaired image files:")
    for img in unpaired_images:
        print(f"  - {img}")
    
    print(f"\nStatistics:")
    print(f"  Total txt files: {len(txt_basenames)}")
    print(f"  Total image files: {len(image_files_to_check)}")
    print(f"  Unpaired images to remove: {len(unpaired_images)}")
    
    return unpaired_images

#useful for CVAT POSE exported dataset
if __name__ == "__main__":
    print("Checking for unpaired image files...")
    print(f"Directory: {DATASET_PATH}")
    print("-" * 50)
    
    # First show preview
    unpaired_files = preview_files_to_remove(DATASET_PATH)
    
    if unpaired_files:
        print("-" * 50)
        response = input("Do you want to proceed with removing these files? (y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            print("\nProceeding with removal...")
            remove_images_without_txt(DATASET_PATH)
        else:
            print("Operation cancelled.")
    else:
        print("\nNo unpaired image files found. All images have corresponding txt files.") 
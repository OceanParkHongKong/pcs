import os
from config import DATASET_PATH

def remove_empty_txt_and_corresponding_jpg(directory):
    # Iterate through all files in the directory
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            # Construct full file path
            file_path = os.path.join(directory, filename)
            # Get the size of the file
            if os.path.getsize(file_path) == 0:
                # Remove the .txt file if it is empty
                os.remove(file_path)
                print(f"Removed empty file: {file_path}")
                
                # Check for various image formats
                image_extensions = ['.jpg', '.jpeg', '.png']
                for ext in image_extensions:
                    image_file = filename.replace('.txt', ext)
                    image_file_path = os.path.join(directory, image_file)
                    # Remove the image file if it exists
                    if os.path.exists(image_file_path):
                        os.remove(image_file_path)
                        print(f"Removed corresponding image file: {image_file_path}")

# Use the path from config
remove_empty_txt_and_corresponding_jpg(DATASET_PATH)


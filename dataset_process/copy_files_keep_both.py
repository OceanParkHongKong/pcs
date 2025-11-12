import os
import shutil

import os
import shutil

def copy_files(src_folder, dst_folder):
    # Make sure the destination folder exists, if not, create it
    if not os.path.exists(dst_folder):
        os.makedirs(dst_folder)
        
    copy_count = 0
    copied_list = set()  # Initialize an empty set to store copied base names
    
    # Walk through all the files in the source folder
    for filename in os.listdir(src_folder):
        # Skip if it's a directory
        if os.path.isdir(os.path.join(src_folder, filename)):
            continue
            
        base, extension = os.path.splitext(filename)
        
        # Skip this file if the base name has already been copied
        if base in copied_list:
            continue
        
        copy_count += 1
        src_file = os.path.join(src_folder, filename)

        # Define image extensions as a set for better readability
        IMAGE_EXTENSIONS = {'.jpg', '.png', '.jpeg'}

        # Debug prints for extension matching
        print(f"\nProcessing file: {filename}")
        print(f"Base: {base}, Extension: {extension}")
        print(f"Is image? {extension in IMAGE_EXTENSIONS}")

        # If current file is a text file, look for matching image file
        if extension == '.txt':
            for img_ext in IMAGE_EXTENSIONS:
                possible_pair = base + img_ext
                if os.path.exists(os.path.join(src_folder, possible_pair)):
                    paired_extension = img_ext
                    break
            else:  # no break occurred (no image found)
                paired_extension = None
        # If current file is an image, look for matching text file
        elif extension in IMAGE_EXTENSIONS:
            possible_pair = base + '.txt'
            paired_extension = '.txt' if os.path.exists(os.path.join(src_folder, possible_pair)) else None
        else:
            paired_extension = None

        paired_filename = base + paired_extension if paired_extension else None
        print(f"Paired extension: {paired_extension}")
        print(f"Paired filename: {paired_filename}")

        paired_src_file = os.path.join(src_folder, paired_filename)

        # Set the initial destination files
        dst_file = os.path.join(dst_folder, filename)
        paired_dst_file = os.path.join(dst_folder, paired_filename)

        # If we stumble upon files with the same name in the destination folder
        count = 1
        print (f"===== {copy_count} exist? {dst_file} {os.path.exists(dst_file)} | {paired_dst_file} {os.path.exists(paired_dst_file)}")
        while os.path.exists(dst_file) or os.path.exists(paired_dst_file):
            dst_file = os.path.join(dst_folder, f"{base}_{count}{extension}")
            paired_dst_file = os.path.join(dst_folder, f"{base}_{count}{paired_extension}")
            count += 1

        # Copy the file from source to destination
        if os.path.isfile(src_file):  # We only want to copy files
            shutil.copy2(src_file, dst_file)
            print(f"Copied: {src_file} to {dst_file}")

        # Copy the paired file if it exists
        if os.path.isfile(paired_src_file):
            shutil.copy2(paired_src_file, paired_dst_file)
            print(f"Copied: {paired_src_file} to {paired_dst_file}")
        
        # Add the base name to the copied list
        copied_list.add(base)
    
    print(f"Total copied: {copy_count}")


#to find out all dir names in current folder:
# ls -d */
# ls -l | grep ^d

# Set your source and destination folder paths
src_folder = '/Users/username/Downloads/top-view-people cabelcar model_AAA_raw/obj_train_data/extracted_frames/'
dst_folder = '/Users/username/Downloads/top-view-people cabelcar model_AAA2/'

# Saddle up and start the copying process
copy_files(src_folder, dst_folder)

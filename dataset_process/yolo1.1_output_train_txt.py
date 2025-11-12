import os

def inscribe_jpg_list(target_folder, output_file='train.txt', relative_path_prefix='data/obj_train_data/'):
    # Prepare the quill to inscribe the scroll named 'train.txt'
    with open(output_file, 'w') as scroll:
        # Traverse the directory for images
        for dirpath, dirnames, filenames in os.walk(target_folder):
            for file in filenames:
                # Only proceed if the file endeth with '.jpg'
                if file.endswith('.jpg'):
                    # Construct the relative path to the image
                    relative_path = os.path.join(relative_path_prefix, os.path.relpath(os.path.join(dirpath, file), start=target_folder))
                    # Scribe the relative path upon the scroll
                    scroll.write(relative_path + '\n')

    print(f"The scroll '{output_file}' hath been inscribed with the names of thy .jpg images.")

# Invoke the function with the path to the target folder and optional parameters as needed
inscribe_jpg_list('/Users/username/Downloads/yolo_1.1/obj_train_data', 'train.txt', 'data/obj_train_data/extracted_frames/')

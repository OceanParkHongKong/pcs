import os

def transmute_label(target_folder):
    # Traverse the directory
    for dirpath, dirnames, filenames in os.walk(target_folder):
        for file in filenames:
            # Only proceed if the file endeth with '.txt'
            if file.endswith('.txt'):
                # Construct the full path to the file
                file_path = os.path.join(dirpath, file)

                # Read the contents of the file
                with open(file_path, 'r') as f:
                    lines = f.readlines()

                # Perform the transmutation on each line
                updated_lines = []
                for line in lines:
                    parts = line.strip().split(' ')
                    if parts[0] == '1':  # Check if the first element is '1'
                        parts[0] = '0'   # Transmute '1' to '0'
                    updated_lines.append(' '.join(parts))

                # Write the updated content back to the file
                with open(file_path, 'w') as f:
                    f.writelines('\n'.join(updated_lines) + '\n')

    print("The transmutation is complete. The first digits are now zeroes where they were once ones within the scrolls ending in '.txt'.")

# Invoke the function with the path to the target folder
transmute_label('/Users/username/Oceanpark/top-bottom - top-view larry.v2i.yolov8-roboflow-backup/merged/')

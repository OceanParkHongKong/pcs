import os

def find_mismatched_files(txt_folder, jpg_folder):
    # Get list of files in both folders
    txt_files = {os.path.splitext(f)[0] for f in os.listdir(txt_folder) if f.endswith('.txt')}
    jpg_files = {os.path.splitext(f)[0] for f in os.listdir(jpg_folder) if f.endswith('.jpg')}
    
    # Find files that exist in txt_folder but not in jpg_folder
    txt_only = txt_files - jpg_files
    
    # Find files that exist in jpg_folder but not in txt_folder
    jpg_only = jpg_files - txt_files
    
    return txt_only, jpg_only

# Example usage
txt_folder = "/Users/username/Downloads/top-view-people cabelcar model_AAA/labels/train"
jpg_folder = "/Users/username/Downloads/top-view-people cabelcar model_AAA/images/train"

txt_missing_jpg, jpg_missing_txt = find_mismatched_files(txt_folder, jpg_folder)

if txt_missing_jpg:
    print("\nFiles in txt folder missing corresponding jpg files: ", len(txt_missing_jpg))
    for file in sorted(txt_missing_jpg):
        print(f"- {file}")

if jpg_missing_txt:
    print("\nFiles in jpg folder missing corresponding txt files: ", len(jpg_missing_txt))
    for file in sorted(jpg_missing_txt):
        print(f"- {file}")

if not txt_missing_jpg and not jpg_missing_txt:
    print("\nAll files match between folders!")
    
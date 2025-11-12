import os
from PIL import Image, ImageDraw
import re

CONFIG = {
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_RIPT_140_27_2025-06-08_14-40-44/": "(4,5),(5,577),(667,202),(926,207),(967,127),(1154,133),(1217,247),(1912,374),(1912,8)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_RIPT_140_27_2025-06-07_17-00-40/": "(4,5),(5,577),(667,202),(926,207),(967,127),(1154,133),(1217,247),(1912,374),(1912,8)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_RIPT_140_27_2025-05-10_13-28-07/": "(4,5),(5,577),(667,202),(926,207),(967,127),(1154,133),(1217,247),(1912,374),(1912,8)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_RIPT_140_17_2025-06-07_14-40-45/": "(5,6),(5,359),(294,289),(288,133),(524,4),(823,99),(870,185),(1319,274),(1722,545),(1919,802),(1917,6)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_RIPT_140_17_2025-06-07_17-30-55/": "(5,6),(5,359),(294,289),(288,133),(524,4),(823,99),(870,185),(1319,274),(1722,545),(1919,802),(1917,6)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_RIPT_140_17_2025-06-08_14-30-55/": "(5,6),(5,359),(294,289),(288,133),(524,4),(823,99),(870,185),(1319,274),(1722,545),(1919,802),(1917,6)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_LC_141_23_2025-06-08_13-10-43/": "(3,0),(5,1038),(263,739),(545,377),(727,145),(926,0),(1342,0)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_LC_141_23_2025-05-10_13-28-07/": "(3,0),(5,1038),(263,739),(545,377),(727,145),(926,0),(1342,0)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_LC_141_23_2025-06-07_14-50-40/": "(3,0),(5,1038),(263,739),(545,377),(727,145),(926,0),(1342,0)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_LC_140_6_2025-06-21_19-11-02/": "(6,654),(5,8),(1914,9),(1918,891),(1217,621),(468,622)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_LC_140_7_2025-06-07_12-10-25/": "(11,314),(6,5),(1920,6),(1916,107),(1337,106),(681,133),(190,200)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_LC_140_7_2025-06-08_13-20-34/": "(11,314),(6,5),(1920,6),(1916,107),(1337,106),(681,133),(190,200)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_LC_140_7_2025-05-10_13-58-12/": "(11,314),(6,5),(1920,6),(1916,107),(1337,106),(681,133),(190,200)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_DL_WS_190_18_2025-06-07_15-50-48/": "(4,4),(11,431),(322,376),(810,314),(1073,338),(1404,366),(1920,403),(1918,7)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_DL_WS_190_18_2025-06-07_15-50-48/": "(8,6),(6,624),(391,457),(713,379),(972,364),(1267,388),(1920,528),(1918,5)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_DL_WS_190_18_2025-06-08_11-00-45/": "(8,6),(6,624),(391,457),(713,379),(972,364),(1267,388),(1920,528),(1918,5)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_DL_WS_190_18_2025-06-08_16-11-01/": "(8,6),(6,624),(391,457),(713,379),(972,364),(1267,388),(1920,528),(1918,5)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_DL_WS_190_69_2025-06-07_13-11-11/": "(1918,7),(1917,414),(1730,345),(1621,261),(1619,230),(1576,162),(1542,114),(1435,63),(1264,58),(1261,135),(1116,147),(1098,290),(938,200),(939,4)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_DL_WS_190_69_2025-06-08_13-31-06/": "(1918,7),(1917,414),(1730,345),(1621,261),(1619,230),(1576,162),(1542,114),(1435,63),(1264,58),(1261,135),(1116,147),(1098,290),(938,200),(939,4)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_DL_WS_190_69_2025-06-08_11-01-01/": "(1918,7),(1917,414),(1730,345),(1621,261),(1619,230),(1576,162),(1542,114),(1435,63),(1264,58),(1261,135),(1116,147),(1098,290),(938,200),(939,4)",
    # "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_DL_WS_190_69_2025-05-10_13-38-08/": "(1918,7),(1917,414),(1730,345),(1621,261),(1619,230),(1576,162),(1542,114),(1435,63),(1264,58),(1261,135),(1116,147),(1098,290),(938,200),(939,4)",
    # Add more as needed
    "/Users/username/temp_del_it/Cavern/": "(1069,114),(731,118),(421,145),(183,202),(211,469),(174,1077),(5,1073),(7,9),(1049,6)",
    
}

def parse_coordinates(coord_string):
    pattern = r'\((\d+),(\d+)\)'
    matches = re.findall(pattern, coord_string)
    return [(int(x), int(y)) for x, y in matches]

def mask_image(image_path, coordinates, output_path, original_format):
    img = Image.open(image_path)
    print(img.size)
    # Create a drawing context
    draw = ImageDraw.Draw(img)
    if len(coordinates) > 2:
        # Draw the polygon directly on the image, filling it with black
        draw.polygon(coordinates, fill=(0, 0, 0, 255))
    
    # Save in the original format
    if original_format.upper() == 'JPG' or original_format.upper() == 'JPEG':
        # Convert RGBA to RGB for JPEG if needed
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(output_path, 'JPEG')
    else:
        img.save(output_path, 'PNG')

def process_folder(folder_path, coordinates):
    # Support both PNG and JPG images
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    for image_file in image_files:
        input_path = os.path.join(folder_path, image_file)
        filename, ext = os.path.splitext(image_file)
        output_filename = filename + "_mask" + ext
        output_path = os.path.join(folder_path, output_filename)
        print(f"Processing {image_file}...")
        mask_image(input_path, coordinates, output_path, ext[1:])  # Remove the dot from extension
        print(f"Created {output_filename}")

def main():
    for folder_path, coord_string in CONFIG.items():
        print(f"\nProcessing folder: {folder_path}")
        print(f"Using coordinates: {coord_string}")
        coordinates = parse_coordinates(coord_string)
        process_folder(folder_path, coordinates)

if __name__ == "__main__":
    main() 
import os
from PIL import Image
import re

CONFIG = {
    # Example configuration - replace with your actual paths and coordinates
    "/Users/username/Oceanpark/people_count_op/dataset_process/extracted_frames_video_RIPT_140_17_2025-06-07_17-30-55": "(760,213),(1400,213),(1400,693),(760,693)",
    # "/path/to/folder2/": "(100, 100),(740, 100),(740, 580),(100, 580)",
    # Add more as needed
}

def parse_coordinates(coord_string):
    """Parse coordinate string into list of tuples"""
    pattern = r'\((\d+),(\d+)\)'
    matches = re.findall(pattern, coord_string)
    coordinates = [(int(x), int(y)) for x, y in matches]
    return coordinates

def get_crop_box_from_rectangle(coordinates):
    """Convert rectangle coordinates to PIL crop box (left, top, right, bottom)"""
    if len(coordinates) != 4:
        raise ValueError("Rectangle must have exactly 4 corner points")
    
    # Extract x and y coordinates
    x_coords = [coord[0] for coord in coordinates]
    y_coords = [coord[1] for coord in coordinates]
    
    # Calculate crop box
    left = min(x_coords)
    top = min(y_coords)
    right = max(x_coords)
    bottom = max(y_coords)
    
    return (left, top, right, bottom)

def crop_image(image_path, coordinates, output_path):
    """Crop image using the rectangle coordinates"""
    try:
        # Open the image
        img = Image.open(image_path)
        print(f"Original image size: {img.size}")
        
        # Get crop box from rectangle coordinates
        crop_box = get_crop_box_from_rectangle(coordinates)
        print(f"Crop box: {crop_box}")
        
        # Crop the image
        cropped_img = img.crop(crop_box)
        print(f"Cropped image size: {cropped_img.size}")
        
        # Save the cropped image
        cropped_img.save(output_path, 'PNG')
        print(f"Cropped image saved to: {output_path}")
        
    except Exception as e:
        print(f"Error processing {image_path}: {e}")

def process_folder(folder_path, coordinates):
    """Process all PNG files in the folder"""
    # Get all PNG files in the folder
    png_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
    
    print(f"Found {len(png_files)} PNG files in {folder_path}")
    
    for png_file in png_files:
        input_path = os.path.join(folder_path, png_file)
        # Create output filename by adding "_crop" before the extension
        output_filename = os.path.splitext(png_file)[0] + "_crop.png"
        output_path = os.path.join(folder_path, output_filename)
        
        print(f"\nProcessing {png_file}...")
        crop_image(input_path, coordinates, output_path)
        print(f"Created {output_filename}")

def main():
    """Main function to process all folders in CONFIG"""
    for folder_path, coord_string in CONFIG.items():
        print(f"\n{'='*60}")
        print(f"Processing folder: {folder_path}")
        print(f"Using coordinates: {coord_string}")
        print(f"{'='*60}")
        
        # Parse coordinates
        coordinates = parse_coordinates(coord_string)
        print(f"Parsed coordinates: {coordinates}")
        
        # Verify we have exactly 4 points for a rectangle
        if len(coordinates) != 4:
            print(f"Warning: Expected 4 coordinates for rectangle, got {len(coordinates)}")
            continue
        
        # Process the folder
        process_folder(folder_path, coordinates)

if __name__ == "__main__":
    main() 
import csv
import os
import shutil
import argparse
import glob
from pathlib import Path
import math

def find_image_file(image_dir, filename_prefix, frame_number):
    """
    Find the image file based on filename prefix and frame number.
    
    Args:
        image_dir: Directory containing images
        filename_prefix: The prefix from CSV (e.g., "video_HC_190_22_2025-05-03_20-27-29")
        frame_number: Frame number from CSV
    
    Returns:
        Full path to the image file if found, None otherwise
    """
    # Create the frame pattern (e.g., "frame_000003")
    frame_pattern = f"frame_{frame_number:06d}"
    
    # Search for files matching the pattern
    # Support both jpg and png extensions
    for ext in ['jpg', 'png', 'jpeg']:
        pattern = f"{filename_prefix}_{frame_pattern}_*.{ext}"
        search_path = os.path.join(image_dir, pattern)
        matches = glob.glob(search_path)
        
        if matches:
            return matches[0]  # Return the first match
    
    return None

def read_csv_data(csv_file):
    """
    Read CSV data and return list of rows.
    
    Args:
        csv_file: Path to CSV file
    
    Returns:
        List of tuples (filename_prefix, frame_number, count_value, original_line)
    """
    data = []
    
    with open(csv_file, 'r', newline='') as file:
        # Try to detect if it's tab-separated or comma-separated
        sample = file.read(1024)
        file.seek(0)
        
        if '\t' in sample:
            reader = csv.reader(file, delimiter='\t')
        else:
            reader = csv.reader(file)
        
        for row_num, row in enumerate(reader, 1):
            if len(row) >= 3:
                try:
                    filename_prefix = row[0].strip()
                    frame_number = int(row[1])
                    count_value = row[2].strip()
                    
                    # Store the original line for writing to output CSV
                    original_line = '\t'.join(row) if '\t' in sample else ','.join(row)
                    
                    data.append((filename_prefix, frame_number, count_value, original_line))
                except ValueError as e:
                    print(f"Warning: Skipping row {row_num} due to invalid data: {e}")
            else:
                print(f"Warning: Skipping row {row_num} - insufficient columns")
    
    return data

def select_samples(data, total_samples):
    """
    Select samples evenly distributed across all data.
    
    Args:
        data: List of data tuples
        total_samples: Number of samples to select
    
    Returns:
        List of selected data tuples
    """
    if total_samples >= len(data):
        return data
    
    # Calculate step size for even distribution
    step = len(data) / total_samples
    selected_indices = [int(i * step) for i in range(total_samples)]
    
    return [data[i] for i in selected_indices]

def copy_files_and_create_csv(selected_data, image_dir, output_dir, csv_file):
    """
    Copy selected images and create new CSV file.
    
    Args:
        selected_data: List of selected data tuples
        image_dir: Source directory containing images
        output_dir: Destination directory
        csv_file: Original CSV file path for determining output CSV name
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare output CSV file
    csv_filename = os.path.basename(csv_file)
    output_csv_path = os.path.join(output_dir, f"selected_{csv_filename}")
    
    copied_count = 0
    missing_count = 0
    
    with open(output_csv_path, 'w', newline='') as output_csv:
        for filename_prefix, frame_number, count_value, original_line in selected_data:
            # Find the corresponding image file
            image_path = find_image_file(image_dir, filename_prefix, frame_number)
            
            if image_path:
                # Copy the image to output directory
                image_filename = os.path.basename(image_path)
                output_image_path = os.path.join(output_dir, image_filename)
                
                try:
                    shutil.copy2(image_path, output_image_path)
                    
                    # Write the corresponding line to output CSV
                    output_csv.write(original_line + '\n')
                    
                    copied_count += 1
                    print(f"Copied: {image_filename}")
                    
                except Exception as e:
                    print(f"Error copying {image_path}: {e}")
                    missing_count += 1
            else:
                print(f"Warning: Image not found for {filename_prefix}, frame {frame_number}")
                missing_count += 1
    
    print(f"\nSummary:")
    print(f"Successfully copied: {copied_count} images")
    print(f"Missing images: {missing_count}")
    print(f"Output directory: {output_dir}")
    print(f"Output CSV: {output_csv_path}")

def main():
    parser = argparse.ArgumentParser(description="Pick up images and CSV lines based on CSV input")
    parser.add_argument('--csv_file', type=str, required=True, 
                       help='Path to the input CSV file')
    parser.add_argument('--image_dir', type=str, required=True,
                       help='Directory containing the images')
    parser.add_argument('--output_dir', type=str, required=True,
                       help='Output directory for selected images and CSV')
    parser.add_argument('--total_samples', type=int, required=True,
                       help='Total number of images/lines to pick up')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.csv_file):
        print(f"Error: CSV file '{args.csv_file}' not found")
        return
    
    if not os.path.exists(args.image_dir):
        print(f"Error: Image directory '{args.image_dir}' not found")
        return
    
    if args.total_samples <= 0:
        print("Error: total_samples must be a positive integer")
        return
    
    print(f"Reading CSV file: {args.csv_file}")
    data = read_csv_data(args.csv_file)
    
    if not data:
        print("Error: No valid data found in CSV file")
        return
    
    print(f"Found {len(data)} rows in CSV")
    
    if args.total_samples > len(data):
        print(f"Warning: Requested {args.total_samples} samples, but only {len(data)} available")
        args.total_samples = len(data)
    
    print(f"Selecting {args.total_samples} samples evenly distributed...")
    selected_data = select_samples(data, args.total_samples)
    
    print(f"Copying images and creating new CSV...")
    copy_files_and_create_csv(selected_data, args.image_dir, args.output_dir, args.csv_file)

if __name__ == '__main__':
    main()
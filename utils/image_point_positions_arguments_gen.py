from tkinter import Tk, Canvas
from PIL import Image, ImageTk
import argparse
import re

def parse_coordinates(coord_string):
    """Parse coordinate string like '(1176,46),(1173,76),(1217,84),(1220,56)' into list of tuples"""
    if not coord_string:
        return []
    
    # Use regex to find all coordinate pairs
    pattern = r'\((\d+),(\d+)\)'
    matches = re.findall(pattern, coord_string)
    
    # Convert to list of integer tuples
    coordinates = [(int(x), int(y)) for x, y in matches]
    return coordinates

def show_image_with_cursor_coordinates(image_path, predefined_coords=None, rectangle=False):
    # Summon the mighty window
    root = Tk()
    root.title("Image Cursor Tracker")

    # Open the image using the potent powers of PIL
    image = Image.open(image_path)
    photo = ImageTk.PhotoImage(image)

    # Create a canvas to be the vessel for the image
    canvas = Canvas(root, width=image.width, height=image.height)
    canvas.pack()

    # Place the image upon the canvas
    canvas.create_image(0, 0, anchor='nw', image=photo)
    
    # Draw predefined region if coordinates are provided
    if predefined_coords and len(predefined_coords) > 0:
        print(f"[INFO] Drawing region with {len(predefined_coords)} points")
        
        # Draw the region (polygon) in green
        if len(predefined_coords) > 2:
            # Flatten the coordinates for the polygon
            flat_coords = [coord for point in predefined_coords for coord in point]
            canvas.create_polygon(flat_coords, outline='green', fill='', width=3)
        elif len(predefined_coords) == 2:
            # Draw a line if only 2 points
            x1, y1 = predefined_coords[0]
            x2, y2 = predefined_coords[1]
            canvas.create_line(x1, y1, x2, y2, fill='green', width=3)
        
        # Draw the points in bold (larger circles with bold outline)
        for i, (x, y) in enumerate(predefined_coords):
            # Draw a larger green circle for each point (bold effect)
            canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill='green', outline='darkgreen', width=3)
            # Add point number label
            canvas.create_text(x + 10, y - 10, text=str(i+1), fill='green', font=('Arial', 10, 'bold'))
            print(f"Point {i+1}: ({x}, {y})")

    # Variables for rectangle mode
    preview_rect = None
    rect_width, rect_height = 640, 640

    def mouse_move(event):
        nonlocal preview_rect
        if rectangle:
            # Delete previous preview rectangle
            if preview_rect:
                canvas.delete(preview_rect)
            
            # Create new preview rectangle at mouse position
            x, y = event.x, event.y
            preview_rect = canvas.create_rectangle(x, y, x + rect_width, y + rect_height, 
                                                 outline='blue', width=2, fill='', dash=(3, 3))

    def click(event):
        if rectangle:
            # Rectangle mode: calculate 640x480 rectangle from click point
            x, y = event.x, event.y
            
            # Calculate the four corners of the rectangle
            top_left = (x, y)
            top_right = (x + rect_width, y)
            bottom_right = (x + rect_width, y + rect_height)
            bottom_left = (x, y + rect_height)
            
            # Print the four corner points
            print(f"640x480 Rectangle corners:")
            print(f"Top-left: {top_left}")
            print(f"Top-right: {top_right}")
            print(f"Bottom-right: {bottom_right}")
            print(f"Bottom-left: {bottom_left}")
            print(f"Coordinate string: {top_left},{top_right},{bottom_right},{bottom_left}")
            
            # Remove the preview rectangle
            if preview_rect:
                canvas.delete(preview_rect)
            
            # Draw the final rectangle on the canvas
            canvas.create_rectangle(x, y, x + rect_width, y + rect_height, 
                                  outline='red', width=3, fill='', dash=(5, 5))
            
            # Draw corner points
            for i, (cx, cy) in enumerate([top_left, top_right, bottom_right, bottom_left]):
                canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill='red', outline='darkred', width=2)
                canvas.create_text(cx + 15, cy - 15, text=str(i+1), fill='red', font=('Arial', 8, 'bold'))
            
            print(f"Rectangle drawn at ({x}, {y}) with size 640x480")
        else:
            # Original mode: capture the mouse position upon the click and inscribe it to the console
            mouse_position = (event.x, event.y)
            # Use an arcane incantation to avoid the newline character, and format without spaces
            print(f"({event.x},{event.y})", end=",", flush=True)
            # Draw a red point where the mouse was clicked
            canvas.create_oval(event.x - 3, event.y - 3, event.x + 3, event.y + 3, fill='red', outline='red')

    # Bind the mouse events
    if rectangle:
        canvas.bind('<Motion>', mouse_move)  # Mouse movement for live preview
    canvas.bind('<Button-1>', click)  # Mouse click

    # Unleash the window upon the world
    root.mainloop()

def main():
    parser = argparse.ArgumentParser(description='Show image with cursor coordinate tracking and optional predefined region')
    parser.add_argument('image_path', help='Path to the image file')
    parser.add_argument('--coords', type=str, help='Optional coordinate string like "(1176,46),(1173,76),(1217,84),(1220,56)" to draw a region')
    parser.add_argument('--rectangle', action='store_true', help='Enable rectangle mode: click to position a 640x480 rectangle and print its four corner points')
    
    args = parser.parse_args()
    
    # Parse coordinates if provided
    predefined_coords = parse_coordinates(args.coords) if args.coords else None
    
    if predefined_coords:
        print(f"[INFO] Loaded {len(predefined_coords)} predefined coordinates: {predefined_coords}")
    
    if args.rectangle:
        print("[INFO] Rectangle mode enabled. Move mouse to preview 640x480 rectangle, then click to place it.")
    
    # Show the image with optional predefined region
    show_image_with_cursor_coordinates(args.image_path, predefined_coords, args.rectangle)

if __name__ == "__main__":
    main()
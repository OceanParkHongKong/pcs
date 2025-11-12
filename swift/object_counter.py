# Ultralytics YOLO 🚀, AGPL-3.0 license

from collections import defaultdict
from abc import ABC, abstractmethod

import cv2

from ultralytics.utils.checks import check_imshow, check_requirements
from plotting import Annotator, colors

check_requirements('shapely>=2.0.0')

from shapely.geometry import LineString, Point, Polygon


class BaseCounter(ABC):
    """Abstract base class for all counter implementations"""
    
    def __init__(self, parent):
        self.parent = parent  # Reference to the ObjectCounter instance
        self.counting_list_in = []
        self.counting_list_out = []
        self.in_counts = 0
        self.out_counts = 0
    
    @abstractmethod
    def process_track(self, track_id, track_line, box, cls):
        """Process a track and update counts if necessary"""
        pass
    
    def reset(self):
        """Reset counter state"""
        self.counting_list_in.clear()
        self.counting_list_out.clear()
        self.in_counts = 0
        self.out_counts = 0
    
    def draw_for_in_count(self, points):
        """Draw visualization for incoming count"""
        if len(points) >= 2:
            self.parent.annotator.draw_region(
                reg_pts=points, 
                color=(0, 255, 255), 
                thickness=self.parent.region_thickness * 5
            )
    
    def draw_for_out_count(self, points):
        """Draw visualization for outgoing count"""
        if len(points) >= 2:
            self.parent.annotator.draw_region(
                reg_pts=points, 
                color=(255, 255, 255), 
                thickness=self.parent.region_thickness * 5
            )


class LineCounter(BaseCounter):
    """Counter implementation for a single line (2 points)"""
    
    def process_track(self, track_id, track_line, box, cls):
        if len(track_line) < 1:
            return
            
        distance = Point(track_line[-1]).distance(self.parent.counting_region)
        if distance < self.parent.line_dist_thresh:
            if track_id not in self.counting_list_in:
                self.counting_list_in.append(track_id)
                if box[0] < self.parent.counting_region.centroid.x:
                    self.out_counts += 1
                else:
                    self.in_counts += 1


class DirectionalCounter(BaseCounter):
    """Counter implementation for directional counting (x+, x-, y+, y-)"""
    
    def process_track(self, track_id, track_line, box, cls):
        if len(track_line) < 2:
            return
            
        if self.parent.counting_region.contains(Point(track_line[-1])):
            if track_id not in self.counting_list_in:
                self.counting_list_in.append(track_id)
                old_pt, first_pt = Point(track_line[-1]), Point(track_line[0])
                
                # Determine direction and update counts
                if self.parent.in_direction == "x+":
                    if old_pt.x > first_pt.x:
                        self.draw_for_out_count(track_line[-2:])
                        self.out_counts += 1
                    else:
                        self.draw_for_in_count(track_line[-2:])
                        self.in_counts += 1
                elif self.parent.in_direction == "x-":
                    if old_pt.x < first_pt.x:
                        self.draw_for_out_count(track_line[-2:])
                        self.out_counts += 1
                    else:
                        self.draw_for_in_count(track_line[-2:])
                        self.in_counts += 1
                elif self.parent.in_direction == "y+":
                    if old_pt.y > first_pt.y:
                        self.draw_for_out_count(track_line[-2:])
                        self.out_counts += 1
                    else:
                        self.draw_for_in_count(track_line[-2:])
                        self.in_counts += 1
                elif self.parent.in_direction == "y-":
                    if old_pt.y < first_pt.y:
                        self.draw_for_out_count(track_line[-2:])
                        self.out_counts += 1
                    else:
                        self.draw_for_in_count(track_line[-2:])
                        self.in_counts += 1


class BorderCounter(BaseCounter):
    """Counter implementation for border crossing detection"""
    
    def process_track(self, track_id, track_line, box, cls):
        if len(track_line) < 2:
            return
            
        if self.parent.counting_region.contains(Point(track_line[-1])):
            if track_id not in self.counting_list_in:
                self.counting_list_in.append(track_id)
                line = LineString(track_line)
                if self.parent.counting_region.exterior.intersects(line):
                    self.draw_for_in_count(track_line[-2:])
                    self.in_counts += 1
        elif track_id in self.counting_list_in and track_id not in self.counting_list_out:
            self.counting_list_out.append(track_id)
            line = LineString(track_line)
            if self.parent.counting_region.exterior.intersects(line):
                self.draw_for_out_count(track_line[-2:])
                self.out_counts += 1


class BorderPlusCounter(BaseCounter):
    """Counter implementation for border crossing detection with additional region check"""
    
    def __init__(self, parent, reverse_counting=False):
        super().__init__(parent)
        # Additional regions for extra validation (now a list)
        self.additional_region_list = []
        # Parameter to reverse in/out counting logic
        self.reverse_counting = reverse_counting
    
    def set_additional_region(self, additional_pts_string_or_list):
        """Set the additional regions for extra validation"""
        self.additional_region_list = []
        
        region_strings = additional_pts_string_or_list.split('|')
        
        for region_string in region_strings:
            region_string = region_string.strip()
            if region_string:
                try:
                    # Parse each region string using the same logic as parse_points
                    import ast
                    points = ast.literal_eval(region_string)
                    if isinstance(points, list) and all(isinstance(p, tuple) and len(p) == 2 for p in points):
                        if len(points) >= 3:
                            polygon = Polygon(points)
                            self.additional_region_list.append(polygon)
                        else:
                            print(f"Additional region needs at least 3 points, got {len(points)}")
                    else:
                        print(f"Invalid format for additional region points: {region_string}")
                except Exception as e:
                    print(f"Error parsing additional region '{region_string}': {e}")
        
        print(f"Created {len(self.additional_region_list)} additional regions")
    
    def set_additional_region_from_polygons(self, polygon_list):
        """Set the additional regions from pre-parsed polygon objects"""
        self.additional_region_list = polygon_list
        print(f"Created {len(self.additional_region_list)} additional regions")
    
    def _increment_count(self, count_type):
        """Helper method to increment counts based on reverse_counting setting"""
        if count_type == 'in':
            if self.reverse_counting:
                self.out_counts += 1
            else:
                self.in_counts += 1
        elif count_type == 'out':
            if self.reverse_counting:
                self.in_counts += 1
            else:
                self.out_counts += 1
    
    def process_track(self, track_id, track_line, box, cls):
        if len(track_line) < 2:
            return
            
        if self.parent.counting_region.contains(Point(track_line[-1])):
            if track_id not in self.counting_list_in:
                self.counting_list_in.append(track_id)
                line = LineString(track_line)
                # Original border intersection check
                if self.parent.counting_region.exterior.intersects(line):
                    # Additional check: does the line also intersect with any of the additional regions?
                    additional_check_passed = True
                    if self.additional_region_list:
                        # Check if the point is contained in ANY of the additional regions
                        additional_check_passed = any(
                            region.exterior.intersects(LineString(track_line)) 
                            for region in self.additional_region_list
                        )
                    
                    if additional_check_passed:
                        self.draw_for_in_count(track_line[-2:])
                        self._increment_count('in')
        elif track_id in self.counting_list_in and track_id not in self.counting_list_out:
        # elif track_id not in self.counting_list_out:
            self.counting_list_out.append(track_id)
            line = LineString(track_line)
            # Original border intersection check
            if self.parent.counting_region.exterior.intersects(line):
                # Additional check: does the line also intersect with any of the additional regions?
                additional_check_passed = True
                if self.additional_region_list:
                    # Check if the point is contained in ANY of the additional regions
                    additional_check_passed = any(
                        region.exterior.intersects(LineString(track_line)) 
                        for region in self.additional_region_list
                    )
                
                if additional_check_passed:
                    self.draw_for_out_count(track_line[-2:])
                    self._increment_count('out')


class ObjectCounter:
    """A class to manage the counting of objects in a real-time video stream based on their tracks."""

    def __init__(self, winTitle="Ultralytics YOLOv8 Object Counter"):
        """Initializes the Counter with default values for various tracking and counting parameters."""

        self.winTitle = winTitle
        # Mouse events
        self.is_drawing = False
        self.selected_point = None

        # Region & Line Information
        self.reg_pts = [(20, 400), (1260, 400)]
        self.line_dist_thresh = 15
        self.counting_region = None
        self.region_color = (255, 0, 255)
        self.region_color_in_out = (0, 255, 0)
        self.region_thickness = 5

        # Image and annotation Information
        self.im0 = None
        self.tf = None
        self.view_img = False

        self.names = None  # Classes names
        self.annotator = None  # Annotator

        # Object counting Information
        self.in_counts = 0
        self.out_counts = 0
        self.region_count_result = 0
        self.counting_list = []
        self.counting_list_outside = []
        self.count_txt_thickness = 0
        self.count_txt_color = (0, 0, 0)
        self.count_color = (255, 255, 255)

        # Tracks info
        self.track_history = defaultdict(list)
        self.track_thickness = 2
        self.draw_tracks = False
        self.draw_head_box = False
        self.track_color = (0, 255, 0)

        # Check if environment support imshow
        self.env_check = check_imshow(warn=True)

        # Counter implementation
        self.counter = None

        self.additional_reg_pts = None  # Additional region points
        self.additional_region_color = (0, 255, 0)  # Green color for additional region

        # Count labels display control (default enabled)
        self.draw_count_labels_enabled = True

    def set_args(self,
                 classes_names,
                 reg_pts,
                 count_reg_color=(255, 0, 255),
                 line_thickness=2,
                 track_thickness=2,
                 view_img=False,
                 draw_tracks=False,
                 draw_head_box=False,
                 count_txt_thickness=1,
                 count_txt_color=(0, 0, 0),
                 count_color=(255, 255, 255),
                 track_color=(0, 255, 0),
                 region_thickness=5,
                 line_dist_thresh=15,
                 in_direction="x+",
                 additional_reg_pts=None):
        """
        Configures the Counter's image, bounding box line thickness, and counting region points.

        Args:
            line_thickness (int): Line thickness for bounding boxes.
            view_img (bool): Flag to control whether to display the video stream.
            reg_pts (list): Initial list of points defining the counting region.
            classes_names (dict): Classes names
            track_thickness (int): Track thickness
            draw_tracks (Bool): draw tracks
            count_txt_thickness (int): Text thickness for object counting display
            count_txt_color (RGB color): count text color value
            count_color (RGB color): count text background color value
            count_reg_color (RGB color): Color of object counting region
            track_color (RGB color): color for tracks
            region_thickness (int): Object counting Region thickness
            line_dist_thresh (int): Euclidean Distance threshold for line counter
        """
        self.tf = line_thickness
        self.view_img = view_img
        self.track_thickness = track_thickness
        self.draw_tracks = draw_tracks
        self.draw_head_box = draw_head_box
        # Region and line selection
        if len(reg_pts) == 2:
            print('Line Counter Initiated.')
            self.reg_pts = reg_pts
            self.counting_region = LineString(self.reg_pts)
            self.counter = LineCounter(self)
        elif len(reg_pts) >= 4:
            print('Region Counter Initiated.')
            self.reg_pts = reg_pts
            self.counting_region = Polygon(self.reg_pts)
            
            if in_direction == "border":
                self.counter = BorderCounter(self)
            elif in_direction == "border_plus" or in_direction == "border_plus_reverse":
                self.counter = BorderPlusCounter(self, reverse_counting=(in_direction == "border_plus_reverse"))
                if additional_reg_pts:
                    self.additional_reg_pts = additional_reg_pts
                    # Parse once and use for both purposes
                    parsed_regions, polygon_regions = self._parse_additional_regions_unified(additional_reg_pts)
                    self.additional_reg_pts_list = parsed_regions
                    self.counter.set_additional_region_from_polygons(polygon_regions)
                else:
                    print("Error: Additional region points are not provided, additional region will not be drawn")
            else:
                self.counter = DirectionalCounter(self)
        else:
            print('Invalid Region points provided, region_points can be 2 or 4')
            print('Using Line Counter Now')
            self.counting_region = LineString(self.reg_pts)
            self.counter = LineCounter(self)

        self.names = classes_names
        self.track_color = track_color
        self.count_txt_thickness = count_txt_thickness
        self.count_txt_color = count_txt_color
        self.count_color = count_color
        self.region_color = count_reg_color
        self.region_thickness = region_thickness
        self.line_dist_thresh = line_dist_thresh
        self.in_direction = in_direction

    def mouse_event_for_region(self, event, x, y, flags, params):
        """
        This function is designed to move region with mouse events in a real-time video stream.

        Args:
            event (int): The type of mouse event (e.g., cv2.EVENT_MOUSEMOVE, cv2.EVENT_LBUTTONDOWN, etc.).
            x (int): The x-coordinate of the mouse pointer.
            y (int): The y-coordinate of the mouse pointer.
            flags (int): Any flags associated with the event (e.g., cv2.EVENT_FLAG_CTRLKEY,
                cv2.EVENT_FLAG_SHIFTKEY, etc.).
            params (dict): Additional parameters you may want to pass to the function.
        """
        # global is_drawing, selected_point
        if event == cv2.EVENT_LBUTTONDOWN:
            for i, point in enumerate(self.reg_pts):
                if isinstance(point, (tuple, list)) and len(point) >= 2:
                    if abs(x - point[0]) < 10 and abs(y - point[1]) < 10:
                        self.selected_point = i
                        self.is_drawing = True
                        break

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.is_drawing and self.selected_point is not None:
                self.reg_pts[self.selected_point] = (x, y)
                self.counting_region = Polygon(self.reg_pts)

        elif event == cv2.EVENT_LBUTTONUP:
            self.is_drawing = False
            self.selected_point = None

    def annotator_init(self, im0):
        self.im0 = im0
        self.annotator = Annotator(self.im0, self.tf, self.names)
        if self.in_direction == 'y+' or self.in_direction == 'y-' or self.in_direction == 'x+' or self.in_direction == 'x-':
            self.annotator.draw_region(reg_pts=self.reg_pts, color=self.region_color_in_out, thickness=self.region_thickness)
        else:
            self.annotator.draw_region(reg_pts=self.reg_pts, color=self.region_color, thickness=self.region_thickness)
        
        # Draw additional regions if they exist
        if hasattr(self, 'additional_reg_pts_list'):
            for region_pts in self.additional_reg_pts_list:
                self.annotator.draw_region(reg_pts=region_pts, color=self.additional_region_color, thickness=self.region_thickness)
    
    def draw_in_out_count_labels(self):
        """Draw count labels only if drawing is enabled"""
        if not self.draw_count_labels_enabled:
            return
            
        if self.in_direction == 'y+':
            incount_label = '^In: ' + f'{self.in_counts}'
        elif self.in_direction == 'y-':
            incount_label = 'vIn: ' + f'{self.in_counts}'
        elif self.in_direction == 'x+':
            incount_label = '<In: ' + f'{self.in_counts}'
        elif self.in_direction == 'x-':
            incount_label = '>In: ' + f'{self.in_counts}'
        else:
            incount_label = 'In: ' + f'{self.in_counts}'

        outcount_label = 'Out: ' + f'{self.out_counts}'
        self.annotator.count_labels(in_count=incount_label,
                                    out_count=outcount_label,
                                    count_txt_size=self.count_txt_thickness,
                                    txt_color=self.count_txt_color,
                                    color=self.count_color)
                
    def extract_and_process_tracks(self, tracks):
        if self.names is None:
            self.names = {0: 'head'}
            
        boxes = tracks[0].boxes.xyxy.cpu()
        clss = tracks[0].boxes.cls.cpu().tolist()
        track_ids = tracks[0].boxes.id.int().cpu().tolist()

        # Annotator Init and region drawing
        self.annotator_init(self.im0)

        # Extract tracks
        for box, track_id, cls in zip(boxes, track_ids, clss):
            # Skip objects with unknown class IDs
            # if cls not in self.names:
            #     print (f'cls: {cls} not in self.names')
                # continue
                
            if self.draw_head_box and cls in self.names:
                self.annotator.box_label(box, label=str(track_id) + ':' + self.names[cls],
                                        color=colors(int(cls), True))  # Draw bounding box

            # Draw Tracks
            track_line = self.track_history[track_id]
            track_line.append((float((box[0] + box[2]) / 2), float((box[1] + box[3]) / 2)))
            if len(track_line) > 30:
                track_line.pop(0)

            # Draw track trails
            if self.draw_tracks:
                self.annotator.draw_centroid_and_tracks(track_line,
                                                        color=self.track_color,
                                                        track_thickness=self.track_thickness)

            # Process track with the appropriate counter
            self.counter.process_track(track_id, track_line, box, cls)

        # Update counts from the counter
        self.in_counts = self.counter.in_counts
        self.out_counts = self.counter.out_counts
        
        self.draw_in_out_count_labels()

        if self.env_check and self.view_img:
            cv2.namedWindow(self.winTitle)
            if len(self.reg_pts) == 4:  # only add mouse event If user drawn region
                cv2.setMouseCallback(self.winTitle, self.mouse_event_for_region,
                                    {'region_points': self.reg_pts})
            cv2.imshow(self.winTitle, self.im0)

    def draw_region_count_label(self, count=0, count_txt_size=2, color=(255, 255, 255), txt_color=(0, 0, 0)):
        """
        Plot count for object counter only if drawing is enabled
        Args:
            count (int): count value
            count_txt_size (int): text size for count display
            color (tuple): background color of count display
            txt_color (tuple): text color of count display
        """
        if not self.draw_count_labels_enabled:
            return
            
        tl = count_txt_size or round(0.002 * (self.im0.shape[0] + self.im0.shape[1]) / 2) + 1
        tf = max(tl - 1, 1)

        text_to_print = "OCC: " + str(count)
        # Get text size for count
        t_size = cv2.getTextSize(text_to_print, 0, fontScale=tl / 2, thickness=tf)

        # Calculate position for count label
        # t_size is a tuple (width, height) - extract just the width
        text_width = t_size[0][0]  # This is the width component of the tuple
        text_height = t_size[0][1]  # This is the height component of the tuple
        gap = int(24 * tl)
        
        text_x = (self.im0.shape[1] - text_width + 120) - gap - 100  # right 

        text_y_ = 100  # top
        text_y = text_y_ + text_height * 3
        
        # Create a rounded rectangle for count
        cv2.rectangle(self.im0, (text_x - 5, text_y - 5), (text_x + text_width + 7, text_y + text_height + 7), color, -1)
        cv2.putText(self.im0,
                    text_to_print, (text_x, text_y + text_height),
                    0,
                    count_txt_size / 2,
                    txt_color,
                    count_txt_size,
                    lineType=cv2.LINE_AA)
        
    def region_counter (self, tracks):
        lCount = 0
        boxes = tracks[0].boxes.xyxy.cpu()
        clss = tracks[0].boxes.cls.cpu().tolist()
        track_ids = tracks[0].boxes.id.int().cpu().tolist()

        # Extract tracks
        for box, track_id, cls in zip(boxes, track_ids, clss):
            x,y = (float((box[0] + box[2]) / 2), float((box[1] + box[3]) / 2))
            if self.counting_region.contains(Point(x,y)):
                lCount += 1
        self.region_count_result = lCount
        self.draw_region_count_label (count=lCount,
                                     count_txt_size=self.count_txt_thickness,
                                    #  txt_color=self.count_txt_color,
                                     color=self.count_color)
                        
    def start_counting(self, im0, tracks):
        """
        Main function to start the object counting process.

        Args:
            im0 (ndarray): Current frame from the video stream.
            tracks (list): List of tracks obtained from the object tracking process.
        """
        self.im0 = im0  # store image

        if tracks[0].boxes.id is None:
            return

        self.extract_and_process_tracks(tracks)
        self.region_counter (tracks)
        return self.im0


    def reset_counters(self):
        """
        Resets all counters, dictionaries, lists, and other data structures to
        their default state to prevent potential memory leaks.
        """
        self.in_counts = 0
        self.out_counts = 0
        self.region_count_result = 0

        # Reset the counter implementation
        if self.counter:
            self.counter.reset()

        # Clear the track history
        self.track_history.clear()

        # Release any potential references to image frames or results
        self.im0 = None
        self.annotator = None
        
    def set_draw_count_labels(self, enabled=True):
        """
        Enable or disable the drawing of count labels (both in/out counts and region count).
        
        Args:
            enabled (bool): True to enable drawing count labels, False to disable. Default is True.
        """
        self.draw_count_labels_enabled = enabled

    def _parse_additional_regions_unified(self, additional_pts_string):
        """Parse additional regions string once for both drawing and polygon creation"""
        regions_list = []
        polygon_list = []
        
        if isinstance(additional_pts_string, str):
            region_strings = additional_pts_string.split('|')
            for region_string in region_strings:
                region_string = region_string.strip()
                if region_string:
                    try:
                        import ast
                        points = ast.literal_eval(region_string)
                        if isinstance(points, list) and all(isinstance(p, tuple) and len(p) == 2 for p in points):
                            regions_list.append(points)
                            # Create polygon if we have enough points
                            if len(points) >= 3:
                                polygon = Polygon(points)
                                polygon_list.append(polygon)
                            else:
                                print(f"Additional region needs at least 3 points, got {len(points)}")
                        else:
                            print(f"Invalid format for additional region points: {region_string}")
                    except Exception as e:
                        print(f"Error parsing region '{region_string}': {e}")
        
        return regions_list, polygon_list

if __name__ == '__main__':
    ObjectCounter()

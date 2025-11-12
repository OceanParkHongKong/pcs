import numpy as np

class MockTrack:
    """Mock track object that mimics the structure of a real track."""
    
    def __init__(self, detection, track_id):
        """
        Initialize a mock track from a detection.
        
        Args:
            detection: Single detection array [x1, y1, x2, y2, confidence, class]
            track_id: Unique track ID
        """
        self.xyxy = detection[:4]  # [x1, y1, x2, y2]
        self.conf = detection[4]   # confidence
        self.cls = int(detection[1])   # class
        self.id = track_id

class EmptyTracker:
    """
    A dummy tracker that returns mock tracks for each detection.
    Useful for testing or when tracking functionality needs to be disabled.
    """
    
    def __init__(self, **kwargs):
        """Initialize empty tracker. Accepts any arguments for compatibility."""
        self.active_tracks = []
        self._next_id = 1
    
    def update(self, detections, frame=None):
        """
        Update method that creates mock tracks for each detection.
        
        Args:
            detections: Detection results (numpy array with shape [N, 6])
            frame: Input frame (ignored)
            
        Returns:
            List of mock tracks
        """
        self.active_tracks = []
        
        if detections is not None and len(detections) > 0:
            for detection in detections:
                mock_track = MockTrack(detection, self._next_id)
                self.active_tracks.append(mock_track)
                self._next_id += 1
        
        return self.active_tracks
    
    def reset(self):
        """Reset tracker state."""
        self.active_tracks = []
        self._next_id = 1 
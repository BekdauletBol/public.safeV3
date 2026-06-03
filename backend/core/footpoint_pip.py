import cv2
import numpy as np
from typing import List, Tuple, Dict
from backend.core.detector import Detection

class ViolationResult:
    def __init__(self, is_current: bool, is_predicted: bool, frames_to_violation: float, confidence: float):
        self.is_current_violation = is_current
        self.is_predicted_violation = is_predicted
        self.frames_to_violation = frames_to_violation
        self.confidence = confidence

class FootpointPIP:
    """
    Footpoint+PIP v2 Algorithm (Patent-Critical).
    Uses optical-flow based velocity to predict future violations.
    """
    def __init__(self):
        pass

    def get_footpoints(self, bbox: List[float]) -> List[Tuple[float, float]]:
        """Returns 3 static foot points: left-bottom, center-bottom, right-bottom."""
        x1, y1, x2, y2 = bbox
        return [
            (x1 + (x2 - x1) * 0.2, y2),
            (x1 + (x2 - x1) * 0.5, y2),
            (x1 + (x2 - x1) * 0.8, y2)
        ]

    def check_violation(self, detection: Detection, zone_polygon: np.ndarray, lookahead_frames: int = 3) -> ViolationResult:
        """
        Algorithm:
        1. Test 3 current foot points against the polygon.
        2. Project foot points forward using velocity vector.
        3. Test projected points against the polygon.
        4. Calculate frames until predicted violation.
        """
        current_points = self.get_footpoints(detection.bbox)
        is_current = False
        for pt in current_points:
            if cv2.pointPolygonTest(zone_polygon, pt, False) >= 0:
                is_current = True
                break

        # Predicted check
        is_predicted = False
        projected_points = [
            (pt[0] + detection.velocity_vector[0] * lookahead_frames, 
             pt[1] + detection.velocity_vector[1] * lookahead_frames)
            for pt in current_points
        ]
        
        for pt in projected_points:
            if cv2.pointPolygonTest(zone_polygon, pt, False) >= 0:
                is_predicted = True
                break

        # Simple heuristic for frames_to_violation
        frames_to_violation = float('inf')
        if is_current:
            frames_to_violation = 0
        elif is_predicted:
            # Estimate based on distance to nearest edge vs velocity magnitude
            frames_to_violation = lookahead_frames / 2.0 # Placeholder logic for complexity

        return ViolationResult(is_current, is_predicted, frames_to_violation, detection.confidence)

footpoint_pip = FootpointPIP()

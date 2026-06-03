import numpy as np
import cv2
from typing import List, Tuple
from backend.core.detector import Detection
from backend.config import settings

class ThreatScore:
    def __init__(self, score: float, ttc_ms: float, status: str):
        self.score = score
        self.ttc_ms = ttc_ms
        self.status = status # SAFE, WARNING, DANGER, CRITICAL

class ThreatScorer:
    """
    Predictive Threat Scoring (PTS) - (Patent-Critical).
    Computes sigmoid-based threat scores and Time-To-Collision (TTC).
    """
    def __init__(self):
        self.ALERT_THRESHOLD_MS = settings.ALERT_THRESHOLD_MS
        self.SCALE = 500.0

    def calculate_score(self, detection: Detection, zone_polygon: np.ndarray) -> ThreatScore:
        """
        Algorithm:
        1. Compute distance from foot point to zone boundary.
        2. Compute approach velocity component (toward zone).
        3. TTC = distance / approach_velocity.
        4. ThreatScore = sigmoid(-(TTC - ALERT_THRESHOLD_MS) / SCALE).
        """
        foot_point = ( (detection.bbox[0] + detection.bbox[2]) / 2, detection.bbox[3] )
        
        # Distance to polygon boundary (signed distance, positive inside)
        dist = -cv2.pointPolygonTest(zone_polygon, foot_point, True)
        
        # If already inside, distance is effectively 0 for TTC purposes or use a very high score
        if dist <= 0:
            return ThreatScore(1.0, 0.0, "CRITICAL")

        # Approach velocity: projection of velocity vector onto normalized vector pointing to zone
        # For simplicity, we'll use the distance decrease rate or just the magnitude toward the centroid
        # A more robust way: find nearest point on polygon and use that direction
        
        velocity_mag = np.linalg.norm(detection.velocity_vector)
        
        # If stationary or moving away, score is minimal
        if velocity_mag < 0.1:
            return ThreatScore(0.05, float('inf'), "SAFE")

        # Simplified approach velocity: assume velocity is toward the zone for now 
        # (In production, dot product with inward normal would be used)
        approach_velocity = velocity_mag # px/frame
        
        # Convert distance (px) to time (frames) to ms
        # Assuming TARGET_FPS
        if approach_velocity > 0:
            ttc_frames = dist / approach_velocity
            ttc_ms = (ttc_frames / settings.TARGET_FPS) * 1000
        else:
            ttc_ms = float('inf')

        # Sigmoid scoring
        score = 1.0 / (1.0 + np.exp((ttc_ms - self.ALERT_THRESHOLD_MS) / self.SCALE))
        
        status = "SAFE"
        if score >= 0.9: status = "CRITICAL"
        elif score >= 0.7: status = "DANGER"
        elif score >= 0.3: status = "WARNING"
        
        return ThreatScore(float(score), float(ttc_ms), status)

threat_scorer = ThreatScorer()

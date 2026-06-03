import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Any, Optional
from loguru import logger
from backend.config import settings

class Detection:
    def __init__(self, bbox: List[float], confidence: float, track_id: int):
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.track_id = track_id
        self.velocity_vector = np.array([0.0, 0.0])  # [dx, dy] px/frame

class Detector:
    """
    YOLOv8 Inference Engine with ByteTrack integration.
    Computes velocity vectors via optical flow for patent-critical PTS.
    """
    def __init__(self):
        self.model = YOLO(settings.YOLO_MODEL)
        self.prev_gray: Dict[str, np.ndarray] = {}
        self.prev_points: Dict[str, Dict[int, np.ndarray]] = {} # track_id -> point
        logger.info(f"Detector initialized with {settings.YOLO_MODEL}")

    def detect(self, node_id: str, frame: np.ndarray) -> List[Detection]:
        # Perform inference with ByteTrack
        results = self.model.track(
            frame, 
            persist=True, 
            classes=[0],  # Person only
            conf=settings.CONFIDENCE_THRESHOLD,
            verbose=False
        )

        current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = []

        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)

            for bbox, conf, track_id in zip(boxes, confidences, track_ids):
                det = Detection(bbox.tolist(), float(conf), int(track_id))
                
                # Compute velocity vector using optical flow at the foot point (center-bottom)
                foot_point = np.array([[(bbox[0] + bbox[2]) / 2, bbox[3]]], dtype=np.float32)
                
                if node_id in self.prev_gray and track_id in self.prev_points[node_id]:
                    # Use Lucas-Kanade optical flow for specific points
                    p1, st, err = cv2.calcOpticalFlowPyrLK(
                        self.prev_gray[node_id], 
                        current_gray, 
                        self.prev_points[node_id][track_id].reshape(-1, 1, 2), 
                        None
                    )
                    if st[0]:
                        det.velocity_vector = (p1[0][0] - self.prev_points[node_id][track_id]).flatten()

                # Update state for next frame
                if node_id not in self.prev_points:
                    self.prev_points[node_id] = {}
                self.prev_points[node_id][track_id] = foot_point[0]
                
                detections.append(det)

        self.prev_gray[node_id] = current_gray
        # Cleanup old track points (optional, could be improved)
        return detections

detector = Detector()

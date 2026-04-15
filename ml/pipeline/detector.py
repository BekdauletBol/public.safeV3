"""
Person detector using YOLOv8.
Handles model loading, inference, ROI filtering, and bbox drawing.
"""

import cv2
import numpy as np
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field
from loguru import logger
import time
import os


@dataclass
class Detection:
    """Single person detection result."""
    bbox: Tuple[int, int, int, int]   # (x1, y1, x2, y2) in PIXEL coords
    confidence: float
    track_id: Optional[int] = None
    class_id: int = 0                 # 0 = person in COCO

    @property
    def x1(self) -> int: return self.bbox[0]
    @property
    def y1(self) -> int: return self.bbox[1]
    @property
    def x2(self) -> int: return self.bbox[2]
    @property
    def y2(self) -> int: return self.bbox[3]

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def width(self) -> int: return self.x2 - self.x1
    @property
    def height(self) -> int: return self.y2 - self.y1

    def to_dict(self) -> dict:
        return {
            "bbox": list(self.bbox),
            "confidence": round(self.confidence, 3),
            "track_id": self.track_id,
            "center": list(self.center),
            "width": self.width,
            "height": self.height,
        }


@dataclass
class FrameResult:
    """Complete result for one processed frame."""
    camera_id: str
    frame_idx: int
    timestamp: float
    detections: List[Detection] = field(default_factory=list)
    annotated_frame: Optional[np.ndarray] = None  # BGR frame with bboxes drawn
    frame_width: int = 0
    frame_height: int = 0
    inference_ms: float = 0.0
    roi_active: bool = False

    @property
    def count(self) -> int:
        return len(self.detections)

    @property
    def track_ids(self) -> List[int]:
        return [d.track_id for d in self.detections if d.track_id is not None]

    @property
    def avg_confidence(self) -> float:
        if not self.detections:
            return 0.0
        return sum(d.confidence for d in self.detections) / len(self.detections)

    def to_ws_payload(self) -> dict:
        """Serialize for WebSocket broadcast — no numpy arrays."""
        return {
            "camera_id": self.camera_id,
            "count": self.count,
            "detections": [d.to_dict() for d in self.detections],
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "inference_ms": round(self.inference_ms, 1),
            "roi_active": self.roi_active,
            "avg_confidence": round(self.avg_confidence, 3),
        }


class PersonDetector:
    """
    YOLOv8-based person detector.
    Falls back to a lightweight HOG detector if YOLO is unavailable (dev mode).
    """

    PERSON_CLASS_ID = 0  # COCO class 0 = person

    # Visual settings for bbox drawing
    BBOX_COLOR_DEFAULT  = (0,   0,   255)   # Red (BGR)
    BBOX_COLOR_TRACKED  = (0,   200, 0)     # Green when tracked
    BBOX_COLOR_ROI_MISS = (128, 128, 128)   # Grey — outside ROI
    LABEL_BG_COLOR      = (0,   0,   200)
    LABEL_TEXT_COLOR    = (255, 255, 255)
    BBOX_THICKNESS      = 2
    FONT                = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE          = 0.55
    FONT_THICKNESS      = 1

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.45,
        iou_threshold: float = 0.45,
        device: str = "cpu",
        use_fallback: bool = True,
    ):
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.model_path = model_path
        self._model = None
        self._use_yolo = False
        self._hog = None
        self._frame_idx = 0

        self._load_model(use_fallback)

    def _load_model(self, use_fallback: bool) -> None:
        """Try YOLO first, fall back to HOG."""
        try:
            from ultralytics import YOLO
            model_file = self.model_path
            if not os.path.exists(model_file):
                logger.info(f"Model {model_file} not found locally — downloading yolov8n.pt")
                model_file = "yolov8n.pt"  # ultralytics will auto-download
            self._model = YOLO(model_file)
            self._model.to(self.device)
            self._use_yolo = True
            logger.info(f"YOLOv8 loaded: {model_file} on {self.device}")
        except Exception as e:
            logger.warning(f"YOLO unavailable ({e}), using HOG fallback")
            if use_fallback:
                self._hog = cv2.HOGDescriptor()
                self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
                self._use_yolo = False

    def detect(
        self,
        frame: np.ndarray,
        roi_polygon: Optional[np.ndarray] = None,
    ) -> List[Detection]:
        """
        Run detection on a single BGR frame.
        Returns list of Detection objects in pixel coordinates.
        """
        if frame is None or frame.size == 0:
            return []

        t0 = time.perf_counter()

        if self._use_yolo:
            raw = self._detect_yolo(frame)
        elif self._hog is not None:
            raw = self._detect_hog(frame)
        else:
            return []

        elapsed_ms = (time.perf_counter() - t0) * 1000

        # ROI filtering
        if roi_polygon is not None and len(roi_polygon) >= 3:
            raw = self._filter_by_roi(raw, roi_polygon, frame.shape)

        logger.debug(
            f"Frame detected: {len(raw)} persons in {elapsed_ms:.1f}ms"
            + (f" | ROI active" if roi_polygon is not None else "")
        )
        for d in raw:
            logger.debug(f"  bbox={d.bbox} conf={d.confidence:.3f}")

        self._frame_idx += 1
        return raw

    def _detect_yolo(self, frame: np.ndarray) -> List[Detection]:
        """Run YOLOv8 inference."""
        results = self._model(
            frame,
            classes=[self.PERSON_CLASS_ID],
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False,
            device=self.device,
        )
        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                detections.append(
                    Detection(
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        confidence=conf,
                    )
                )
        return detections

    def _detect_hog(self, frame: np.ndarray) -> List[Detection]:
        """HOG-based pedestrian detector fallback."""
        h, w = frame.shape[:2]
        scale = min(640 / w, 480 / h, 1.0)
        small = cv2.resize(frame, (int(w * scale), int(h * scale)))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        rects, weights = self._hog.detectMultiScale(
            gray,
            winStride=(8, 8),
            padding=(4, 4),
            scale=1.05,
        )
        detections = []
        for (x, y, bw, bh), weight in zip(rects, weights):
            conf = min(float(weight[0]) / 2.0, 1.0)
            if conf < self.confidence_threshold:
                continue
            # Scale back to original frame coords
            sx, sy = int(x / scale), int(y / scale)
            sw, sh = int(bw / scale), int(bh / scale)
            detections.append(
                Detection(
                    bbox=(sx, sy, sx + sw, sy + sh),
                    confidence=conf,
                )
            )
        return detections

    def _filter_by_roi(
        self,
        detections: List[Detection],
        roi_polygon: np.ndarray,
        frame_shape: Tuple,
    ) -> List[Detection]:
        """Keep only detections whose center falls inside the ROI polygon."""
        filtered = []
        for det in detections:
            cx, cy = det.center
            inside = cv2.pointPolygonTest(roi_polygon, (float(cx), float(cy)), False)
            if inside >= 0:
                filtered.append(det)
        dropped = len(detections) - len(filtered)
        if dropped:
            logger.debug(f"ROI filtered out {dropped} detection(s)")
        return filtered

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        roi_polygon: Optional[np.ndarray] = None,
        show_confidence: bool = True,
        show_track_id: bool = True,
    ) -> np.ndarray:
        """
        Draw bounding boxes and labels on frame IN-PLACE.
        Returns the annotated frame (same array).

        This is the single authoritative place where visual bbox rendering happens.
        Drawing on the server side eliminates ALL coordinate-scaling bugs
        that would occur if the frontend tried to rescale canvas overlays.
        """
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # ── Draw ROI overlay ────────────────────────────────────────────────
        if roi_polygon is not None and len(roi_polygon) >= 3:
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [roi_polygon], (0, 255, 100))
            cv2.addWeighted(overlay, 0.08, annotated, 0.92, 0, annotated)
            cv2.polylines(annotated, [roi_polygon], True, (0, 220, 80), 2)

        # ── Draw each detection ─────────────────────────────────────────────
        for det in detections:
            x1, y1, x2, y2 = det.bbox

            # Clamp to frame boundaries (prevents negative coords from crashing)
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(0, min(x2, w - 1))
            y2 = max(0, min(y2, h - 1))

            # Choose color based on tracking state
            color = self.BBOX_COLOR_TRACKED if det.track_id is not None else self.BBOX_COLOR_DEFAULT

            # ── Outer glow effect (slightly larger, semi-transparent) ────────
            glow = annotated.copy()
            cv2.rectangle(glow, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), color, self.BBOX_THICKNESS + 2)
            cv2.addWeighted(glow, 0.3, annotated, 0.7, 0, annotated)

            # ── Main bounding box ────────────────────────────────────────────
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, self.BBOX_THICKNESS)

            # ── Corner markers for cleaner look ─────────────────────────────
            corner_len = max(8, min(20, (x2 - x1) // 4))
            thick = self.BBOX_THICKNESS + 1
            for px, py, dx, dy in [
                (x1, y1,  1,  1),
                (x2, y1, -1,  1),
                (x1, y2,  1, -1),
                (x2, y2, -1, -1),
            ]:
                cv2.line(annotated, (px, py), (px + dx * corner_len, py), color, thick)
                cv2.line(annotated, (px, py), (px, py + dy * corner_len), color, thick)

            # ── Label (track_id + confidence) ────────────────────────────────
            parts = []
            if show_track_id and det.track_id is not None:
                parts.append(f"#{det.track_id}")
            if show_confidence:
                parts.append(f"{det.confidence:.0%}")
            label = " ".join(parts) if parts else "Person"

            (lw, lh), baseline = cv2.getTextSize(
                label, self.FONT, self.FONT_SCALE, self.FONT_THICKNESS
            )
            label_y = y1 - 6 if y1 - lh - 6 >= 0 else y2 + lh + 6
            label_x = x1

            # Label background
            cv2.rectangle(
                annotated,
                (label_x, label_y - lh - baseline),
                (label_x + lw + 4, label_y + baseline),
                self.LABEL_BG_COLOR,
                cv2.FILLED,
            )
            # Label text
            cv2.putText(
                annotated,
                label,
                (label_x + 2, label_y),
                self.FONT,
                self.FONT_SCALE,
                self.LABEL_TEXT_COLOR,
                self.FONT_THICKNESS,
                cv2.LINE_AA,
            )

        # ── People count HUD (top-left) ──────────────────────────────────────
        count_text = f"People: {len(detections)}"
        cv2.rectangle(annotated, (8, 8), (170, 36), (0, 0, 0), cv2.FILLED)
        cv2.putText(
            annotated, count_text,
            (14, 28),
            self.FONT, 0.7, (0, 255, 0), 2, cv2.LINE_AA,
        )

        return annotated

    def normalize_roi(
        self,
        roi_points: List[Dict],
        frame_width: int,
        frame_height: int,
    ) -> Optional[np.ndarray]:
        """
        Convert normalized ROI points [{x: 0.0-1.0, y: 0.0-1.0}]
        → pixel-coordinate numpy polygon array.
        """
        if not roi_points:
            return None
        pts = [
            (int(p["x"] * frame_width), int(p["y"] * frame_height))
            for p in roi_points
        ]
        return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
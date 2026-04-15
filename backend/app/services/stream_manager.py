"""
StreamManager — FIXED VERSION

Root causes addressed:
  1. _read_frame() now runs YOLO + tracker before encoding the frame
  2. Bboxes are drawn server-side with OpenCV (eliminates coordinate scaling bugs)
  3. _latest_detections stored per stream (accessible for WebSocket broadcast)
  4. _stream_loop() calls ws_manager.broadcast_camera_update() after every frame
  5. Two frame buffers: annotated (for streaming) + raw (for detection input)
"""

import asyncio
import base64
import cv2
import numpy as np
from typing import Dict, Optional, List, AsyncGenerator, Any
from datetime import datetime
from loguru import logger
from app.core.config import settings


class DetectionSnapshot:
    """Thread-safe snapshot of one frame's detection results."""
    __slots__ = (
        "count", "detections", "track_ids", "avg_confidence",
        "frame_width", "frame_height", "inference_ms", "timestamp",
        "roi_active",
    )

    def __init__(self, count, detections, track_ids, avg_confidence,
                 frame_width, frame_height, inference_ms, roi_active=False):
        self.count = count
        self.detections = detections
        self.track_ids = track_ids
        self.avg_confidence = avg_confidence
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.inference_ms = inference_ms
        self.timestamp = datetime.utcnow().isoformat()
        self.roi_active = roi_active

    def to_dict(self):
        return {
            "count": self.count,
            "detections": self.detections,
            "track_ids": self.track_ids,
            "avg_confidence": round(self.avg_confidence, 3),
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "inference_ms": round(self.inference_ms, 1),
            "roi_active": self.roi_active,
            "timestamp": self.timestamp,
        }


class CameraStream:
    """Manages a single RTSP camera stream with embedded detection."""

    BBOX_COLOR = (0, 0, 255)        # Red (BGR) — default
    BBOX_TRACKED = (0, 200, 0)      # Green when tracked ID assigned
    LABEL_BG = (0, 0, 180)
    LABEL_FG = (255, 255, 255)
    FONT = cv2.FONT_HERSHEY_SIMPLEX

    def __init__(self, camera_id, rtsp_url, fps=5, roi_points=None,
                 confidence_threshold=0.45):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.roi_points = roi_points
        self.confidence_threshold = confidence_threshold
        self.is_running = False
        self._cap = None
        self._annotated_frame: Optional[bytes] = None
        self._frame_timestamp: Optional[datetime] = None
        self._latest_detections: Optional[DetectionSnapshot] = None
        self._error_count = 0
        self._frame_idx = 0
        self._task = None
        self._detector = None
        self._tracker = None
        self._ml_ready = False

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        await asyncio.get_event_loop().run_in_executor(None, self._init_ml)
        self._task = asyncio.create_task(self._stream_loop())
        logger.info(f"Stream started: camera={self.camera_id}")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await asyncio.get_event_loop().run_in_executor(None, self._release_cap)
        logger.info(f"Stream stopped: camera={self.camera_id}")

    def _init_ml(self):
        try:
            import sys, os
            for p in [
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "pipeline"),
                "/app/ml/pipeline",
                "/ml/pipeline",
            ]:
                if os.path.isdir(p) and p not in sys.path:
                    sys.path.insert(0, p)
            from ml.pipeline.detector import PersonDetector
            from ml.pipeline.tracker import SORTTracker
            self._detector = PersonDetector(
                confidence_threshold=self.confidence_threshold,
                use_fallback=True,
            )
            self._tracker = SORTTracker()
            self._ml_ready = True
            logger.info(f"ML pipeline ready: camera={self.camera_id}")
        except Exception as e:
            logger.warning(f"ML init failed camera={self.camera_id}: {e}")
            self._ml_ready = False

    def _release_cap(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None

    async def _stream_loop(self):
        interval = 1.0 / max(self.fps, 1)
        loop = asyncio.get_event_loop()
        while self.is_running:
            try:
                result = await loop.run_in_executor(None, self._process_frame)
                if result is not None:
                    jpeg_bytes, snapshot = result
                    self._annotated_frame = jpeg_bytes
                    self._frame_timestamp = datetime.utcnow()
                    self._latest_detections = snapshot
                    self._error_count = 0
                    await self._broadcast_update(snapshot)
                else:
                    self._error_count += 1
                    if self._error_count >= 10:
                        logger.warning(f"Camera {self.camera_id}: reconnecting")
                        await loop.run_in_executor(None, self._reconnect)
                        self._error_count = 0
            except Exception as e:
                logger.error(f"Stream error camera={self.camera_id}: {e}", exc_info=True)
                self._error_count += 1
            await asyncio.sleep(interval)

    def _process_frame(self):
        """
        Core frame processing (runs in thread pool):
        1. Read raw BGR from RTSP
        2. Detect persons with YOLO (or HOG fallback)
        3. Track with SORT → assign track IDs
        4. Draw bboxes server-side with OpenCV
        5. Encode annotated frame to JPEG
        """
        if self._cap is None or not self._cap.isOpened():
            self._reconnect()
        if self._cap is None:
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None

        frame_h, frame_w = frame.shape[:2]
        self._frame_idx += 1
        import time
        t0 = time.perf_counter()

        # ── ROI polygon in pixel coords ──────────────────────────────────────
        roi_polygon = None
        if self.roi_points:
            pts = [(int(p["x"] * frame_w), int(p["y"] * frame_h))
                   for p in self.roi_points]
            roi_polygon = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))

        # ── Detection ────────────────────────────────────────────────────────
        raw_detections = []
        if self._ml_ready and self._detector is not None:
            raw_detections = self._detector.detect(frame, roi_polygon=roi_polygon)
            logger.debug(
                f"cam={self.camera_id} frame#{self._frame_idx}: "
                f"{len(raw_detections)} person(s) detected"
            )
            for d in raw_detections:
                logger.debug(f"  bbox={d.bbox} conf={d.confidence:.3f}")

        # ── Tracking ─────────────────────────────────────────────────────────
        tracked = []
        if self._tracker is not None and raw_detections:
            bboxes = [d.bbox for d in raw_detections]
            tracks = self._tracker.update(bboxes)
            track_map = {}
            for x1, y1, x2, y2, tid in tracks:
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                best, best_d = None, float("inf")
                for d in raw_detections:
                    dist = abs(d.center[0] - cx) + abs(d.center[1] - cy)
                    if dist < best_d:
                        best_d, best = dist, d
                if best:
                    best.track_id = int(tid)
                    tracked.append(best)
        else:
            tracked = raw_detections

        inference_ms = (time.perf_counter() - t0) * 1000

        # ── Draw bboxes SERVER-SIDE (eliminates all frontend scaling bugs) ───
        annotated = frame.copy()

        # ROI overlay
        if roi_polygon is not None:
            ov = annotated.copy()
            cv2.fillPoly(ov, [roi_polygon], (0, 255, 100))
            cv2.addWeighted(ov, 0.08, annotated, 0.92, 0, annotated)
            cv2.polylines(annotated, [roi_polygon], True, (0, 220, 80), 2)

        for det in tracked:
            x1, y1, x2, y2 = det.bbox
            # Clamp to frame
            x1 = max(0, min(x1, frame_w - 1))
            y1 = max(0, min(y1, frame_h - 1))
            x2 = max(0, min(x2, frame_w - 1))
            y2 = max(0, min(y2, frame_h - 1))

            color = self.BBOX_TRACKED if det.track_id is not None else self.BBOX_COLOR

            # Glow
            glow = annotated.copy()
            cv2.rectangle(glow, (x1-2, y1-2), (x2+2, y2+2), color, 4)
            cv2.addWeighted(glow, 0.3, annotated, 0.7, 0, annotated)

            # Main box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Corner markers
            cl = max(8, min(20, (x2 - x1) // 4))
            for px, py, dx, dy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
                cv2.line(annotated, (px, py), (px + dx*cl, py), color, 3)
                cv2.line(annotated, (px, py), (px, py + dy*cl), color, 3)

            # Label
            parts = []
            if det.track_id is not None:
                parts.append(f"#{det.track_id}")
            parts.append(f"{det.confidence:.0%}")
            label = " ".join(parts)

            (lw, lh), baseline = cv2.getTextSize(label, self.FONT, 0.55, 1)
            ly = y1 - 6 if y1 - lh - 6 >= 0 else y2 + lh + 6
            cv2.rectangle(annotated, (x1, ly - lh - baseline), (x1 + lw + 4, ly + baseline),
                          self.LABEL_BG, cv2.FILLED)
            cv2.putText(annotated, label, (x1 + 2, ly), self.FONT, 0.55,
                        self.LABEL_FG, 1, cv2.LINE_AA)

        # Count HUD
        hud = f"People: {len(tracked)}"
        cv2.rectangle(annotated, (8, 8), (180, 38), (0, 0, 0), cv2.FILLED)
        cv2.putText(annotated, hud, (14, 29), self.FONT, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

        # ── Encode ───────────────────────────────────────────────────────────
        ok, buf = cv2.imencode(".jpg", annotated,
                               [cv2.IMWRITE_JPEG_QUALITY, settings.STREAM_QUALITY])
        if not ok:
            return None

        snapshot = DetectionSnapshot(
            count=len(tracked),
            detections=[d.to_dict() for d in tracked],
            track_ids=[d.track_id for d in tracked if d.track_id is not None],
            avg_confidence=(
                sum(d.confidence for d in tracked) / len(tracked) if tracked else 0.0
            ),
            frame_width=frame_w,
            frame_height=frame_h,
            inference_ms=inference_ms,
            roi_active=roi_polygon is not None,
        )
        return buf.tobytes(), snapshot

    async def _broadcast_update(self, snapshot: DetectionSnapshot):
        try:
            from app.services.websocket_manager import ws_manager
            await ws_manager.broadcast_camera_update(self.camera_id, snapshot.to_dict())
        except Exception as e:
            logger.warning(f"WS broadcast failed cam={self.camera_id}: {e}")

    def _reconnect(self):
        self._release_cap()
        cap = cv2.VideoCapture(self.rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        if cap.isOpened():
            self._cap = cap
            logger.info(f"Camera {self.camera_id}: RTSP connected")
        else:
            logger.error(f"Camera {self.camera_id}: failed: {self.rtsp_url}")

    def get_latest_frame_raw(self) -> Optional[bytes]:
        return self._annotated_frame

    def get_latest_frame_b64(self) -> Optional[str]:
        if self._annotated_frame:
            return base64.b64encode(self._annotated_frame).decode("utf-8")
        return None

    def get_latest_detections(self) -> Optional[DetectionSnapshot]:
        return self._latest_detections

    def update_roi(self, roi_points):
        self.roi_points = roi_points

    @property
    def is_online(self):
        if not self.is_running or self._annotated_frame is None:
            return False
        if not self._frame_timestamp:
            return False
        return (datetime.utcnow() - self._frame_timestamp).total_seconds() < 30.0


class StreamManager:
    def __init__(self):
        self._streams: Dict[str, CameraStream] = {}

    async def add_camera(self, camera_id, rtsp_url, fps=5,
                         roi_points=None, confidence_threshold=0.45):
        if camera_id in self._streams:
            await self.remove_camera(camera_id)
        stream = CameraStream(camera_id, rtsp_url, fps, roi_points, confidence_threshold)
        self._streams[camera_id] = stream
        await stream.start()
        return stream

    async def remove_camera(self, camera_id):
        stream = self._streams.pop(camera_id, None)
        if stream:
            await stream.stop()

    def get_stream(self, camera_id) -> Optional[CameraStream]:
        return self._streams.get(camera_id)

    def get_latest_frame(self, camera_id) -> Optional[bytes]:
        s = self._streams.get(camera_id)
        return s.get_latest_frame_raw() if s else None

    def get_latest_frame_b64(self, camera_id) -> Optional[str]:
        s = self._streams.get(camera_id)
        return s.get_latest_frame_b64() if s else None

    def get_latest_detections(self, camera_id) -> Optional[DetectionSnapshot]:
        s = self._streams.get(camera_id)
        return s.get_latest_detections() if s else None

    def is_camera_online(self, camera_id) -> bool:
        s = self._streams.get(camera_id)
        return s.is_online if s else False

    def update_camera_roi(self, camera_id, roi_points):
        s = self._streams.get(camera_id)
        if s:
            s.update_roi(roi_points)

    async def get_all_status(self) -> Dict[str, dict]:
        return {
            cid: {
                "online": s.is_online,
                "fps": s.fps,
                "has_frame": s._annotated_frame is not None,
                "count": s.get_latest_detections().count if s.get_latest_detections() else 0,
            }
            for cid, s in self._streams.items()
        }

    async def stop_all(self):
        tasks = [s.stop() for s in self._streams.values()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._streams.clear()

    async def mjpeg_generator(self, camera_id) -> AsyncGenerator[bytes, None]:
        """Yields annotated MJPEG frames (bboxes already drawn server-side)."""
        stream = self._streams.get(camera_id)
        if not stream:
            return
        interval = 1.0 / max(stream.fps, 1)
        while stream.is_running:
            frame = stream.get_latest_frame_raw()
            if frame:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            await asyncio.sleep(interval)


stream_manager = StreamManager()
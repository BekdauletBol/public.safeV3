import cv2
import numpy as np
import base64
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from backend.core.queue_manager import queue_manager
from backend.core.detector import detector
from backend.core.footpoint_pip import footpoint_pip
from backend.core.threat_scorer import threat_scorer
from backend.core.zone_manager import zone_manager
from backend.core.mesh_coordinator import mesh_coordinator
from backend.storage.telemetry import telemetry_logger

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/node/{node_id}")
async def node_websocket(websocket: WebSocket, node_id: str):
    await websocket.accept()
    logger.info(f"Node {node_id} connected via WebSocket")
    
    try:
        while True:
            # Receive binary frame (JPEG)
            data = await websocket.receive_bytes()
            await queue_manager.put_frame(node_id, data)
            
            # Process frame
            frame_bytes = await queue_manager.get_frame(node_id)
            if not frame_bytes: continue
            
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None: continue

            # AI Pipeline
            detections = detector.detect(node_id, frame)
            active_zone = zone_manager.get_active_zone(node_id)
            
            results = []
            max_threat_score = 0.0
            
            for det in detections:
                if active_zone.size > 0:
                    # 1. Violation Check
                    viol = footpoint_pip.check_violation(det, active_zone)
                    # 2. Threat Scoring
                    ts = threat_scorer.calculate_score(det, active_zone)
                    
                    max_threat_score = max(max_threat_score, ts.score)
                    
                    # 3. Telemetry
                    telemetry_logger.log_detection(node_id, det.track_id, ts.score, ts.ttc_ms, ts.status)
                    
                    # 4. Mesh Propagation (if critical)
                    if ts.status == "CRITICAL":
                        # In real scenario, compute threat direction from velocity
                        await mesh_coordinator.propagate_alert(node_id, (0, 0))

                    results.append({
                        "track_id": det.track_id,
                        "bbox": det.bbox,
                        "threat_score": ts.score,
                        "ttc_ms": ts.ttc_ms,
                        "status": ts.status
                    })
                    
                    # Overlays
                    color = (0, 255, 0)
                    if ts.status == "CRITICAL": color = (0, 0, 255)
                    elif ts.status == "DANGER": color = (0, 165, 255)
                    elif ts.status == "WARNING": color = (0, 255, 255)
                    
                    cv2.rectangle(frame, (int(det.bbox[0]), int(det.bbox[1])), (int(det.bbox[2]), int(det.bbox[3])), color, 2)
                    cv2.putText(frame, f"ID:{det.track_id} TTC:{ts.ttc_ms/1000:.1f}s", (int(det.bbox[0]), int(det.bbox[1]-10)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Draw Zone
            if active_zone.size > 0:
                cv2.polylines(frame, [active_zone], True, (255, 255, 0), 2)

            # Update density
            zone_manager.update_density(node_id, len(detections))

            # Encode processed frame to base64 for dashboard
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')

            # Broadcast to dashboard
            await manager.broadcast({
                "type": "FRAME_UPDATE",
                "node_id": node_id,
                "frame": jpg_as_text,
                "detections": results,
                "max_threat": max_threat_score
            })

    except WebSocketDisconnect:
        logger.info(f"Node {node_id} disconnected")

@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

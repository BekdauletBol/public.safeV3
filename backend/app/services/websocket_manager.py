import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket
from loguru import logger
from datetime import datetime


class WebSocketManager:
    """
    Manages WebSocket connections with per-client ID tracking
    and channel-based subscriptions (dashboard, per-camera).
    """

    def __init__(self):
        # client_id → WebSocket
        self._clients: Dict[str, WebSocket] = {}
        # client_ids subscribed to the dashboard feed
        self._dashboard_subs: Set[str] = set()
        # camera_id → set of client_ids
        self._camera_subs: Dict[str, Set[str]] = {}

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self._clients[client_id] = websocket
        logger.info(f"WS connected: {client_id} (total={len(self._clients)})")

    async def disconnect(self, client_id: str):
        self._clients.pop(client_id, None)
        self._dashboard_subs.discard(client_id)
        for subs in self._camera_subs.values():
            subs.discard(client_id)
        logger.info(f"WS disconnected: {client_id} (total={len(self._clients)})")

    # ── Subscriptions ─────────────────────────────────────────────────────────

    async def subscribe_dashboard(self, client_id: str):
        self._dashboard_subs.add(client_id)

    async def subscribe_camera(self, client_id: str, camera_id: str):
        if camera_id not in self._camera_subs:
            self._camera_subs[camera_id] = set()
        self._camera_subs[camera_id].add(client_id)

    async def unsubscribe_camera(self, client_id: str, camera_id: str):
        if camera_id in self._camera_subs:
            self._camera_subs[camera_id].discard(client_id)

    # ── Sending ───────────────────────────────────────────────────────────────

    async def send_to_client(self, client_id: str, data: dict):
        ws = self._clients.get(client_id)
        if ws is None:
            return
        try:
            await ws.send_text(json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"WS send failed for {client_id}: {e}")
            await self.disconnect(client_id)

    async def broadcast(self, message: dict):
        if not self._clients:
            return
        payload = json.dumps(message, default=str)
        dead = []
        for client_id, ws in list(self._clients.items()):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(client_id)
        for client_id in dead:
            await self.disconnect(client_id)

    async def broadcast_camera_update(self, camera_id: str, data: dict):
        message = {
            "type": "camera_update",
            "camera_id": camera_id,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        # Send to camera-specific subscribers
        subs = self._camera_subs.get(str(camera_id), set())
        for client_id in list(subs):
            await self.send_to_client(client_id, message)
        # Also send to dashboard subscribers
        for client_id in list(self._dashboard_subs):
            await self.send_to_client(client_id, message)

    async def broadcast_system_update(self, data: dict):
        message = {
            "type": "system_update",
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)


# Singleton instances
ws_manager = WebSocketManager()
manager = ws_manager  # legacy alias for any code still using `manager`

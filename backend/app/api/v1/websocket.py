import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_manager
from loguru import logger
import json

router = APIRouter()


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket connection.
    Client sends subscription messages:
      {"action": "subscribe_dashboard"}
      {"action": "subscribe_camera", "camera_id": "<uuid>"}
      {"action": "unsubscribe_camera", "camera_id": "<uuid>"}
    Server pushes:
      {"type": "camera_update", "camera_id": "...", "data": {...}}
      {"type": "system_event", "data": {...}}
    """
    client_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, client_id)

    try:
        # Send welcome
        await ws_manager.send_to_client(client_id, {
            "type": "connected",
            "client_id": client_id,
        })

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = msg.get("action")

            if action == "subscribe_dashboard":
                await ws_manager.subscribe_dashboard(client_id)
                await ws_manager.send_to_client(client_id, {
                    "type": "subscribed",
                    "channel": "dashboard",
                })

            elif action == "subscribe_camera":
                cam_id = msg.get("camera_id")
                if cam_id:
                    await ws_manager.subscribe_camera(client_id, cam_id)
                    await ws_manager.send_to_client(client_id, {
                        "type": "subscribed",
                        "channel": f"camera:{cam_id}",
                    })

            elif action == "unsubscribe_camera":
                cam_id = msg.get("camera_id")
                if cam_id:
                    await ws_manager.unsubscribe_camera(client_id, cam_id)

            elif action == "ping":
                await ws_manager.send_to_client(client_id, {"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error client={client_id}: {e}")
    finally:
        await ws_manager.disconnect(client_id)
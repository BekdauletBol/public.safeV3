from uuid import UUID
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from app.services.stream_manager import stream_manager

router = APIRouter()


@router.get("/{camera_id}/mjpeg")
async def mjpeg_stream(camera_id: UUID):
    """
    MJPEG streaming endpoint.
    Returns annotated frames (bboxes already drawn server-side).
    Frontend can use: <img src="/api/v1/streams/{id}/mjpeg" />
    """
    cam_id = str(camera_id)
    if not stream_manager.get_stream(cam_id):
        raise HTTPException(status_code=404, detail="Stream not found or camera offline")

    return StreamingResponse(
        stream_manager.mjpeg_generator(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/{camera_id}/snapshot")
async def get_snapshot(camera_id: UUID):
    """Return latest annotated JPEG frame as a single image."""
    cam_id = str(camera_id)
    frame = stream_manager.get_latest_frame(cam_id)
    if not frame:
        raise HTTPException(status_code=404, detail="No frame available")
    return Response(
        content=frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{camera_id}/snapshot-b64")
async def get_snapshot_b64(camera_id: UUID):
    """Return latest frame as base64 JSON."""
    cam_id = str(camera_id)
    b64 = stream_manager.get_latest_frame_b64(cam_id)
    if not b64:
        raise HTTPException(status_code=404, detail="No frame available")
    dets = stream_manager.get_latest_detections(cam_id)
    return {
        "camera_id": cam_id,
        "frame_b64": b64,
        "detections": dets.to_dict() if dets else None,
    }


@router.get("/{camera_id}/detections")
async def get_detections(camera_id: UUID):
    """Return latest detection snapshot for a camera."""
    cam_id = str(camera_id)
    dets = stream_manager.get_latest_detections(cam_id)
    if dets is None:
        return {"camera_id": cam_id, "count": 0, "detections": []}
    return {"camera_id": cam_id, **dets.to_dict()}


@router.get("/status/all")
async def all_streams_status():
    """Return status for all active streams."""
    return await stream_manager.get_all_status()
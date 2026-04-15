from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, AnyUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.camera_service import CameraService
from app.services.stream_manager import stream_manager
from app.core.security import get_current_admin

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    name: str
    location: str
    rtsp_url: str
    street_address: Optional[str] = None
    fps: int = 5
    detection_confidence: float = 0.45
    model_variant: str = "yolov8n"
    roi: Optional[list] = None


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    rtsp_url: Optional[str] = None
    street_address: Optional[str] = None
    fps: Optional[int] = None
    detection_confidence: Optional[float] = None
    is_active: Optional[bool] = None
    roi: Optional[list] = None


class CameraResponse(BaseModel):
    id: str
    name: str
    location: str
    street_address: Optional[str]
    rtsp_url: str
    is_active: bool
    is_online: bool
    fps: int
    detection_confidence: float
    model_variant: str
    roi: Optional[list]
    last_count: int
    last_seen: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


def camera_to_response(cam) -> dict:
    return {
        "id": str(cam.id),
        "name": cam.name,
        "location": cam.location,
        "street_address": cam.street_address,
        "rtsp_url": cam.rtsp_url,
        "is_active": cam.is_active,
        "is_online": stream_manager.is_camera_online(str(cam.id)),
        "fps": cam.fps,
        "detection_confidence": cam.detection_confidence,
        "model_variant": cam.model_variant,
        "roi": cam.roi,
        "last_count": cam.last_count or 0,
        "last_seen": cam.last_seen.isoformat() if cam.last_seen else None,
        "created_at": cam.created_at.isoformat(),
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[dict])
async def list_cameras(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    svc = CameraService(db)
    cameras = await svc.list_cameras(active_only=active_only)
    return [camera_to_response(c) for c in cameras]


@router.get("/{camera_id}", response_model=dict)
async def get_camera(camera_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = CameraService(db)
    cam = await svc.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera_to_response(cam)


@router.post("/", response_model=dict, status_code=201)
async def create_camera(
    payload: CameraCreate,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    svc = CameraService(db)
    cam = await svc.create_camera(**payload.model_dump())
    # Start stream immediately
    try:
        await stream_manager.add_camera(
            camera_id=str(cam.id),
            rtsp_url=cam.rtsp_url,
            fps=cam.fps,
            roi_points=cam.roi,
            confidence_threshold=cam.detection_confidence,
        )
    except Exception as e:
        pass  # Non-fatal — stream starts async
    return camera_to_response(cam)


@router.put("/{camera_id}", response_model=dict)
async def update_camera(
    camera_id: UUID,
    payload: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    svc = CameraService(db)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    cam = await svc.update_camera(camera_id, **updates)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Hot-update stream if ROI or URL changed
    if "rtsp_url" in updates or "fps" in updates:
        try:
            await stream_manager.add_camera(  # re-adds = restarts
                camera_id=str(cam.id),
                rtsp_url=cam.rtsp_url,
                fps=cam.fps,
                roi_points=cam.roi,
                confidence_threshold=cam.detection_confidence,
            )
        except Exception:
            pass
    elif "roi" in updates:
        stream_manager.update_camera_roi(str(cam.id), cam.roi)

    return camera_to_response(cam)


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    svc = CameraService(db)
    deleted = await svc.delete_camera(camera_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Camera not found")
    await stream_manager.remove_camera(str(camera_id))


@router.post("/{camera_id}/restart-stream")
async def restart_stream(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    svc = CameraService(db)
    cam = await svc.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    await stream_manager.add_camera(
        camera_id=str(cam.id),
        rtsp_url=cam.rtsp_url,
        fps=cam.fps,
        roi_points=cam.roi,
        confidence_threshold=cam.detection_confidence,
    )
    return {"status": "stream restarted", "camera_id": str(camera_id)}
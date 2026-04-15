from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.camera_service import CameraService
from app.services.stream_manager import stream_manager
from app.core.security import get_current_admin

router = APIRouter()


class ROIPoint(BaseModel):
    x: float  # normalized 0.0–1.0
    y: float


class ROISaveRequest(BaseModel):
    points: List[ROIPoint]
    name: str = "Default ROI"
    rect_x: Optional[float] = None
    rect_y: Optional[float] = None
    rect_width: Optional[float] = None
    rect_height: Optional[float] = None


@router.get("/{camera_id}")
async def get_roi(camera_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = CameraService(db)
    roi = await svc.get_roi(camera_id)
    if not roi:
        return {"camera_id": str(camera_id), "roi": None}
    return {
        "camera_id": str(camera_id),
        "roi_id": str(roi.id),
        "name": roi.name,
        "points": roi.points,
        "rect": roi.get_rect(),
        "is_active": roi.is_active,
        "created_at": roi.created_at.isoformat(),
    }


@router.post("/{camera_id}")
async def save_roi(
    camera_id: UUID,
    payload: ROISaveRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    svc = CameraService(db)
    cam = await svc.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    points_dict = [{"x": p.x, "y": p.y} for p in payload.points]

    roi = await svc.save_roi(
        camera_id=camera_id,
        points=points_dict,
        name=payload.name,
        rect_x=payload.rect_x,
        rect_y=payload.rect_y,
        rect_width=payload.rect_width,
        rect_height=payload.rect_height,
    )

    # Hot-update the running stream's ROI without restart
    stream_manager.update_camera_roi(str(camera_id), points_dict)

    return {
        "camera_id": str(camera_id),
        "roi_id": str(roi.id),
        "name": roi.name,
        "points": roi.points,
        "rect": roi.get_rect(),
        "message": "ROI saved and applied to live stream",
    }


@router.delete("/{camera_id}")
async def delete_roi(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    svc = CameraService(db)
    deleted = await svc.delete_roi(camera_id)
    stream_manager.update_camera_roi(str(camera_id), None)
    return {"camera_id": str(camera_id), "deleted": deleted}
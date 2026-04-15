from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.camera_repo import CameraRepository
from app.repositories.analytics_repo import AnalyticsRepository
from app.db.models.camera import Camera
from app.db.models.roi import ROIConfig
from sqlalchemy import select, update, delete
from app.db.session import AsyncSessionLocal
from loguru import logger


class CameraService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.camera_repo = CameraRepository(db)

    async def create_camera(
        self,
        name: str,
        location: str,
        rtsp_url: str,
        street_address: Optional[str] = None,
        fps: int = 5,
        detection_confidence: float = 0.5,
        model_variant: str = "yolov8n",
        roi: Optional[list] = None,
    ) -> Camera:
        camera = await self.camera_repo.create(
            name=name,
            location=location,
            rtsp_url=rtsp_url,
            street_address=street_address,
            fps=fps,
            detection_confidence=detection_confidence,
            model_variant=model_variant,
            roi=roi,
        )
        logger.info(f"Camera created: {camera.id} - {camera.name}")
        return camera

    async def get_camera(self, camera_id: UUID) -> Optional[Camera]:
        return await self.camera_repo.get_by_id(camera_id)

    async def list_cameras(self, active_only: bool = False) -> List[Camera]:
        return await self.camera_repo.get_all(active_only=active_only)

    async def update_camera(self, camera_id: UUID, **kwargs) -> Optional[Camera]:
        camera = await self.camera_repo.update(camera_id, **kwargs)
        if camera:
            logger.info(f"Camera updated: {camera_id}")
        return camera

    async def delete_camera(self, camera_id: UUID) -> bool:
        result = await self.camera_repo.delete(camera_id)
        if result:
            logger.info(f"Camera deleted: {camera_id}")
        return result

    async def get_roi(self, camera_id: UUID) -> Optional[ROIConfig]:
        result = await self.db.execute(
            select(ROIConfig)
            .where(ROIConfig.camera_id == camera_id, ROIConfig.is_active == True)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_roi(
        self,
        camera_id: UUID,
        points: list,
        name: str = "Default ROI",
        rect_x: Optional[float] = None,
        rect_y: Optional[float] = None,
        rect_width: Optional[float] = None,
        rect_height: Optional[float] = None,
    ) -> ROIConfig:
        # Deactivate existing ROIs
        await self.db.execute(
            update(ROIConfig)
            .where(ROIConfig.camera_id == camera_id)
            .values(is_active=False)
        )

        # Create new ROI
        roi = ROIConfig(
            camera_id=camera_id,
            name=name,
            points=points,
            rect_x=rect_x,
            rect_y=rect_y,
            rect_width=rect_width,
            rect_height=rect_height,
            is_active=True,
        )
        self.db.add(roi)

        # Also update camera's roi field for quick access
        await self.camera_repo.update(camera_id, roi=points)

        await self.db.flush()
        await self.db.refresh(roi)
        logger.info(f"ROI saved for camera {camera_id}")
        return roi

    async def delete_roi(self, camera_id: UUID) -> bool:
        result = await self.db.execute(
            delete(ROIConfig).where(ROIConfig.camera_id == camera_id)
        )
        await self.camera_repo.update(camera_id, roi=None)
        return result.rowcount > 0

    async def set_online_status(self, camera_id: UUID, is_online: bool) -> None:
        await self.camera_repo.set_online_status(camera_id, is_online)
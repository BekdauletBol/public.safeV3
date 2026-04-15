from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.camera import Camera
from app.db.models.people_count import PeopleCount
from datetime import datetime


class CameraRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Camera:
        camera = Camera(**kwargs)
        self.db.add(camera)
        await self.db.flush()
        await self.db.refresh(camera)
        return camera

    async def get_by_id(self, camera_id: UUID) -> Optional[Camera]:
        result = await self.db.execute(
            select(Camera).where(Camera.id == camera_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, active_only: bool = False) -> List[Camera]:
        query = select(Camera)
        if active_only:
            query = query.where(Camera.is_active == True)
        query = query.order_by(Camera.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, camera_id: UUID, **kwargs) -> Optional[Camera]:
        kwargs["updated_at"] = datetime.utcnow()
        await self.db.execute(
            update(Camera).where(Camera.id == camera_id).values(**kwargs)
        )
        await self.db.flush()
        return await self.get_by_id(camera_id)

    async def delete(self, camera_id: UUID) -> bool:
        result = await self.db.execute(
            delete(Camera).where(Camera.id == camera_id)
        )
        return result.rowcount > 0

    async def set_online_status(self, camera_id: UUID, is_online: bool) -> None:
        await self.db.execute(
            update(Camera)
            .where(Camera.id == camera_id)
            .values(is_online=is_online, updated_at=datetime.utcnow())
        )

    async def update_last_count(self, camera_id: UUID, count: int) -> None:
        await self.db.execute(
            update(Camera)
            .where(Camera.id == camera_id)
            .values(last_count=count, last_seen=datetime.utcnow())
        )

    async def get_total_count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Camera))
        return result.scalar() or 0

    async def get_active_count(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Camera).where(Camera.is_active == True)
        )
        return result.scalar() or 0
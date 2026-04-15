from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, update, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.report import Report, ReportStatus, ReportType


class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Report:
        report = Report(**kwargs)
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def get_by_id(self, report_id: UUID) -> Optional[Report]:
        result = await self.db.execute(
            select(Report).where(Report.id == report_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        camera_id: Optional[UUID] = None,
        report_type: Optional[ReportType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Report]:
        query = select(Report)
        if camera_id:
            query = query.where(Report.camera_id == camera_id)
        if report_type:
            query = query.where(Report.report_type == report_type)
        query = query.order_by(desc(Report.created_at)).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        report_id: UUID,
        status: ReportStatus,
        error_message: Optional[str] = None,
        file_path: Optional[str] = None,
        insights: Optional[dict] = None,
        data: Optional[dict] = None,
        summary: Optional[str] = None,
    ) -> Optional[Report]:
        values = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        if file_path is not None:
            values["file_path"] = file_path
        if insights is not None:
            values["insights"] = insights
        if data is not None:
            values["data"] = data
        if summary is not None:
            values["summary"] = summary
        if status == ReportStatus.COMPLETED:
            values["completed_at"] = datetime.utcnow()

        await self.db.execute(
            update(Report).where(Report.id == report_id).values(**values)
        )
        await self.db.flush()
        return await self.get_by_id(report_id)

    async def get_latest_weekly(self, camera_id: Optional[UUID] = None) -> Optional[Report]:
        query = (
            select(Report)
            .where(
                and_(
                    Report.report_type == ReportType.WEEKLY,
                    Report.status == ReportStatus.COMPLETED,
                )
            )
            .order_by(desc(Report.created_at))
            .limit(1)
        )
        if camera_id:
            query = query.where(Report.camera_id == camera_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
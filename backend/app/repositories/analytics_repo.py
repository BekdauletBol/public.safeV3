from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, func, text, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.people_count import PeopleCount
from app.db.models.analytics import HourlyAggregate, DailyAggregate


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Raw Counts ────────────────────────────────────────────────────────────

    async def insert_count(
        self,
        camera_id: UUID,
        count: int,
        entering: int = 0,
        exiting: int = 0,
        confidence_avg: Optional[float] = None,
        track_ids: Optional[list] = None,
        roi_filtered: bool = False,
        timestamp: Optional[datetime] = None,
    ) -> PeopleCount:
        record = PeopleCount(
            camera_id=camera_id,
            timestamp=timestamp or datetime.utcnow(),
            count=count,
            entering=entering,
            exiting=exiting,
            confidence_avg=confidence_avg,
            track_ids=track_ids or [],
            roi_filtered=roi_filtered,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get_latest_count(self, camera_id: UUID) -> Optional[PeopleCount]:
        result = await self.db.execute(
            select(PeopleCount)
            .where(PeopleCount.camera_id == camera_id)
            .order_by(desc(PeopleCount.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_counts_range(
        self,
        camera_id: UUID,
        start: datetime,
        end: datetime,
        limit: int = 1000,
    ) -> List[PeopleCount]:
        result = await self.db.execute(
            select(PeopleCount)
            .where(
                and_(
                    PeopleCount.camera_id == camera_id,
                    PeopleCount.timestamp >= start,
                    PeopleCount.timestamp <= end,
                )
            )
            .order_by(PeopleCount.timestamp)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ─── Hourly Aggregates ─────────────────────────────────────────────────────

    async def upsert_hourly_aggregate(
        self,
        camera_id: UUID,
        hour_bucket: datetime,
    ) -> HourlyAggregate:
        """Compute and upsert hourly aggregate from raw data."""
        hour_start = hour_bucket.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)

        stats = await self.db.execute(
            select(
                func.avg(PeopleCount.count).label("avg_count"),
                func.max(PeopleCount.count).label("max_count"),
                func.min(PeopleCount.count).label("min_count"),
                func.sum(PeopleCount.entering).label("total_entering"),
                func.sum(PeopleCount.exiting).label("total_exiting"),
                func.count(PeopleCount.id).label("sample_count"),
            ).where(
                and_(
                    PeopleCount.camera_id == camera_id,
                    PeopleCount.timestamp >= hour_start,
                    PeopleCount.timestamp < hour_end,
                )
            )
        )
        row = stats.one()

        # Check existing
        existing = await self.db.execute(
            select(HourlyAggregate).where(
                and_(
                    HourlyAggregate.camera_id == camera_id,
                    HourlyAggregate.hour_bucket == hour_start,
                )
            )
        )
        agg = existing.scalar_one_or_none()

        if agg is None:
            agg = HourlyAggregate(camera_id=camera_id, hour_bucket=hour_start)
            self.db.add(agg)

        agg.avg_count = float(row.avg_count or 0)
        agg.max_count = int(row.max_count or 0)
        agg.min_count = int(row.min_count or 0)
        agg.total_entering = int(row.total_entering or 0)
        agg.total_exiting = int(row.total_exiting or 0)
        agg.sample_count = int(row.sample_count or 0)
        agg.updated_at = datetime.utcnow()

        await self.db.flush()
        return agg

    async def get_hourly_aggregates(
        self,
        camera_id: UUID,
        start: datetime,
        end: datetime,
    ) -> List[HourlyAggregate]:
        result = await self.db.execute(
            select(HourlyAggregate)
            .where(
                and_(
                    HourlyAggregate.camera_id == camera_id,
                    HourlyAggregate.hour_bucket >= start,
                    HourlyAggregate.hour_bucket <= end,
                )
            )
            .order_by(HourlyAggregate.hour_bucket)
        )
        return list(result.scalars().all())

    # ─── Daily Aggregates ──────────────────────────────────────────────────────

    async def upsert_daily_aggregate(
        self,
        camera_id: UUID,
        day_bucket: datetime,
    ) -> DailyAggregate:
        day_start = day_bucket.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # Get hourly aggregates for this day
        hourly = await self.get_hourly_aggregates(camera_id, day_start, day_end)

        if not hourly:
            return None

        avg_count = sum(h.avg_count for h in hourly) / len(hourly)
        max_count = max(h.max_count for h in hourly)
        min_count = min(h.min_count for h in hourly)
        total_entering = sum(h.total_entering for h in hourly)
        total_exiting = sum(h.total_exiting for h in hourly)
        sample_count = sum(h.sample_count for h in hourly)

        # Peak hour = hour with highest avg
        peak_h = max(hourly, key=lambda h: h.avg_count)
        peak_hour = peak_h.hour_bucket.hour

        existing = await self.db.execute(
            select(DailyAggregate).where(
                and_(
                    DailyAggregate.camera_id == camera_id,
                    DailyAggregate.day_bucket == day_start,
                )
            )
        )
        agg = existing.scalar_one_or_none()

        if agg is None:
            agg = DailyAggregate(camera_id=camera_id, day_bucket=day_start)
            self.db.add(agg)

        agg.avg_count = avg_count
        agg.max_count = max_count
        agg.min_count = min_count
        agg.total_entering = total_entering
        agg.total_exiting = total_exiting
        agg.peak_hour = peak_hour
        agg.sample_count = sample_count
        agg.updated_at = datetime.utcnow()

        await self.db.flush()
        return agg

    async def get_daily_aggregates(
        self,
        camera_id: UUID,
        start: datetime,
        end: datetime,
    ) -> List[DailyAggregate]:
        result = await self.db.execute(
            select(DailyAggregate)
            .where(
                and_(
                    DailyAggregate.camera_id == camera_id,
                    DailyAggregate.day_bucket >= start,
                    DailyAggregate.day_bucket <= end,
                )
            )
            .order_by(DailyAggregate.day_bucket)
        )
        return list(result.scalars().all())

    async def get_all_cameras_latest(self) -> List[Dict[str, Any]]:
        """Get latest count for every camera."""
        subquery = (
            select(
                PeopleCount.camera_id,
                func.max(PeopleCount.timestamp).label("max_ts"),
            )
            .group_by(PeopleCount.camera_id)
            .subquery()
        )

        result = await self.db.execute(
            select(PeopleCount, Camera.name, Camera.location)
            .join(subquery, and_(
                PeopleCount.camera_id == subquery.c.camera_id,
                PeopleCount.timestamp == subquery.c.max_ts,
            ))
            .join(Camera, Camera.id == PeopleCount.camera_id)
        )

        rows = result.all()
        return [
            {
                "camera_id": str(r.PeopleCount.camera_id),
                "camera_name": r.name,
                "camera_location": r.location,
                "count": r.PeopleCount.count,
                "timestamp": r.PeopleCount.timestamp.isoformat(),
            }
            for r in rows
        ]

    async def get_system_totals(self, since: datetime) -> Dict[str, Any]:
        result = await self.db.execute(
            select(
                func.sum(PeopleCount.entering).label("total_entering"),
                func.sum(PeopleCount.exiting).label("total_exiting"),
                func.avg(PeopleCount.count).label("avg_concurrent"),
                func.max(PeopleCount.count).label("peak_count"),
            ).where(PeopleCount.timestamp >= since)
        )
        row = result.one()
        return {
            "total_entering": int(row.total_entering or 0),
            "total_exiting": int(row.total_exiting or 0),
            "avg_concurrent": float(row.avg_concurrent or 0),
            "peak_count": int(row.peak_count or 0),
        }
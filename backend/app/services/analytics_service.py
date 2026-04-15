from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID
from loguru import logger

from app.db.models.analytics import AnalyticsRecord, HourlyAggregate, DailyAggregate
from app.db.models.camera import Camera


class AnalyticsService:
    """Supports both instance-style (AnalyticsService(db)) and legacy static calls."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Instance methods (used by v1 router) ───────────────────────────────────

    async def get_time_series(
        self,
        camera_id: UUID,
        start: datetime,
        end: datetime,
        granularity: str = "hourly",
    ) -> List[Dict[str, Any]]:
        """Return time-series data using pre-aggregated tables."""
        from app.repositories.analytics_repo import AnalyticsRepository
        repo = AnalyticsRepository(self.db)

        if granularity == "daily":
            rows = await repo.get_daily_aggregates(camera_id, start, end)
            return [
                {
                    "day_bucket": r.day_bucket.isoformat(),
                    "avg_count": r.avg_count,
                    "max_count": r.max_count,
                    "min_count": r.min_count,
                    "total_entering": r.total_entering,
                    "total_exiting": r.total_exiting,
                    "peak_hour": r.peak_hour,
                    "sample_count": r.sample_count,
                }
                for r in rows
            ]
        else:  # hourly (default) or raw
            rows = await repo.get_hourly_aggregates(camera_id, start, end)
            return [
                {
                    "hour_bucket": r.hour_bucket.isoformat(),
                    "avg_count": r.avg_count,
                    "max_count": r.max_count,
                    "min_count": r.min_count,
                    "total_entering": r.total_entering,
                    "total_exiting": r.total_exiting,
                    "sample_count": r.sample_count,
                }
                for r in rows
            ]

    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Current live counts + today totals for all cameras."""
        from app.repositories.analytics_repo import AnalyticsRepository
        repo = AnalyticsRepository(self.db)

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        totals = await repo.get_system_totals(since=today_start)

        latest = await repo.get_all_cameras_latest()
        return {
            "today": totals,
            "cameras": latest,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def generate_ai_insights(
        self,
        camera_id: UUID,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """Generate simple rule-based insights for a camera over a period."""
        rows = await self.get_time_series(camera_id, start, end, "hourly")
        if not rows:
            return {"summary": "No data available for this period.", "highlights": []}

        total_entering = sum(r.get("total_entering", 0) or 0 for r in rows)
        total_exiting  = sum(r.get("total_exiting", 0) or 0 for r in rows)
        peak_row = max(rows, key=lambda r: r.get("avg_count", 0))
        peak_ts  = peak_row.get("hour_bucket") or peak_row.get("day_bucket", "")
        peak_val = peak_row.get("avg_count", 0)

        highlights = []
        if total_entering:
            highlights.append(f"Total entering: {total_entering:,}")
        if total_exiting:
            highlights.append(f"Total exiting: {total_exiting:,}")
        if peak_ts:
            highlights.append(f"Peak at {peak_ts[:16]}: {peak_val:.1f} avg people")

        summary = (
            f"Period {start.date()} – {end.date()}: "
            f"{len(rows)} data points, "
            f"peak avg {peak_val:.1f} people."
        )
        return {"summary": summary, "highlights": highlights}

    async def run_hourly_aggregation(self) -> int:
        """Aggregate the previous full hour for all cameras."""
        from app.repositories.analytics_repo import AnalyticsRepository
        repo = AnalyticsRepository(self.db)

        now = datetime.utcnow()
        prev_hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

        cameras_result = await self.db.execute(select(Camera))
        cameras = cameras_result.scalars().all()

        count = 0
        for cam in cameras:
            try:
                await repo.upsert_hourly_aggregate(cam.id, prev_hour)
                count += 1
            except Exception as e:
                logger.warning(f"Hourly agg failed for camera {cam.id}: {e}")
        await self.db.commit()
        logger.info(f"Hourly aggregation: processed {count} cameras for {prev_hour}")
        return count

    async def run_daily_aggregation(self) -> int:
        """Aggregate yesterday for all cameras."""
        from app.repositories.analytics_repo import AnalyticsRepository
        repo = AnalyticsRepository(self.db)

        yesterday = (datetime.utcnow() - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        cameras_result = await self.db.execute(select(Camera))
        cameras = cameras_result.scalars().all()

        count = 0
        for cam in cameras:
            try:
                result = await repo.upsert_daily_aggregate(cam.id, yesterday)
                if result:
                    count += 1
            except Exception as e:
                logger.warning(f"Daily agg failed for camera {cam.id}: {e}")
        await self.db.commit()
        logger.info(f"Daily aggregation: processed {count} cameras for {yesterday.date()}")
        return count


    @staticmethod
    async def record_count(
        db: AsyncSession,
        camera_id: int,
        people_count: int,
        confidence_avg: float = 0.0,
    ):
        record = AnalyticsRecord(
            camera_id=camera_id,
            people_count=people_count,
            confidence_avg=confidence_avg,
            period_type="realtime",
        )
        db.add(record)
        await db.flush()

    @staticmethod
    async def get_realtime_counts(db: AsyncSession) -> Dict[int, int]:
        cutoff = datetime.utcnow() - timedelta(seconds=10)
        result = await db.execute(
            select(
                AnalyticsRecord.camera_id,
                func.avg(AnalyticsRecord.people_count).label("avg_count"),
            )
            .where(AnalyticsRecord.timestamp >= cutoff)
            .group_by(AnalyticsRecord.camera_id)
        )
        return {row.camera_id: int(row.avg_count) for row in result}

    @staticmethod
    async def get_hourly_data(
        db: AsyncSession,
        camera_id: int,
        start: datetime,
        end: datetime,
    ) -> List[Dict]:
        result = await db.execute(
            select(
                func.date_trunc("hour", AnalyticsRecord.timestamp).label("hour"),
                func.avg(AnalyticsRecord.people_count).label("avg"),
                func.max(AnalyticsRecord.people_count).label("max"),
                func.sum(AnalyticsRecord.people_count).label("total"),
                func.count(AnalyticsRecord.id).label("samples"),
            )
            .where(
                and_(
                    AnalyticsRecord.camera_id == camera_id,
                    AnalyticsRecord.timestamp >= start,
                    AnalyticsRecord.timestamp <= end,
                )
            )
            .group_by(func.date_trunc("hour", AnalyticsRecord.timestamp))
            .order_by(func.date_trunc("hour", AnalyticsRecord.timestamp))
        )
        rows = result.all()
        return [
            {
                "hour": row.hour.isoformat() if row.hour else None,
                "avg": round(float(row.avg), 2) if row.avg else 0,
                "max": row.max or 0,
                "total": row.total or 0,
                "samples": row.samples or 0,
            }
            for row in rows
        ]

    @staticmethod
    async def get_daily_data(
        db: AsyncSession,
        camera_id: int,
        days: int = 7,
    ) -> List[Dict]:
        start = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(
                func.date_trunc("day", AnalyticsRecord.timestamp).label("day"),
                func.avg(AnalyticsRecord.people_count).label("avg"),
                func.max(AnalyticsRecord.people_count).label("max"),
                func.sum(AnalyticsRecord.people_count).label("total"),
            )
            .where(
                and_(
                    AnalyticsRecord.camera_id == camera_id,
                    AnalyticsRecord.timestamp >= start,
                )
            )
            .group_by(func.date_trunc("day", AnalyticsRecord.timestamp))
            .order_by(func.date_trunc("day", AnalyticsRecord.timestamp))
        )
        rows = result.all()
        return [
            {
                "date": row.day.strftime("%Y-%m-%d") if row.day else None,
                "avg": round(float(row.avg), 2) if row.avg else 0,
                "max": row.max or 0,
                "total": row.total or 0,
            }
            for row in rows
        ]

    @staticmethod
    async def get_peak_hours(db: AsyncSession, camera_id: int, days: int = 7) -> Dict:
        start = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(
                func.extract("hour", AnalyticsRecord.timestamp).label("hour"),
                func.avg(AnalyticsRecord.people_count).label("avg_count"),
            )
            .where(
                and_(
                    AnalyticsRecord.camera_id == camera_id,
                    AnalyticsRecord.timestamp >= start,
                )
            )
            .group_by(func.extract("hour", AnalyticsRecord.timestamp))
            .order_by(func.avg(AnalyticsRecord.people_count).desc())
        )
        rows = result.all()
        peak_hours = [{"hour": int(row.hour), "avg": round(float(row.avg_count), 2)} for row in rows]
        return {
            "peak_hours": peak_hours[:3],
            "distribution": peak_hours,
        }

    @staticmethod
    async def get_weekly_summary(
        db: AsyncSession,
        start: datetime,
        end: datetime,
    ) -> Dict:
        cameras_result = await db.execute(select(Camera).where(Camera.is_active == True))
        cameras = cameras_result.scalars().all()

        summary = {
            "total_cameras": len(cameras),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "cameras": [],
            "total_traffic": 0,
            "peak_hour": None,
        }

        all_hour_data = []

        for camera in cameras:
            hourly = await AnalyticsService.get_hourly_data(db, camera.id, start, end)
            peaks = await AnalyticsService.get_peak_hours(db, camera.id, 7)
            total = sum(h["total"] for h in hourly)
            avg = round(sum(h["avg"] for h in hourly) / len(hourly), 2) if hourly else 0.0
            max_count = max((h["max"] for h in hourly), default=0)

            summary["cameras"].append({
                "camera_id": camera.id,
                "camera_name": camera.name,
                "address": camera.address,
                "total_traffic": total,
                "avg_count": avg,
                "max_count": max_count,
                "hourly_breakdown": hourly,
                "peak_hours": peaks["peak_hours"],
            })
            summary["total_traffic"] += total
            all_hour_data.extend(peaks["distribution"])

        if all_hour_data:
            peak = max(all_hour_data, key=lambda x: x["avg"])
            summary["peak_hour"] = peak["hour"]

        return summary

    @staticmethod
    async def reset_weekly_stats(db: AsyncSession, before: datetime):
        from sqlalchemy import delete
        await db.execute(
            delete(AnalyticsRecord).where(AnalyticsRecord.timestamp < before)
        )
        await db.commit()
        logger.info(f"Weekly stats reset: deleted records before {before}")

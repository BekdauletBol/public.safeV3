"""
Analytics endpoints — includes on-demand graph generation (NEW FEATURE).
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.analytics_service import AnalyticsService
from app.services.graph_service import (
    generate_traffic_graph, generate_bar_summary,
    generate_hourly_heatmap, png_to_base64,
)

router = APIRouter()


def _parse_datetime(dt_str: Optional[str], default: datetime) -> datetime:
    if not dt_str:
        return default
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid datetime: {dt_str}")


# ─── Time-series data ─────────────────────────────────────────────────────────

@router.get("/time-series/{camera_id}")
async def get_time_series(
    camera_id: UUID,
    from_dt: Optional[str] = Query(None, alias="from"),
    to_dt:   Optional[str] = Query(None, alias="to"),
    granularity: str = Query("hourly", pattern="^(raw|hourly|daily)$"),
    db: AsyncSession = Depends(get_db),
):
    """Fetch time-series data for a camera."""
    now = datetime.utcnow()
    start = _parse_datetime(from_dt, now - timedelta(days=7))
    end   = _parse_datetime(to_dt,   now)

    svc = AnalyticsService(db)
    data = await svc.get_time_series(camera_id, start, end, granularity)
    return {"camera_id": str(camera_id), "granularity": granularity, "data": data}


@router.get("/dashboard")
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Overall dashboard summary — current counts, today totals, etc."""
    svc = AnalyticsService(db)
    return await svc.get_dashboard_summary()


@router.get("/insights/{camera_id}")
async def get_insights(
    camera_id: UUID,
    from_dt: Optional[str] = Query(None, alias="from"),
    to_dt:   Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    """AI-generated insights for a camera over a period."""
    now = datetime.utcnow()
    start = _parse_datetime(from_dt, now - timedelta(days=7))
    end   = _parse_datetime(to_dt,   now)
    svc = AnalyticsService(db)
    return await svc.generate_ai_insights(camera_id, start, end)


# ─── ON-DEMAND GRAPH GENERATION (NEW FEATURE) ────────────────────────────────

@router.get("/generate")
async def generate_analytics_graph(
    camera_id: Optional[str] = Query(None),
    from_dt:   Optional[str] = Query(None, alias="from"),
    to_dt:     Optional[str] = Query(None, alias="to"),
    granularity: str = Query("hourly", pattern="^(raw|hourly|daily)$"),
    format: str = Query("json", pattern="^(json|png)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    On-demand analytics graph generation.

    GET /analytics/generate?camera_id=<uuid>&from=2024-01-01&to=2024-01-07&granularity=hourly

    Returns:
        format=json  → structured data + base64 chart image
        format=png   → raw PNG image bytes
    """
    now = datetime.utcnow()
    start = _parse_datetime(from_dt, now - timedelta(days=7))
    end   = _parse_datetime(to_dt,   now)

    svc = AnalyticsService(db)

    # Fetch time-series data
    if camera_id:
        try:
            cam_uuid = UUID(camera_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid camera_id UUID")

        time_series = await svc.get_time_series(cam_uuid, start, end, granularity)
        insights    = await svc.generate_ai_insights(cam_uuid, start, end)
        camera_name = camera_id  # will be enriched below

        # Get camera name from DB
        from app.repositories.camera_repo import CameraRepository
        from app.db.session import get_db
        cam_repo = CameraRepository(db)
        cam = await cam_repo.get_by_id(cam_uuid)
        camera_name = cam.name if cam else str(cam_uuid)
        camera_addr = cam.street_address or cam.location if cam else ""
    else:
        # System-wide: aggregate all cameras
        time_series = []
        insights = {}
        camera_name = "All Cameras"
        camera_addr = "System"

    # ── Generate graph PNG ───────────────────────────────────────────────────
    span_hours = (end - start).total_seconds() / 3600
    graph_title = (
        f"Traffic: {start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    )

    try:
        png_bytes = generate_traffic_graph(
            time_series=time_series,
            camera_name=camera_name,
            title=graph_title,
            granularity=granularity,
            figsize=(12, 5),
            dpi=130,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph generation failed: {e}")

    if format == "png":
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Cache-Control": "no-cache"},
        )

    # JSON response with base64 graph + analytics data
    return {
        "camera_id": camera_id,
        "camera_name": camera_name,
        "camera_address": camera_addr,
        "period": {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "granularity": granularity,
        },
        "graph": {
            "base64": png_to_base64(png_bytes),
            "format": "png",
            "size_bytes": len(png_bytes),
        },
        "summary": {
            "data_points": len(time_series),
            "total_entering": sum(
                r.get("total_entering", r.get("entering", 0)) or 0
                for r in time_series
            ),
            "total_exiting": sum(
                r.get("total_exiting", r.get("exiting", 0)) or 0
                for r in time_series
            ),
            "peak_count": max(
                (r.get("max_count", r.get("count", 0)) or 0 for r in time_series),
                default=0,
            ),
            "avg_count": (
                sum(r.get("avg_count", r.get("count", 0)) or 0 for r in time_series)
                / max(len(time_series), 1)
            ),
        },
        "insights": insights,
        "data": time_series,
    }


@router.get("/generate/heatmap/{camera_id}")
async def generate_heatmap(
    camera_id: UUID,
    from_dt: Optional[str] = Query(None, alias="from"),
    to_dt:   Optional[str] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    """Generate a weekly hourly heatmap for a camera."""
    now = datetime.utcnow()
    start = _parse_datetime(from_dt, now - timedelta(days=7))
    end   = _parse_datetime(to_dt, now)

    from app.repositories.analytics_repo import AnalyticsRepository
    repo = AnalyticsRepository(db)
    hourly = await repo.get_hourly_aggregates(camera_id, start, end)

    # Build day × hour matrix
    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    hourly_by_day = {d: [0.0] * 24 for d in day_names}
    for h in hourly:
        day = h.hour_bucket.strftime("%A")
        hr  = h.hour_bucket.hour
        if day in hourly_by_day:
            hourly_by_day[day][hr] = h.avg_count

    png_bytes = generate_hourly_heatmap(
        hourly_by_day,
        title=f"Weekly Heatmap — {start.strftime('%b %d')} to {end.strftime('%b %d')}",
    )
    return {
        "camera_id": str(camera_id),
        "graph": {"base64": png_to_base64(png_bytes), "format": "png"},
    }


# ─── Aggregation triggers ─────────────────────────────────────────────────────

@router.post("/aggregate/hourly")
async def trigger_hourly_agg(db: AsyncSession = Depends(get_db)):
    svc = AnalyticsService(db)
    count = await svc.run_hourly_aggregation()
    return {"processed": count}


@router.post("/aggregate/daily")
async def trigger_daily_agg(db: AsyncSession = Depends(get_db)):
    svc = AnalyticsService(db)
    count = await svc.run_daily_aggregation()
    return {"processed": count}
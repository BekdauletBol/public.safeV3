"""
Reports endpoints — includes on-demand generation (NEW FEATURE).
"""

import os
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.report_service import ReportService
from app.core.security import get_current_admin
from pydantic import BaseModel


router = APIRouter()


def _parse_dt(dt_str: Optional[str], default: datetime) -> datetime:
    if not dt_str:
        return default
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid datetime: {dt_str}")


def _report_to_dict(report) -> dict:
    def _val(field):
        """Return .value if it's an enum, otherwise the raw field."""
        return field.value if hasattr(field, "value") else field

    return {
        "id": str(report.id),
        "camera_id": str(getattr(report, "camera_id", None)) if getattr(report, "camera_id", None) else None,
        "report_type": _val(getattr(report, "report_type", None)),
        "status": _val(getattr(report, "status", None)),
        "title": getattr(report, "title", None),
        "summary": getattr(report, "summary", getattr(report, "ai_insights", None)),
        "insights": getattr(report, "insights", None),
        "period_start": report.period_start.isoformat() if getattr(report, "period_start", None) else None,
        "period_end":   report.period_end.isoformat()   if getattr(report, "period_end", None)   else None,
        "file_path": getattr(report, "file_path", None),
        "file_size_bytes": getattr(report, "file_size_bytes", None),
        "created_at":   report.created_at.isoformat()   if getattr(report, "created_at", None)   else None,
        "completed_at": report.completed_at.isoformat() if getattr(report, "completed_at", None) else None,
        "error_message": getattr(report, "error_message", None),
        "has_file": bool(
            getattr(report, "file_path", None) and os.path.exists(report.file_path)
        ),
    }



# ─── List ──────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_reports(
    camera_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    svc = ReportService(db)
    cam_uuid = UUID(camera_id) if camera_id else None
    reports = await svc.list_reports(camera_id=cam_uuid, limit=limit)
    return [_report_to_dict(r) for r in reports]


@router.get("/{report_id}")
async def get_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = ReportService(db)
    report = await svc.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_to_dict(report)


# ─── ON-DEMAND GENERATION (NEW FEATURE) ──────────────────────────────────────

class GenerateReportRequest(BaseModel):
    camera_id: Optional[str] = None
    from_dt:   Optional[str] = None
    to_dt:     Optional[str] = None
    granularity: str = "hourly"


@router.post("/generate")
async def generate_report_on_demand(
    payload: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    """
    On-demand report generation.
    Generates graph + embeds it in PDF + stores metadata in DB.
    Returns the completed report immediately (synchronous generation).
    """
    now = datetime.utcnow()
    start = _parse_dt(payload.from_dt, now - timedelta(days=7))
    end   = _parse_dt(payload.to_dt,   now)

    cam_uuid = UUID(payload.camera_id) if payload.camera_id else None

    svc = ReportService(db)
    report = await svc.create_on_demand_report(
        camera_id=cam_uuid,
        start=start,
        end=end,
        granularity=payload.granularity,
    )
    await db.commit()

    result = _report_to_dict(report)

    # Add download URL if file was created
    if report.file_path and os.path.exists(report.file_path):
        filename = os.path.basename(report.file_path)
        result["download_url"] = f"/reports/{filename}"

    return result


@router.post("/generate/weekly")
async def generate_weekly(
    camera_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    cam_uuid = UUID(camera_id) if camera_id else None
    svc = ReportService(db)
    report = await svc.create_weekly_report(camera_id=cam_uuid)
    await db.commit()
    result = _report_to_dict(report)
    if report.file_path and os.path.exists(report.file_path):
        result["download_url"] = f"/reports/{os.path.basename(report.file_path)}"
    return result


@router.post("/generate/daily")
async def generate_daily(
    camera_id: Optional[str] = None,
    date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    cam_uuid = UUID(camera_id) if camera_id else None
    day = _parse_dt(date, datetime.utcnow()) if date else None
    svc = ReportService(db)
    report = await svc.create_daily_report(camera_id=cam_uuid, date=day)
    await db.commit()
    result = _report_to_dict(report)
    if report.file_path and os.path.exists(report.file_path):
        result["download_url"] = f"/reports/{os.path.basename(report.file_path)}"
    return result


# ─── Download ─────────────────────────────────────────────────────────────────

@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    svc = ReportService(db)
    report = await svc.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(
        path=report.file_path,
        filename=os.path.basename(report.file_path),
        media_type="application/pdf",
    )


@router.get("/{report_id}/export-csv")
async def export_csv(
    report_id: UUID,
    granularity: str = "hourly",
    db: AsyncSession = Depends(get_db),
):
    svc = ReportService(db)
    report = await svc.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    cam_uuid = report.camera_id
    csv_content = await svc.export_csv(
        cam_uuid, report.period_start, report.period_end, granularity
    )
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report_{report_id}.csv"'},
    )
import os
import csv
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID
from loguru import logger

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.report import Report
from app.services.analytics_service import AnalyticsService


class ReportService:
    """Instance-based service used by the v1 reports router."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_reports(
        self,
        camera_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Report]:
        query = select(Report).order_by(desc(Report.created_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_report(self, report_id: UUID) -> Optional[Report]:
        # The old model uses Integer PK; cast UUID → int for compatibility
        try:
            rid = int(str(report_id).replace("-", "")[:8], 16) % (2**31)
        except Exception:
            return None
        result = await self.db.execute(select(Report).where(Report.id == rid))
        report = result.scalar_one_or_none()
        # Fallback: try raw int if UUID happened to encode a small int
        if report is None:
            try:
                rid2 = int(report_id)
                result2 = await self.db.execute(select(Report).where(Report.id == rid2))
                report = result2.scalar_one_or_none()
            except Exception:
                pass
        return report

    async def create_on_demand_report(
        self,
        camera_id: Optional[UUID],
        start: datetime,
        end: datetime,
        granularity: str = "hourly",
    ) -> Report:
        """Generate analytics summary + PDF and persist as a Report row."""
        svc = AnalyticsService(self.db)

        if camera_id:
            time_series = await svc.get_time_series(camera_id, start, end, granularity)
            insights_data = await svc.generate_ai_insights(camera_id, start, end)
        else:
            time_series = []
            insights_data = {}

        summary = {
            "total_cameras": 1 if camera_id else 0,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "cameras": [],
            "total_traffic": sum(
                r.get("total_entering", 0) or 0 for r in time_series
            ),
            "peak_hour": None,
            "ai_insights": insights_data.get("summary", ""),
        }

        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(settings.REPORTS_DIR, f"report_{ts}.pdf")

        try:
            await generate_pdf_report(summary, pdf_path)
        except Exception as e:
            logger.warning(f"PDF generation skipped: {e}")
            pdf_path = None

        report = Report(
            title=f"On-Demand Report {start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}",
            report_type="custom",
            period_start=start,
            period_end=end,
            file_path=pdf_path,
            file_format="pdf",
            status="ready",
            ai_insights=insights_data.get("summary", ""),
        )
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def create_weekly_report(
        self,
        camera_id: Optional[UUID] = None,
    ) -> Report:
        """Thin wrapper around the legacy create_weekly_report function."""
        return await create_weekly_report(self.db)

    async def create_daily_report(
        self,
        camera_id: Optional[UUID] = None,
        date: Optional[datetime] = None,
    ) -> Report:
        target = date or datetime.utcnow()
        day_start = target.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = target.replace(hour=23, minute=59, second=59, microsecond=0)

        svc = AnalyticsService(self.db)
        if camera_id:
            time_series = await svc.get_time_series(camera_id, day_start, day_end, "hourly")
            insights_data = await svc.generate_ai_insights(camera_id, day_start, day_end)
        else:
            time_series = []
            insights_data = {}

        summary = {
            "total_cameras": 1 if camera_id else 0,
            "period_start": day_start.isoformat(),
            "period_end":   day_end.isoformat(),
            "cameras": [],
            "total_traffic": sum(r.get("total_entering", 0) or 0 for r in time_series),
            "peak_hour": None,
            "ai_insights": insights_data.get("summary", ""),
        }

        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(settings.REPORTS_DIR, f"daily_report_{ts}.pdf")

        try:
            await generate_pdf_report(summary, pdf_path)
        except Exception as e:
            logger.warning(f"PDF generation skipped: {e}")
            pdf_path = None

        report = Report(
            title=f"Daily Report {target.strftime('%b %d, %Y')}",
            report_type="daily",
            period_start=day_start,
            period_end=day_end,
            file_path=pdf_path,
            file_format="pdf",
            status="ready",
            ai_insights=insights_data.get("summary", ""),
        )
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def export_csv(
        self,
        camera_id: Optional[UUID],
        start: datetime,
        end: datetime,
        granularity: str = "hourly",
    ) -> str:
        """Return CSV content as a string."""
        svc = AnalyticsService(self.db)
        rows = await svc.get_time_series(camera_id, start, end, granularity) if camera_id else []

        buf = io.StringIO()
        writer = csv.writer(buf)
        if granularity == "daily":
            writer.writerow(["day_bucket", "avg_count", "max_count", "total_entering", "total_exiting"])
            for r in rows:
                writer.writerow([
                    r.get("day_bucket", ""), r.get("avg_count", 0),
                    r.get("max_count", 0), r.get("total_entering", 0), r.get("total_exiting", 0),
                ])
        else:
            writer.writerow(["hour_bucket", "avg_count", "max_count", "total_entering", "total_exiting"])
            for r in rows:
                writer.writerow([
                    r.get("hour_bucket", ""), r.get("avg_count", 0),
                    r.get("max_count", 0), r.get("total_entering", 0), r.get("total_exiting", 0),
                ])
        return buf.getvalue()




def generate_ai_insights(summary: Dict) -> str:
    total = summary.get("total_traffic", 0)
    peak_hour = summary.get("peak_hour")
    cameras = summary.get("cameras", [])

    insights = []
    insights.append(f"Weekly surveillance summary for {summary['period_start'][:10]} to {summary['period_end'][:10]}.")

    if total > 0:
        insights.append(f"Total foot traffic recorded: {total:,} people across {len(cameras)} camera(s).")

    if peak_hour is not None:
        period = "morning" if 6 <= peak_hour < 12 else "afternoon" if 12 <= peak_hour < 18 else "evening" if 18 <= peak_hour < 22 else "night"
        insights.append(f"Peak activity was observed at {peak_hour:02d}:00 ({period} hours).")

    busiest = max(cameras, key=lambda c: c["total_traffic"], default=None) if cameras else None
    if busiest:
        insights.append(f"The busiest location was '{busiest['camera_name']}' at {busiest['address']} with {busiest['total_traffic']:,} total counts.")

    quietest = min(cameras, key=lambda c: c["total_traffic"], default=None) if cameras and len(cameras) > 1 else None
    if quietest and quietest != busiest:
        insights.append(f"The least active location was '{quietest['camera_name']}' with {quietest['total_traffic']:,} total counts.")

    avg_total = sum(c["avg_count"] for c in cameras) / len(cameras) if cameras else 0
    if avg_total > 50:
        insights.append("High average occupancy detected — consider increasing patrol frequency during peak hours.")
    elif avg_total > 20:
        insights.append("Moderate traffic levels observed. Current monitoring coverage appears adequate.")
    else:
        insights.append("Low traffic levels recorded this week. System is operating in low-load mode.")

    return " ".join(insights)


async def generate_pdf_report(summary: Dict, file_path: str):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#1a1a2e"), alignment=TA_CENTER, spaceAfter=6)
        sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#666666"), alignment=TA_CENTER, spaceAfter=20)
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#16213e"), spaceBefore=14, spaceAfter=6)
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)

        story = []

        story.append(Paragraph("public.safeV3", title_style))
        story.append(Paragraph("Weekly Surveillance Intelligence Report", sub_style))
        story.append(Paragraph(f"Period: {summary['period_start'][:10]} → {summary['period_end'][:10]}", sub_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0f3460")))
        story.append(Spacer(1, 0.4*cm))

        # Summary table
        story.append(Paragraph("Executive Summary", h2_style))
        summary_data = [
            ["Metric", "Value"],
            ["Total Cameras", str(summary["total_cameras"])],
            ["Total Traffic (week)", f"{summary['total_traffic']:,}"],
            ["Peak Hour", f"{summary['peak_hour']:02d}:00" if summary.get("peak_hour") is not None else "N/A"],
            ["Report Generated", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
        ]
        t = Table(summary_data, colWidths=[8*cm, 8*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

        # Per camera
        story.append(Paragraph("Per-Camera Analytics", h2_style))
        for cam in summary.get("cameras", []):
            story.append(Paragraph(f"📷 {cam['camera_name']} — {cam['address']}", body_style))
            cam_data = [
                ["Total Traffic", "Avg Count", "Max Count"],
                [str(cam["total_traffic"]), str(cam["avg_count"]), str(cam["max_count"])],
            ]
            ct = Table(cam_data, colWidths=[5.3*cm, 5.3*cm, 5.3*cm])
            ct.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f4fd")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(ct)
            story.append(Spacer(1, 0.2*cm))

        # AI insights
        story.append(Paragraph("AI-Generated Insights", h2_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dee2e6")))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(summary.get("ai_insights", "No insights available."), body_style))

        doc.build(story)
        logger.info(f"PDF report generated: {file_path}")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise


async def generate_csv_report(summary: Dict, file_path: str):
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Weekly Report", summary["period_start"][:10], "to", summary["period_end"][:10]])
        writer.writerow([])
        writer.writerow(["Camera ID", "Camera Name", "Address", "Total Traffic", "Avg Count", "Max Count"])
        for cam in summary.get("cameras", []):
            writer.writerow([
                cam["camera_id"], cam["camera_name"], cam["address"],
                cam["total_traffic"], cam["avg_count"], cam["max_count"],
            ])
        writer.writerow([])
        writer.writerow(["AI Insights"])
        writer.writerow([summary.get("ai_insights", "")])
    logger.info(f"CSV report generated: {file_path}")


async def create_weekly_report(db) -> Report:
    from app.db.models.report import Report

    now = datetime.utcnow()
    period_end = now
    period_start = now - timedelta(days=7)

    logger.info("Generating weekly report...")

    summary = await AnalyticsService.get_weekly_summary(db, period_start, period_end)
    ai_insights = generate_ai_insights(summary)
    summary["ai_insights"] = ai_insights

    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    ts = now.strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(settings.REPORTS_DIR, f"weekly_report_{ts}.pdf")
    csv_path = os.path.join(settings.REPORTS_DIR, f"weekly_report_{ts}.csv")

    await generate_pdf_report(summary, pdf_path)
    await generate_csv_report(summary, csv_path)

    report = Report(
        title=f"Weekly Report {period_start.strftime('%b %d')} – {period_end.strftime('%b %d, %Y')}",
        report_type="weekly",
        period_start=period_start,
        period_end=period_end,
        file_path=pdf_path,
        file_format="pdf",
        status="ready",
        ai_insights=ai_insights,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    await AnalyticsService.reset_weekly_stats(db, period_start)

    logger.info(f"Weekly report created: ID {report.id}")
    return report

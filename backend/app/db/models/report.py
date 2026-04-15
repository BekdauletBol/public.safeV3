from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.db.session import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    report_type = Column(String(50), default="weekly")  # weekly, daily, custom
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_format = Column(String(10), default="pdf")
    status = Column(String(20), default="pending")  # pending, generating, ready, failed
    ai_insights = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_reset_done = Column(Boolean, default=False)

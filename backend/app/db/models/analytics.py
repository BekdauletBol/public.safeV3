from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class AnalyticsRecord(Base):
    __tablename__ = "analytics_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    people_count = Column(Integer, default=0)
    confidence_avg = Column(Float, default=0.0)
    period_type = Column(String(20), default="realtime")  # realtime, hourly, daily

    camera = relationship("Camera", back_populates="analytics")


class HourlyAggregate(Base):
    __tablename__ = "hourly_aggregates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    hour_start = Column(DateTime(timezone=True), nullable=False, index=True)
    total_count = Column(Integer, default=0)
    avg_count = Column(Float, default=0.0)
    max_count = Column(Integer, default=0)
    min_count = Column(Integer, default=0)
    sample_count = Column(Integer, default=0)


class DailyAggregate(Base):
    __tablename__ = "daily_aggregates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    total_count = Column(Integer, default=0)
    avg_count = Column(Float, default=0.0)
    max_count = Column(Integer, default=0)
    peak_hour = Column(Integer, nullable=True)

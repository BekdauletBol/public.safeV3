import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Index, Boolean, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class PeopleCount(Base):
    """
    TimescaleDB hypertable for raw people count events.
    Partitioned by time (bucket: 1 day).
    """
    __tablename__ = "people_counts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    count = Column(Integer, nullable=False, default=0)
    entering = Column(Integer, default=0)
    exiting = Column(Integer, default=0)

    # Detection metadata
    confidence_avg = Column(Float, nullable=True)
    track_ids = Column(JSON, nullable=True)  # list of active track IDs
    roi_filtered = Column(Boolean, default=False)

    # Relationships
    camera = relationship("Camera", back_populates="people_counts")

    __table_args__ = (
        Index("ix_people_counts_camera_timestamp", "camera_id", "timestamp"),
        Index("ix_people_counts_timestamp", "timestamp"),
    )



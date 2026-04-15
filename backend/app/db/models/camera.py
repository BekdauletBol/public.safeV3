from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from app.db.session import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(255), nullable=False)
    stream_url = Column(Text, nullable=False)
    address = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    fps = Column(Integer, default=15)
    resolution_width = Column(Integer, default=1280)
    resolution_height = Column(Integer, default=720)

    # Fields expected by v1 API (defaults for compatibility)
    detection_confidence = Column(Float, default=0.45)
    model_variant = Column(String(50), default="yolov8n")
    last_count = Column(Integer, default=0)
    last_seen = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    analytics = relationship("AnalyticsRecord", back_populates="camera", cascade="all, delete-orphan")
    people_counts = relationship("PeopleCount", back_populates="camera", cascade="all, delete-orphan")
    roi = relationship("ROIConfig", back_populates="camera", uselist=False, cascade="all, delete-orphan")

    # ── Compatibility aliases ────────────────────────────────────────────────
    # v1 router uses cam.rtsp_url, cam.location, cam.street_address
    @hybrid_property
    def rtsp_url(self):
        return self.stream_url

    @rtsp_url.setter
    def rtsp_url(self, value):
        self.stream_url = value

    @hybrid_property
    def location(self):
        return self.address

    @location.setter
    def location(self, value):
        self.address = value

    @hybrid_property
    def street_address(self):
        return self.address

    @street_address.setter
    def street_address(self, value):
        self.address = value

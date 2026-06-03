from pydantic_settings import BaseSettings
from typing import List, Tuple
import os

class Settings(BaseSettings):
    APP_NAME: str = "public.safe"
    APP_VERSION: str = "3.0.0"
    
    # YOLO Settings
    YOLO_MODEL: str = "yolov8n.pt"
    CONFIDENCE_THRESHOLD: float = 0.30
    
    # Threat Scoring
    ALERT_THRESHOLD_MS: int = 2000
    
    # Mesh Network
    MESH_RADIUS_METERS: float = 150.0
    
    # Processing
    LIFO_QUEUE_MAX: int = 1
    JPEG_QUALITY: int = 65
    TARGET_FPS: int = 30
    
    # Adaptive Zone Modifiers
    NIGHT_MODE_START: int = 22
    NIGHT_MODE_END: int = 6
    RUSH_HOUR_MORNING: Tuple[int, int] = (7, 9)
    RUSH_HOUR_EVENING: Tuple[int, int] = (17, 19)
    
    # Storage
    DATA_DIR: str = "./data"
    TELEMETRY_PATH: str = "./data/telemetry.csv"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()
os.makedirs(settings.DATA_DIR, exist_ok=True)

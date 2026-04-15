from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    APP_NAME: str = "public.safeV3"
    APP_VERSION: str = "3.0.0"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/publicsafe"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@publicsafe.local"

    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"]

    MODEL_PATH: str = "../ml/models/yolov8n.pt"
    INFERENCE_DEVICE: str = "cpu"
    CONFIDENCE_THRESHOLD: float = 0.5
    IOU_THRESHOLD: float = 0.4

    STREAM_RECONNECT_DELAY: int = 5
    STREAM_MAX_RETRIES: int = 10
    STREAM_BUFFER_SIZE: int = 10

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    REPORTS_DIR: str = "./reports"
    REPORT_OUTPUT_DIR: str = "./reports"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

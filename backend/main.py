"""
public.safeV3 — FastAPI application entry point.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocket
from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import router as api_v1_router
from app.services.stream_manager import stream_manager
from app.db.session import engine, Base

from app.api.routes.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────────────────
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Ensure report output dir exists
    os.makedirs(settings.REPORT_OUTPUT_DIR, exist_ok=True)
    os.makedirs("./logs", exist_ok=True)

    # Auto-start active cameras from DB
    try:
        from app.db.session import AsyncSessionLocal
        from app.repositories.camera_repo import CameraRepository
        async with AsyncSessionLocal() as db:
            repo = CameraRepository(db)
            cameras = await repo.get_all(active_only=True)
            for cam in cameras:
                try:
                    await stream_manager.add_camera(
                        camera_id=str(cam.id),
                        rtsp_url=cam.rtsp_url,
                        fps=cam.fps,
                        roi_points=cam.roi,
                        confidence_threshold=cam.detection_confidence,
                    )
                    logger.info(f"Auto-started stream: {cam.name}")
                except Exception as e:
                    logger.error(f"Failed to start stream for {cam.name}: {e}")
    except Exception as e:
        logger.error(f"Camera auto-start failed: {e}")

    logger.info("Application ready")
    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down streams...")
    await stream_manager.stop_all()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered video surveillance and people counting system",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/auth", tags=["Auth-Alias"])


os.makedirs(settings.REPORT_OUTPUT_DIR, exist_ok=True)
app.mount("/reports", StaticFiles(directory=settings.REPORT_OUTPUT_DIR), name="reports")

from app.api.v1.websocket import websocket_endpoint

@app.websocket("/ws/live")
async def websocket_live_route(websocket: WebSocket):
    """Legacy /ws/live endpoint for frontend compatibility"""
    await websocket_endpoint(websocket)


@app.get("/health")
async def health():
    stream_status = await stream_manager.get_all_status()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "active_streams": len(stream_status),
        "streams": stream_status,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
from fastapi import APIRouter

from .auth import router as auth_router
from .cameras import router as cameras_router
from .streams import router as streams_router
from .analytics import router as analytics_router
from .reports import router as reports_router
from .roi import router as roi_router
from .websocket import router as websocket_router

router = APIRouter()

router.include_router(auth_router,      prefix="/auth",      tags=["Auth"])
router.include_router(cameras_router,   prefix="/cameras",   tags=["Cameras"])
router.include_router(streams_router,   prefix="/streams",   tags=["Streams"])
router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
router.include_router(reports_router,   prefix="/reports",   tags=["Reports"])
router.include_router(roi_router,       prefix="/roi",       tags=["ROI"])
router.include_router(websocket_router, prefix="/ws",        tags=["WebSocket"])
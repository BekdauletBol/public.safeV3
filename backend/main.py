from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.websocket import router as ws_router
from backend.api.rest import router as rest_router
from backend.config import settings
from loguru import logger

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="public.safe - Intelligent Pedestrian Safety Network"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(ws_router)
app.include_router(rest_router)

@app.on_event("startup")
async def startup_event():
    logger.info("SafeGrid OS Backend Starting...")

if __name__ == "__main__":
    import uvicorn
    # Use string reference to avoid import issues in some environments
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

"""
API Endpoints
"""
from fastapi import APIRouter
from .tts import router as tts_router
from .roleplay import router as roleplay_router
from .health import router as health_router

router = APIRouter()

# Include sub-routers
router.include_router(tts_router, prefix="/tts", tags=["TTS"])
router.include_router(roleplay_router, prefix="/roleplay", tags=["Role Play"])
router.include_router(health_router, prefix="/health", tags=["Health"])

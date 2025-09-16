"""
Health Check Endpoints
"""
from fastapi import APIRouter
from app.config.settings import settings
from app.utils.logger import get_logger

log = get_logger("health_endpoints")
router = APIRouter()

@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "tts_system": settings.TTS_SYSTEM
    }

@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with system info"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "tts_system": settings.TTS_SYSTEM,
        "llm_model": settings.LLM_MODEL,
        "piper_model": settings.PIPER_MODEL_NAME,
        "database_path": settings.DB_PATH
    }

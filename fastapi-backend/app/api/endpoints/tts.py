"""
TTS Endpoints
"""
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.tts_service import TTSService
from app.utils.logger import get_logger, log_exception

log = get_logger("tts_endpoints")
router = APIRouter()
tts_service = TTSService()

class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    voice: Optional[str] = None
    level: str = "medium"

class TTSResponse(BaseModel):
    status: str
    message: str
    text: str
    language: str
    audio_base64: Optional[str] = None
    audio_size: Optional[int] = None
    audio_format: str = "wav"
    sample_rate: int = 22050
    tts_system: str

@router.post("/synthesize", response_model=TTSResponse)
async def synthesize_text(request: TTSRequest):
    """Synthesize text to speech"""
    try:
        log.info(f"TTS request: {request.text[:50]}...")
        
        # Synthesize audio
        audio_data = await tts_service.synthesize_with_level(
            text=request.text,
            language=request.language,
            voice=request.voice,
            level=request.level
        )
        
        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            tts_info = tts_service.get_tts_info()
            
            return TTSResponse(
                status="success",
                message="TTS synthesis successful",
                text=request.text,
                language=request.language,
                audio_base64=audio_b64,
                audio_size=len(audio_data),
                tts_system=tts_info.get('preferred_system', 'piper')
            )
        else:
            raise HTTPException(status_code=500, detail="TTS synthesis failed")
            
    except Exception as e:
        log_exception(log, "TTS synthesis error", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def test_tts(
    text: str = "Hello, this is a test of the TTS system.",
    language: str = "en",
    voice: Optional[str] = None
):
    """Test TTS functionality"""
    try:
        audio_data = await tts_service.synthesize_text(
            text=text,
            language=language,
            voice=voice
        )
        
        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            tts_info = tts_service.get_tts_info()
            
            return {
                "status": "success",
                "message": "TTS test successful",
                "text": text,
                "language": language,
                "voice": voice,
                "audio_size": len(audio_data),
                "audio_base64": audio_b64,
                "audio_format": "wav",
                "sample_rate": 22050,
                "tts_system": tts_info.get('preferred_system', 'piper')
            }
        else:
            raise HTTPException(status_code=500, detail="TTS test failed")
            
    except Exception as e:
        log_exception(log, "TTS test error", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info")
async def get_tts_info():
    """Get TTS system information"""
    try:
        tts_info = tts_service.get_tts_info()
        return {
            "status": "success",
            "tts_info": tts_info
        }
    except Exception as e:
        log_exception(log, "TTS info error", e)
        raise HTTPException(status_code=500, detail=str(e))


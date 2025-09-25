"""
Speech-to-Text (STT) API Endpoints
==================================

This module provides REST API endpoints for Whisper-based speech-to-text functionality.
It handles audio file uploads and real-time audio processing.

Author: SHCI Development Team
Date: 2025
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import json

from app.services.whisper_stt_service import get_whisper_stt_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Speech-to-Text"])

@router.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe")
):
    """
    Transcribe an uploaded audio file.
    
    Args:
        audio_file: Audio file to transcribe
        language: Language code (optional, auto-detect if not provided)
        task: Task type ('transcribe' or 'translate')
        
    Returns:
        JSON response with transcription results
    """
    try:
        # Validate file type
        if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read audio data
        audio_data = await audio_file.read()
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Get Whisper service
        whisper_service = await get_whisper_stt_service()
        
        # Transcribe audio
        result = await whisper_service.transcribe_audio(
            audio_data=audio_data,
            language=language,
            task=task
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages."""
    try:
        whisper_service = await get_whisper_stt_service()
        languages = whisper_service.get_supported_languages()
        
        return JSONResponse(content={
            "success": True,
            "languages": languages
        })
        
    except Exception as e:
        logger.error(f"Error getting languages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get languages: {str(e)}")

@router.get("/model-info")
async def get_model_info():
    """Get information about the loaded Whisper model."""
    try:
        whisper_service = await get_whisper_stt_service()
        info = whisper_service.get_model_info()
        
        return JSONResponse(content={
            "success": True,
            "model_info": info
        })
        
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")

@router.websocket("/stream")
async def websocket_audio_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio streaming and transcription.
    
    This endpoint handles:
    - Real-time audio data streaming
    - Continuous transcription
    - Language detection
    - Confidence scoring
    """
    await websocket.accept()
    logger.info("WebSocket STT connection established")
    
    try:
        # Get Whisper service
        whisper_service = await get_whisper_stt_service()
        
        # Audio buffer for accumulating audio data
        audio_buffer = b""
        buffer_size = 16000 * 30  # 30 seconds of 16kHz audio
        
        while True:
            try:
                # Receive data from client
                data = await websocket.receive_bytes()
                
                # Add to buffer
                audio_buffer += data
                
                # Process buffer if it's large enough (every 5 seconds of audio)
                if len(audio_buffer) >= buffer_size // 6:  # Process every 5 seconds
                    # Process the audio buffer - force English for now
                    result = await whisper_service.transcribe_audio(
                        audio_data=audio_buffer,
                        language="en",  # Force English to avoid wrong language detection
                        task="transcribe"
                    )
                    
                    # Send result back to client
                    await websocket.send_text(json.dumps({
                        "type": "transcription",
                        "data": result
                    }))
                    
                    # Keep only the last 10 seconds in buffer to avoid memory issues
                    if len(audio_buffer) > buffer_size // 3:
                        audio_buffer = audio_buffer[-buffer_size // 3:]
                
            except WebSocketDisconnect:
                logger.info("WebSocket STT connection closed")
                break
            except Exception as e:
                logger.error(f"WebSocket STT error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
                break
                
    except Exception as e:
        logger.error(f"WebSocket STT connection error: {e}")
        try:
            await websocket.close()
        except:
            pass

@router.post("/health")
async def stt_health_check():
    """Health check for STT service."""
    try:
        whisper_service = await get_whisper_stt_service()
        model_info = whisper_service.get_model_info()
        
        return JSONResponse(content={
            "success": True,
            "status": "healthy",
            "model_initialized": model_info["is_initialized"],
            "model_size": model_info["model_size"],
            "device": model_info["device"]
        })
        
    except Exception as e:
        logger.error(f"STT health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "status": "unhealthy",
                "error": str(e)
            }
        )

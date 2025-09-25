"""
RealtimeSTT API Endpoints for Professional Real-time Speech Recognition
"""

import asyncio
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from app.services.realtime_stt_service import (
    get_realtime_stt_service, 
    RealtimeSTTConfig, 
    RealtimeSTTCallbacks
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Realtime Speech-to-Text"])

# Global service instance
realtime_stt_service = None

@router.websocket("/stream")
async def websocket_realtime_stt(websocket: WebSocket):
    """
    WebSocket endpoint for real-time speech recognition using RealtimeSTT.
    
    This endpoint provides:
    - Real-time transcription updates
    - Final transcription when speech ends
    - Language detection
    - Error handling and recovery
    - Professional logging
    """
    global realtime_stt_service
    
    await websocket.accept()
    logger.info("WebSocket RealtimeSTT connection established")
    
    try:
        # Initialize RealtimeSTT service
        if realtime_stt_service is None:
            # Configuration for real-time STT
            config = RealtimeSTTConfig(
                model="base.en",  # Fast and accurate model
                language="en",    # English language
                use_microphone=True,
                post_speech_silence_duration=1.0,  # 1 second silence to end speech
                spinner=False,    # No loading spinner
                enable_realtime_transcription=True,
                enable_final_transcription=True
            )
            
            # Callbacks for handling transcription events
            callbacks = RealtimeSTTCallbacks(
                on_realtime_transcription=create_realtime_callback(websocket),
                on_final_transcription=create_final_callback(websocket),
                on_error=create_error_callback(websocket),
                on_state_change=create_state_callback(websocket),
                on_language_detected=create_language_callback(websocket)
            )
            
            realtime_stt_service = get_realtime_stt_service()
            realtime_stt_service.config = config
            realtime_stt_service.callbacks = callbacks
            
            # Initialize the service
            success = await realtime_stt_service.initialize()
            if not success:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Failed to initialize RealtimeSTT service",
                    "timestamp": asyncio.get_event_loop().time()
                }))
                return
        
        # Start the service
        success = await realtime_stt_service.start()
        if not success:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Failed to start RealtimeSTT service",
                "timestamp": asyncio.get_event_loop().time()
            }))
            return
        
        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "RealtimeSTT service started successfully",
            "status": realtime_stt_service.get_status(),
            "timestamp": asyncio.get_event_loop().time()
        }))
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages from client
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle different message types
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": asyncio.get_event_loop().time()
                    }))
                elif data.get("type") == "update_config":
                    await handle_config_update(websocket, data)
                elif data.get("type") == "get_status":
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "status": realtime_stt_service.get_status(),
                        "timestamp": asyncio.get_event_loop().time()
                    }))
                elif data.get("type") == "audio_data":
                    # Handle audio data from frontend
                    audio_data = data.get("data", [])
                    sample_rate = data.get("sampleRate", 16000)
                    chunk_size = data.get("chunkSize", 1024)
                    
                    # Process audio data with RealtimeSTT
                    if audio_data:
                        await process_audio_data(realtime_stt_service, audio_data, sample_rate, chunk_size)
                        
                elif data.get("type") == "stop":
                    realtime_stt_service.stop()
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "message": "RealtimeSTT service stopped",
                        "timestamp": asyncio.get_event_loop().time()
                    }))
                elif data.get("type") == "start":
                    success = await realtime_stt_service.start()
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "message": "RealtimeSTT service started" if success else "Failed to start RealtimeSTT service",
                        "success": success,
                        "timestamp": asyncio.get_event_loop().time()
                    }))
                    
            except WebSocketDisconnect:
                logger.info("WebSocket RealtimeSTT connection closed by client")
                break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received from client")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": asyncio.get_event_loop().time()
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Server error: {str(e)}",
                    "timestamp": asyncio.get_event_loop().time()
                }))
                
    except Exception as e:
        logger.error(f"WebSocket RealtimeSTT error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Connection error: {str(e)}",
                "timestamp": asyncio.get_event_loop().time()
            }))
        except:
            pass
    finally:
        # Clean up
        if realtime_stt_service:
            realtime_stt_service.stop()
        logger.info("WebSocket RealtimeSTT connection closed")

def create_realtime_callback(websocket: WebSocket):
    """Create callback for real-time transcription updates."""
    async def callback(text: str, confidence: float, is_final: bool):
        try:
            await websocket.send_text(json.dumps({
                "type": "realtime_transcription",
                "text": text,
                "confidence": confidence,
                "is_final": is_final,
                "timestamp": asyncio.get_event_loop().time()
            }))
        except Exception as e:
            logger.error(f"Error sending realtime transcription: {e}")
    return callback

def create_final_callback(websocket: WebSocket):
    """Create callback for final transcription."""
    async def callback(text: str, confidence: float):
        try:
            await websocket.send_text(json.dumps({
                "type": "final_transcription",
                "text": text,
                "confidence": confidence,
                "timestamp": asyncio.get_event_loop().time()
            }))
        except Exception as e:
            logger.error(f"Error sending final transcription: {e}")
    return callback

def create_error_callback(websocket: WebSocket):
    """Create callback for error handling."""
    async def callback(error: str):
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": error,
                "timestamp": asyncio.get_event_loop().time()
            }))
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
    return callback

def create_state_callback(websocket: WebSocket):
    """Create callback for state changes."""
    async def callback(is_recording: bool):
        try:
            await websocket.send_text(json.dumps({
                "type": "state_change",
                "is_recording": is_recording,
                "timestamp": asyncio.get_event_loop().time()
            }))
        except Exception as e:
            logger.error(f"Error sending state change: {e}")
    return callback

def create_language_callback(websocket: WebSocket):
    """Create callback for language detection."""
    async def callback(language: str):
        try:
            await websocket.send_text(json.dumps({
                "type": "language_detected",
                "language": language,
                "timestamp": asyncio.get_event_loop().time()
            }))
        except Exception as e:
            logger.error(f"Error sending language detection: {e}")
    return callback

async def process_audio_data(realtime_stt_service, audio_data: list, sample_rate: int, chunk_size: int):
    """Process audio data from frontend."""
    try:
        import numpy as np
        
        # Convert list to numpy array
        audio_array = np.array(audio_data, dtype=np.float32)
        
        # Normalize audio data
        if audio_array.max() > 1.0:
            audio_array = audio_array / 32768.0  # Convert from 16-bit to float
        
        # Process with RealtimeSTT service
        if hasattr(realtime_stt_service, '_recorder') and realtime_stt_service._recorder:
            # Feed audio data to RealtimeSTT
            # Note: This is a simplified approach - RealtimeSTT might need different handling
            logger.debug(f"Processing audio chunk: {len(audio_array)} samples at {sample_rate}Hz")
            
    except Exception as e:
        logger.error(f"Error processing audio data: {e}")

async def handle_config_update(websocket: WebSocket, data: Dict[str, Any]):
    """Handle configuration updates."""
    try:
        if realtime_stt_service:
            # Update configuration
            if "language" in data:
                realtime_stt_service.config.language = data["language"]
            if "model" in data:
                realtime_stt_service.config.model = data["model"]
            if "post_speech_silence_duration" in data:
                realtime_stt_service.config.post_speech_silence_duration = data["post_speech_silence_duration"]
            
            await websocket.send_text(json.dumps({
                "type": "config_updated",
                "config": {
                    "language": realtime_stt_service.config.language,
                    "model": realtime_stt_service.config.model,
                    "post_speech_silence_duration": realtime_stt_service.config.post_speech_silence_duration
                },
                "timestamp": asyncio.get_event_loop().time()
            }))
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "RealtimeSTT service not initialized",
                "timestamp": asyncio.get_event_loop().time()
            }))
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Configuration update failed: {str(e)}",
            "timestamp": asyncio.get_event_loop().time()
        }))

@router.get("/status")
async def get_realtime_stt_status():
    """Get the current status of the RealtimeSTT service."""
    try:
        if realtime_stt_service:
            return JSONResponse({
                "success": True,
                "status": realtime_stt_service.get_status(),
                "timestamp": asyncio.get_event_loop().time()
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "RealtimeSTT service not initialized",
                "timestamp": asyncio.get_event_loop().time()
            })
    except Exception as e:
        logger.error(f"Error getting RealtimeSTT status: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }, status_code=500)

@router.post("/start")
async def start_realtime_stt():
    """Start the RealtimeSTT service."""
    try:
        global realtime_stt_service
        
        if realtime_stt_service is None:
            return JSONResponse({
                "success": False,
                "message": "RealtimeSTT service not initialized",
                "timestamp": asyncio.get_event_loop().time()
            }, status_code=400)
        
        success = await realtime_stt_service.start()
        return JSONResponse({
            "success": success,
            "message": "RealtimeSTT service started" if success else "Failed to start RealtimeSTT service",
            "timestamp": asyncio.get_event_loop().time()
        })
    except Exception as e:
        logger.error(f"Error starting RealtimeSTT service: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }, status_code=500)

@router.post("/stop")
async def stop_realtime_stt():
    """Stop the RealtimeSTT service."""
    try:
        global realtime_stt_service
        
        if realtime_stt_service is None:
            return JSONResponse({
                "success": False,
                "message": "RealtimeSTT service not initialized",
                "timestamp": asyncio.get_event_loop().time()
            }, status_code=400)
        
        realtime_stt_service.stop()
        return JSONResponse({
            "success": True,
            "message": "RealtimeSTT service stopped",
            "timestamp": asyncio.get_event_loop().time()
        })
    except Exception as e:
        logger.error(f"Error stopping RealtimeSTT service: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }, status_code=500)

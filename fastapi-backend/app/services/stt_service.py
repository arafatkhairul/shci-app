"""
Real-time Speech-to-Text Service using WhisperX
"""
import asyncio
import numpy as np
import torch
import whisperx
from typing import Optional, Dict, Any, List
from collections import deque
import io
import wave
from app.utils.logger import get_logger

log = get_logger("stt_service")

class STTService:
    """Real-time Speech-to-Text service using WhisperX"""
    
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.sample_rate = 16000
        self.chunk_length = 30  # seconds
        self.batch_size = 16
        self.audio_buffer = deque(maxlen=1000)  # Buffer for audio frames
        self.is_processing = False
        self.initialized = False
        
    async def initialize(self):
        """Initialize WhisperX model"""
        try:
            log.info(f"🎤 Initializing STT service on {self.device}")
            
            # Load WhisperX model with latest API
            # Reference: https://github.com/m-bain/whisperX
            compute_type = "int8"  # Use int8 for CPU compatibility
            
            self.model = whisperx.load_model(
                "base", 
                device=self.device, 
                compute_type=compute_type
            )
            
            self.initialized = True
            log.info("✅ STT service initialized successfully")
            return True
            
        except Exception as e:
            log.error(f"❌ Failed to initialize STT service: {e}")
            # Try fallback with minimal parameters
            try:
                log.info("🔄 Trying fallback initialization...")
                self.model = whisperx.load_model("base", device=self.device)
                self.initialized = True
                log.info("✅ STT service initialized with fallback")
                return True
            except Exception as e2:
                log.error(f"❌ Fallback initialization also failed: {e2}")
                # Try with tiny model as last resort
                try:
                    log.info("🔄 Trying tiny model as last resort...")
                    self.model = whisperx.load_model("tiny", device=self.device)
                    self.initialized = True
                    log.info("✅ STT service initialized with tiny model")
                    return True
                except Exception as e3:
                    log.error(f"❌ All initialization attempts failed: {e3}")
                    return False
    
    def add_audio_frame(self, audio_data: bytes):
        """Add audio frame to buffer"""
        if not self.initialized:
            return
            
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            self.audio_buffer.extend(audio_array)
            
        except Exception as e:
            log.error(f"Error adding audio frame: {e}")
    
    def get_audio_chunk(self, duration_ms: int = 3000) -> Optional[np.ndarray]:
        """Get audio chunk from buffer for processing"""
        if not self.initialized or len(self.audio_buffer) == 0:
            return None
            
        # Calculate samples needed for duration
        samples_needed = int(self.sample_rate * duration_ms / 1000)
        
        if len(self.audio_buffer) < samples_needed:
            return None
            
        # Get audio chunk
        audio_chunk = np.array(list(self.audio_buffer)[-samples_needed:], dtype=np.float32)
        
        # Normalize audio
        audio_chunk = audio_chunk / 32768.0
        
        return audio_chunk
    
    async def transcribe_audio(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Transcribe audio data using WhisperX"""
        if not self.initialized:
            return None
            
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Ensure minimum length
            if len(audio_array) < self.sample_rate * 0.5:  # 0.5 seconds minimum
                return None
            
            # Transcribe using WhisperX with latest API
            # Reference: https://github.com/m-bain/whisperX
            result = self.model.transcribe(audio_array, batch_size=self.batch_size)
            
            if result and "segments" in result and len(result["segments"]) > 0:
                # Get the most recent segment
                latest_segment = result["segments"][-1]
                
                return {
                    "text": latest_segment.get("text", "").strip(),
                    "confidence": latest_segment.get("avg_logprob", 0.0),
                    "start": latest_segment.get("start", 0.0),
                    "end": latest_segment.get("end", 0.0),
                    "is_final": True
                }
            
            return None
            
        except Exception as e:
            log.error(f"Error transcribing audio: {e}")
            return None
    
    async def transcribe_buffer(self) -> Optional[Dict[str, Any]]:
        """Transcribe from audio buffer"""
        if not self.initialized:
            return None
            
        try:
            # Get audio chunk from buffer
            audio_chunk = self.get_audio_chunk(duration_ms=3000)  # 3 seconds
            
            if audio_chunk is None:
                return None
            
            # Transcribe using WhisperX with latest API
            # Reference: https://github.com/m-bain/whisperX
            result = self.model.transcribe(audio_chunk, batch_size=self.batch_size)
            
            if result and "segments" in result and len(result["segments"]) > 0:
                # Get the most recent segment
                latest_segment = result["segments"][-1]
                
                return {
                    "text": latest_segment.get("text", "").strip(),
                    "confidence": latest_segment.get("avg_logprob", 0.0),
                    "start": latest_segment.get("start", 0.0),
                    "end": latest_segment.get("end", 0.0),
                    "is_final": True
                }
            
            return None
            
        except Exception as e:
            log.error(f"Error transcribing buffer: {e}")
            return None
    
    def clear_buffer(self):
        """Clear audio buffer"""
        self.audio_buffer.clear()
    
    def is_ready(self) -> bool:
        """Check if STT service is ready"""
        return self.initialized and self.model is not None
    
    def get_buffer_size(self) -> int:
        """Get current buffer size"""
        return len(self.audio_buffer)
    
    def get_buffer_duration(self) -> float:
        """Get buffer duration in seconds"""
        return len(self.audio_buffer) / self.sample_rate

# Global STT service instance
stt_service = STTService()

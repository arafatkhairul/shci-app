#!/usr/bin/env python3
"""
RealtimeSTT - Speech-to-Text implementation based on RealtimeVoiceChat
Real-time speech recognition with Whisper model
"""

import os
import logging
import asyncio
import tempfile
import wave
import io
import numpy as np
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

log = logging.getLogger("realtime_stt")

# Import Whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    log.warning("Whisper not available - install with: pip install openai-whisper")

# Import PyTorch for GPU support
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    log.warning("PyTorch not available - install with: pip install torch")

@dataclass
class STTConfig:
    """Configuration for Speech-to-Text"""
    model: str = "base.en"
    language: str = "en"
    device: str = "auto"
    silence_limit_seconds: float = 1.0
    phrase_timeout: float = 3.0
    chunk_size: int = 1024
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2

class RealtimeSTT:
    """Real-time Speech-to-Text using Whisper model"""
    
    def __init__(self, config: STTConfig = None):
        self.config = config or STTConfig()
        self.available = WHISPER_AVAILABLE and TORCH_AVAILABLE
        self.whisper_model = None
        self.device = self._detect_device()
        self._initialized = False
        
        # Audio processing
        self.audio_buffer = []
        self.is_recording = False
        self.silence_counter = 0
        self.last_audio_time = 0
        
        # Callbacks
        self.on_transcription = None
        self.on_silence = None
        self.on_phrase_complete = None
        
        if self.available:
            self._initialize_whisper()
            self._initialized = True
            log.info(f"✅ RealtimeSTT initialized with device: {self.device}")
        else:
            log.warning("❌ RealtimeSTT not available")
    
    def _detect_device(self):
        """Detect best available device"""
        if not TORCH_AVAILABLE:
            return "cpu"
        
        if self.config.device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        else:
            return self.config.device
    
    def _initialize_whisper(self):
        """Initialize Whisper model"""
        try:
            log.info(f"🎤 Loading Whisper model: {self.config.model}")
            
            # Load Whisper model
            self.whisper_model = whisper.load_model(
                self.config.model,
                device=self.device
            )
            
            log.info(f"✅ Whisper model loaded on {self.device}")
            
        except Exception as e:
            log.error(f"Failed to initialize Whisper: {e}")
            self.available = False
    
    def set_config(self, config: STTConfig):
        """Update STT configuration"""
        self.config = config
        if self._initialized and self.config.model != self.whisper_model.name:
            self._initialize_whisper()
    
    def set_callbacks(self, 
                     on_transcription: Callable[[str], None] = None,
                     on_silence: Callable[[], None] = None,
                     on_phrase_complete: Callable[[str], None] = None):
        """Set callback functions"""
        self.on_transcription = on_transcription
        self.on_silence = on_silence
        self.on_phrase_complete = on_phrase_complete
    
    async def transcribe_audio_async(self, audio_data: bytes) -> str:
        """Asynchronously transcribe audio data"""
        if not self.available or not self.whisper_model:
            raise RuntimeError("RealtimeSTT not available")
        
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.transcribe_audio_sync, audio_data)
        except Exception as e:
            log.error(f"Transcription error: {e}")
            return ""
    
    def transcribe_audio_sync(self, audio_data: bytes) -> str:
        """Synchronously transcribe audio data"""
        if not self.available or not self.whisper_model:
            raise RuntimeError("RealtimeSTT not available")
        
        try:
            # Convert audio bytes to numpy array
            audio_array = self._bytes_to_audio_array(audio_data)
            
            if audio_array is None or len(audio_array) == 0:
                return ""
            
            # Transcribe using Whisper
            result = self.whisper_model.transcribe(
                audio_array,
                language=self.config.language,
                fp16=False  # Use fp32 for better compatibility
            )
            
            text = result["text"].strip()
            
            if text:
                log.info(f"🎤 Transcribed: '{text}'")
                if self.on_transcription:
                    self.on_transcription(text)
            
            return text
            
        except Exception as e:
            log.error(f"Transcription failed: {e}")
            return ""
    
    def _bytes_to_audio_array(self, audio_data: bytes) -> Optional[np.ndarray]:
        """Convert audio bytes to numpy array"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_file.write(audio_data)
                temp_path = tmp_file.name
            
            # Load audio file
            audio_array, sample_rate = whisper.load_audio(temp_path)
            
            # Clean up
            os.unlink(temp_path)
            
            return audio_array
            
        except Exception as e:
            log.error(f"Failed to convert audio bytes: {e}")
            return None
    
    def process_audio_chunk(self, audio_chunk: bytes):
        """Process incoming audio chunk for real-time transcription"""
        if not self.is_recording:
            return
        
        # Add to buffer
        self.audio_buffer.append(audio_chunk)
        self.last_audio_time = asyncio.get_event_loop().time()
        
        # Check for silence
        if self._is_silence(audio_chunk):
            self.silence_counter += 1
            if self.silence_counter >= self.config.silence_limit_seconds * 10:  # Assuming 10 chunks per second
                if self.on_silence:
                    self.on_silence()
                self._process_phrase()
        else:
            self.silence_counter = 0
    
    def _is_silence(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk is silence"""
        try:
            # Convert to numpy array
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Calculate RMS (Root Mean Square)
            rms = np.sqrt(np.mean(audio_array**2))
            
            # Threshold for silence detection
            silence_threshold = 500  # Adjust based on your needs
            
            return rms < silence_threshold
            
        except Exception:
            return True
    
    def _process_phrase(self):
        """Process accumulated audio as a phrase"""
        if not self.audio_buffer:
            return
        
        try:
            # Combine audio chunks
            combined_audio = b''.join(self.audio_buffer)
            
            # Transcribe
            text = self.transcribe_audio_sync(combined_audio)
            
            if text and self.on_phrase_complete:
                self.on_phrase_complete(text)
            
            # Clear buffer
            self.audio_buffer.clear()
            self.silence_counter = 0
            
        except Exception as e:
            log.error(f"Failed to process phrase: {e}")
            self.audio_buffer.clear()
    
    def start_recording(self):
        """Start real-time recording"""
        self.is_recording = True
        self.audio_buffer.clear()
        self.silence_counter = 0
        log.info("🎤 Started real-time recording")
    
    def stop_recording(self):
        """Stop real-time recording"""
        self.is_recording = False
        if self.audio_buffer:
            self._process_phrase()
        log.info("🎤 Stopped real-time recording")
    
    def reset(self):
        """Reset STT state"""
        self.stop_recording()
        self.audio_buffer.clear()
        self.silence_counter = 0
        log.info("🔄 STT state reset")
    
    def is_available(self) -> bool:
        """Check if RealtimeSTT is available"""
        return self.available and self.whisper_model is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get RealtimeSTT system information"""
        info = {
            "name": "RealtimeSTT",
            "available": self.is_available(),
            "system_type": "Whisper-based STT",
            "model": self.config.model,
            "language": self.config.language,
            "device": self.device,
            "sample_rate": self.config.sample_rate,
            "chunk_size": self.config.chunk_size,
            "silence_limit": self.config.silence_limit_seconds,
            "phrase_timeout": self.config.phrase_timeout,
            "is_recording": self.is_recording
        }
        
        return info

# Global RealtimeSTT instance
_realtime_stt_instance = None

def get_realtime_stt(config: STTConfig = None) -> RealtimeSTT:
    """Get singleton RealtimeSTT instance"""
    global _realtime_stt_instance
    if _realtime_stt_instance is None:
        _realtime_stt_instance = RealtimeSTT(config)
        log.info("🏭 RealtimeSTT initialized (singleton)")
    return _realtime_stt_instance

# Convenience functions
async def transcribe_audio_async(audio_data: bytes, config: STTConfig = None) -> str:
    """Transcribe audio data asynchronously"""
    stt = get_realtime_stt(config)
    return await stt.transcribe_audio_async(audio_data)

def transcribe_audio_sync(audio_data: bytes, config: STTConfig = None) -> str:
    """Transcribe audio data synchronously"""
    stt = get_realtime_stt(config)
    return stt.transcribe_audio_sync(audio_data)

def get_stt_info(config: STTConfig = None) -> Dict[str, Any]:
    """Get RealtimeSTT system information"""
    stt = get_realtime_stt(config)
    return stt.get_info()

if __name__ == "__main__":
    # Test RealtimeSTT
    print("🎤 RealtimeSTT Test")
    print("=" * 50)
    
    config = STTConfig(
        model="base.en",
        language="en",
        silence_limit_seconds=1.0
    )
    
    stt = get_realtime_stt(config)
    print(f"✅ STT System: {stt.name}")
    print(f"✅ Available: {stt.is_available()}")
    print(f"✅ Device: {stt.device}")
    print(f"✅ Model: {stt.config.model}")
    
    if stt.is_available():
        print("\n🎤 RealtimeSTT is ready for real-time transcription")
        print("Use start_recording() to begin, process_audio_chunk() for audio data")
    
    print("\n" + "=" * 50)

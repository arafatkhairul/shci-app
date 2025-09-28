import asyncio
import numpy as np
import torch
import whisperx
from typing import Optional, Dict, Any
from collections import deque
from app.utils.logger import get_logger

log = get_logger("stt_service")

class STTService:
    """
    Real-time Speech-to-Text service using WhisperX.

    This service manages an audio buffer and uses a lock to handle transcription
    requests asynchronously, preventing blocking of the main event loop.
    """

    def __init__(self,
                 model_size: str = "base",
                 buffer_duration_s: int = 30,
                 min_chunk_s: float = 1.0):
        """
        Initializes the STTService.
        """
        self.model_size = model_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # More robust compute type determination
        if self.device == "cuda":
            if torch.cuda.is_bf16_supported():
                self.compute_type = "bfloat16"
            else:
                self.compute_type = "float16"
        else:
            # For CPU, use int8 but have fallbacks
            self.compute_type = "int8"

        self.sample_rate = 16000
        self.batch_size = 8  # Reduced for stability
        
        self.buffer_duration_s = buffer_duration_s
        buffer_max_samples = self.sample_rate * self.buffer_duration_s
        self.audio_buffer = deque(maxlen=buffer_max_samples)
        
        self.min_chunk_samples = int(self.sample_rate * min_chunk_s)

        self.model = None
        self.initialized = False
        self.processing_lock = asyncio.Lock()
        self._initialization_attempted = False

    async def initialize(self):
        """
        Initializes and loads the WhisperX model with robust error handling.
        """
        if self.initialized:
            log.info("STT service is already initialized.")
            return True

        if self._initialization_attempted:
            log.warning("STT service initialization was already attempted and failed.")
            return False

        self._initialization_attempted = True
        log.info(f"🎤 Initializing STT service on device '{self.device}' with model '{self.model_size}' and compute type '{self.compute_type}'...")
        
        try:
            # Try loading with the preferred compute type first
            self.model = await asyncio.to_thread(
                whisperx.load_model,
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            self.initialized = True
            log.info("✅ STT service initialized successfully.")
            return True
            
        except Exception as e:
            log.error(f"❌ Failed to initialize STT service with compute type '{self.compute_type}': {e}")
            
            # Fallback strategies for different error types
            if "operator torchvision::nms does not exist" in str(e):
                log.warning("🔧 Torchvision compatibility issue detected. Trying fallback initialization...")
                return await self._initialize_fallback()
            elif "Requested float16" in str(e) or "compute type" in str(e).lower():
                log.warning("🔧 Compute type issue detected. Trying alternative compute types...")
                return await self._initialize_with_fallback_compute_types()
            else:
                log.error(f"❌ Unrecoverable error during STT service initialization: {e}")
                self.model = None
                self.initialized = False
                return False

    async def _initialize_fallback(self):
        """
        Fallback initialization for torchvision compatibility issues.
        """
        try:
            log.info("🔄 Attempting fallback initialization with default parameters...")
            self.model = await asyncio.to_thread(
                whisperx.load_model,
                self.model_size,
                device=self.device,
                # Let whisperx choose the compute type automatically
            )
            self.initialized = True
            log.info("✅ STT service initialized successfully with fallback parameters.")
            return True
        except Exception as e:
            log.error(f"❌ Fallback initialization also failed: {e}")
            return await self._initialize_with_fallback_compute_types()

    async def _initialize_with_fallback_compute_types(self):
        """
        Try different compute types as fallback.
        """
        fallback_compute_types = ["float32", "int8", "float16"] if self.device == "cpu" else ["float32", "int8"]
        
        for compute_type in fallback_compute_types:
            if compute_type == self.compute_type:
                continue  # Skip the one we already tried
                
            try:
                log.info(f"🔄 Trying fallback compute type: {compute_type}")
                self.model = await asyncio.to_thread(
                    whisperx.load_model,
                    self.model_size,
                    device=self.device,
                    compute_type=compute_type,
                )
                self.compute_type = compute_type
                self.initialized = True
                log.info(f"✅ STT service initialized successfully with compute type '{compute_type}'.")
                return True
            except Exception as e:
                log.warning(f"⚠️ Compute type '{compute_type}' also failed: {e}")
                continue
        
        # Last resort: try without specifying compute type
        try:
            log.info("🔄 Attempting initialization without specifying compute type...")
            self.model = await asyncio.to_thread(
                whisperx.load_model,
                self.model_size,
                device=self.device,
            )
            self.initialized = True
            log.info("✅ STT service initialized successfully without compute type specification.")
            return True
        except Exception as e:
            log.error(f"❌ All initialization attempts failed: {e}")
            self.model = None
            self.initialized = False
            return False

    def add_audio_frame(self, audio_data: bytes):
        """
        Adds a raw audio frame in bytes to the internal buffer.
        """
        if not self.initialized:
            # Silently drop frames if not initialized to avoid spamming logs
            return

        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            self.audio_buffer.extend(audio_array)
        except Exception as e:
            log.error(f"Error adding audio frame: {e}")

    async def process_buffer(self) -> Optional[Dict[str, Any]]:
        """
        Processes the current audio buffer if it contains enough new data.
        """
        if not self.is_ready():
            return None

        if len(self.audio_buffer) < self.min_chunk_samples:
            return None

        if self.processing_lock.locked():
            log.debug("Processing lock is acquired, skipping this cycle.")
            return None

        async with self.processing_lock:
            try:
                buffer_duration = self.get_buffer_duration()
                log.info(f"Processing audio buffer of {buffer_duration:.2f}s...")
                
                # Convert audio data to float32 and normalize
                audio_chunk = np.array(self.audio_buffer, dtype=np.float32) / 32768.0
                
                # Clear buffer before processing to avoid processing same audio twice
                self.clear_buffer()

                # Transcribe with proper error handling
                result = await asyncio.to_thread(
                    self.model.transcribe,
                    audio_chunk,
                    batch_size=self.batch_size,
                    language="en",  # Specify language
                    task="transcribe"  # Specify the task
                )
                
                segments_count = len(result.get('segments', []))
                log.info(f"Transcription complete. Segments found: {segments_count}")
                
                if segments_count > 0:
                    return result
                return None
                
            except Exception as e:
                log.error(f"Error during transcription: {e}")
                # Don't clear buffer on transcription error so we can retry
                return None

    def clear_buffer(self):
        """Clears the audio buffer."""
        self.audio_buffer.clear()

    def is_ready(self) -> bool:
        """Checks if the service is initialized and ready to transcribe."""
        return self.initialized and self.model is not None

    def get_buffer_size(self) -> int:
        """Gets the current number of audio samples in the buffer."""
        return len(self.audio_buffer)

    def get_buffer_duration(self) -> float:
        """Gets the current duration of audio in the buffer in seconds."""
        return len(self.audio_buffer) / self.sample_rate

    async def cleanup(self):
        """Clean up resources."""
        if self.model is not None:
            # WhisperX models don't have explicit cleanup, but we can delete reference
            del self.model
            self.model = None
        self.initialized = False
        self.clear_buffer()
        log.info("STT service cleaned up.")


# Global STT service instance with error handling
stt_service = STTService()

async def initialize_stt_service():
    """Initialize the global STT service with error handling."""
    try:
        success = await stt_service.initialize()
        if not success:
            log.error("Failed to initialize STT service. Audio processing will be disabled.")
        return success
    except Exception as e:
        log.error(f"Unexpected error during STT service initialization: {e}")
        return False

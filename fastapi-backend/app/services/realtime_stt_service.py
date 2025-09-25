"""
Professional RealtimeSTT Service for Real-time Speech Recognition
Replaces faster-whisper with RealtimeSTT for better real-time performance
"""

import asyncio
import logging
import threading
import time
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from RealtimeSTT import AudioToTextRecorder
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class RealtimeSTTConfig:
    """Configuration for RealtimeSTT service."""
    model: str = "base.en"  # Model size: tiny.en, base.en, small.en, medium.en
    language: str = "en"  # Language code
    use_microphone: bool = True  # Use microphone input
    post_speech_silence_duration: float = 1.0  # Silence duration to end speech
    spinner: bool = False  # Show loading spinner
    enable_realtime_transcription: bool = True  # Enable real-time updates
    enable_final_transcription: bool = True  # Enable final transcription
    sample_rate: int = 16000  # Audio sample rate
    chunk_size: int = 1024  # Audio chunk size

@dataclass
class RealtimeSTTCallbacks:
    """Callbacks for RealtimeSTT events."""
    on_realtime_transcription: Optional[Callable[[str, float, bool], None]] = None
    on_final_transcription: Optional[Callable[[str, float], None]] = None
    on_error: Optional[Callable[[str], None]] = None
    on_state_change: Optional[Callable[[bool], None]] = None
    on_language_detected: Optional[Callable[[str], None]] = None

class RealtimeSTTService:
    """
    Professional RealtimeSTT service for real-time speech recognition.
    
    Features:
    - Real-time transcription with live updates
    - Final transcription when speech ends
    - Language detection and validation
    - Error handling and recovery
    - Thread-safe operations
    - Professional logging
    """
    
    def __init__(self, config: RealtimeSTTConfig, callbacks: RealtimeSTTCallbacks):
        self.config = config
        self.callbacks = callbacks
        self.recorder: Optional[AudioToTextRecorder] = None
        self.is_initialized = False
        self.is_recording = False
        self.is_connected = False
        self._lock = threading.Lock()
        self._recorder_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Statistics
        self.total_transcriptions = 0
        self.successful_transcriptions = 0
        self.failed_transcriptions = 0
        self.start_time = None
        
        logger.info(f"RealtimeSTT Service initialized with model: {config.model}, language: {config.language}")

    async def initialize(self) -> bool:
        """
        Initialize the RealtimeSTT service.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing RealtimeSTT with model: {self.config.model}")
            
            # Initialize AudioToTextRecorder in a separate thread
            loop = asyncio.get_event_loop()
            self.recorder = await loop.run_in_executor(
                None,
                self._create_recorder
            )
            
            self.is_initialized = True
            self.is_connected = True
            self.start_time = time.time()
            
            logger.info(f"RealtimeSTT initialized successfully with model: {self.config.model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RealtimeSTT: {e}")
            self.is_initialized = False
            self.is_connected = False
            return False

    def _create_recorder(self) -> AudioToTextRecorder:
        """Create and configure the AudioToTextRecorder."""
        try:
            # Configure recorder with callbacks
            recorder = AudioToTextRecorder(
                model=self.config.model,
                language=self.config.language,
                use_microphone=self.config.use_microphone,
                on_realtime_transcription_update=self._on_realtime_transcription,
                spinner=self.config.spinner,
                post_speech_silence_duration=self.config.post_speech_silence_duration
            )
            
            # Override the final transcription callback
            recorder._on_final_transcription = self._on_final_transcription
            
            return recorder
            
        except Exception as e:
            logger.error(f"Failed to create AudioToTextRecorder: {e}")
            raise

    def _on_realtime_transcription(self, text: str):
        """Handle real-time transcription updates."""
        try:
            if not text or not text.strip():
                return
                
            # Calculate confidence (simple heuristic)
            confidence = min(1.0, max(0.0, len(text.strip()) / 50.0))
            
            # Update statistics
            self.total_transcriptions += 1
            
            logger.debug(f"Realtime transcription: {text[:50]}...")
            
            # Call user callback
            if self.callbacks.on_realtime_transcription:
                try:
                    self.callbacks.on_realtime_transcription(text, confidence, False)
                except Exception as e:
                    logger.error(f"Error in realtime transcription callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error in realtime transcription handler: {e}")
            self.failed_transcriptions += 1

    def _on_final_transcription(self, text: str):
        """Handle final transcription when speech ends."""
        try:
            if not text or not text.strip():
                return
                
            # Calculate confidence
            confidence = min(1.0, max(0.0, len(text.strip()) / 50.0))
            
            # Update statistics
            self.successful_transcriptions += 1
            
            logger.info(f"Final transcription: {text}")
            
            # Call user callback
            if self.callbacks.on_final_transcription:
                try:
                    self.callbacks.on_final_transcription(text, confidence)
                except Exception as e:
                    logger.error(f"Error in final transcription callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error in final transcription handler: {e}")
            self.failed_transcriptions += 1

    async def start(self) -> bool:
        """
        Start the RealtimeSTT service.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            with self._lock:
                if not self.is_initialized:
                    logger.warning("RealtimeSTT not initialized, cannot start")
                    return False
                    
                if self.is_recording:
                    logger.warning("RealtimeSTT already recording")
                    return True
                
                logger.info("Starting RealtimeSTT service...")
                
                # Start recording in a separate thread
                self._stop_event.clear()
                self._recorder_thread = threading.Thread(
                    target=self._recording_loop,
                    daemon=True
                )
                self._recorder_thread.start()
                
                self.is_recording = True
                
                # Notify state change
                if self.callbacks.on_state_change:
                    try:
                        self.callbacks.on_state_change(True)
                    except Exception as e:
                        logger.error(f"Error in state change callback: {e}")
                
                logger.info("RealtimeSTT service started successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start RealtimeSTT service: {e}")
            return False

    def stop(self):
        """Stop the RealtimeSTT service."""
        try:
            with self._lock:
                if not self.is_recording:
                    logger.warning("RealtimeSTT not recording, cannot stop")
                    return
                
                logger.info("Stopping RealtimeSTT service...")
                
                # Signal stop
                self._stop_event.set()
                
                # Wait for thread to finish
                if self._recorder_thread and self._recorder_thread.is_alive():
                    self._recorder_thread.join(timeout=2.0)
                
                self.is_recording = False
                
                # Notify state change
                if self.callbacks.on_state_change:
                    try:
                        self.callbacks.on_state_change(False)
                    except Exception as e:
                        logger.error(f"Error in state change callback: {e}")
                
                logger.info("RealtimeSTT service stopped")
                
        except Exception as e:
            logger.error(f"Error stopping RealtimeSTT service: {e}")

    def _recording_loop(self):
        """Main recording loop running in a separate thread."""
        try:
            logger.info("RealtimeSTT recording loop started")
            
            while not self._stop_event.is_set():
                try:
                    if self.recorder:
                        # This is a blocking call that waits for speech
                        # and calls the callbacks when speech is detected
                        self.recorder.text(self._on_final_transcription)
                    else:
                        logger.warning("Recorder not available, stopping loop")
                        break
                        
                except Exception as e:
                    logger.error(f"Error in recording loop: {e}")
                    if self.callbacks.on_error:
                        try:
                            self.callbacks.on_error(str(e))
                        except Exception as callback_error:
                            logger.error(f"Error in error callback: {callback_error}")
                    
                    # Wait a bit before retrying
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Fatal error in recording loop: {e}")
        finally:
            logger.info("RealtimeSTT recording loop ended")

    def update_config(self, new_config: RealtimeSTTConfig):
        """Update the configuration."""
        try:
            with self._lock:
                self.config = new_config
                logger.info("RealtimeSTT configuration updated")
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the service."""
        try:
            with self._lock:
                uptime = time.time() - self.start_time if self.start_time else 0
                
                return {
                    "is_initialized": self.is_initialized,
                    "is_recording": self.is_recording,
                    "is_connected": self.is_connected,
                    "model": self.config.model,
                    "language": self.config.language,
                    "total_transcriptions": self.total_transcriptions,
                    "successful_transcriptions": self.successful_transcriptions,
                    "failed_transcriptions": self.failed_transcriptions,
                    "uptime_seconds": uptime,
                    "success_rate": (
                        self.successful_transcriptions / max(1, self.total_transcriptions) * 100
                    )
                }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "is_initialized": False,
                "is_recording": False,
                "is_connected": False,
                "error": str(e)
            }

    def destroy(self):
        """Clean up resources."""
        try:
            logger.info("Destroying RealtimeSTT service...")
            
            # Stop recording
            self.stop()
            
            # Clean up recorder
            if self.recorder:
                try:
                    self.recorder.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down recorder: {e}")
                finally:
                    self.recorder = None
            
            self.is_initialized = False
            self.is_connected = False
            
            logger.info("RealtimeSTT service destroyed")
            
        except Exception as e:
            logger.error(f"Error destroying RealtimeSTT service: {e}")

# Global service instance
_realtime_stt_service: Optional[RealtimeSTTService] = None

def get_realtime_stt_service() -> RealtimeSTTService:
    """Get the global RealtimeSTT service instance."""
    global _realtime_stt_service
    if _realtime_stt_service is None:
        # Default configuration
        config = RealtimeSTTConfig(
            model="base.en",
            language="en",
            use_microphone=True,
            post_speech_silence_duration=1.0,
            spinner=False,
            enable_realtime_transcription=True,
            enable_final_transcription=True
        )
        
        # Default callbacks
        callbacks = RealtimeSTTCallbacks()
        
        _realtime_stt_service = RealtimeSTTService(config, callbacks)
    
    return _realtime_stt_service

def create_realtime_stt_service(config: RealtimeSTTConfig, callbacks: RealtimeSTTCallbacks) -> RealtimeSTTService:
    """Create a new RealtimeSTT service instance."""
    return RealtimeSTTService(config, callbacks)

#!/usr/bin/env python3
"""
Audio Processor - Based on RealtimeVoiceChat implementation
Handles audio processing, turn detection, and real-time communication
"""

import os
import logging
import asyncio
import time
import wave
import io
import numpy as np
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("audio_processor")

class AudioState(Enum):
    """Audio processing states"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

@dataclass
class AudioConfig:
    """Configuration for audio processing"""
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    chunk_size: int = 1024
    silence_threshold: float = 0.01
    min_audio_length: float = 0.5
    max_audio_length: float = 10.0
    phrase_timeout: float = 3.0
    turn_detection_enabled: bool = True

class TurnDetector:
    """Turn detection for conversation flow"""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self.is_speaking = False
        self.silence_start = None
        self.last_audio_time = 0
        self.audio_buffer = []
        
    def update_settings(self, 
                       silence_threshold: float = None,
                       phrase_timeout: float = None,
                       min_audio_length: float = None):
        """Update turn detection settings"""
        if silence_threshold is not None:
            self.config.silence_threshold = silence_threshold
        if phrase_timeout is not None:
            self.config.phrase_timeout = phrase_timeout
        if min_audio_length is not None:
            self.config.min_audio_length = min_audio_length
    
    def process_audio_chunk(self, audio_chunk: bytes) -> bool:
        """Process audio chunk and detect turn completion"""
        current_time = time.time()
        
        # Check if audio is silence
        if self._is_silence(audio_chunk):
            if not self.is_speaking:
                return False
            
            if self.silence_start is None:
                self.silence_start = current_time
            
            # Check if silence duration exceeds timeout
            silence_duration = current_time - self.silence_start
            if silence_duration >= self.config.phrase_timeout:
                # Turn completed
                self.is_speaking = False
                self.silence_start = None
                return True
        else:
            # Audio detected
            self.is_speaking = True
            self.silence_start = None
            self.last_audio_time = current_time
            self.audio_buffer.append(audio_chunk)
        
        return False
    
    def _is_silence(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk is silence"""
        try:
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_array**2))
            return rms < (self.config.silence_threshold * 32767)  # Convert to int16 range
        except Exception:
            return True
    
    def reset(self):
        """Reset turn detector state"""
        self.is_speaking = False
        self.silence_start = None
        self.last_audio_time = 0
        self.audio_buffer.clear()

class AudioProcessor:
    """Main audio processor for real-time voice chat"""
    
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
        self.state = AudioState.IDLE
        self.turn_detector = TurnDetector(self.config)
        
        # Audio processing
        self.audio_buffer = []
        self.current_audio_length = 0
        self.last_audio_time = 0
        
        # Callbacks
        self.on_audio_received = None
        self.on_turn_complete = None
        self.on_silence_detected = None
        self.on_state_change = None
        
        # Performance tracking
        self.audio_chunks_processed = 0
        self.total_processing_time = 0
        
        log.info("✅ AudioProcessor initialized")
    
    def set_callbacks(self,
                     on_audio_received: Callable[[bytes], None] = None,
                     on_turn_complete: Callable[[bytes], None] = None,
                     on_silence_detected: Callable[[], None] = None,
                     on_state_change: Callable[[AudioState], None] = None):
        """Set callback functions"""
        self.on_audio_received = on_audio_received
        self.on_turn_complete = on_turn_complete
        self.on_silence_detected = on_silence_detected
        self.on_state_change = on_state_change
    
    def set_state(self, new_state: AudioState):
        """Change audio processing state"""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            log.info(f"🔄 Audio state changed: {old_state.value} -> {new_state.value}")
            
            if self.on_state_change:
                self.on_state_change(new_state)
    
    def process_audio_chunk(self, audio_chunk: bytes):
        """Process incoming audio chunk"""
        if self.state != AudioState.LISTENING:
            return
        
        start_time = time.time()
        
        try:
            # Add to buffer
            self.audio_buffer.append(audio_chunk)
            self.current_audio_length += len(audio_chunk)
            self.last_audio_time = time.time()
            
            # Notify audio received
            if self.on_audio_received:
                self.on_audio_received(audio_chunk)
            
            # Check audio length limits
            audio_duration = self.current_audio_length / (self.config.sample_rate * self.config.sample_width * self.config.channels)
            
            if audio_duration > self.config.max_audio_length:
                log.warning("⚠️ Audio length exceeded maximum, processing current buffer")
                self._process_turn()
                return
            
            # Turn detection
            if self.config.turn_detection_enabled:
                turn_complete = self.turn_detector.process_audio_chunk(audio_chunk)
                
                if turn_complete:
                    log.info("🎤 Turn completed, processing audio")
                    self._process_turn()
                elif audio_duration >= self.config.min_audio_length:
                    # Check for silence
                    if self.turn_detector.silence_start and \
                       (time.time() - self.turn_detector.silence_start) >= self.config.phrase_timeout:
                        if self.on_silence_detected:
                            self.on_silence_detected()
                        self._process_turn()
            
            # Update performance metrics
            self.audio_chunks_processed += 1
            self.total_processing_time += time.time() - start_time
            
        except Exception as e:
            log.error(f"Audio processing error: {e}")
    
    def _process_turn(self):
        """Process completed turn"""
        if not self.audio_buffer:
            return
        
        try:
            # Combine audio chunks
            combined_audio = b''.join(self.audio_buffer)
            
            # Validate audio length
            audio_duration = len(combined_audio) / (self.config.sample_rate * self.config.sample_width * self.config.channels)
            
            if audio_duration < self.config.min_audio_length:
                log.debug("Audio too short, ignoring")
                self._reset_buffer()
                return
            
            # Notify turn complete
            if self.on_turn_complete:
                self.on_turn_complete(combined_audio)
            
            # Reset for next turn
            self._reset_buffer()
            
        except Exception as e:
            log.error(f"Turn processing error: {e}")
            self._reset_buffer()
    
    def _reset_buffer(self):
        """Reset audio buffer"""
        self.audio_buffer.clear()
        self.current_audio_length = 0
        self.turn_detector.reset()
    
    def start_listening(self):
        """Start listening for audio"""
        self.set_state(AudioState.LISTENING)
        self._reset_buffer()
        log.info("🎤 Started listening")
    
    def stop_listening(self):
        """Stop listening and process any remaining audio"""
        if self.state == AudioState.LISTENING:
            if self.audio_buffer:
                self._process_turn()
            self.set_state(AudioState.IDLE)
            log.info("🎤 Stopped listening")
    
    def start_speaking(self):
        """Start speaking state"""
        self.set_state(AudioState.SPEAKING)
        log.info("🔊 Started speaking")
    
    def stop_speaking(self):
        """Stop speaking state"""
        if self.state == AudioState.SPEAKING:
            self.set_state(AudioState.IDLE)
            log.info("🔊 Stopped speaking")
    
    def reset(self):
        """Reset audio processor"""
        self.stop_listening()
        self.stop_speaking()
        self._reset_buffer()
        self.audio_chunks_processed = 0
        self.total_processing_time = 0
        log.info("🔄 Audio processor reset")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_processing_time = 0
        if self.audio_chunks_processed > 0:
            avg_processing_time = self.total_processing_time / self.audio_chunks_processed
        
        return {
            "state": self.state.value,
            "audio_chunks_processed": self.audio_chunks_processed,
            "total_processing_time": self.total_processing_time,
            "avg_processing_time": avg_processing_time,
            "current_buffer_size": len(self.audio_buffer),
            "current_audio_length": self.current_audio_length,
            "turn_detector_active": self.turn_detector.is_speaking
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get audio processor information"""
        return {
            "name": "AudioProcessor",
            "state": self.state.value,
            "config": {
                "sample_rate": self.config.sample_rate,
                "channels": self.config.channels,
                "sample_width": self.config.sample_width,
                "chunk_size": self.config.chunk_size,
                "silence_threshold": self.config.silence_threshold,
                "min_audio_length": self.config.min_audio_length,
                "max_audio_length": self.config.max_audio_length,
                "phrase_timeout": self.config.phrase_timeout,
                "turn_detection_enabled": self.config.turn_detection_enabled
            },
            "performance": self.get_performance_stats()
        }

# Global AudioProcessor instance
_audio_processor_instance = None

def get_audio_processor(config: AudioConfig = None) -> AudioProcessor:
    """Get singleton AudioProcessor instance"""
    global _audio_processor_instance
    if _audio_processor_instance is None:
        _audio_processor_instance = AudioProcessor(config)
        log.info("🏭 AudioProcessor initialized (singleton)")
    return _audio_processor_instance

# Convenience functions
def process_audio_chunk(audio_chunk: bytes, config: AudioConfig = None):
    """Process audio chunk"""
    processor = get_audio_processor(config)
    processor.process_audio_chunk(audio_chunk)

def get_audio_info(config: AudioConfig = None) -> Dict[str, Any]:
    """Get AudioProcessor information"""
    processor = get_audio_processor(config)
    return processor.get_info()

if __name__ == "__main__":
    # Test AudioProcessor
    print("🎤 AudioProcessor Test")
    print("=" * 50)
    
    config = AudioConfig(
        sample_rate=16000,
        chunk_size=1024,
        silence_threshold=0.01,
        phrase_timeout=2.0
    )
    
    processor = get_audio_processor(config)
    print(f"✅ AudioProcessor initialized")
    print(f"✅ State: {processor.state.value}")
    print(f"✅ Config: {config}")
    
    print("\n🎤 AudioProcessor is ready for real-time audio processing")
    print("Use start_listening() to begin, process_audio_chunk() for audio data")
    
    print("\n" + "=" * 50)

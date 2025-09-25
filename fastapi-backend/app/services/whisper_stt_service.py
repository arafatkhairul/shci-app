"""
Whisper Speech-to-Text Service
==============================

This service provides Whisper-based speech-to-text functionality for the SHCI voice assistant.
It handles audio processing, transcription, and language detection using OpenAI's Whisper model.

Features:
- Real-time audio transcription
- Multiple language support
- Audio format conversion
- Confidence scoring
- GPU acceleration support

Author: SHCI Development Team
Date: 2025
"""

import asyncio
import io
import logging
import tempfile
import wave
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import numpy as np
from faster_whisper import WhisperModel
import librosa
from app.utils.logger import get_logger

logger = get_logger(__name__)

class WhisperSTTService:
    """
    Whisper-based Speech-to-Text service for real-time audio transcription.
    """
    
    def __init__(self, model_size: str = "base", device: str = "auto"):
        """
        Initialize the Whisper STT service.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to run on (auto, cpu, cuda)
        """
        self.model_size = model_size
        self.device = self._detect_device(device)
        self.model = None
        self.is_initialized = False
        
        # Audio processing parameters
        self.sample_rate = 16000  # Whisper expects 16kHz
        self.chunk_duration = 30  # Process audio in 30-second chunks
        self.min_audio_length = 0.5  # Minimum audio length in seconds
        
        logger.info(f"Whisper STT Service initialized with model: {model_size}, device: {self.device}")
    
    def _detect_device(self, device: str) -> str:
        """Detect the best available device for Whisper."""
        if device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    logger.info("🚀 CUDA detected - Using GPU acceleration")
                    return "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    logger.info("🍎 Apple Silicon detected - Using Metal Performance Shaders")
                    return "mps"  # Apple Silicon
                else:
                    logger.info("💻 Using CPU fallback")
                    return "cpu"
            except ImportError:
                logger.warning("PyTorch not available - Using CPU")
                return "cpu"
        return device
    
    async def initialize(self) -> bool:
        """
        Initialize the Whisper model.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Loading Faster Whisper model: {self.model_size}")
            
            # Load model in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                WhisperModel, 
                self.model_size, 
                self.device
            )
            
            self.is_initialized = True
            logger.info(f"Whisper model loaded successfully on {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Whisper model on {self.device}: {e}")
            
            # If MPS failed, try CPU as fallback
            if self.device == "mps":
                logger.info("MPS failed, trying CPU as fallback...")
                try:
                    self.device = "cpu"
                    self.model = await loop.run_in_executor(
                        None, 
                        WhisperModel, 
                        self.model_size, 
                        "cpu"
                    )
                    self.is_initialized = True
                    logger.info(f"Whisper model loaded successfully on CPU (fallback)")
                    return True
                except Exception as cpu_error:
                    logger.error(f"CPU fallback also failed: {cpu_error}")
                    return False
            # If CUDA failed, try CPU as fallback
            elif self.device == "cuda":
                logger.info("CUDA failed, trying CPU as fallback...")
                try:
                    self.device = "cpu"
                    self.model = await loop.run_in_executor(
                        None, 
                        WhisperModel, 
                        self.model_size, 
                        "cpu"
                    )
                    self.is_initialized = True
                    logger.info(f"Whisper model loaded successfully on CPU (fallback)")
                    return True
                except Exception as cpu_error:
                    logger.error(f"CPU fallback also failed: {cpu_error}")
                    return False
            else:
                return False
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio data using Whisper.
        
        Args:
            audio_data: Raw audio data bytes
            language: Language code (e.g., 'en', 'it') or None for auto-detection
            task: Task type ('transcribe' or 'translate')
            
        Returns:
            Dict containing transcription results
        """
        if not self.is_initialized:
            return {
                "success": False,
                "error": "Whisper model not initialized",
                "transcript": "",
                "confidence": 0.0
            }
        
        try:
            # Convert audio data to numpy array
            audio_array = await self._process_audio_data(audio_data)
            
            if audio_array is None or len(audio_array) == 0:
                return {
                    "success": False,
                    "error": "Invalid audio data",
                    "transcript": "",
                    "confidence": 0.0
                }
            
            # Check minimum audio length
            duration = len(audio_array) / self.sample_rate
            if duration < self.min_audio_length:
                return {
                    "success": False,
                    "error": f"Audio too short: {duration:.2f}s (minimum: {self.min_audio_length}s)",
                    "transcript": "",
                    "confidence": 0.0
                }
            
            # Validate and normalize language
            if language and language not in ["en", "it"]:
                logger.warning(f"Unsupported language '{language}', defaulting to English")
                language = "en"
            elif not language:
                language = "en"  # Default to English
            
            # Transcribe using Whisper
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_with_whisper,
                audio_array,
                language,
                task
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0
            }
    
    def _transcribe_with_whisper(
        self, 
        audio_array: np.ndarray, 
        language: Optional[str], 
        task: str
    ) -> Dict[str, Any]:
        """Transcribe audio using Whisper model."""
        try:
            # Prepare options for Faster Whisper (optimized for speed)
            options = {
                "task": task,
                "fp16": self.device != "cpu",  # Use fp16 for GPU
                "verbose": False,
                "beam_size": 1,  # Faster inference
                "best_of": 1,    # Faster inference
                "patience": 1,   # Faster inference
                "length_penalty": 1.0,
                "repetition_penalty": 1.0,
                "no_repeat_ngram_size": 0,
                "temperature": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                "compression_ratio_threshold": 2.4,
                "log_prob_threshold": -1.0,
                "no_speech_threshold": 0.6,
                "condition_on_previous_text": True,
                "prompt_reset_on_temperature": 0.5,
                "suppress_blank": True,
                "suppress_tokens": [-1],
                "without_timestamps": False,
                "word_timestamps": False,
                "vad_filter": False,
                "max_new_tokens": 0
            }
            
            if language:
                options["language"] = language
            
            # Transcribe using Faster Whisper
            segments, info = self.model.transcribe(audio_array, **options)
            
            # Convert segments to list and extract transcript
            segments_list = list(segments)
            transcript = " ".join([seg.text for seg in segments_list]).strip()
            
            # Filter out gibberish results (patterns of repeated characters/numbers)
            if self._is_gibberish(transcript):
                logger.warning(f"Filtered out gibberish transcript: {transcript[:50]}...")
                return {
                    "success": False,
                    "error": "Audio quality too poor for transcription",
                    "transcript": "",
                    "confidence": 0.0
                }
            
            # Calculate average confidence from segments
            if segments_list:
                avg_confidence = np.mean([seg.avg_logprob for seg in segments_list])
                # Convert log probability to confidence (0-1)
                confidence = min(1.0, max(0.0, np.exp(avg_confidence)))
            else:
                confidence = 0.5  # Default confidence
            
            # Convert segments to dict format for compatibility
            segments_dict = [
                {
                    "id": i,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "avg_logprob": seg.avg_logprob,
                    "no_speech_prob": seg.no_speech_prob
                }
                for i, seg in enumerate(segments_list)
            ]
            
            return {
                "success": True,
                "transcript": transcript,
                "confidence": float(confidence),
                "language": info.language if hasattr(info, 'language') else language,
                "duration": len(audio_array) / self.sample_rate,
                "segments": segments_dict
            }
            
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0
            }
    
    def _is_gibberish(self, text: str) -> bool:
        """Check if transcript appears to be gibberish."""
        if not text or len(text) < 3:
            return True
        
        # Check for patterns of repeated characters/numbers
        if len(set(text)) < 3:  # Too few unique characters
            return True
        
        # Check for patterns like "1.0.1.1.1.1..." or "0.0.0.0..."
        if text.count('.') > len(text) * 0.3:  # Too many dots
            return True
        
        # Check for repeated patterns
        if len(text) > 10:
            # Look for repeated substrings
            for i in range(2, min(10, len(text) // 2)):
                pattern = text[:i]
                if text.count(pattern) > len(text) / (i * 2):
                    return True
        
        return False
    
    async def _process_audio_data(self, audio_data: bytes) -> Optional[np.ndarray]:
        """
        Process raw audio data and convert to the format expected by Whisper.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            numpy array of audio samples or None if processing fails
        """
        try:
            # Try to load as WAV first
            try:
                with io.BytesIO(audio_data) as audio_io:
                    audio_array, sr = librosa.load(audio_io, sr=self.sample_rate, dtype=np.float32)
                    # Ensure float32 dtype to avoid dtype mismatches
                    audio_array = audio_array.astype(np.float32)
                    return audio_array
            except Exception:
                # If WAV loading fails, try to process as raw audio
                pass
            
            # Try to process as raw audio data
            try:
                # Check if this looks like WAV data (starts with RIFF header)
                if audio_data.startswith(b'RIFF') or audio_data.startswith(b'data'):
                    # Try to process as WAV using librosa
                    with io.BytesIO(audio_data) as audio_io:
                        audio_array, sr = librosa.load(audio_io, sr=self.sample_rate, dtype=np.float32)
                        return audio_array.astype(np.float32)
                
                # Assume 16-bit PCM audio (most common for real-time streaming)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Validate audio data - check if it looks like real audio
                if len(audio_array) == 0 or np.all(audio_array == 0):
                    logger.warning("Received empty or silent audio data")
                    return None
                
                # Check for binary patterns that indicate corrupted data
                unique_values = len(np.unique(audio_array))
                if unique_values < 10:  # Too few unique values suggests binary data
                    logger.warning(f"Audio data appears corrupted (only {unique_values} unique values)")
                    return None
                
                # Convert to float32 and normalize
                audio_array = audio_array.astype(np.float32) / 32768.0
                
                # Resample if necessary (assume 44.1kHz input)
                if len(audio_array) > 0:
                    target_length = int(len(audio_array) * self.sample_rate / 44100)
                    if target_length != len(audio_array):
                        audio_array = np.interp(
                            np.linspace(0, len(audio_array), target_length, dtype=np.float32),
                            np.arange(len(audio_array), dtype=np.float32),
                            audio_array
                        ).astype(np.float32)
                
                # Ensure final dtype is float32
                return audio_array.astype(np.float32)
                
            except Exception as e:
                logger.error(f"Audio processing failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Audio data processing error: {e}")
            return None
    
    async def transcribe_file(self, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe an audio file.
        
        Args:
            file_path: Path to audio file
            language: Language code or None for auto-detection
            
        Returns:
            Dict containing transcription results
        """
        try:
            with open(file_path, 'rb') as f:
                audio_data = f.read()
            
            return await self.transcribe_audio(audio_data, language)
            
        except Exception as e:
            logger.error(f"File transcription failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0
            }
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        return [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
            "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no",
            "fi", "cs", "hu", "ro", "bg", "hr", "sk", "sl", "et", "lv",
            "lt", "el", "he", "ur", "bn", "ta", "te", "ml", "kn", "gu",
            "pa", "or", "as", "ne", "si", "my", "km", "lo", "ka", "am",
            "sw", "zu", "af", "sq", "az", "be", "bs", "ca", "cy", "eo",
            "eu", "fa", "gl", "is", "mk", "ms", "mt", "sr", "tl", "uk"
        ]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "is_initialized": self.is_initialized,
            "sample_rate": self.sample_rate,
            "supported_languages": self.get_supported_languages()
        }
    
    async def cleanup(self):
        """Clean up resources."""
        if self.model:
            del self.model
            self.model = None
        self.is_initialized = False
        logger.info("Whisper STT service cleaned up")

# Global instance
whisper_stt_service = None

async def get_whisper_stt_service() -> WhisperSTTService:
    """Get or create the global Whisper STT service instance."""
    global whisper_stt_service
    
    if whisper_stt_service is None:
        whisper_stt_service = WhisperSTTService()
        await whisper_stt_service.initialize()
    
    return whisper_stt_service

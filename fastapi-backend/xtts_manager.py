#!/usr/bin/env python3
"""
XTTS Manager - Professional XTTS (Coqui TTS) Integration
Handles XTTS model loading, voice synthesis, and configuration management.
Based on simple_tts_test.py implementation with reference audio support.
"""

import os
import io
import logging
import threading
import time
import warnings
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

import torch
import numpy as np
import soundfile as sf
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig
from TTS.config.shared_configs import BaseDatasetConfig
from TTS.tts.models.xtts import XttsArgs

log = logging.getLogger("xtts_manager")

# --- PyTorch 2.6+ FIX ---
# The xtts_v2 model file contains multiple configuration objects
# which PyTorch's new security protocol blocks by default.
# We need to explicitly allowlist all of them.
try:
    torch.serialization.add_safe_globals([
        XttsConfig,
        XttsAudioConfig,
        BaseDatasetConfig,
        XttsArgs
    ])
except AttributeError:
    # PyTorch version doesn't support add_safe_globals
    log.warning("PyTorch version doesn't support add_safe_globals, using alternative approach")
    # Set environment variable to disable weights_only globally
    os.environ['TORCH_WEIGHTS_ONLY'] = 'False'

# Suppress unnecessary warnings from libraries
warnings.filterwarnings("ignore", category=UserWarning)

class XTTSManager:
    """
    Professional XTTS Manager for high-quality text-to-speech synthesis.
    Supports multiple languages, voices, and real-time synthesis.
    """
    
    def __init__(self):
        self.tts = None
        self.model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False
        self.lock = threading.Lock()
        
        # Performance optimization settings
        self.use_fp16 = True  # Enable FP16 for faster inference
        self.use_amp = True   # Enable Automatic Mixed Precision
        self.use_inference_mode = True  # Enable torch inference mode
        self.compiled_model = None  # Store compiled model for optimization
        
        # Reference audio configuration (from simple_tts_test.py)
        self.reference_voice_path = "00005.wav"  # Default reference audio
        self.fallback_speaker = "Tammie Ema"  # Fallback speaker name
        
        # Default settings
        self.sample_rate = 22050
        self.language = "en"
        self.speed = 1.0
        self.temperature = 0.75
        self.length_penalty = 1.0
        self.repetition_penalty = 2.0
        self.top_k = 50
        self.top_p = 0.85
        
        # Available languages
        self.supported_languages = {
            "en": "English",
            "es": "Spanish", 
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "pl": "Polish",
            "tr": "Turkish",
            "ru": "Russian",
            "nl": "Dutch",
            "cs": "Czech",
            "ar": "Arabic",
            "zh": "Chinese",
            "ja": "Japanese",
            "hu": "Hungarian",
            "ko": "Korean"
        }
        
        log.info(f"XTTS Manager initialized on device: {self.device}")
        log.info(f"Reference voice path: {self.reference_voice_path}")
        log.info(f"Fallback speaker: {self.fallback_speaker}")
        log.info(f"Performance optimizations: FP16={self.use_fp16}, AMP={self.use_amp}, Inference Mode={self.use_inference_mode}")
    
    def load_model(self, model_name: str = None) -> bool:
        """
        Load XTTS model with professional error handling.
        Based on simple_tts_test.py implementation.
        
        Args:
            model_name: Optional model name to load
            
        Returns:
            bool: True if model loaded successfully
        """
        try:
            with self.lock:
                if self.is_loaded:
                    log.info("Model already loaded")
                    return True
                
                log.info("🚀 Initializing TTS model...")
                start_time = time.time()
                
                # Use provided model name or default
                self.model_name = model_name or self.model_name
                
                # Initialize TTS with XTTS model (from simple_tts_test.py approach)
                try:
                    # Alternative approach: Use context manager for safer loading
                    with torch.serialization.safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs]):
                        self.tts = TTS(self.model_name).to(self.device)
                    log.info("✅ TTS model initialized successfully.")
                except Exception as e:
                    log.error(f"❌ Failed to initialize TTS model: {e}")
                    # Try one more approach with weights_only=False as fallback
                    try:
                        log.info("Trying alternative loading method...")
                        self.tts = TTS(self.model_name, weights_only=False).to(self.device)
                        log.info("✅ TTS model initialized successfully with weights_only=False.")
                    except Exception as e2:
                        log.error(f"❌ All initialization attempts failed: {e2}")
                        return False
                
                # Apply performance optimizations
                self._apply_optimizations()
                
                load_time = time.time() - start_time
                self.is_loaded = True
                
                log.info(f"✅ XTTS model loaded successfully in {load_time:.2f}s")
                log.info(f"Model: {self.model_name}")
                log.info(f"Device: {self.device}")
                
                return True
                
        except Exception as e:
            log.error(f"❌ Failed to load XTTS model: {e}")
            self.is_loaded = False
            return False
    
    def _apply_optimizations(self):
        """
        Apply performance optimizations to the loaded model.
        Enables FP16, AMP, inference mode, and model compilation.
        """
        try:
            if not self.tts or not self.is_loaded:
                log.warning("Cannot apply optimizations: model not loaded")
                return
            
            log.info("🚀 Applying performance optimizations...")
            
            # Enable FP16 if supported
            if self.use_fp16 and self.device == "cuda":
                try:
                    # Convert model to half precision
                    if hasattr(self.tts, 'model') and hasattr(self.tts.model, 'half'):
                        self.tts.model = self.tts.model.half()
                        log.info("✅ FP16 optimization enabled")
                    else:
                        log.warning("⚠️ FP16 not supported for this model")
                except Exception as e:
                    log.warning(f"⚠️ FP16 optimization failed: {e}")
            
            # Enable Automatic Mixed Precision (AMP)
            if self.use_amp and self.device == "cuda":
                try:
                    # Enable AMP autocast
                    torch.backends.cudnn.benchmark = True
                    torch.backends.cudnn.deterministic = False
                    log.info("✅ AMP optimization enabled")
                except Exception as e:
                    log.warning(f"⚠️ AMP optimization failed: {e}")
            
            # Enable inference mode optimization
            if self.use_inference_mode:
                try:
                    # Set model to eval mode for inference
                    if hasattr(self.tts, 'model'):
                        self.tts.model.eval()
                    log.info("✅ Inference mode optimization enabled")
                except Exception as e:
                    log.warning(f"⚠️ Inference mode optimization failed: {e}")
            
            # Model compilation (PyTorch 2.0+)
            if hasattr(torch, 'compile') and self.device == "cuda":
                try:
                    log.info("🔄 Compiling model for maximum performance...")
                    if hasattr(self.tts, 'model'):
                        self.compiled_model = torch.compile(self.tts.model, mode="max-autotune")
                        log.info("✅ Model compilation completed")
                    else:
                        log.warning("⚠️ Model compilation not available")
                except Exception as e:
                    log.warning(f"⚠️ Model compilation failed: {e}")
            
            log.info("🎯 Performance optimizations applied successfully!")
            
        except Exception as e:
            log.error(f"❌ Error applying optimizations: {e}")
    
    def _get_optimized_model(self):
        """
        Get the optimized model for inference.
        Returns compiled model if available, otherwise original model.
        """
        if self.compiled_model:
            return self.compiled_model
        elif hasattr(self.tts, 'model'):
            return self.tts.model
        else:
            return self.tts
    
    def set_language(self, language: str) -> bool:
        """
        Set synthesis language.
        
        Args:
            language: Language code (e.g., 'en', 'es', 'fr')
            
        Returns:
            bool: True if language is supported
        """
        if language in self.supported_languages:
            self.language = language
            log.info(f"Language set to: {self.supported_languages[language]} ({language})")
            return True
        else:
            log.error(f"Unsupported language: {language}")
            return False
    
    def set_speaker_wav(self, speaker_wav_path: str) -> bool:
        """
        Set reference speaker audio file for voice cloning.
        Based on simple_tts_test.py implementation.
        
        Args:
            speaker_wav_path: Path to reference speaker audio file
            
        Returns:
            bool: True if speaker file is valid
        """
        try:
            if os.path.exists(speaker_wav_path):
                self.reference_voice_path = speaker_wav_path
                log.info(f"🎙️ Reference file found at '{speaker_wav_path}'. Using it for voice output.")
                return True
            else:
                log.warning(f"⚠️ Warning: Reference file not found at '{speaker_wav_path}'.")
                log.info(f"--> Using fallback default speaker: '{self.fallback_speaker}'")
                return False
        except Exception as e:
            log.error(f"Error setting speaker file: {e}")
            return False
    
    def set_synthesis_params(self, **kwargs) -> bool:
        """
        Set synthesis parameters for fine-tuning output quality.
        
        Args:
            **kwargs: Synthesis parameters (speed, temperature, etc.)
            
        Returns:
            bool: True if parameters are valid
        """
        try:
            if 'speed' in kwargs:
                self.speed = max(0.5, min(2.0, kwargs['speed']))
            if 'temperature' in kwargs:
                self.temperature = max(0.1, min(1.0, kwargs['temperature']))
            if 'length_penalty' in kwargs:
                self.length_penalty = max(0.1, min(2.0, kwargs['length_penalty']))
            if 'repetition_penalty' in kwargs:
                self.repetition_penalty = max(1.0, min(5.0, kwargs['repetition_penalty']))
            if 'top_k' in kwargs:
                self.top_k = max(1, min(100, kwargs['top_k']))
            if 'top_p' in kwargs:
                self.top_p = max(0.1, min(1.0, kwargs['top_p']))
            
            log.info(f"Synthesis parameters updated: speed={self.speed}, temp={self.temperature}")
            return True
            
        except Exception as e:
            log.error(f"Error setting synthesis parameters: {e}")
            return False
    
    def synthesize_text(self, text: str, language: str = None, speaker_wav: str = None) -> bytes:
        """
        Synthesize text to speech with professional quality.
        Based on simple_tts_test.py implementation with reference audio support.
        
        Args:
            text: Text to synthesize
            language: Language code (optional, uses current setting if not provided)
            speaker_wav: Speaker reference file (optional)
            
        Returns:
            bytes: Audio data in WAV format
        """
        try:
            if not self.is_loaded:
                log.error("Model not loaded. Call load_model() first.")
                return b""
            
            if not text.strip():
                log.error("Empty text provided")
                return b""
            
            # Use provided language or current setting
            synthesis_language = language or self.language
            
            log.info(f"Synthesizing audio for: '{text[:50]}...'")
            start_time = time.time()
            
            with self.lock:
                # Determine speaker parameters (from simple_tts_test.py logic)
                speaker_wav_param = None
                speaker_param = None
                
                # Check if the reference audio file exists
                reference_to_check = speaker_wav or self.reference_voice_path
                if os.path.exists(reference_to_check):
                    log.info(f"🎙️ Reference file found at '{reference_to_check}'. Using it for voice output.")
                    speaker_wav_param = reference_to_check
                else:
                    log.warning(f"⚠️ Warning: Reference file not found at '{reference_to_check}'.")
                    log.info(f"--> Using fallback default speaker: '{self.fallback_speaker}'")
                    speaker_param = self.fallback_speaker
                
                # Synthesize with XTTS using optimized inference
                try:
                    # Use optimized inference context
                    with torch.inference_mode() if self.use_inference_mode else torch.no_grad():
                        # Enable AMP autocast if available
                        if self.use_amp and self.device == "cuda":
                            with torch.autocast(device_type='cuda', dtype=torch.float16 if self.use_fp16 else torch.float32):
                                # Use the appropriate parameter based on whether the reference file was found
                                if speaker_wav_param:
                                    # Use reference audio for voice cloning
                                    audio_data = self.tts.tts(
                                        text=text,
                                        speaker_wav=speaker_wav_param,
                                        language=synthesis_language,
                                    )
                                else:
                                    # Use default speaker
                                    audio_data = self.tts.tts(
                                        text=text,
                                        speaker=speaker_param,
                                        language=synthesis_language,
                                    )
                        else:
                            # Use the appropriate parameter based on whether the reference file was found
                            if speaker_wav_param:
                                # Use reference audio for voice cloning
                                audio_data = self.tts.tts(
                                    text=text,
                                    speaker_wav=speaker_wav_param,
                                    language=synthesis_language,
                                )
                            else:
                                # Use default speaker
                                audio_data = self.tts.tts(
                                    text=text,
                                    speaker=speaker_param,
                                    language=synthesis_language,
                                )
                    
                    # Convert audio data to bytes if it's a list or numpy array
                    import numpy as np
                    import torch
                    
                    if isinstance(audio_data, list):
                        # If it's a list, convert each element to numpy array and concatenate
                        processed_audio = []
                        for item in audio_data:
                            if isinstance(item, torch.Tensor):
                                # Convert torch tensor to numpy
                                item = item.detach().cpu().numpy()
                            if isinstance(item, np.ndarray):
                                # Ensure it's at least 1D
                                item = np.atleast_1d(item)
                            else:
                                # Convert scalar to numpy array
                                item = np.array([item])
                            processed_audio.append(item)
                        
                        # Concatenate all audio segments
                        audio_data = np.concatenate(processed_audio)
                    
                    elif isinstance(audio_data, torch.Tensor):
                        # Convert torch tensor to numpy
                        audio_data = audio_data.detach().cpu().numpy()
                    
                    if isinstance(audio_data, np.ndarray):
                        # Ensure it's at least 1D
                        audio_data = np.atleast_1d(audio_data)
                        
                        # Convert numpy array to bytes using soundfile
                        import soundfile as sf
                        audio_bytes = io.BytesIO()
                        sf.write(audio_bytes, audio_data, self.sample_rate, format='WAV')
                        audio_data = audio_bytes.getvalue()
                    
                    if len(audio_data) > 0:
                        log.info(f"✅ Synthesis completed successfully")
                    else:
                        log.error("❌ Audio generation failed. The output file was empty.")
                        return b""
                        
                except Exception as synthesis_error:
                    log.error(f"❌ An error occurred during audio generation: {synthesis_error}")
                    return b""
            
            synthesis_time = time.time() - start_time
            
            log.info(f"✅ Synthesis completed in {synthesis_time:.2f}s")
            log.info(f"Audio size: {len(audio_data)} bytes")
            
            return audio_data
            
        except Exception as e:
            log.error(f"❌ Synthesis failed: {e}")
            import traceback
            traceback.print_exc()
            return b""
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get current model information and status.
        
        Returns:
            Dict containing model information
        """
        return {
            "tts_system": "XTTS (Coqui TTS)",
            "model_name": self.model_name,
            "device": self.device,
            "is_loaded": self.is_loaded,
            "sample_rate": self.sample_rate,
            "current_language": self.language,
            "supported_languages": self.supported_languages,
            "reference_voice_path": self.reference_voice_path,
            "fallback_speaker": self.fallback_speaker,
            "performance_optimizations": {
                "fp16_enabled": self.use_fp16,
                "amp_enabled": self.use_amp,
                "inference_mode_enabled": self.use_inference_mode,
                "model_compiled": self.compiled_model is not None,
                "cuda_available": torch.cuda.is_available(),
                "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
            },
            "synthesis_params": {
                "speed": self.speed,
                "temperature": self.temperature,
                "length_penalty": self.length_penalty,
                "repetition_penalty": self.repetition_penalty,
                "top_k": self.top_k,
                "top_p": self.top_p
            }
        }
    
    def list_available_models(self) -> List[str]:
        """
        List available XTTS models.
        
        Returns:
            List of available model names
        """
        return [
            "tts_models/multilingual/multi-dataset/xtts_v2",
            "tts_models/multilingual/multi-dataset/xtts_v1.1"
        ]
    
    def get_available_voices(self) -> List[Dict[str, str]]:
        """
        Get available voice options.
        
        Returns:
            List of voice information dictionaries
        """
        return [
            {"name": "Default", "description": "Default XTTS voice", "language": "multilingual"},
            {"name": "Custom Speaker", "description": "Custom speaker from audio file", "language": "multilingual"}
        ]
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the XTTS system.
        
        Returns:
            Dict containing health status
        """
        try:
            if not self.is_loaded:
                return {"status": "not_loaded", "message": "Model not loaded"}
            
            # Test synthesis
            test_text = "Hello, this is a test."
            test_audio = self.synthesize_text(test_text)
            
            if test_audio:
                return {
                    "status": "healthy",
                    "message": "XTTS system is working properly",
                    "test_audio_size": len(test_audio)
                }
            else:
                return {"status": "error", "message": "Test synthesis failed"}
                
        except Exception as e:
            return {"status": "error", "message": f"Health check failed: {e}"}
    
    def cleanup(self):
        """Clean up resources."""
        try:
            with self.lock:
                if self.compiled_model:
                    del self.compiled_model
                    self.compiled_model = None
                if self.tts:
                    del self.tts
                    self.tts = None
                self.is_loaded = False
                log.info("XTTS resources cleaned up")
        except Exception as e:
            log.error(f"Error during cleanup: {e}")

# Global XTTS manager instance
xtts_manager = XTTSManager()

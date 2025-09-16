#!/usr/bin/env python3
"""
Coqui TTS Provider - Based on RealtimeVoiceChat implementation
High-quality TTS with multiple voice support and optimization
"""

import os
import logging
import asyncio
import tempfile
import wave
import io
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod

log = logging.getLogger("coqui_tts")

# Import Coqui TTS
try:
    from TTS.api import TTS
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    COQUI_TTS_AVAILABLE = True
except ImportError:
    COQUI_TTS_AVAILABLE = False
    log.warning("Coqui TTS not available - install with: pip install TTS")

# Import PyTorch for GPU support
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    log.warning("PyTorch not available - install with: pip install torch")

class CoquiTTSProvider:
    """Coqui TTS provider with optimization similar to RealtimeVoiceChat"""
    
    def __init__(self):
        self.name = "Coqui TTS"
        self.available = COQUI_TTS_AVAILABLE and TORCH_AVAILABLE
        self.tts_model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._voice_cache = {}
        self._initialized = False
        
        # Voice configurations (similar to RealtimeVoiceChat)
        self.voice_configs = {
            "default": {
                "name": "Default Voice",
                "model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
                "language": "en",
                "speaker_wav": None
            },
            "female": {
                "name": "Female Voice",
                "model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
                "language": "en",
                "speaker_wav": None
            },
            "male": {
                "name": "Male Voice", 
                "model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
                "language": "en",
                "speaker_wav": None
            }
        }
        
        # Current voice settings
        self.current_voice = "default"
        self.sample_rate = 22050
        
        # Performance settings
        self.use_deepspeed = os.getenv("USE_DEEPSPEED", "false").lower() == "true"
        self.gpu_id = int(os.getenv("CUDA_VISIBLE_DEVICES", "0"))
        
        if self.available:
            self._initialize_tts()
            self._initialized = True
            log.info(f"✅ Coqui TTS initialized with device: {self.device}")
        else:
            log.warning("❌ Coqui TTS not available")
    
    def _initialize_tts(self):
        """Initialize Coqui TTS model with optimization"""
        try:
            log.info("🎤 Initializing Coqui TTS model...")
            
            # Initialize TTS with optimization
            self.tts_model = TTS(
                model_name=self.voice_configs[self.current_voice]["model_name"],
                progress_bar=False,
                gpu=self.device == "cuda"
            )
            
            # Move to device
            if self.device == "cuda":
                self.tts_model.to(self.device)
                log.info(f"🚀 TTS model loaded on GPU {self.gpu_id}")
            else:
                log.info("💻 TTS model loaded on CPU")
            
            # Cache the model
            self._voice_cache[self.current_voice] = self.tts_model
            log.info(f"💾 Voice cached: {self.current_voice}")
            
        except Exception as e:
            log.error(f"Failed to initialize Coqui TTS: {e}")
            self.available = False
    
    def set_voice(self, voice_id: str):
        """Switch to a different voice model"""
        if voice_id not in self.voice_configs:
            log.warning(f"Voice {voice_id} not found, using default")
            voice_id = "default"
        
        if voice_id != self.current_voice:
            log.info(f"🎤 Switching voice from {self.current_voice} to {voice_id}")
            
            # Check if voice is already cached
            if voice_id in self._voice_cache:
                log.info(f"🎤 Using cached voice: {voice_id}")
                self.tts_model = self._voice_cache[voice_id]
                self.current_voice = voice_id
                log.info(f"✅ Voice switched successfully to {voice_id} (from cache)")
            else:
                # Load new voice model
                log.info(f"🎤 Loading new voice model: {voice_id}")
                try:
                    voice_config = self.voice_configs[voice_id]
                    self.tts_model = TTS(
                        model_name=voice_config["model_name"],
                        progress_bar=False,
                        gpu=self.device == "cuda"
                    )
                    
                    if self.device == "cuda":
                        self.tts_model.to(self.device)
                    
                    # Cache the new voice
                    self._voice_cache[voice_id] = self.tts_model
                    self.current_voice = voice_id
                    
                    log.info(f"✅ Voice switched successfully to {voice_id}")
                except Exception as e:
                    log.error(f"❌ Failed to load voice model for {voice_id}: {e}")
    
    async def synthesize_async(self, text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
        """Asynchronously synthesize text using Coqui TTS"""
        if not self.available or not self.tts_model:
            raise RuntimeError("Coqui TTS not available")
        
        # Switch voice if specified
        if voice and voice != self.current_voice:
            self.set_voice(voice)
        
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.synthesize_sync, text, language, voice, **kwargs)
        except Exception as e:
            log.error(f"Synthesis error: {e}")
            return b""
    
    def synthesize_sync(self, text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
        """Synchronously synthesize text using Coqui TTS"""
        if not self.available or not self.tts_model:
            raise RuntimeError("Coqui TTS not available")
        
        # Switch voice if specified
        if voice and voice != self.current_voice:
            self.set_voice(voice)
        
        try:
            # Create temporary file for audio output
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            # Get voice configuration
            voice_config = self.voice_configs[self.current_voice]
            
            # Synthesize audio using Coqui TTS
            self.tts_model.tts_to_file(
                text=text,
                file_path=temp_path,
                language=language,
                speaker_wav=voice_config.get("speaker_wav")
            )
            
            # Read the generated audio file
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            log.info(f"✅ Coqui TTS synthesis completed: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            log.error(f"Coqui TTS synthesis failed: {e}")
            return b""
    
    def synthesize_stream_optimized(self, text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
        """Optimized synthesis for real-time response using memory buffer"""
        if not self.available or not self.tts_model:
            raise RuntimeError("Coqui TTS not available")
        
        # Switch voice if specified
        if voice and voice != self.current_voice:
            self.set_voice(voice)
        
        try:
            # Use memory buffer for faster processing
            wav_buffer = io.BytesIO()
            
            # Get voice configuration
            voice_config = self.voice_configs[self.current_voice]
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            # Synthesize audio
            self.tts_model.tts_to_file(
                text=text,
                file_path=temp_path,
                language=language,
                speaker_wav=voice_config.get("speaker_wav")
            )
            
            # Read into memory buffer
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            # Clean up
            os.unlink(temp_path)
            
            return audio_data
            
        except Exception as e:
            log.error(f"Optimized Coqui TTS synthesis failed: {e}")
            return b""
    
    def is_available(self) -> bool:
        """Check if Coqui TTS is available"""
        return self.available and self.tts_model is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get Coqui TTS system information"""
        info = {
            "name": self.name,
            "available": self.is_available(),
            "system_type": "Coqui TTS",
            "environment": "production",
            "current_voice": self.current_voice,
            "voice_configs": self.voice_configs,
            "device": self.device,
            "sample_rate": self.sample_rate,
            "use_deepspeed": self.use_deepspeed,
            "gpu_id": self.gpu_id,
            "cached_voices": list(self._voice_cache.keys())
        }
        
        return info

# Global Coqui TTS provider instance
_coqui_provider_instance = None

def get_coqui_provider() -> CoquiTTSProvider:
    """Get singleton Coqui TTS provider instance"""
    global _coqui_provider_instance
    if _coqui_provider_instance is None:
        _coqui_provider_instance = CoquiTTSProvider()
        log.info("🏭 Coqui TTS Provider initialized (singleton)")
    return _coqui_provider_instance

# Convenience functions
async def synthesize_text_coqui(text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
    """Synthesize text using Coqui TTS"""
    provider = get_coqui_provider()
    return await provider.synthesize_async(text, language, voice, **kwargs)

def synthesize_text_coqui_sync(text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
    """Synchronously synthesize text using Coqui TTS"""
    provider = get_coqui_provider()
    return provider.synthesize_sync(text, language, voice, **kwargs)

def get_coqui_info() -> Dict[str, Any]:
    """Get Coqui TTS system information"""
    provider = get_coqui_provider()
    return provider.get_info()

if __name__ == "__main__":
    # Test Coqui TTS
    print("🎤 Coqui TTS Test")
    print("=" * 50)
    
    provider = get_coqui_provider()
    print(f"✅ TTS System: {provider.name}")
    print(f"✅ Available: {provider.is_available()}")
    print(f"✅ Device: {provider.device}")
    
    if provider.is_available():
        # Test synthesis
        test_text = "Hello! This is a test of the Coqui TTS system."
        print(f"\n🎤 Testing synthesis with: '{test_text}'")
        
        try:
            audio_data = provider.synthesize_sync(test_text, "en")
            if audio_data:
                print(f"✅ Synthesis successful: {len(audio_data)} bytes")
            else:
                print("❌ Synthesis failed")
        except Exception as e:
            print(f"❌ Synthesis error: {e}")
    
    print("\n" + "=" * 50)

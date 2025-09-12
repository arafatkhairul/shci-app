#!/usr/bin/env python3
"""
TTS Factory Pattern
Environment-based TTS system selection (gTTS for local, Coqui TTS for production).
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod
from enum import Enum

log = logging.getLogger("tts_factory")

# Import TTS systems
try:
    from gtts import gTTS
    import pygame
    pygame.mixer.init()
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    log.warning("gTTS not available - install with: pip install gtts pygame")

try:
    from xtts_manager import xtts_manager
    COQUI_TTS_AVAILABLE = True
except ImportError:
    COQUI_TTS_AVAILABLE = False
    log.warning("Coqui TTS not available")

class TTSEnvironment(Enum):
    """TTS Environment types."""
    LOCAL = "local"
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    LIVE = "live"

class TTSSystem(Enum):
    """TTS System types."""
    GTTS = "gtts"
    COQUI = "coqui"
    FALLBACK = "fallback"

class TTSInterface(ABC):
    """Abstract TTS interface."""
    
    @abstractmethod
    async def synthesize_async(self, text: str, language: str = "en", **kwargs) -> bytes:
        """Asynchronously synthesize text to speech."""
        pass
    
    @abstractmethod
    def synthesize_sync(self, text: str, language: str = "en", **kwargs) -> bytes:
        """Synchronously synthesize text to speech."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if TTS system is available."""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get TTS system information."""
        pass

class GTTSProvider(TTSInterface):
    """gTTS provider for local/development environment."""
    
    def __init__(self):
        self.name = "Google Text-to-Speech (gTTS)"
        self.available = GTTS_AVAILABLE
        self.sample_rate = 22050
        self.supported_languages = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ar": "Arabic",
            "hi": "Hindi",
            "bn": "Bengali"
        }
        
        if self.available:
            log.info("✅ gTTS provider initialized")
        else:
            log.warning("❌ gTTS provider not available")
    
    async def synthesize_async(self, text: str, language: str = "en", **kwargs) -> bytes:
        """Asynchronously synthesize text using gTTS."""
        if not self.available:
            raise RuntimeError("gTTS not available")
        
        try:
            # gTTS doesn't support speaker_wav, so filter it out
            gtts_kwargs = {k: v for k, v in kwargs.items() if k != 'speaker_wav'}
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.synthesize_sync, text, language, **gtts_kwargs)
        except Exception as e:
            log.error(f"gTTS async synthesis failed: {e}")
            return b""
    
    def synthesize_sync(self, text: str, language: str = "en", **kwargs) -> bytes:
        """Synchronously synthesize text using gTTS."""
        if not self.available:
            raise RuntimeError("gTTS not available")
        
        try:
            import io
            import tempfile
            
            # gTTS doesn't support speaker_wav, so filter it out
            gtts_kwargs = {k: v for k, v in kwargs.items() if k != 'speaker_wav'}
            
            # Create gTTS object
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                tts.save(tmp_file.name)
                
                # Convert MP3 to WAV bytes
                import pydub
                audio = pydub.AudioSegment.from_mp3(tmp_file.name)
                
                # Convert to WAV bytes
                wav_buffer = io.BytesIO()
                audio.export(wav_buffer, format="wav")
                audio_data = wav_buffer.getvalue()
                
                # Clean up temporary file
                os.unlink(tmp_file.name)
                
                log.info(f"✅ gTTS synthesis completed: {len(audio_data)} bytes")
                return audio_data
                
        except Exception as e:
            log.error(f"gTTS synthesis failed: {e}")
            return b""
    
    def is_available(self) -> bool:
        """Check if gTTS is available."""
        return self.available
    
    def get_info(self) -> Dict[str, Any]:
        """Get gTTS system information."""
        return {
            "name": self.name,
            "available": self.available,
            "sample_rate": self.sample_rate,
            "supported_languages": self.supported_languages,
            "system_type": "gTTS",
            "environment": "local/development"
        }

class CoquiTTSProvider(TTSInterface):
    """Coqui TTS provider for production/live environment."""
    
    def __init__(self):
        self.name = "Coqui TTS (XTTS)"
        self.available = COQUI_TTS_AVAILABLE
        self.manager = xtts_manager if COQUI_TTS_AVAILABLE else None
        
        if self.available:
            log.info("✅ Coqui TTS provider initialized")
        else:
            log.warning("❌ Coqui TTS provider not available")
    
    async def synthesize_async(self, text: str, language: str = "en", speaker_wav: str = None, **kwargs) -> bytes:
        """Asynchronously synthesize text using Coqui TTS."""
        if not self.available:
            raise RuntimeError("Coqui TTS not available")
        
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                self.manager.synthesize_text, 
                text, 
                language, 
                speaker_wav
            )
        except Exception as e:
            log.error(f"Coqui TTS async synthesis failed: {e}")
            return b""
    
    def synthesize_sync(self, text: str, language: str = "en", speaker_wav: str = None, **kwargs) -> bytes:
        """Synchronously synthesize text using Coqui TTS."""
        if not self.available:
            raise RuntimeError("Coqui TTS not available")
        
        try:
            return self.manager.synthesize_text(text, language, speaker_wav)
        except Exception as e:
            log.error(f"Coqui TTS synthesis failed: {e}")
            return b""
    
    def is_available(self) -> bool:
        """Check if Coqui TTS is available."""
        return self.available
    
    def get_info(self) -> Dict[str, Any]:
        """Get Coqui TTS system information."""
        info = {
            "name": self.name,
            "available": self.available,
            "system_type": "Coqui TTS",
            "environment": "production/live"
        }
        
        if self.available and self.manager:
            manager_info = self.manager.get_model_info()
            info.update(manager_info)
        
        return info

class FallbackTTSProvider(TTSInterface):
    """Fallback TTS provider using system TTS."""
    
    def __init__(self):
        self.name = "System Fallback TTS"
        self.available = True
        self.sample_rate = 22050
        
        log.info("✅ Fallback TTS provider initialized")
    
    async def synthesize_async(self, text: str, language: str = "en", **kwargs) -> bytes:
        """Asynchronously synthesize text using fallback TTS."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.synthesize_sync, text, language, **kwargs)
        except Exception as e:
            log.error(f"Fallback TTS async synthesis failed: {e}")
            return b""
    
    def synthesize_sync(self, text: str, language: str = "en", **kwargs) -> bytes:
        """Synchronously synthesize text using fallback TTS."""
        try:
            import pyttsx3
            import tempfile
            import os
            
            # Initialize TTS engine
            engine = pyttsx3.init()
            
            # Configure engine
            engine.setProperty('rate', 200)  # Speed
            engine.setProperty('volume', 0.8)  # Volume
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            try:
                # Save to temporary file
                engine.save_to_file(text, temp_path)
                engine.runAndWait()
                
                # Read the generated audio file
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                log.info(f"✅ Fallback TTS synthesis completed: {len(audio_data)} bytes")
                return audio_data
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            log.error(f"Fallback TTS synthesis failed: {e}")
            return b""
    
    def is_available(self) -> bool:
        """Check if fallback TTS is available."""
        return self.available
    
    def get_info(self) -> Dict[str, Any]:
        """Get fallback TTS system information."""
        return {
            "name": self.name,
            "available": self.available,
            "sample_rate": self.sample_rate,
            "system_type": "Fallback",
            "environment": "any"
        }

class TTSFactory:
    """Factory for creating TTS providers based on environment."""
    
    def __init__(self):
        self.providers = {
            TTSSystem.GTTS: GTTSProvider(),
            TTSSystem.COQUI: CoquiTTSProvider(),
            TTSSystem.FALLBACK: FallbackTTSProvider()
        }
        
        # Environment configuration
        self.environment = self._detect_environment()
        self.preferred_system = self._get_preferred_system()
        
        log.info(f"TTS Factory initialized - Environment: {self.environment.value}, Preferred: {self.preferred_system.value}")
    
    def _detect_environment(self) -> TTSEnvironment:
        """Detect current environment."""
        env_str = os.getenv("TTS_ENVIRONMENT", "").lower()
        
        if env_str in ["local", "development", "dev"]:
            return TTSEnvironment.LOCAL
        elif env_str in ["production", "live", "prod"]:
            return TTSEnvironment.PRODUCTION
        else:
            # Auto-detect based on other environment variables
            if os.getenv("ENVIRONMENT") == "production" or os.getenv("NODE_ENV") == "production":
                return TTSEnvironment.PRODUCTION
            else:
                return TTSEnvironment.LOCAL
    
    def _get_preferred_system(self) -> TTSSystem:
        """Get preferred TTS system based on environment."""
        # Check explicit configuration
        tts_system = os.getenv("TTS_SYSTEM", "").lower()
        
        if tts_system == "gtts":
            return TTSSystem.GTTS
        elif tts_system == "coqui":
            return TTSSystem.COQUI
        elif tts_system == "fallback":
            return TTSSystem.FALLBACK
        
        # Auto-select based on environment
        if self.environment == TTSEnvironment.LOCAL:
            if self.providers[TTSSystem.GTTS].is_available():
                return TTSSystem.GTTS
            else:
                return TTSSystem.FALLBACK
        else:  # PRODUCTION/LIVE
            if self.providers[TTSSystem.COQUI].is_available():
                return TTSSystem.COQUI
            else:
                return TTSSystem.FALLBACK
    
    def get_provider(self, system: Optional[TTSSystem] = None) -> TTSInterface:
        """Get TTS provider for specified system or preferred system."""
        if system is None:
            system = self.preferred_system
        
        provider = self.providers.get(system)
        if not provider or not provider.is_available():
            log.warning(f"Requested TTS system {system.value} not available, using fallback")
            return self.providers[TTSSystem.FALLBACK]
        
        return provider
    
    def get_available_providers(self) -> Dict[TTSSystem, TTSInterface]:
        """Get all available TTS providers."""
        return {
            system: provider 
            for system, provider in self.providers.items() 
            if provider.is_available()
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get information about all TTS systems."""
        return {
            "environment": self.environment.value,
            "preferred_system": self.preferred_system.value,
            "providers": {
                system.value: provider.get_info()
                for system, provider in self.providers.items()
            },
            "available_providers": [
                system.value 
                for system, provider in self.providers.items() 
                if provider.is_available()
            ]
        }
    
    async def synthesize_async(self, text: str, language: str = "en", system: Optional[TTSSystem] = None, **kwargs) -> bytes:
        """Synthesize text using preferred or specified TTS system."""
        provider = self.get_provider(system)
        return await provider.synthesize_async(text, language, **kwargs)
    
    def synthesize_sync(self, text: str, language: str = "en", system: Optional[TTSSystem] = None, **kwargs) -> bytes:
        """Synthesize text using preferred or specified TTS system."""
        provider = self.get_provider(system)
        return provider.synthesize_sync(text, language, **kwargs)

# Global TTS factory instance
tts_factory = TTSFactory()

# Convenience functions
def get_tts_provider(system: Optional[TTSSystem] = None) -> TTSInterface:
    """Get TTS provider instance."""
    return tts_factory.get_provider(system)

def synthesize_text(text: str, language: str = "en", system: Optional[TTSSystem] = None, **kwargs) -> bytes:
    """Synthesize text using preferred TTS system."""
    return tts_factory.synthesize_sync(text, language, system, **kwargs)

async def synthesize_text_async(text: str, language: str = "en", system: Optional[TTSSystem] = None, **kwargs) -> bytes:
    """Asynchronously synthesize text using preferred TTS system."""
    return await tts_factory.synthesize_async(text, language, system, **kwargs)

def get_tts_info() -> Dict[str, Any]:
    """Get TTS system information."""
    return tts_factory.get_system_info()

def is_environment_local() -> bool:
    """Check if current environment is local/development."""
    return tts_factory.environment == TTSEnvironment.LOCAL

def is_environment_production() -> bool:
    """Check if current environment is production/live."""
    return tts_factory.environment == TTSEnvironment.PRODUCTION

if __name__ == "__main__":
    # Test the TTS factory
    print("🎵 TTS Factory Test")
    print("="*50)
    
    # Show system info
    info = get_tts_info()
    print(f"Environment: {info['environment']}")
    print(f"Preferred System: {info['preferred_system']}")
    print(f"Available Providers: {', '.join(info['available_providers'])}")
    
    # Test synthesis
    test_text = "Hello! This is a test of the TTS factory system."
    
    print(f"\nTesting synthesis with: '{test_text}'")
    
    try:
        audio_data = synthesize_text(test_text, "en")
        if audio_data:
            print(f"✅ Synthesis successful: {len(audio_data)} bytes")
        else:
            print("❌ Synthesis failed")
    except Exception as e:
        print(f"❌ Synthesis error: {e}")
    
    print("\n" + "="*50)

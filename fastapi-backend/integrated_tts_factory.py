#!/usr/bin/env python3
"""
Integrated TTS Factory - Supports both Piper and Coqui TTS
Based on RealtimeVoiceChat architecture with optimization
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod
from enum import Enum

log = logging.getLogger("integrated_tts")

# Import TTS providers
try:
    from tts_factory import PiperTTSProvider, get_tts_factory
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False
    log.warning("Piper TTS not available")

try:
    from coqui_tts_provider import CoquiTTSProvider, get_coqui_provider
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False
    log.warning("Coqui TTS not available")

class TTSProvider(Enum):
    """Available TTS providers"""
    PIPER = "piper"
    COQUI = "coqui"
    AUTO = "auto"

class TTSInterface(ABC):
    """Abstract TTS interface"""
    
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

class IntegratedTTSProvider(TTSInterface):
    """Integrated TTS provider supporting multiple engines"""
    
    def __init__(self, preferred_provider: TTSProvider = TTSProvider.AUTO):
        self.name = "Integrated TTS"
        self.preferred_provider = preferred_provider
        self.current_provider = None
        self.providers = {}
        
        # Initialize available providers
        self._initialize_providers()
        
        # Select best available provider
        self._select_provider()
        
        log.info(f"✅ Integrated TTS initialized with provider: {self.current_provider}")
    
    def _initialize_providers(self):
        """Initialize available TTS providers"""
        # Initialize Piper TTS
        if PIPER_AVAILABLE:
            try:
                self.providers[TTSProvider.PIPER] = get_tts_factory().get_provider()
                log.info("✅ Piper TTS provider initialized")
            except Exception as e:
                log.warning(f"Failed to initialize Piper TTS: {e}")
        
        # Initialize Coqui TTS
        if COQUI_AVAILABLE:
            try:
                self.providers[TTSProvider.COQUI] = get_coqui_provider()
                log.info("✅ Coqui TTS provider initialized")
            except Exception as e:
                log.warning(f"Failed to initialize Coqui TTS: {e}")
    
    def _select_provider(self):
        """Select the best available provider"""
        if self.preferred_provider == TTSProvider.AUTO:
            # Auto-select based on availability and performance
            if TTSProvider.PIPER in self.providers and self.providers[TTSProvider.PIPER].is_available():
                self.current_provider = TTSProvider.PIPER
            elif TTSProvider.COQUI in self.providers and self.providers[TTSProvider.COQUI].is_available():
                self.current_provider = TTSProvider.COQUI
            else:
                log.error("❌ No TTS providers available")
                return
        else:
            # Use preferred provider
            if self.preferred_provider in self.providers and self.providers[self.preferred_provider].is_available():
                self.current_provider = self.preferred_provider
            else:
                log.warning(f"Preferred provider {self.preferred_provider.value} not available, falling back to auto")
                self._select_provider()
                return
        
        log.info(f"🎤 Selected TTS provider: {self.current_provider.value}")
    
    def switch_provider(self, provider: TTSProvider):
        """Switch to a different TTS provider"""
        if provider in self.providers and self.providers[provider].is_available():
            self.current_provider = provider
            log.info(f"🔄 Switched to TTS provider: {provider.value}")
        else:
            log.warning(f"Cannot switch to provider {provider.value} - not available")
    
    def get_current_provider(self) -> Optional[TTSInterface]:
        """Get current TTS provider instance"""
        if self.current_provider and self.current_provider in self.providers:
            return self.providers[self.current_provider]
        return None
    
    async def synthesize_async(self, text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
        """Asynchronously synthesize text using current provider"""
        provider = self.get_current_provider()
        if not provider:
            raise RuntimeError("No TTS provider available")
        
        try:
            return await provider.synthesize_async(text, language, voice, **kwargs)
        except Exception as e:
            log.error(f"Synthesis error with {self.current_provider.value}: {e}")
            # Try fallback provider
            if self._try_fallback_provider():
                provider = self.get_current_provider()
                return await provider.synthesize_async(text, language, voice, **kwargs)
            else:
                raise RuntimeError(f"All TTS providers failed: {e}")
    
    def synthesize_sync(self, text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
        """Synchronously synthesize text using current provider"""
        provider = self.get_current_provider()
        if not provider:
            raise RuntimeError("No TTS provider available")
        
        try:
            return provider.synthesize_sync(text, language, voice, **kwargs)
        except Exception as e:
            log.error(f"Synthesis error with {self.current_provider.value}: {e}")
            # Try fallback provider
            if self._try_fallback_provider():
                provider = self.get_current_provider()
                return provider.synthesize_sync(text, language, voice, **kwargs)
            else:
                raise RuntimeError(f"All TTS providers failed: {e}")
    
    def _try_fallback_provider(self) -> bool:
        """Try to switch to a fallback provider"""
        fallback_order = [TTSProvider.PIPER, TTSProvider.COQUI]
        
        for provider in fallback_order:
            if provider != self.current_provider and provider in self.providers and self.providers[provider].is_available():
                log.info(f"🔄 Switching to fallback provider: {provider.value}")
                self.current_provider = provider
                return True
        
        return False
    
    def is_available(self) -> bool:
        """Check if any TTS provider is available"""
        return self.current_provider is not None and self.get_current_provider() is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get integrated TTS system information"""
        current_provider_info = {}
        if self.get_current_provider():
            current_provider_info = self.get_current_provider().get_info()
        
        return {
            "name": self.name,
            "available": self.is_available(),
            "current_provider": self.current_provider.value if self.current_provider else None,
            "preferred_provider": self.preferred_provider.value,
            "available_providers": [p.value for p in self.providers.keys() if self.providers[p].is_available()],
            "current_provider_info": current_provider_info,
            "all_providers_info": {
                p.value: self.providers[p].get_info() 
                for p in self.providers.keys()
            }
        }
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get available voices from all providers"""
        voices = {}
        
        for provider_name, provider in self.providers.items():
            if provider.is_available():
                try:
                    provider_info = provider.get_info()
                    if "voice_configs" in provider_info:
                        voices[provider_name.value] = provider_info["voice_configs"]
                except Exception as e:
                    log.warning(f"Failed to get voices from {provider_name.value}: {e}")
        
        return voices
    
    def set_voice(self, voice_id: str, provider: Optional[TTSProvider] = None):
        """Set voice for specific provider or current provider"""
        target_provider = provider or self.current_provider
        
        if target_provider and target_provider in self.providers:
            provider_instance = self.providers[target_provider]
            if hasattr(provider_instance, 'set_voice'):
                provider_instance.set_voice(voice_id)
                log.info(f"🎤 Set voice '{voice_id}' for provider {target_provider.value}")
            else:
                log.warning(f"Provider {target_provider.value} does not support voice switching")

# Global Integrated TTS factory instance
_integrated_tts_instance = None

def get_integrated_tts(preferred_provider: TTSProvider = TTSProvider.AUTO) -> IntegratedTTSProvider:
    """Get singleton Integrated TTS instance"""
    global _integrated_tts_instance
    if _integrated_tts_instance is None:
        _integrated_tts_instance = IntegratedTTSProvider(preferred_provider)
        log.info("🏭 Integrated TTS Factory initialized (singleton)")
    return _integrated_tts_instance

# Convenience functions
async def synthesize_text_integrated(text: str, language: str = "en", voice: str = None, provider: TTSProvider = TTSProvider.AUTO, **kwargs) -> bytes:
    """Synthesize text using integrated TTS system"""
    tts = get_integrated_tts(provider)
    return await tts.synthesize_async(text, language, voice, **kwargs)

def synthesize_text_integrated_sync(text: str, language: str = "en", voice: str = None, provider: TTSProvider = TTSProvider.AUTO, **kwargs) -> bytes:
    """Synchronously synthesize text using integrated TTS system"""
    tts = get_integrated_tts(provider)
    return tts.synthesize_sync(text, language, voice, **kwargs)

def get_integrated_tts_info(provider: TTSProvider = TTSProvider.AUTO) -> Dict[str, Any]:
    """Get integrated TTS system information"""
    tts = get_integrated_tts(provider)
    return tts.get_info()

def get_available_voices(provider: TTSProvider = TTSProvider.AUTO) -> Dict[str, Any]:
    """Get available voices from all providers"""
    tts = get_integrated_tts(provider)
    return tts.get_available_voices()

if __name__ == "__main__":
    # Test Integrated TTS
    print("🎤 Integrated TTS Test")
    print("=" * 50)
    
    tts = get_integrated_tts()
    print(f"✅ TTS System: {tts.name}")
    print(f"✅ Available: {tts.is_available()}")
    print(f"✅ Current Provider: {tts.current_provider.value if tts.current_provider else 'None'}")
    print(f"✅ Available Providers: {[p.value for p in tts.providers.keys()]}")
    
    if tts.is_available():
        # Test synthesis
        test_text = "Hello! This is a test of the integrated TTS system."
        print(f"\n🎤 Testing synthesis with: '{test_text}'")
        
        try:
            audio_data = tts.synthesize_sync(test_text, "en")
            if audio_data:
                print(f"✅ Synthesis successful: {len(audio_data)} bytes")
            else:
                print("❌ Synthesis failed")
        except Exception as e:
            print(f"❌ Synthesis error: {e}")
    
    # Show available voices
    voices = tts.get_available_voices()
    if voices:
        print(f"\n🎤 Available Voices:")
        for provider, voice_list in voices.items():
            print(f"  {provider}: {list(voice_list.keys())}")
    
    print("\n" + "=" * 50)

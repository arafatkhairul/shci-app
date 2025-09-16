"""
Integrated TTS Service - Supports both Piper and Coqui TTS
Based on RealtimeVoiceChat architecture
"""
from typing import Optional
from app.config.settings import settings
from app.utils.logger import get_logger
from integrated_tts_factory import get_integrated_tts, TTSProvider, synthesize_text_integrated

log = get_logger("integrated_tts_service")

class IntegratedTTSService:
    """Integrated TTS service supporting multiple engines"""
    
    def __init__(self):
        self.tts_system = settings.TTS_SYSTEM.lower()
        self.piper_model = settings.PIPER_MODEL_NAME
        self.length_scale = settings.PIPER_LENGTH_SCALE
        self.noise_scale = settings.PIPER_NOISE_SCALE
        self.noise_w = settings.PIPER_NOISE_W
        
        # Select TTS provider based on configuration
        if self.tts_system == "piper":
            self.provider = TTSProvider.PIPER
        elif self.tts_system == "coqui":
            self.provider = TTSProvider.COQUI
        else:
            self.provider = TTSProvider.AUTO
        
        # Get integrated TTS factory
        self.tts_factory = get_integrated_tts(self.provider)
        
        log.info(f"🎤 Integrated TTS Service initialized")
        log.info(f"🎤 TTS System: {self.tts_system}")
        log.info(f"🎤 Provider: {self.provider.value}")
        log.info(f"🎤 Current Provider: {self.tts_factory.current_provider.value if self.tts_factory.current_provider else 'None'}")

    async def synthesize_text(
        self, 
        text: str, 
        language: str = "en",
        voice: Optional[str] = None,
        length_scale: Optional[float] = None,
        use_provider: Optional[TTSProvider] = None
    ) -> Optional[bytes]:
        """Synthesize text to audio using integrated TTS system"""
        
        try:
            # Use specified provider or current provider
            provider_to_use = use_provider or self.provider
            
            # Use provided voice or default
            voice_to_use = voice or self.piper_model
            
            # Use provided length scale or default
            length_scale_to_use = length_scale or self.length_scale
            
            # Synthesize using integrated TTS factory
            audio_data = await synthesize_text_integrated(
                text=text,
                language=language,
                voice=voice_to_use,
                provider=provider_to_use,
                length_scale=length_scale_to_use,
                noise_scale=self.noise_scale,
                noise_w=self.noise_w
            )
            
            if audio_data:
                log.info(f"✅ TTS synthesis successful: {len(audio_data)} bytes using {provider_to_use.value}")
            else:
                log.warning("⚠️ TTS synthesis returned empty audio")
            
            return audio_data
            
        except Exception as e:
            log.error(f"❌ TTS synthesis error: {e}")
            return None

    def get_tts_info(self) -> dict:
        """Get TTS system information"""
        return self.tts_factory.get_info()

    def switch_provider(self, provider: TTSProvider):
        """Switch to a different TTS provider"""
        self.tts_factory.switch_provider(provider)
        log.info(f"🔄 Switched to TTS provider: {provider.value}")

    def get_available_voices(self) -> dict:
        """Get available voices from all providers"""
        return self.tts_factory.get_available_voices()

    def adjust_speed_for_level(self, level: str) -> float:
        """Adjust TTS speed based on difficulty level"""
        speed_adjustments = {
            "easy": 0.8,    # Slower for beginners
            "medium": 1.0,   # Normal speed
            "fast": 1.2      # Faster for advanced
        }
        return speed_adjustments.get(level, 1.0)

    async def synthesize_with_level(
        self,
        text: str,
        language: str = "en",
        voice: Optional[str] = None,
        level: str = "medium",
        use_provider: Optional[TTSProvider] = None
    ) -> Optional[bytes]:
        """Synthesize text with difficulty level adjustment"""
        
        # Adjust length scale based on level
        adjusted_length_scale = self.length_scale * self.adjust_speed_for_level(level)
        
        return await self.synthesize_text(
            text=text,
            language=language,
            voice=voice,
            length_scale=adjusted_length_scale,
            use_provider=use_provider
        )

    async def synthesize_with_piper(self, text: str, language: str = "en", voice: Optional[str] = None) -> Optional[bytes]:
        """Force synthesis using Piper TTS (fast)"""
        return await self.synthesize_text(text, language, voice, use_provider=TTSProvider.PIPER)

    async def synthesize_with_coqui(self, text: str, language: str = "en", voice: Optional[str] = None) -> Optional[bytes]:
        """Force synthesis using Coqui TTS (high-quality)"""
        return await self.synthesize_text(text, language, voice, use_provider=TTSProvider.COQUI)

    def get_performance_stats(self) -> dict:
        """Get performance statistics"""
        info = self.get_tts_info()
        return {
            "current_provider": info.get("current_provider"),
            "available_providers": info.get("available_providers"),
            "provider_info": info.get("current_provider_info", {}),
            "system_status": "operational" if self.tts_factory.is_available() else "error"
        }

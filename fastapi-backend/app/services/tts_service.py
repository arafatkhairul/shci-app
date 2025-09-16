"""
Optimized TTS Service for text-to-speech functionality
"""
from typing import Optional
from app.config.settings import settings
from app.utils.logger import get_logger
from tts_factory import get_tts_factory, synthesize_text_async, get_tts_info

log = get_logger("tts_service")

class TTSService:
    """Optimized service for text-to-speech functionality with caching"""
    
    def __init__(self):
        self.tts_system = settings.TTS_SYSTEM
        self.piper_model = settings.PIPER_MODEL_NAME
        self.length_scale = settings.PIPER_LENGTH_SCALE
        self.noise_scale = settings.PIPER_NOISE_SCALE
        self.noise_w = settings.PIPER_NOISE_W
        
        # Get singleton TTS factory (models loaded once)
        self.tts_factory = get_tts_factory()
        self.tts_provider = self.tts_factory.get_provider()
        
        log.info(f"🎤 TTS Service initialized with {self.tts_system} system")
        log.info(f"🎤 Default voice: {self.piper_model}")

    async def synthesize_text(
        self, 
        text: str, 
        language: str = "en",
        voice: Optional[str] = None,
        length_scale: Optional[float] = None
    ) -> Optional[bytes]:
        """Ultra-fast synthesize text to audio using cached models"""
        
        try:
            # Use provided voice or default
            voice_to_use = voice or self.piper_model
            
            # Use provided length scale or default
            length_scale_to_use = length_scale or self.length_scale
            
            # Direct synthesis using cached provider (no model reloading)
            audio_data = await self.tts_provider.synthesize_async(
                text=text,
                language=language,
                voice=voice_to_use,
                length_scale=length_scale_to_use,
                noise_scale=self.noise_scale,
                noise_w=self.noise_w
            )
            
            return audio_data
            
        except Exception as e:
            log.error(f"TTS synthesis error: {e}")
            return None

    def get_tts_info(self) -> dict:
        """Get TTS system information"""
        return get_tts_info()

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
        level: str = "medium"
    ) -> Optional[bytes]:
        """Synthesize text with difficulty level adjustment"""
        
        # Adjust length scale based on level
        adjusted_length_scale = self.length_scale * self.adjust_speed_for_level(level)
        
        return await self.synthesize_text(
            text=text,
            language=language,
            voice=voice,
            length_scale=adjusted_length_scale
        )


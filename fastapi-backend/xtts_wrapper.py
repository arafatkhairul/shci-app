#!/usr/bin/env python3
"""
XTTS Wrapper - FastAPI Integration for XTTS (Coqui TTS)
Provides seamless integration between XTTS Manager and FastAPI application.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from xtts_manager import xtts_manager

log = logging.getLogger("xtts_wrapper")

class XTTSWrapper:
    """
    FastAPI wrapper for XTTS Manager.
    Handles async operations and provides FastAPI-compatible interface.
    """
    
    def __init__(self):
        self.manager = xtts_manager
        self.initialized = False
        self.model_loading = False
        
        # Configuration
        self.default_model = "tts_models/multilingual/multi-dataset/xtts_v2"
        self.auto_load = True
        
        log.info("XTTS Wrapper initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize XTTS system asynchronously.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            if self.initialized:
                return True
            
            log.info("Initializing XTTS system...")
            
            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self.manager.load_model, self.default_model)
            
            if success:
                self.initialized = True
                log.info("✅ XTTS system initialized successfully")
                return True
            else:
                log.error("❌ Failed to initialize XTTS system")
                return False
                
        except Exception as e:
            log.error(f"❌ XTTS initialization error: {e}")
            return False
    
    async def synthesize_async(self, text: str, language: str = "en", speaker_wav: str = None) -> bytes:
        """
        Asynchronously synthesize text to speech.
        
        Args:
            text: Text to synthesize
            language: Language code
            speaker_wav: Optional speaker reference file
            
        Returns:
            bytes: Audio data in WAV format
        """
        try:
            if not self.initialized:
                await self.initialize()
            
            if not text.strip():
                log.error("Empty text provided for synthesis")
                return b""
            
            # Run synthesis in thread pool
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                None, 
                self.manager.synthesize_text, 
                text, 
                language, 
                speaker_wav
            )
            
            return audio_data
            
        except Exception as e:
            log.error(f"❌ Async synthesis error: {e}")
            return b""
    
    def synthesize_sync(self, text: str, language: str = "en", speaker_wav: str = None) -> bytes:
        """
        Synchronously synthesize text to speech.
        
        Args:
            text: Text to synthesize
            language: Language code
            speaker_wav: Optional speaker reference file
            
        Returns:
            bytes: Audio data in WAV format
        """
        try:
            if not self.initialized:
                log.error("XTTS not initialized")
                return b""
            
            return self.manager.synthesize_text(text, language, speaker_wav)
            
        except Exception as e:
            log.error(f"❌ Sync synthesis error: {e}")
            return b""
    
    async def set_language_async(self, language: str) -> bool:
        """
        Asynchronously set synthesis language.
        
        Args:
            language: Language code
            
        Returns:
            bool: True if language is supported
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.manager.set_language, language)
        except Exception as e:
            log.error(f"❌ Error setting language: {e}")
            return False
    
    async def set_speaker_async(self, speaker_wav_path: str) -> bool:
        """
        Asynchronously set speaker reference file.
        
        Args:
            speaker_wav_path: Path to speaker audio file
            
        Returns:
            bool: True if speaker file is valid
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.manager.set_speaker_wav, speaker_wav_path)
        except Exception as e:
            log.error(f"❌ Error setting speaker: {e}")
            return False
    
    async def update_params_async(self, **params) -> bool:
        """
        Asynchronously update synthesis parameters.
        
        Args:
            **params: Synthesis parameters
            
        Returns:
            bool: True if parameters are valid
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.manager.set_synthesis_params, **params)
        except Exception as e:
            log.error(f"❌ Error updating parameters: {e}")
            return False
    
    async def get_info_async(self) -> Dict[str, Any]:
        """
        Asynchronously get system information.
        
        Returns:
            Dict containing system information
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.manager.get_model_info)
        except Exception as e:
            log.error(f"❌ Error getting info: {e}")
            return {"error": str(e)}
    
    async def health_check_async(self) -> Dict[str, Any]:
        """
        Asynchronously perform health check.
        
        Returns:
            Dict containing health status
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.manager.health_check)
        except Exception as e:
            log.error(f"❌ Health check error: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current wrapper status.
        
        Returns:
            Dict containing wrapper status
        """
        return {
            "initialized": self.initialized,
            "model_loading": self.model_loading,
            "default_model": self.default_model,
            "auto_load": self.auto_load
        }
    
    async def cleanup_async(self):
        """Asynchronously cleanup resources."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.manager.cleanup)
            self.initialized = False
            log.info("XTTS wrapper cleaned up")
        except Exception as e:
            log.error(f"❌ Cleanup error: {e}")

# Global XTTS wrapper instance
xtts_wrapper = XTTSWrapper()

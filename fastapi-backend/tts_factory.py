#!/usr/bin/env python3
"""
TTS Factory Pattern
Environment-based TTS system selection with Piper TTS for both local and production.
"""

import os
import logging
import asyncio
import wave
import tempfile
import inspect
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod
from enum import Enum

log = logging.getLogger("tts_factory")

# Import Piper TTS
try:
    from piper.voice import PiperVoice
    PIPER_TTS_AVAILABLE = True
except ImportError:
    PIPER_TTS_AVAILABLE = False

# Import requests for model downloading
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    log.warning("Requests not available - install with: pip install requests")

class TTSEnvironment(Enum):
    """TTS Environment types."""
    LOCAL = "local"
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    LIVE = "live"

class TTSSystem(Enum):
    """TTS System types."""
    PIPER = "piper"
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

class PiperTTSProvider(TTSInterface):
    """Piper TTS provider for both local and production environments."""
    
    def __init__(self):
        self.name = "Piper TTS"
        self.available = PIPER_TTS_AVAILABLE and REQUESTS_AVAILABLE
        self.voice = None
        self.model_path = None
        self.config_path = None
        self._voice_cache = {}  # Cache for multiple voice models
        self._initialized = False
        
        # Voice configuration with multiple models
        self.voice_configs = {
            "en_US-hfc_male-medium": {
                "name": "Ryan (Male)",
                "gender": "male",
                "quality": "medium",
                "model_path": "en_US-hfc_male-medium.onnx",
                "config_path": "en_US-hfc_male-medium.onnx.json",
                "model_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx",
                "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx.json"
            },
            "en_US-ryan-medium": {
                "name": "Ryan (Male)",
                "gender": "male",
                "quality": "medium",
                "model_path": "en_US-ryan-medium.onnx",
                "config_path": "en_US-ryan-medium.onnx.json",
                "model_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx",
                "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json"
            },
            "en_US-libritts_r-medium": {
                "name": "Sarah (Female)",
                "gender": "female",
                "quality": "medium",
                "model_path": "en_US-libritts_r-medium.onnx",
                "config_path": "en_US-libritts_r-medium.onnx.json",
                "model_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx",
                "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json"
            },
            "en_US-ljspeech-medium": {
                "name": "David (Female)",
                "gender": "female",
                "quality": "medium",
                "model_path": "en_US-ljspeech-medium.onnx",
                "config_path": "en_US-ljspeech-medium.onnx.json",
                "model_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx",
                "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx.json"
            }
        }
        
        # Default voice selection
        self.current_voice = os.getenv("PIPER_VOICE", "en_US-libritts_r-medium")
        self.model_path = self.voice_configs[self.current_voice]["model_path"]
        self.config_path = self.voice_configs[self.current_voice]["config_path"]
        
        # Device configuration (GPU/CPU detection)
        self.device_config = self._detect_device_config()
        self.use_cuda = self.device_config['use_cuda']
        self.device_info = self.device_config['device_info']
        
        # Synthesis parameters - Balanced for old Intel Xeon
        self.length_scale = float(os.getenv("PIPER_LENGTH_SCALE", "0.6"))  # Balanced speech speed
        self.noise_scale = float(os.getenv("PIPER_NOISE_SCALE", "1.0"))    # Default to medium speed
        self.noise_w = float(os.getenv("PIPER_NOISE_W", "0.5"))             # Balanced for CPU
        
        # Server performance optimizations (after attributes are initialized)
        self._apply_server_optimizations()
        
        # Supported languages
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
            self._initialize_voice()
            self._initialized = True
            log.info(f"🔧 CUDA: {'Enabled' if self.use_cuda else 'Disabled'}")
            log.info(f"✅ Piper TTS initialized with voice: {self.current_voice}")
        else:
            log.warning("❌ Piper TTS not available")
    
    def _detect_device_config(self):
        """Force CPU usage for Piper TTS - GPU completely disabled."""
        
        # Disable CUDA completely
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        os.environ["PIPER_FORCE_CPU"] = "true"
        os.environ["PIPER_DEVICE"] = "cpu"
        
        device_config = {
            'use_cuda': False,
            'device_info': {
                'device_type': 'CPU',
                'device_name': 'CPU (Forced)',
                'cuda_available': False,
                'cuda_device_count': 0,
                'gpu_id': 0
            }
        }
        
        return device_config
    
    def _apply_server_optimizations(self):
        """Apply server-specific performance optimizations."""
        import platform
        import psutil
        
        # Detect server environment
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        
        log.info(f"🖥️  Server Environment Detection:")
        log.info(f"   CPU Cores: {cpu_count}")
        log.info(f"   CPU Frequency: {cpu_freq.max if cpu_freq else 'Unknown'} MHz")
        log.info(f"   Total Memory: {memory.total / (1024**3):.1f} GB")
        log.info(f"   Available Memory: {memory.available / (1024**3):.1f} GB")
        
        # Optimize for older Intel CPUs (like E5-2697v2)
        if "Intel" in platform.processor() or "x86_64" in platform.machine():
            log.info("🔧 Detected Intel CPU - Applying optimizations")
            
            log.info("🚀 Using Balanced CPU optimization for old Intel Xeon")
            # Set environment variables for balanced CPU performance
            os.environ["OMP_NUM_THREADS"] = str(min(cpu_count, 6))  # Limit threads
            os.environ["MKL_NUM_THREADS"] = str(min(cpu_count, 6))
            os.environ["NUMEXPR_NUM_THREADS"] = str(min(cpu_count, 6))
            os.environ["OPENBLAS_NUM_THREADS"] = str(min(cpu_count, 6))
            os.environ["MKL_DYNAMIC"] = "false"
            os.environ["OMP_DYNAMIC"] = "false"
            
            # Balanced optimization for older CPU architecture
            self.length_scale = min(self.length_scale, 0.6)  # Balanced processing
            self.noise_scale = min(self.noise_scale, 3.0)    # Allow up to 3.0 for easy speed
            self.noise_w = min(self.noise_w, 0.5)            # Balanced for CPU
        
        # Memory optimization
        if memory.total < 32 * (1024**3):  # Less than 32GB RAM
            log.info("🔧 Low memory detected - Applying memory optimizations")
            # Reduce memory usage
            self.length_scale = min(self.length_scale, 0.8)
    
    def _download_if_missing(self, path: str, url: str):
        """Download model files if missing."""
        if os.path.exists(path):
            log.info(f"[SKIP] {path} already exists")
            return
        
        log.info(f"[DOWNLOAD] {path} downloading...")
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(path, "wb") as f:
                for chunk in response.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            
            log.info(f"[OK] {path} download completed")
        except Exception as e:
            log.error(f"Failed to download {path}: {e}")
            raise
    
    def _initialize_voice(self):
        """Initialize Piper voice model with GPU/CPU configuration."""
        try:
            # Check if voice is already cached
            if self.current_voice in self._voice_cache:
                log.info(f"🎤 Using cached voice: {self.current_voice}")
                self.voice = self._voice_cache[self.current_voice]
                return
            
            # Get URLs for current voice
            voice_config = self.voice_configs[self.current_voice]
            model_url = voice_config["model_url"]
            config_url = voice_config["config_url"]
            
            # Download model files if missing
            self._download_if_missing(self.model_path, model_url)
            self._download_if_missing(self.config_path, config_url)
            
            # Load voice model with device configuration
            log.info(f"[LOAD] {self.model_path}")
            log.info(f"[DEVICE] Using {'GPU' if self.use_cuda else 'CPU'}")
            
            # Set CUDA device if using GPU
            if self.use_cuda and self.device_info['cuda_available']:
                try:
                    import torch
                    gpu_id = self.device_info.get('gpu_id', 0)
                    torch.cuda.set_device(gpu_id)
                    log.info(f"[CUDA] Set to GPU {gpu_id}: {torch.cuda.get_device_name(gpu_id)}")
                except Exception as cuda_set_error:
                    log.warning(f"Failed to set CUDA device: {cuda_set_error}")
            
            # Load with CUDA if available and configured
            if self.use_cuda and self.device_info['cuda_available']:
                try:
                    self.voice = PiperVoice.load(
                        self.model_path, 
                        config_path=self.config_path,
                        use_cuda=True
                    )
                    gpu_id = self.device_info.get('gpu_id', 0)
                    log.info(f"[OK] Model loaded successfully with GPU {gpu_id} acceleration")
                except Exception as cuda_error:
                    log.warning(f"GPU loading failed, falling back to CPU: {cuda_error}")
                    self.voice = PiperVoice.load(
                        self.model_path, 
                        config_path=self.config_path,
                        use_cuda=False
                    )
                    log.info("[OK] Model loaded successfully with CPU fallback")
            else:
                self.voice = PiperVoice.load(
                    self.model_path, 
                    config_path=self.config_path,
                    use_cuda=False
                )
                log.info("[OK] Model loaded successfully with CPU")
            
            # Cache the loaded voice
            self._voice_cache[self.current_voice] = self.voice
            log.info(f"💾 Voice cached: {self.current_voice}")
            
        except Exception as e:
            log.error(f"Failed to initialize Piper voice: {e}")
            self.available = False
    
    def set_voice(self, voice_id: str):
        """Switch to a different voice model."""
        if voice_id not in self.voice_configs:
            log.warning(f"Voice {voice_id} not found, using default")
            voice_id = "en_US-libritts_r-medium"
        
        if voice_id != self.current_voice:
            log.info(f"🎤 Switching voice from {self.current_voice} to {voice_id}")
            voice_config = self.voice_configs[voice_id]
            log.info(f"🎤 New voice config: {voice_config['name']} ({voice_config['gender']}, {voice_config['quality']})")
            
            # Update current voice and paths
            self.current_voice = voice_id
            self.model_path = voice_config["model_path"]
            self.config_path = voice_config["config_path"]
            
            # Check if voice is already cached
            if voice_id in self._voice_cache:
                log.info(f"🎤 Using cached voice: {voice_id}")
                self.voice = self._voice_cache[voice_id]
                log.info(f"✅ Voice switched successfully to {voice_config['name']} (from cache)")
            else:
                # Load new voice model
                log.info(f"🎤 Loading new model: {self.model_path}")
                self._initialize_voice()
                
                if self.voice:
                    log.info(f"✅ Voice switched successfully to {voice_config['name']}")
                else:
                    log.error(f"❌ Failed to load voice model for {voice_id}")

    async def synthesize_async(self, text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
        """Asynchronously synthesize text using Piper TTS."""
        if not self.available or not self.voice:
            raise RuntimeError("Piper TTS not available")
        
        # Switch voice if specified (optimized with caching)
        if voice and voice != self.current_voice:
            self.set_voice(voice)
        
        try:
            loop = asyncio.get_event_loop()
            # Remove unsupported parameters from kwargs as Piper TTS doesn't support them
            piper_kwargs = {k: v for k, v in kwargs.items() if k not in ['speaker_wav', 'speed']}
            # Use optimized streaming for better performance
            return await loop.run_in_executor(None, self.synthesize_stream_optimized, text, language, voice, piper_kwargs)
        except Exception as e:
            log.error(f"Synthesis error: {e}")
            return b""
    
    def synthesize_sync(self, text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
        """Synchronously synthesize text using Piper TTS."""
        if not self.available or not self.voice:
            raise RuntimeError("Piper TTS not available")
        
        # Switch voice if specified
        if voice and voice != self.current_voice:
            log.info(f"🎤 Switching voice from {self.current_voice} to {voice}")
            self.set_voice(voice)
        elif voice:
            log.info(f"🎤 Using current voice: {voice}")
        
        # Log current voice being used for synthesis
        current_voice_config = self.voice_configs.get(self.current_voice, {})
        voice_name = current_voice_config.get('name', 'Unknown')
        log.info(f"🎤 Synthesizing with voice: {voice_name} ({self.current_voice})")
        
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            # Configure WAV file
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.voice.config.sample_rate)
                
                # Get synthesis parameters
                kwargs = kwargs or {}
                length_scale = kwargs.get('length_scale', self.length_scale)
                noise_scale = kwargs.get('noise_scale', self.noise_scale)
                noise_w = kwargs.get('noise_w', self.noise_w)
                
                # Debug log for noise_scale
                log.info(f"🎵 NOISE_SCALE DEBUG: kwargs={kwargs}, noise_scale={noise_scale}, self.noise_scale={self.noise_scale}")
                
                # Detect API signature
                sig = inspect.signature(PiperVoice.synthesize)
                params = sig.parameters
                use_kwargs = all(k in params for k in ("length_scale", "noise_scale", "noise_w"))
                has_syn_config = ("syn_config" in params) or ("synthesis_config" in params)
                
                log.debug(f"Piper API signature: {sig}")
                log.debug(f"use_kwargs: {use_kwargs}, has_syn_config: {has_syn_config}")
                
                # Synthesize based on API version (following working code pattern)
                if use_kwargs:
                    # New API: direct kwargs
                    self.voice.synthesize(
                        text,
                        wf,
                        length_scale=length_scale,
                        noise_scale=noise_scale,
                        noise_w=noise_w,
                        sentence_silence=0.0,
                    )
                elif has_syn_config:
                    # Old API: SynthesisConfig object (this is what works)
                    from piper.voice import SynthesisConfig
                    
                    # NOTE: কিছু রিলিজে 'noise_w' না হয়ে 'noise_w_scale' ছিল—সেই কেস কভার:
                    try:
                        cfg = SynthesisConfig(length_scale=length_scale, noise_scale=noise_scale, noise_w=noise_w)
                    except TypeError:
                        cfg = SynthesisConfig(length_scale=length_scale, noise_scale=noise_scale, noise_w_scale=noise_w)
                    
                    kw = {}
                    if "syn_config" in params:
                        kw["syn_config"] = cfg
                    else:
                        kw["synthesis_config"] = cfg
                    
                    # কিছু রিলিজে নাম 'synthesize_wav'—ফলব্যাক ট্রাই:
                    try:
                        self.voice.synthesize(text, wf, **kw)
                    except TypeError:
                        self.voice.synthesize_wav(text, wf, **kw)
                else:
                    # Optimized streaming for real-time response
                    log.info("🎤 Using optimized streaming synthesis for real-time response")
                    
                    # Try the new streaming API first
                    try:
                        # Use synthesize_stream for better performance
                        for chunk in self.voice.synthesize_stream(
                            text, 
                            length_scale=length_scale, 
                            noise_scale=noise_scale, 
                            noise_w=noise_w
                        ):
                            # Set audio format from chunk
                            wf.setnchannels(chunk.sample_channels)
                            wf.setsampwidth(chunk.sample_width)
                            wf.setframerate(chunk.sample_rate)
                            
                            # Write chunk data directly
                            wf.writeframes(chunk.audio_int16_bytes)
                            
                    except AttributeError:
                        # Fallback to raw streaming if new API not available
                        log.info("🔄 Falling back to raw streaming API")
                        for audio in self.voice.synthesize_stream_raw(
                            text, length_scale=length_scale, noise_scale=noise_scale, noise_w=noise_w
                        ):
                            wf.writeframes(audio)
                
                # Read the generated audio file
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
            return audio_data
                    
        except Exception as e:
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return b""
    
    def synthesize_stream_optimized(self, text: str, language: str = "en", voice: str = None, kwargs: dict = None) -> bytes:
        """Ultra-optimized synthesis for minimal latency using direct memory operations."""
        if not self.available or not self.voice:
            raise RuntimeError("Piper TTS not available")
        
        # Use memory buffer for fastest processing
        import io
        
        # Create in-memory WAV buffer
        wav_buffer = io.BytesIO()
        
        try:
            with wave.open(wav_buffer, 'wb') as wf:
                # Set audio format for optimal speed
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.voice.config.sample_rate)
                
                # Get synthesis parameters for natural human-like speech
                kwargs = kwargs or {}
                length_scale = kwargs.get('length_scale', self.length_scale)
                noise_scale = kwargs.get('noise_scale', self.noise_scale)
                noise_w = kwargs.get('noise_w', self.noise_w)
                sentence_silence = kwargs.get('sentence_silence', 0.1)  # Small pause for natural speech
                
                # Use the fastest synthesis method available
                try:
                    # Try direct synthesis (fastest method)
                    self.voice.synthesize(
                        text,
                        wf,
                        length_scale=length_scale,
                        noise_scale=noise_scale,
                        noise_w=noise_w,
                        sentence_silence=0.0,
                    )
                except Exception as e:
                    # Fallback to SynthesisConfig if direct method fails
                    try:
                        from piper.voice import SynthesisConfig
                        cfg = SynthesisConfig(
                            length_scale=length_scale, 
                            noise_scale=noise_scale, 
                            noise_w=noise_w
                        )
                        self.voice.synthesize(text, wf, syn_config=cfg)
                    except Exception:
                        # Final fallback
                        self.voice.synthesize_wav(text, wf)
            
            # Get audio data from buffer
            audio_data = wav_buffer.getvalue()
            wav_buffer.close()
            
            return audio_data
            
        except Exception as e:
            log.error(f"Ultra-optimized synthesis failed: {e}")
            wav_buffer.close()
            return b""
    
    def is_available(self) -> bool:
        """Check if Piper TTS is available."""
        return self.available and self.voice is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get Piper TTS system information."""
        info = {
            "name": self.name,
            "available": self.is_available(),
            "system_type": "Piper TTS",
            "environment": "local + production",
            "current_voice": self.current_voice,
            "voice_configs": self.voice_configs,
            "model_path": self.model_path,
            "config_path": self.config_path,
            "supported_languages": self.supported_languages,
            "sample_rate": self.voice.config.sample_rate if self.voice else 22050,
            "device_config": {
                "use_cuda": self.use_cuda,
                "device_type": self.device_info['device_type'],
                "device_name": self.device_info['device_name'],
                "cuda_available": self.device_info['cuda_available'],
                "cuda_device_count": self.device_info['cuda_device_count'],
                "gpu_id": self.device_info.get('gpu_id', 0)
            },
            "synthesis_params": {
                "length_scale": self.length_scale,
                "noise_scale": self.noise_scale,
                "noise_w": self.noise_w
            }
        }
        
        return info

class FallbackTTSProvider(TTSInterface):
    """Fallback TTS provider using system TTS."""
    
    def __init__(self):
        self.name = "System Fallback TTS"
        self.available = True
        self.sample_rate = 22050
        
    
    async def synthesize_async(self, text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
        """Asynchronously synthesize text using fallback TTS."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.synthesize_sync, text, language, voice, **kwargs)
        except Exception as e:
            return b""
    
    def synthesize_sync(self, text: str, language: str = "en", voice: str = None, **kwargs) -> bytes:
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
                
                return audio_data
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
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
            TTSSystem.PIPER: PiperTTSProvider(),
            TTSSystem.FALLBACK: FallbackTTSProvider()
        }
        
        # Environment configuration
        self.environment = self._detect_environment()
        self.preferred_system = self._get_preferred_system()
        
    
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
        
        if tts_system == "piper":
            return TTSSystem.PIPER
        elif tts_system == "fallback":
            return TTSSystem.FALLBACK
        
        # Auto-select: Piper TTS for both local and production
        if self.providers[TTSSystem.PIPER].is_available():
            return TTSSystem.PIPER
        else:
            return TTSSystem.FALLBACK
    
    def get_provider(self, system: Optional[TTSSystem] = None) -> TTSInterface:
        """Get TTS provider for specified system or preferred system."""
        if system is None:
            system = self.preferred_system
        
        provider = self.providers.get(system)
        if not provider or not provider.is_available():
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
    
    async def synthesize_async(self, text: str, language: str = "en", voice: str = None, system: Optional[TTSSystem] = None, **kwargs) -> bytes:
        """Synthesize text using preferred or specified TTS system."""
        provider = self.get_provider(system)
        return await provider.synthesize_async(text, language, voice, **kwargs)
    
    def synthesize_sync(self, text: str, language: str = "en", voice: str = None, system: Optional[TTSSystem] = None, **kwargs) -> bytes:
        """Synthesize text using preferred or specified TTS system."""
        provider = self.get_provider(system)
        return provider.synthesize_sync(text, language, voice, **kwargs)

# Global TTS factory instance (Singleton pattern)
_tts_factory_instance = None

def get_tts_factory() -> TTSFactory:
    """Get singleton TTS factory instance."""
    global _tts_factory_instance
    if _tts_factory_instance is None:
        _tts_factory_instance = TTSFactory()
        log.info("🏭 TTS Factory initialized (singleton)")
    return _tts_factory_instance

# Global TTS factory instance
tts_factory = get_tts_factory()

# Convenience functions
def get_tts_provider(system: Optional[TTSSystem] = None) -> TTSInterface:
    """Get TTS provider instance."""
    return tts_factory.get_provider(system)

def synthesize_text(text: str, language: str = "en", voice: str = None, system: Optional[TTSSystem] = None, **kwargs) -> bytes:
    """Synthesize text using preferred TTS system."""
    return tts_factory.synthesize_sync(text, language, voice, system, **kwargs)

async def synthesize_text_async(text: str, language: str = "en", voice: str = None, system: Optional[TTSSystem] = None, **kwargs) -> bytes:
    """Asynchronously synthesize text using preferred TTS system."""
    return await tts_factory.synthesize_async(text, language, voice, system, **kwargs)

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
    test_text = "Hello! This is a test of the Piper TTS factory system."
    
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

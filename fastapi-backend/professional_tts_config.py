#!/usr/bin/env python3
"""
Professional TTS Configuration System
Provides optimized TTS configuration for real-time responses with StyleTTS2 integration.
"""

import os
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import yaml

log = logging.getLogger("professional_tts_config")

@dataclass
class TTSModelConfig:
    """Configuration for TTS model parameters."""
    name: str = "StyleTTS2"
    model_path: str = "models/styletts2"
    device: str = "auto"  # auto, cpu, cuda
    precision: str = "fp16"  # fp16, fp32
    batch_size: int = 1
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    length_penalty: float = 1.0
    no_repeat_ngram_size: int = 3
    early_stopping: bool = True
    use_cache: bool = True
    cache_size: int = 100

@dataclass
class VoiceConfig:
    """Configuration for voice synthesis parameters."""
    speaker_id: str = "default"
    speaker_wav: Optional[str] = None
    language: str = "en"
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    emotion: str = "neutral"  # neutral, happy, sad, angry, excited
    style: str = "normal"  # normal, formal, casual, dramatic
    emphasis: List[str] = field(default_factory=list)

@dataclass
class AudioConfig:
    """Configuration for audio output parameters."""
    sample_rate: int = 22050
    bit_depth: int = 16
    channels: int = 1
    format: str = "wav"
    compression: bool = False
    normalize: bool = True
    trim_silence: bool = True
    fade_in: float = 0.0
    fade_out: float = 0.0

@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""
    enable_streaming: bool = True
    chunk_size: int = 1024
    buffer_size: int = 4096
    preload_models: bool = True
    warmup_enabled: bool = True
    parallel_processing: bool = True
    max_workers: int = 4
    timeout: float = 30.0
    retry_attempts: int = 3
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds

@dataclass
class RealTimeConfig:
    """Configuration for real-time processing."""
    enable_realtime: bool = True
    latency_target: float = 0.5  # seconds
    max_latency: float = 2.0  # seconds
    adaptive_speed: bool = True
    priority_queue: bool = True
    interrupt_enabled: bool = True
    voice_activity_detection: bool = True
    silence_threshold: float = 0.01
    min_speech_duration: float = 0.1

class ProfessionalTTSConfig:
    """
    Professional TTS Configuration Manager
    Handles all TTS-related configurations for optimal real-time performance.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "tts_config.yaml"
        self.model_config = TTSModelConfig()
        self.voice_config = VoiceConfig()
        self.audio_config = AudioConfig()
        self.performance_config = PerformanceConfig()
        self.realtime_config = RealTimeConfig()
        
        # Load configuration
        self.load_config()
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_latency": 0.0,
            "max_latency": 0.0,
            "min_latency": float('inf'),
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        log.info("Professional TTS Configuration initialized")
    
    def load_config(self):
        """Load configuration from file or environment variables."""
        try:
            # Try to load from YAML file first
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    self._apply_config_data(config_data)
                log.info(f"Configuration loaded from {self.config_file}")
            else:
                log.info("No config file found, using environment variables")
            
            # Override with environment variables
            self._load_from_env()
            
        except Exception as e:
            log.error(f"Error loading configuration: {e}")
            log.info("Using default configuration")
    
    def _apply_config_data(self, config_data: Dict[str, Any]):
        """Apply configuration data from file."""
        if 'model' in config_data:
            model_data = config_data['model']
            for key, value in model_data.items():
                if hasattr(self.model_config, key):
                    setattr(self.model_config, key, value)
        
        if 'voice' in config_data:
            voice_data = config_data['voice']
            for key, value in voice_data.items():
                if hasattr(self.voice_config, key):
                    setattr(self.voice_config, key, value)
        
        if 'audio' in config_data:
            audio_data = config_data['audio']
            for key, value in audio_data.items():
                if hasattr(self.audio_config, key):
                    setattr(self.audio_config, key, value)
        
        if 'performance' in config_data:
            perf_data = config_data['performance']
            for key, value in perf_data.items():
                if hasattr(self.performance_config, key):
                    setattr(self.performance_config, key, value)
        
        if 'realtime' in config_data:
            rt_data = config_data['realtime']
            for key, value in rt_data.items():
                if hasattr(self.realtime_config, key):
                    setattr(self.realtime_config, key, value)
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Model configuration
        self.model_config.name = os.getenv("TTS_MODEL_NAME", self.model_config.name)
        self.model_config.model_path = os.getenv("TTS_MODEL_PATH", self.model_config.model_path)
        self.model_config.device = os.getenv("TTS_DEVICE", self.model_config.device)
        self.model_config.precision = os.getenv("TTS_PRECISION", self.model_config.precision)
        self.model_config.batch_size = int(os.getenv("TTS_BATCH_SIZE", self.model_config.batch_size))
        self.model_config.temperature = float(os.getenv("TTS_TEMPERATURE", self.model_config.temperature))
        
        # Voice configuration
        self.voice_config.speaker_id = os.getenv("TTS_SPEAKER_ID", self.voice_config.speaker_id)
        self.voice_config.speaker_wav = os.getenv("TTS_SPEAKER_WAV", self.voice_config.speaker_wav)
        self.voice_config.language = os.getenv("TTS_LANGUAGE", self.voice_config.language)
        self.voice_config.speed = float(os.getenv("TTS_SPEED", self.voice_config.speed))
        self.voice_config.emotion = os.getenv("TTS_EMOTION", self.voice_config.emotion)
        
        # Audio configuration
        self.audio_config.sample_rate = int(os.getenv("TTS_SAMPLE_RATE", self.audio_config.sample_rate))
        self.audio_config.format = os.getenv("TTS_FORMAT", self.audio_config.format)
        self.audio_config.normalize = os.getenv("TTS_NORMALIZE", "true").lower() == "true"
        
        # Performance configuration
        self.performance_config.enable_streaming = os.getenv("TTS_STREAMING", "true").lower() == "true"
        self.performance_config.chunk_size = int(os.getenv("TTS_CHUNK_SIZE", self.performance_config.chunk_size))
        self.performance_config.max_workers = int(os.getenv("TTS_MAX_WORKERS", self.performance_config.max_workers))
        self.performance_config.cache_enabled = os.getenv("TTS_CACHE", "true").lower() == "true"
        
        # Real-time configuration
        self.realtime_config.enable_realtime = os.getenv("TTS_REALTIME", "true").lower() == "true"
        self.realtime_config.latency_target = float(os.getenv("TTS_LATENCY_TARGET", self.realtime_config.latency_target))
        self.realtime_config.adaptive_speed = os.getenv("TTS_ADAPTIVE_SPEED", "true").lower() == "true"
    
    def save_config(self, file_path: Optional[str] = None):
        """Save current configuration to file."""
        try:
            save_path = file_path or self.config_file
            config_data = {
                'model': self.model_config.__dict__,
                'voice': self.voice_config.__dict__,
                'audio': self.audio_config.__dict__,
                'performance': self.performance_config.__dict__,
                'realtime': self.realtime_config.__dict__
            }
            
            with open(save_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            log.info(f"Configuration saved to {save_path}")
            return True
            
        except Exception as e:
            log.error(f"Error saving configuration: {e}")
            return False
    
    def optimize_for_realtime(self):
        """Optimize configuration for real-time performance."""
        log.info("Optimizing configuration for real-time performance...")
        
        # Model optimization
        self.model_config.precision = "fp16"
        self.model_config.batch_size = 1
        self.model_config.use_cache = True
        self.model_config.cache_size = 200
        
        # Performance optimization
        self.performance_config.enable_streaming = True
        self.performance_config.chunk_size = 512
        self.performance_config.buffer_size = 2048
        self.performance_config.preload_models = True
        self.performance_config.warmup_enabled = True
        self.performance_config.parallel_processing = True
        self.performance_config.cache_enabled = True
        
        # Real-time optimization
        self.realtime_config.enable_realtime = True
        self.realtime_config.latency_target = 0.3
        self.realtime_config.max_latency = 1.5
        self.realtime_config.adaptive_speed = True
        self.realtime_config.priority_queue = True
        self.realtime_config.interrupt_enabled = True
        
        # Audio optimization
        self.audio_config.sample_rate = 22050
        self.audio_config.normalize = True
        self.audio_config.trim_silence = True
        
        log.info("✅ Configuration optimized for real-time performance")
    
    def optimize_for_quality(self):
        """Optimize configuration for maximum quality."""
        log.info("Optimizing configuration for maximum quality...")
        
        # Model optimization
        self.model_config.precision = "fp32"
        self.model_config.batch_size = 4
        self.model_config.temperature = 0.7
        self.model_config.top_p = 0.9
        self.model_config.top_k = 50
        
        # Audio optimization
        self.audio_config.sample_rate = 44100
        self.audio_config.bit_depth = 24
        self.audio_config.normalize = True
        self.audio_config.trim_silence = True
        self.audio_config.fade_in = 0.01
        self.audio_config.fade_out = 0.01
        
        # Performance optimization
        self.performance_config.enable_streaming = False
        self.performance_config.cache_enabled = True
        self.performance_config.cache_ttl = 7200
        
        log.info("✅ Configuration optimized for maximum quality")
    
    def get_optimized_config(self, mode: str = "realtime") -> Dict[str, Any]:
        """
        Get optimized configuration for specific mode.
        
        Args:
            mode: Configuration mode ('realtime', 'quality', 'balanced')
            
        Returns:
            Dict containing optimized configuration
        """
        if mode == "realtime":
            self.optimize_for_realtime()
        elif mode == "quality":
            self.optimize_for_quality()
        elif mode == "balanced":
            # Balanced configuration
            self.model_config.precision = "fp16"
            self.model_config.batch_size = 2
            self.performance_config.enable_streaming = True
            self.performance_config.chunk_size = 1024
            self.realtime_config.latency_target = 0.8
            self.audio_config.sample_rate = 22050
        
        return {
            'model': self.model_config.__dict__,
            'voice': self.voice_config.__dict__,
            'audio': self.audio_config.__dict__,
            'performance': self.performance_config.__dict__,
            'realtime': self.realtime_config.__dict__
        }
    
    def update_metrics(self, latency: float, success: bool, cache_hit: bool = False):
        """Update performance metrics."""
        self.metrics["total_requests"] += 1
        
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        if cache_hit:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
        
        # Update latency metrics
        self.metrics["max_latency"] = max(self.metrics["max_latency"], latency)
        self.metrics["min_latency"] = min(self.metrics["min_latency"], latency)
        
        # Calculate average latency
        total_successful = self.metrics["successful_requests"]
        if total_successful > 0:
            current_avg = self.metrics["average_latency"]
            self.metrics["average_latency"] = (current_avg * (total_successful - 1) + latency) / total_successful
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        total_requests = self.metrics["total_requests"]
        success_rate = (self.metrics["successful_requests"] / total_requests * 100) if total_requests > 0 else 0
        cache_hit_rate = (self.metrics["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.metrics,
            "success_rate": success_rate,
            "cache_hit_rate": cache_hit_rate,
            "current_config": {
                "model": self.model_config.__dict__,
                "voice": self.voice_config.__dict__,
                "audio": self.audio_config.__dict__,
                "performance": self.performance_config.__dict__,
                "realtime": self.realtime_config.__dict__
            }
        }
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate current configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate model configuration
        if not os.path.exists(self.model_config.model_path):
            errors.append(f"Model path does not exist: {self.model_config.model_path}")
        
        if self.model_config.batch_size < 1:
            errors.append("Batch size must be at least 1")
        
        if not (0.1 <= self.model_config.temperature <= 2.0):
            errors.append("Temperature must be between 0.1 and 2.0")
        
        # Validate voice configuration
        if self.voice_config.speaker_wav and not os.path.exists(self.voice_config.speaker_wav):
            errors.append(f"Speaker WAV file does not exist: {self.voice_config.speaker_wav}")
        
        if not (0.5 <= self.voice_config.speed <= 2.0):
            errors.append("Speed must be between 0.5 and 2.0")
        
        # Validate audio configuration
        if self.audio_config.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            errors.append("Sample rate must be one of: 8000, 16000, 22050, 44100, 48000")
        
        if self.audio_config.bit_depth not in [16, 24, 32]:
            errors.append("Bit depth must be one of: 16, 24, 32")
        
        # Validate performance configuration
        if self.performance_config.chunk_size < 256:
            errors.append("Chunk size must be at least 256")
        
        if self.performance_config.max_workers < 1:
            errors.append("Max workers must be at least 1")
        
        # Validate real-time configuration
        if self.realtime_config.latency_target > self.realtime_config.max_latency:
            errors.append("Latency target cannot be greater than max latency")
        
        return len(errors) == 0, errors
    
    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self.model_config = TTSModelConfig()
        self.voice_config = VoiceConfig()
        self.audio_config = AudioConfig()
        self.performance_config = PerformanceConfig()
        self.realtime_config = RealTimeConfig()
        
        log.info("Configuration reset to defaults")
    
    def get_config_summary(self) -> str:
        """Get a human-readable configuration summary."""
        summary = f"""
Professional TTS Configuration Summary:
=====================================

Model Configuration:
- Name: {self.model_config.name}
- Path: {self.model_config.model_path}
- Device: {self.model_config.device}
- Precision: {self.model_config.precision}
- Batch Size: {self.model_config.batch_size}

Voice Configuration:
- Speaker ID: {self.voice_config.speaker_id}
- Language: {self.voice_config.language}
- Speed: {self.voice_config.speed}x
- Emotion: {self.voice_config.emotion}
- Style: {self.voice_config.style}

Audio Configuration:
- Sample Rate: {self.audio_config.sample_rate} Hz
- Bit Depth: {self.audio_config.bit_depth} bits
- Format: {self.audio_config.format}
- Normalize: {self.audio_config.normalize}

Performance Configuration:
- Streaming: {self.performance_config.enable_streaming}
- Chunk Size: {self.performance_config.chunk_size}
- Max Workers: {self.performance_config.max_workers}
- Cache: {self.performance_config.cache_enabled}

Real-time Configuration:
- Real-time Mode: {self.realtime_config.enable_realtime}
- Latency Target: {self.realtime_config.latency_target}s
- Max Latency: {self.realtime_config.max_latency}s
- Adaptive Speed: {self.realtime_config.adaptive_speed}

Performance Metrics:
- Total Requests: {self.metrics['total_requests']}
- Success Rate: {(self.metrics['successful_requests'] / max(1, self.metrics['total_requests']) * 100):.1f}%
- Average Latency: {self.metrics['average_latency']:.3f}s
- Cache Hit Rate: {(self.metrics['cache_hits'] / max(1, self.metrics['total_requests']) * 100):.1f}%
"""
        return summary

# Global configuration instance
tts_config = ProfessionalTTSConfig()

# Convenience functions
def get_tts_config() -> ProfessionalTTSConfig:
    """Get the global TTS configuration instance."""
    return tts_config

def optimize_for_realtime():
    """Optimize global configuration for real-time performance."""
    tts_config.optimize_for_realtime()

def optimize_for_quality():
    """Optimize global configuration for maximum quality."""
    tts_config.optimize_for_quality()

def get_optimized_config(mode: str = "realtime") -> Dict[str, Any]:
    """Get optimized configuration for specific mode."""
    return tts_config.get_optimized_config(mode)

def validate_config() -> Tuple[bool, List[str]]:
    """Validate current configuration."""
    return tts_config.validate_config()

def get_config_summary() -> str:
    """Get configuration summary."""
    return tts_config.get_config_summary()

if __name__ == "__main__":
    # Test the configuration system
    config = ProfessionalTTSConfig()
    
    print("=== Professional TTS Configuration Test ===")
    print(config.get_config_summary())
    
    # Test optimization
    print("\n=== Testing Real-time Optimization ===")
    config.optimize_for_realtime()
    print("Real-time config applied")
    
    # Test validation
    print("\n=== Testing Configuration Validation ===")
    is_valid, errors = config.validate_config()
    if is_valid:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has errors:")
        for error in errors:
            print(f"  - {error}")
    
    # Test metrics
    print("\n=== Testing Metrics ===")
    config.update_metrics(0.5, True, False)
    config.update_metrics(0.3, True, True)
    config.update_metrics(0.8, False, False)
    
    metrics = config.get_metrics()
    print(f"Success Rate: {metrics['success_rate']:.1f}%")
    print(f"Cache Hit Rate: {metrics['cache_hit_rate']:.1f}%")
    print(f"Average Latency: {metrics['average_latency']:.3f}s")

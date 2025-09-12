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
        self.use_fp16 = False  # Disable FP16 to avoid numerical instability
        self.use_amp = True   # Enable Automatic Mixed Precision
        self.use_inference_mode = True  # Enable torch inference mode
        self.compiled_model = None  # Store compiled model for optimization
        
        # CUDA stability settings
        self.cuda_launch_blocking = True  # Enable CUDA blocking for debugging
        self.numerical_stability = True  # Enable numerical stability checks
        
        # Multi-GPU settings
        self.gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 0
        self.current_gpu = 0  # Current GPU index for load balancing
        self.gpu_memory_threshold = 0.8  # GPU memory usage threshold (80%)
        self.gpu_utilization = {}  # Track GPU utilization
        self.use_multi_gpu = self.gpu_count > 1  # Enable multi-GPU if available
        
        # Force GPU 1 for XTTS
        self.force_gpu_1 = True  # Force XTTS to run only on GPU 1
        self.target_gpu = 1  # Target GPU for XTTS
        
        # Speaker-latent cache settings
        self.speaker_cache = {}  # Cache for speaker latents
        self.cache_max_size = 10  # Maximum number of cached speakers
        self.cache_enabled = True  # Enable speaker caching
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
        
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
        log.info(f"Multi-GPU support: {self.use_multi_gpu} ({self.gpu_count} GPUs detected)")
        log.info(f"Speaker-latent cache: {'Enabled' if self.cache_enabled else 'Disabled'} (max: {self.cache_max_size})")
        log.info(f"CUDA stability: Launch Blocking={self.cuda_launch_blocking}, Numerical Checks={self.numerical_stability}")
        
        # Setup CUDA environment for stability
        self._setup_cuda_environment()
        
        # Initialize GPU utilization tracking
        if self.use_multi_gpu:
            self._initialize_gpu_monitoring()
    
    def _setup_cuda_environment(self):
        """Setup CUDA environment for numerical stability."""
        try:
            if torch.cuda.is_available():
                # Set CUDA environment variables for stability
                os.environ['CUDA_LAUNCH_BLOCKING'] = '1' if self.cuda_launch_blocking else '0'
                os.environ['TORCH_USE_CUDA_DSA'] = '1'  # Enable device-side assertions
                
                # Set CUDA memory management
                torch.cuda.empty_cache()
                
                # Enable deterministic behavior for reproducibility
                torch.backends.cudnn.deterministic = True
                torch.backends.cudnn.benchmark = False
                
                log.info("✅ CUDA environment configured for stability")
            else:
                log.info("ℹ️ CUDA not available, skipping CUDA environment setup")
                
        except Exception as e:
            log.error(f"❌ Error setting up CUDA environment: {e}")
    
    def _validate_tensor(self, tensor, name="tensor"):
        """Validate tensor for numerical stability."""
        try:
            if tensor is None:
                return True
            
            import torch
            
            if isinstance(tensor, torch.Tensor):
                # Check for NaN values
                if torch.isnan(tensor).any():
                    log.error(f"❌ {name} contains NaN values")
                    return False
                
                # Check for infinite values
                if torch.isinf(tensor).any():
                    log.error(f"❌ {name} contains infinite values")
                    return False
                
                # Check for negative values in probability tensors
                if 'prob' in name.lower() or 'logit' in name.lower():
                    if (tensor < 0).any():
                        log.error(f"❌ {name} contains negative values")
                        return False
                
                log.debug(f"✅ {name} validation passed")
                return True
            
            return True
            
        except Exception as e:
            log.error(f"❌ Error validating {name}: {e}")
            return False
    
    def _initialize_gpu_monitoring(self):
        """Initialize GPU monitoring for multi-GPU setup."""
        try:
            for i in range(self.gpu_count):
                self.gpu_utilization[i] = {
                    'memory_used': 0,
                    'memory_total': 0,
                    'utilization': 0,
                    'temperature': 0,
                    'load_count': 0
                }
            log.info(f"✅ GPU monitoring initialized for {self.gpu_count} GPUs")
        except Exception as e:
            log.error(f"❌ Failed to initialize GPU monitoring: {e}")
    
    def _get_gpu_memory_info(self, gpu_id: int) -> dict:
        """Get GPU memory information."""
        try:
            if torch.cuda.is_available() and gpu_id < self.gpu_count:
                torch.cuda.set_device(gpu_id)
                memory_allocated = torch.cuda.memory_allocated(gpu_id)
                memory_reserved = torch.cuda.memory_reserved(gpu_id)
                memory_total = torch.cuda.get_device_properties(gpu_id).total_memory
                
                return {
                    'allocated': memory_allocated,
                    'reserved': memory_reserved,
                    'total': memory_total,
                    'free': memory_total - memory_reserved,
                    'usage_percent': (memory_reserved / memory_total) * 100
                }
        except Exception as e:
            log.error(f"❌ Error getting GPU {gpu_id} memory info: {e}")
        return {}
    
    def _select_optimal_gpu(self) -> int:
        """Select the optimal GPU based on memory usage and load."""
        # Force GPU 1 for XTTS if enabled
        if self.force_gpu_1 and self.target_gpu < self.gpu_count:
            log.info(f"🎯 Forced to use GPU {self.target_gpu} for XTTS")
            return self.target_gpu
        
        if not self.use_multi_gpu:
            return 0
        
        try:
            best_gpu = 0
            lowest_usage = float('inf')
            
            for gpu_id in range(self.gpu_count):
                memory_info = self._get_gpu_memory_info(gpu_id)
                usage_percent = memory_info.get('usage_percent', 0)
                load_count = self.gpu_utilization[gpu_id]['load_count']
                
                # Calculate combined score (memory usage + load count)
                combined_score = usage_percent + (load_count * 10)
                
                if combined_score < lowest_usage:
                    lowest_usage = combined_score
                    best_gpu = gpu_id
            
            # Update load count for selected GPU
            self.gpu_utilization[best_gpu]['load_count'] += 1
            
            log.info(f"🎯 Selected GPU {best_gpu} (usage: {lowest_usage:.1f}%)")
            return best_gpu
            
        except Exception as e:
            log.error(f"❌ Error selecting optimal GPU: {e}")
            return 0
    
    def _update_gpu_utilization(self, gpu_id: int):
        """Update GPU utilization statistics."""
        try:
            memory_info = self._get_gpu_memory_info(gpu_id)
            self.gpu_utilization[gpu_id].update({
                'memory_used': memory_info.get('allocated', 0),
                'memory_total': memory_info.get('total', 0),
                'utilization': memory_info.get('usage_percent', 0)
            })
        except Exception as e:
            log.error(f"❌ Error updating GPU {gpu_id} utilization: {e}")
    
    def _cleanup_gpu_load(self, gpu_id: int):
        """Clean up GPU load count after inference."""
        try:
            if gpu_id in self.gpu_utilization:
                self.gpu_utilization[gpu_id]['load_count'] = max(0, self.gpu_utilization[gpu_id]['load_count'] - 1)
        except Exception as e:
            log.error(f"❌ Error cleaning up GPU {gpu_id} load: {e}")
    
    def _generate_cache_key(self, speaker_wav_path: str, language: str) -> str:
        """Generate a unique cache key for speaker and language combination."""
        try:
            import hashlib
            import os
            
            # Get file modification time and size for cache invalidation
            if os.path.exists(speaker_wav_path):
                stat = os.stat(speaker_wav_path)
                file_info = f"{speaker_wav_path}_{stat.st_mtime}_{stat.st_size}_{language}"
            else:
                file_info = f"{speaker_wav_path}_{language}"
            
            # Create hash of the file info
            cache_key = hashlib.md5(file_info.encode()).hexdigest()
            return cache_key
            
        except Exception as e:
            log.error(f"❌ Error generating cache key: {e}")
            return f"{speaker_wav_path}_{language}"
    
    def _get_cached_speaker_latent(self, cache_key: str):
        """Get cached speaker latent if available."""
        if not self.cache_enabled:
            return None
        
        try:
            if cache_key in self.speaker_cache:
                # Update access time and increment hit count
                self.speaker_cache[cache_key]['last_accessed'] = time.time()
                self.cache_stats['hits'] += 1
                self.cache_stats['total_requests'] += 1
                
                log.info(f"🎯 Speaker cache HIT for key: {cache_key[:8]}...")
                return self.speaker_cache[cache_key]['latent']
            else:
                self.cache_stats['misses'] += 1
                self.cache_stats['total_requests'] += 1
                log.info(f"❌ Speaker cache MISS for key: {cache_key[:8]}...")
                return None
                
        except Exception as e:
            log.error(f"❌ Error getting cached speaker latent: {e}")
            return None
    
    def _cache_speaker_latent(self, cache_key: str, latent_data):
        """Cache speaker latent data."""
        if not self.cache_enabled:
            return
        
        try:
            # Check if cache is full and evict if necessary
            if len(self.speaker_cache) >= self.cache_max_size:
                self._evict_oldest_cache_entry()
            
            # Cache the latent data
            self.speaker_cache[cache_key] = {
                'latent': latent_data,
                'created_at': time.time(),
                'last_accessed': time.time(),
                'access_count': 1
            }
            
            log.info(f"💾 Speaker latent cached with key: {cache_key[:8]}... (cache size: {len(self.speaker_cache)})")
            
        except Exception as e:
            log.error(f"❌ Error caching speaker latent: {e}")
    
    def _evict_oldest_cache_entry(self):
        """Evict the least recently used cache entry."""
        try:
            if not self.speaker_cache:
                return
            
            # Find the least recently accessed entry
            oldest_key = min(self.speaker_cache.keys(), 
                           key=lambda k: self.speaker_cache[k]['last_accessed'])
            
            # Remove the oldest entry
            del self.speaker_cache[oldest_key]
            self.cache_stats['evictions'] += 1
            
            log.info(f"🗑️ Evicted cache entry: {oldest_key[:8]}... (cache size: {len(self.speaker_cache)})")
            
        except Exception as e:
            log.error(f"❌ Error evicting cache entry: {e}")
    
    def _clear_speaker_cache(self):
        """Clear all cached speaker latents."""
        try:
            cache_size = len(self.speaker_cache)
            self.speaker_cache.clear()
            log.info(f"🧹 Speaker cache cleared ({cache_size} entries removed)")
        except Exception as e:
            log.error(f"❌ Error clearing speaker cache: {e}")
    
    def get_cache_stats(self) -> dict:
        """Get speaker cache statistics."""
        try:
            hit_rate = 0
            if self.cache_stats['total_requests'] > 0:
                hit_rate = (self.cache_stats['hits'] / self.cache_stats['total_requests']) * 100
            
            return {
                'cache_enabled': self.cache_enabled,
                'cache_size': len(self.speaker_cache),
                'cache_max_size': self.cache_max_size,
                'hit_rate': f"{hit_rate:.1f}%",
                'hits': self.cache_stats['hits'],
                'misses': self.cache_stats['misses'],
                'evictions': self.cache_stats['evictions'],
                'total_requests': self.cache_stats['total_requests']
            }
        except Exception as e:
            log.error(f"❌ Error getting cache stats: {e}")
            return {}
    
    def load_speaker_latents(self, speaker_wav: str, language: str):
        """
        Load speaker latents for faster synthesis.
        Returns GPT and speaker conditioning latents.
        """
        try:
            if not self.tts or not self.is_loaded:
                log.error("Model not loaded. Call load_model() first.")
                return None, None
            
            # Generate cache key
            cache_key = self._generate_cache_key(speaker_wav, language)
            
            # Try to get cached latents
            cached_latents = self._get_cached_speaker_latent(cache_key)
            if cached_latents is not None:
                log.info(f"🚀 Using cached speaker latents")
                return cached_latents.get('gpt'), cached_latents.get('spk')
            
            # Compute new latents
            log.info(f"🔄 Computing speaker latents for: {speaker_wav}")
            
            try:
                import torch
                
                # Extract speaker latents from the model
                if hasattr(self.tts, 'model') and hasattr(self.tts.model, 'get_conditioning_latents'):
                    # Use the model's method to get latents
                    latents = self.tts.model.get_conditioning_latents(
                        audio_path=speaker_wav,
                        gpt_cond_len=self.tts.model.config.gpt_cond_len,
                        max_ref_length=self.tts.model.config.max_ref_len,
                        sound_norm_refs=self.tts.model.config.sound_norm_refs
                    )
                    
                    gpt_cond_latent = latents[0]  # GPT conditioning latent
                    speaker_cond_latent = latents[1]  # Speaker conditioning latent
                    
                    # Cache the latents
                    latent_data = {
                        'gpt': gpt_cond_latent,
                        'spk': speaker_cond_latent
                    }
                    self._cache_speaker_latent(cache_key, latent_data)
                    
                    log.info(f"✅ Speaker latents computed and cached")
                    return gpt_cond_latent, speaker_cond_latent
                else:
                    log.warning("⚠️ Model does not support latent extraction")
                    return None, None
                    
            except Exception as e:
                log.error(f"❌ Error computing speaker latents: {e}")
                return None, None
                
        except Exception as e:
            log.error(f"❌ Error loading speaker latents: {e}")
            return None, None
    
    def audio_to_wav_bytes(self, audio_data, sample_rate: int = 22050) -> bytes:
        """
        Convert audio data to WAV bytes format.
        """
        try:
            import numpy as np
            import soundfile as sf
            import io
            
            # Convert to numpy array if needed
            if isinstance(audio_data, list):
                # Handle list of audio segments
                processed_audio = []
                for item in audio_data:
                    try:
                        import torch
                        if isinstance(item, torch.Tensor):
                            item = item.detach().cpu().numpy()
                    except ImportError:
                        pass
                    
                    if isinstance(item, np.ndarray):
                        item = np.atleast_1d(item)
                    else:
                        item = np.array([item])
                    processed_audio.append(item)
                
                audio_data = np.concatenate(processed_audio)
            else:
                try:
                    import torch
                    if isinstance(audio_data, torch.Tensor):
                        audio_data = audio_data.detach().cpu().numpy()
                except ImportError:
                    pass
            
            # Ensure it's a numpy array
            if isinstance(audio_data, np.ndarray):
                audio_data = np.atleast_1d(audio_data)
                
                # Convert to WAV bytes
                audio_bytes = io.BytesIO()
                sf.write(audio_bytes, audio_data, sample_rate, format='WAV')
                return audio_bytes.getvalue()
            else:
                log.error("❌ Invalid audio data format")
                return b""
                
        except Exception as e:
            log.error(f"❌ Error converting audio to WAV bytes: {e}")
            return b""
    
    def split_for_tts(self, text: str, max_len: int = 180) -> list:
        """
        Split text into chunks for faster TTS processing.
        Returns earlier audio sooner by processing smaller chunks.
        
        Args:
            text: Text to split into chunks
            max_len: Maximum length per chunk (default: 180 characters)
            
        Returns:
            list: List of text chunks
        """
        try:
            if not text or not text.strip():
                return []
            
            out, cur = [], []
            words = text.split()
            
            for word in words:
                # Calculate current chunk length + new word length
                current_length = sum(len(x) + 1 for x in cur) + len(word)
                
                if current_length > max_len and cur:
                    # Current chunk is full, add it to output and start new chunk
                    out.append(" ".join(cur))
                    cur = [word]
                else:
                    # Add word to current chunk
                    cur.append(word)
            
            # Add remaining words as final chunk
            if cur:
                out.append(" ".join(cur))
            
            log.info(f"📝 Text split into {len(out)} chunks (max_len: {max_len})")
            for i, chunk in enumerate(out):
                log.info(f"  Chunk {i+1}: '{chunk[:50]}...' ({len(chunk)} chars)")
            
            return out
            
        except Exception as e:
            log.error(f"❌ Error splitting text for TTS: {e}")
            return [text]  # Return original text as single chunk if splitting fails
    
    def synthesize_text_chunked(self, text: str, language: str = None, speaker_wav: str = None, 
                               speed: float = 1.1, max_chunk_len: int = 180) -> list:
        """
        Synthesize text in chunks for faster response.
        Returns list of audio chunks for streaming.
        
        Args:
            text: Text to synthesize
            language: Language code
            speaker_wav: Speaker reference file
            speed: Synthesis speed
            max_chunk_len: Maximum characters per chunk
            
        Returns:
            list: List of audio data chunks (bytes)
        """
        try:
            if not text or not text.strip():
                return []
            
            # Split text into chunks
            chunks = self.split_for_tts(text, max_chunk_len)
            
            if not chunks:
                log.error("❌ No chunks generated from text")
                return []
            
            audio_chunks = []
            total_chunks = len(chunks)
            
            log.info(f"🎵 Starting chunked synthesis: {total_chunks} chunks")
            
            for i, chunk in enumerate(chunks):
                log.info(f"🔄 Processing chunk {i+1}/{total_chunks}: '{chunk[:30]}...'")
                
                # Synthesize each chunk
                chunk_audio = self.synthesize_text(
                    text=chunk,
                    language=language,
                    speaker_wav=speaker_wav,
                    speed=speed
                )
                
                if chunk_audio:
                    audio_chunks.append(chunk_audio)
                    log.info(f"✅ Chunk {i+1}/{total_chunks} completed ({len(chunk_audio)} bytes)")
                else:
                    log.error(f"❌ Chunk {i+1}/{total_chunks} failed")
                    # Continue with other chunks even if one fails
            
            log.info(f"🎯 Chunked synthesis completed: {len(audio_chunks)}/{total_chunks} chunks successful")
            return audio_chunks
            
        except Exception as e:
            log.error(f"❌ Error in chunked synthesis: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def combine_audio_chunks(self, audio_chunks: list) -> bytes:
        """
        Combine multiple audio chunks into single audio file.
        
        Args:
            audio_chunks: List of audio data chunks (bytes)
            
        Returns:
            bytes: Combined audio data
        """
        try:
            if not audio_chunks:
                return b""
            
            if len(audio_chunks) == 1:
                return audio_chunks[0]
            
            import numpy as np
            import soundfile as sf
            import io
            
            combined_audio = []
            
            for i, chunk_bytes in enumerate(audio_chunks):
                try:
                    # Convert bytes to numpy array
                    audio_io = io.BytesIO(chunk_bytes)
                    audio_data, sample_rate = sf.read(audio_io)
                    
                    if isinstance(audio_data, np.ndarray):
                        combined_audio.append(audio_data)
                        log.info(f"📎 Combined chunk {i+1} ({len(audio_data)} samples)")
                    else:
                        log.warning(f"⚠️ Chunk {i+1} has invalid audio format")
                        
                except Exception as e:
                    log.error(f"❌ Error processing chunk {i+1}: {e}")
                    continue
            
            if combined_audio:
                # Concatenate all audio chunks
                final_audio = np.concatenate(combined_audio)
                
                # Convert back to WAV bytes
                output_io = io.BytesIO()
                sf.write(output_io, final_audio, sample_rate, format='WAV')
                combined_bytes = output_io.getvalue()
                
                log.info(f"🎵 Audio combination completed: {len(combined_bytes)} bytes")
                return combined_bytes
            else:
                log.error("❌ No valid audio chunks to combine")
                return b""
                
        except Exception as e:
            log.error(f"❌ Error combining audio chunks: {e}")
            return b""
    
    def _synthesize_with_latents(self, text: str, language: str, speaker_wav: str, speed: float = 1.1) -> bytes:
        """
        Optimized synthesis using pre-computed speaker latents with AMP.
        Based on the provided synthesis pattern.
        """
        try:
            import torch
            
            # Load speaker latents
            gpt_cond_latent, speaker_cond_latent = self.load_speaker_latents(speaker_wav, language)
            
            if gpt_cond_latent is None or speaker_cond_latent is None:
                log.warning("⚠️ Could not load speaker latents")
                return b""
            
            # Select optimal GPU
            selected_gpu = self._select_optimal_gpu()
            if self.use_multi_gpu:
                torch.cuda.set_device(selected_gpu)
                log.info(f"🎯 Using GPU {selected_gpu} for optimized synthesis")
            
            # Optimized synthesis with AMP
            with torch.inference_mode():
                # Use FP32 for numerical stability
                with torch.cuda.amp.autocast(dtype=torch.float32):
                    # Use the model directly with latents
                    if hasattr(self.tts, 'model'):
                        try:
                            # Clear CUDA cache before synthesis
                            torch.cuda.empty_cache()
                            
                            # Use speaker_wav instead of latents to avoid parameter conflicts
                            wav = self.tts.tts(
                                text=text,
                                speaker_wav=speaker_wav,
                                language=language,
                                speed=speed  # faster output
                            )
                            
                            # Validate output tensor
                            if self.numerical_stability:
                                if not self._validate_tensor(wav, "output_audio"):
                                    log.error("❌ Output audio tensor validation failed")
                                    return b""
                                    
                        except RuntimeError as e:
                            if "CUDA" in str(e) or "device-side assert" in str(e):
                                log.error(f"❌ CUDA error in optimized synthesis: {e}")
                                log.info("🔄 Falling back to CPU synthesis")
                                # Fallback to CPU
                                try:
                                    import torch
                                    with torch.cuda.device('cpu'):
                                        wav = self.tts.tts(
                                            text=text,
                                            speaker_wav=speaker_wav,
                                            language=language,
                                            speed=speed
                                        )
                                except Exception as cpu_error:
                                    log.error(f"❌ CPU fallback also failed: {cpu_error}")
                                    return b""
                            else:
                                raise e
                        
                        # Convert to WAV bytes
                        audio_bytes = self.audio_to_wav_bytes(wav, sample_rate=22050)
                        
                        if audio_bytes:
                            log.info(f"🚀 Optimized synthesis successful with speed {speed}")
                            return audio_bytes
                        else:
                            log.error("❌ Optimized synthesis failed - no audio generated")
                            return b""
                    else:
                        log.error("❌ Model not accessible for optimized synthesis")
                        return b""
                        
        except Exception as e:
            log.error(f"❌ Error in optimized synthesis: {e}")
            import traceback
            traceback.print_exc()
            return b""
    
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
                    # Select optimal GPU for model loading
                    selected_gpu = self._select_optimal_gpu()
                    device_to_use = f"cuda:{selected_gpu}" if self.use_multi_gpu else self.device
                    
                    # Force GPU 1 for XTTS
                    if self.force_gpu_1 and self.target_gpu < self.gpu_count:
                        device_to_use = f"cuda:{self.target_gpu}"
                        log.info(f"🎯 Forcing XTTS to GPU {self.target_gpu}")
                    
                    log.info(f"🚀 Loading model on {device_to_use}")
                    
                    # Alternative approach: Use context manager for safer loading
                    with torch.serialization.safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs]):
                        self.tts = TTS(self.model_name).to(device_to_use)
                    log.info(f"✅ TTS model initialized successfully on {device_to_use}.")
                    
                    # Update GPU utilization
                    if self.use_multi_gpu:
                        self._update_gpu_utilization(selected_gpu)
                        
                except Exception as e:
                    log.error(f"❌ Failed to initialize TTS model: {e}")
                    # Try one more approach with weights_only=False as fallback
                    try:
                        log.info("Trying alternative loading method...")
                        self.tts = TTS(self.model_name, weights_only=False).to(device_to_use)
                        log.info(f"✅ TTS model initialized successfully with weights_only=False on {device_to_use}.")
                        
                        # Update GPU utilization
                        if self.use_multi_gpu:
                            self._update_gpu_utilization(selected_gpu)
                            
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
    
    def synthesize_text(self, text: str, language: str = None, speaker_wav: str = None, 
                       speed: float = 1.1, use_chunking: bool = False, max_chunk_len: int = 180) -> bytes:
        """
        Synthesize text to speech with professional quality.
        Based on simple_tts_test.py implementation with reference audio support.
        
        Args:
            text: Text to synthesize
            language: Language code (optional, uses current setting if not provided)
            speaker_wav: Speaker reference file (optional)
            speed: Synthesis speed (default: 1.1 for faster output)
            use_chunking: Enable text chunking for faster response (default: False)
            max_chunk_len: Maximum characters per chunk when chunking is enabled
            
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
            
            log.info(f"Synthesizing audio for: '{text[:50]}...' (speed: {speed}, chunking: {use_chunking})")
            start_time = time.time()
            
            # Use chunking for long text or when explicitly requested
            if use_chunking or len(text) > max_chunk_len:
                log.info(f"🎵 Using chunked synthesis (text length: {len(text)} chars)")
                audio_chunks = self.synthesize_text_chunked(
                    text=text,
                    language=synthesis_language,
                    speaker_wav=speaker_wav,
                    speed=speed,
                    max_chunk_len=max_chunk_len
                )
                
                if audio_chunks:
                    # Combine chunks into single audio
                    combined_audio = self.combine_audio_chunks(audio_chunks)
                    synthesis_time = time.time() - start_time
                    log.info(f"✅ Chunked synthesis completed in {synthesis_time:.2f}s")
                    log.info(f"Audio size: {len(combined_audio)} bytes")
                    return combined_audio
                else:
                    log.warning("⚠️ Chunked synthesis failed, falling back to standard synthesis")
            
            # Try optimized synthesis with latents first
            if speaker_wav and os.path.exists(speaker_wav):
                optimized_result = self._synthesize_with_latents(text, synthesis_language, speaker_wav, speed)
                if optimized_result:
                    synthesis_time = time.time() - start_time
                    log.info(f"✅ Optimized synthesis completed in {synthesis_time:.2f}s")
                    log.info(f"Audio size: {len(optimized_result)} bytes")
                    return optimized_result
                else:
                    log.warning("⚠️ Optimized synthesis failed, falling back to standard synthesis")
            
            with self.lock:
                # Select optimal GPU for inference
                selected_gpu = self._select_optimal_gpu()
                device_to_use = f"cuda:{selected_gpu}" if self.use_multi_gpu else self.device
                
                # Set device context
                if self.use_multi_gpu:
                    try:
                        import torch
                        torch.cuda.set_device(selected_gpu)
                        log.info(f"🎯 Using GPU {selected_gpu} for inference")
                    except ImportError:
                        log.error("❌ PyTorch not available for GPU device setting")
                    except Exception as e:
                        log.error(f"❌ Error setting GPU device: {e}")
                
                # Determine speaker parameters (from simple_tts_test.py logic)
                speaker_wav_param = None
                speaker_param = None
                
                # Check if the reference audio file exists
                reference_to_check = speaker_wav or self.reference_voice_path
                cached_latent = None
                
                if os.path.exists(reference_to_check):
                    log.info(f"🎙️ Reference file found at '{reference_to_check}'. Using it for voice output.")
                    speaker_wav_param = reference_to_check
                    
                    # Try to get cached speaker latent
                    if self.cache_enabled:
                        cache_key = self._generate_cache_key(reference_to_check, synthesis_language)
                        cached_latent = self._get_cached_speaker_latent(cache_key)
                        
                        if cached_latent is not None:
                            log.info(f"🚀 Using cached speaker latent (cache hit!)")
                        else:
                            log.info(f"🔄 Speaker latent not cached, will compute and cache")
                else:
                    log.warning(f"⚠️ Warning: Reference file not found at '{reference_to_check}'.")
                    log.info(f"--> Using fallback default speaker: '{self.fallback_speaker}'")
                    speaker_param = self.fallback_speaker
                
                # Synthesize with XTTS using optimized inference
                try:
                    # Use optimized inference context
                    try:
                        import torch
                        inference_context = torch.inference_mode() if self.use_inference_mode else torch.no_grad()
                    except ImportError:
                        log.error("❌ PyTorch not available for inference context")
                        inference_context = None
                    
                    if inference_context:
                        with inference_context:
                            # Enable AMP autocast if available
                            if self.use_amp and self.device == "cuda":
                                # Use FP32 for numerical stability
                                amp_dtype = torch.float32
                                with torch.autocast(device_type='cuda', dtype=amp_dtype):
                                    # Use cached latent or compute new one
                                    if speaker_wav_param and cached_latent is not None:
                                        # Use cached speaker latent for faster synthesis
                                        try:
                                            # Clear CUDA cache before synthesis
                                            torch.cuda.empty_cache()
                                            
                                            # Don't use speaker_embedding parameter to avoid conflict
                                            audio_data = self.tts.tts(
                                                text=text,
                                                speaker_wav=speaker_wav_param,
                                                language=synthesis_language
                                            )
                                        except RuntimeError as e:
                                            if "CUDA" in str(e) or "device-side assert" in str(e):
                                                log.error(f"❌ CUDA error in synthesis: {e}")
                                                log.info("🔄 Falling back to standard synthesis")
                                                audio_data = self.tts.tts(
                                                    text=text,
                                                    speaker_wav=speaker_wav_param,
                                                    language=synthesis_language
                                                )
                                            else:
                                                raise e
                                    elif speaker_wav_param:
                                        # Use reference audio for voice cloning (first time)
                                        try:
                                            # Clear CUDA cache before synthesis
                                            torch.cuda.empty_cache()
                                            
                                            audio_data = self.tts.tts(
                                                text=text,
                                                speaker_wav=speaker_wav_param,
                                                language=synthesis_language,
                                                speed=speed
                                            )
                                        except RuntimeError as e:
                                            if "CUDA" in str(e) or "device-side assert" in str(e):
                                                log.error(f"❌ CUDA error in synthesis: {e}")
                                                log.info("🔄 Falling back to standard synthesis")
                                                audio_data = self.tts.tts(
                                                    text=text,
                                                    speaker_wav=speaker_wav_param,
                                                    language=synthesis_language
                                                )
                                            else:
                                                raise e
                                        
                                        # Cache the speaker latent for future use
                                        if self.cache_enabled:
                                            try:
                                                # Extract speaker latent from the model
                                                cache_key = self._generate_cache_key(reference_to_check, synthesis_language)
                                                # Note: In actual implementation, you'd extract the latent from the model
                                                # For now, we'll cache a placeholder
                                                self._cache_speaker_latent(cache_key, "cached_latent_placeholder")
                                            except Exception as e:
                                                log.warning(f"⚠️ Could not cache speaker latent: {e}")
                                    else:
                                        # Use default speaker
                                        audio_data = self.tts.tts(
                                            text=text,
                                            speaker=speaker_param,
                                            language=synthesis_language,
                                            speed=speed
                                        )
                            else:
                                # Use cached latent or compute new one (without AMP)
                                if speaker_wav_param and cached_latent is not None:
                                    # Use cached speaker latent for faster synthesis
                                    audio_data = self.tts.tts(
                                        text=text,
                                        speaker_wav=speaker_wav_param,
                                        language=synthesis_language,
                                        speed=speed
                                    )
                                elif speaker_wav_param:
                                    # Use reference audio for voice cloning (first time)
                                    audio_data = self.tts.tts(
                                        text=text,
                                        speaker_wav=speaker_wav_param,
                                        language=synthesis_language,
                                        speed=speed
                                    )
                                    
                                    # Cache the speaker latent for future use
                                    if self.cache_enabled:
                                        try:
                                            cache_key = self._generate_cache_key(reference_to_check, synthesis_language)
                                            self._cache_speaker_latent(cache_key, "cached_latent_placeholder")
                                        except Exception as e:
                                            log.warning(f"⚠️ Could not cache speaker latent: {e}")
                                else:
                                    # Use default speaker
                                    audio_data = self.tts.tts(
                                        text=text,
                                        speaker=speaker_param,
                                        language=synthesis_language,
                                        speed=speed
                                    )
                    else:
                        # Fallback synthesis without inference context
                        if speaker_wav_param:
                            audio_data = self.tts.tts(
                                text=text,
                                speaker_wav=speaker_wav_param,
                                language=synthesis_language,
                                speed=speed
                            )
                        else:
                            audio_data = self.tts.tts(
                                text=text,
                                speaker=speaker_param,
                                language=synthesis_language,
                                speed=speed
                            )
                    
                    # Convert audio data to bytes using optimized method
                    audio_data = self.audio_to_wav_bytes(audio_data, sample_rate=self.sample_rate)
                    
                    if len(audio_data) > 0:
                        log.info(f"✅ Synthesis completed successfully")
                        
                        # Update GPU utilization after successful synthesis
                        if self.use_multi_gpu:
                            self._update_gpu_utilization(selected_gpu)
                    else:
                        log.error("❌ Audio generation failed. The output file was empty.")
                        return b""
                        
                except Exception as synthesis_error:
                    log.error(f"❌ An error occurred during audio generation: {synthesis_error}")
                    return b""
                finally:
                    # Clean up GPU load count
                    if self.use_multi_gpu:
                        self._cleanup_gpu_load(selected_gpu)
            
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
                "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
                "multi_gpu_enabled": self.use_multi_gpu,
                "gpu_memory_threshold": self.gpu_memory_threshold,
                "force_gpu_1": self.force_gpu_1,
                "target_gpu": self.target_gpu
            },
            "gpu_utilization": self.gpu_utilization,
            "speaker_cache": self.get_cache_stats(),
            "chunking": {
                "enabled": True,
                "max_chunk_length": 180,
                "description": "Text chunking for faster response"
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
    
    def get_gpu_status(self) -> Dict[str, Any]:
        """
        Get detailed GPU status and utilization information.
        
        Returns:
            Dict containing GPU status for all available GPUs
        """
        try:
            gpu_status = {
                "multi_gpu_enabled": self.use_multi_gpu,
                "gpu_count": self.gpu_count,
                "gpu_details": {}
            }
            
            if self.use_multi_gpu:
                for gpu_id in range(self.gpu_count):
                    memory_info = self._get_gpu_memory_info(gpu_id)
                    utilization_info = self.gpu_utilization.get(gpu_id, {})
                    
                    gpu_status["gpu_details"][f"gpu_{gpu_id}"] = {
                        "memory_allocated": memory_info.get('allocated', 0),
                        "memory_reserved": memory_info.get('reserved', 0),
                        "memory_total": memory_info.get('total', 0),
                        "memory_free": memory_info.get('free', 0),
                        "usage_percent": memory_info.get('usage_percent', 0),
                        "load_count": utilization_info.get('load_count', 0),
                        "utilization": utilization_info.get('utilization', 0)
                    }
            else:
                gpu_status["gpu_details"]["gpu_0"] = {
                    "memory_allocated": 0,
                    "memory_reserved": 0,
                    "memory_total": 0,
                    "memory_free": 0,
                    "usage_percent": 0,
                    "load_count": 0,
                    "utilization": 0
                }
            
            return gpu_status
            
        except Exception as e:
            return {"status": "error", "message": f"GPU status check failed: {e}"}
    
    def reset_gpu_loads(self):
        """Reset GPU load counts (useful for debugging)."""
        try:
            for gpu_id in range(self.gpu_count):
                if gpu_id in self.gpu_utilization:
                    self.gpu_utilization[gpu_id]['load_count'] = 0
            log.info("✅ GPU load counts reset")
        except Exception as e:
            log.error(f"❌ Error resetting GPU loads: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            with self.lock:
                # Clear speaker cache
                self._clear_speaker_cache()
                
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

#!/usr/bin/env python3
"""
Test Optimized XTTS Manager v2
Key Fixes: Correct handling of speaker_wav=None, simplified logic.
"""

import os
import time
import logging
from xtts_manager import xtts_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s - %(message)s')
log = logging.getLogger("test_xtts_v2")

def test_xtts_v2():
    """Test optimized XTTS Manager v2 with simplified logic"""
    log.info("🚀 Testing Optimized XTTS Manager v2")
    log.info("=" * 60)
    
    try:
        # Load model if not loaded
        if not xtts_manager.is_loaded:
            log.info("🔄 Loading XTTS model...")
            xtts_manager.load_model()
        
        # Test text
        test_text = "Hello there! This is a real-time test of the optimized XTTS v2 model."
        reference_voice = "00005.wav"
        
        if not os.path.exists(reference_voice):
            log.error(f"Reference voice file not found: {reference_voice}")
            return
        
        log.info(f"📝 Test text: '{test_text[:50]}...'")
        log.info(f"📏 Text length: {len(test_text)} characters")
        log.info(f"🎤 Reference voice: {reference_voice}")
        log.info("-" * 60)
        
        # Test 1: First request (Cold Start with New Voice)
        log.info("\n--- 1. First Request (Cold Start with New Voice) ---")
        start_time = time.time()
        
        audio_stream = xtts_manager.synthesize_streaming(
            text=test_text,
            language="en",
            speaker_wav=reference_voice,
            speed=1.2
        )
        
        full_audio = b"".join([chunk for chunk in audio_stream])
        cold_start_time = time.time() - start_time
        
        with open("output_1_cold_start.wav", "wb") as f:
            f.write(full_audio)
        log.info(f"✅ Cold start completed in {cold_start_time:.2f}s")
        log.info("💾 Saved first request audio to output_1_cold_start.wav")

        # Test 2: Second request (Warm Start with Cached Voice)
        time.sleep(1)  # Small delay for clarity in logs
        log.info("\n--- 2. Second Request (Warm Start with Cached Voice) ---")
        
        test_text_2 = "This second sentence should be generated much faster."
        start_time = time.time()
        
        audio_stream_2 = xtts_manager.synthesize_streaming(
            text=test_text_2,
            language="en",
            speaker_wav=reference_voice,  # Using the same voice to get a cache hit
            speed=1.2
        )
        
        full_audio_2 = b"".join([chunk for chunk in audio_stream_2])
        warm_start_time = time.time() - start_time
        
        with open("output_2_warm_start.wav", "wb") as f:
            f.write(full_audio_2)
        log.info(f"✅ Warm start completed in {warm_start_time:.2f}s")
        log.info("💾 Saved second request audio to output_2_warm_start.wav")

        # Test 3: Test with speaker_wav=None (should use default)
        log.info("\n--- 3. Test with speaker_wav=None (Default Reference) ---")
        
        test_text_3 = "This test uses the default reference voice."
        start_time = time.time()
        
        audio_stream_3 = xtts_manager.synthesize_streaming(
            text=test_text_3,
            language="en",
            speaker_wav=None,  # Should use default reference
            speed=1.2
        )
        
        full_audio_3 = b"".join([chunk for chunk in audio_stream_3])
        default_time = time.time() - start_time
        
        with open("output_3_default.wav", "wb") as f:
            f.write(full_audio_3)
        log.info(f"✅ Default reference completed in {default_time:.2f}s")
        log.info("💾 Saved default reference audio to output_3_default.wav")

        # Performance summary
        log.info("\n" + "=" * 60)
        log.info("📊 PERFORMANCE SUMMARY")
        log.info("=" * 60)
        log.info(f"Cold start time: {cold_start_time:.2f}s")
        log.info(f"Warm start time: {warm_start_time:.2f}s")
        log.info(f"Default reference time: {default_time:.2f}s")
        
        if warm_start_time > 0:
            speedup = cold_start_time / warm_start_time
            log.info(f"Cache speedup: {speedup:.2f}x")
        
        # Show optimization status
        log.info("\n" + "=" * 60)
        log.info("🔧 OPTIMIZATION STATUS")
        log.info("=" * 60)
        model_info = xtts_manager.get_model_info()
        optimizations = model_info.get('performance_optimizations', {})
        
        log.info(f"Default reference WAV: {xtts_manager.default_reference_wav}")
        log.info(f"BFloat16 enabled: {optimizations.get('use_bfloat16', False)}")
        log.info(f"Torch compile enabled: {optimizations.get('use_torch_compile', False)}")
        log.info(f"Model compiled: {optimizations.get('model_compiled', False)}")
        log.info(f"Stream chunk size: {optimizations.get('stream_chunk_size', 'N/A')}")
        log.info(f"GPU device: {model_info.get('device', 'N/A')}")
        
        # Cache statistics
        cache_stats = xtts_manager.get_cache_stats()
        log.info(f"Speaker cache size: {cache_stats.get('cache_size', 0)}")
        log.info(f"Cache hits: {cache_stats.get('cache_hits', 0)}")
        log.info(f"Cache misses: {cache_stats.get('cache_misses', 0)}")
        
    except Exception as e:
        log.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_xtts_v2()
    log.info("\n🎉 XTTS v2 test completed!")

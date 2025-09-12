#!/usr/bin/env python3
"""
Test Optimized Streaming XTTS Synthesis
Hardware Target: NVIDIA RTX A5000 (Ampere Architecture)
"""

import os
import time
import logging
from xtts_manager import xtts_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s - %(message)s')
log = logging.getLogger("test_streaming")

def test_optimized_streaming():
    """Test optimized streaming synthesis"""
    log.info("🚀 Testing Optimized Streaming XTTS Synthesis")
    log.info("=" * 60)
    
    try:
        # Load model if not loaded
        if not xtts_manager.is_loaded:
            log.info("🔄 Loading XTTS model...")
            xtts_manager.load_model()
        
        # Test text
        test_text = "Hello there! This is a real-time test of the optimized XTTS v2 model, streaming audio chunks as they are generated."
        reference_voice = "00005.wav"
        
        if not os.path.exists(reference_voice):
            log.error(f"Reference voice file not found: {reference_voice}")
            return
        
        log.info(f"📝 Test text: '{test_text[:50]}...'")
        log.info(f"📏 Text length: {len(test_text)} characters")
        log.info(f"🎤 Reference voice: {reference_voice}")
        log.info("-" * 60)
        
        # Test streaming synthesis
        log.info("🎤 Starting optimized streaming synthesis...")
        start_time = time.time()
        
        audio_stream = xtts_manager.synthesize_streaming(
            text=test_text,
            language="en",
            speaker_wav=reference_voice,
            speed=1.2
        )
        
        # Collect streaming chunks
        full_audio = b""
        chunk_count = 0
        chunk_times = []
        
        for audio_chunk in audio_stream:
            chunk_time = time.time()
            chunk_duration = chunk_time - start_time
            chunk_times.append(chunk_duration)
            
            log.info(f"🎧 Received chunk {chunk_count}, size: {len(audio_chunk)} bytes, time: {chunk_duration:.2f}s")
            full_audio += audio_chunk
            chunk_count += 1
        
        total_time = time.time() - start_time
        
        # Save combined audio
        if full_audio:
            output_filename = "optimized_streaming_output.wav"
            with open(output_filename, "wb") as f:
                f.write(full_audio)
            log.info(f"💾 Full audio saved to {output_filename}")
        
        # Performance summary
        log.info("-" * 60)
        log.info("📊 PERFORMANCE SUMMARY")
        log.info("-" * 60)
        log.info(f"Total synthesis time: {total_time:.2f}s")
        log.info(f"Total chunks received: {chunk_count}")
        log.info(f"Total audio size: {len(full_audio)} bytes")
        
        if chunk_times:
            first_chunk_time = chunk_times[0]
            log.info(f"Time to first chunk: {first_chunk_time:.2f}s")
            log.info(f"Average chunk interval: {total_time/chunk_count:.2f}s")
        
        # Show optimization status
        log.info("-" * 60)
        log.info("🔧 OPTIMIZATION STATUS")
        log.info("-" * 60)
        model_info = xtts_manager.get_model_info()
        optimizations = model_info.get('performance_optimizations', {})
        
        log.info(f"BFloat16 enabled: {optimizations.get('use_bfloat16', False)}")
        log.info(f"Torch compile enabled: {optimizations.get('use_torch_compile', False)}")
        log.info(f"Model compiled: {optimizations.get('model_compiled', False)}")
        log.info(f"Stream chunk size: {optimizations.get('stream_chunk_size', 'N/A')}")
        log.info(f"GPU device: {model_info.get('device', 'N/A')}")
        
    except Exception as e:
        log.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def test_performance_comparison():
    """Compare streaming vs non-streaming performance"""
    log.info("\n🚀 Performance Comparison Test")
    log.info("=" * 60)
    
    test_text = "This is a performance comparison test between streaming and non-streaming synthesis."
    reference_voice = "00005.wav"
    
    if not os.path.exists(reference_voice):
        log.error(f"Reference voice file not found: {reference_voice}")
        return
    
    try:
        # Test non-streaming synthesis
        log.info("🔄 Testing non-streaming synthesis...")
        start_time = time.time()
        
        audio_data = xtts_manager.synthesize_text(
            text=test_text,
            language="en",
            speaker_wav=reference_voice,
            speed=1.2
        )
        
        non_streaming_time = time.time() - start_time
        log.info(f"✅ Non-streaming synthesis: {non_streaming_time:.2f}s, size: {len(audio_data)} bytes")
        
        # Test streaming synthesis
        log.info("🔄 Testing streaming synthesis...")
        start_time = time.time()
        
        audio_stream = xtts_manager.synthesize_streaming(
            text=test_text,
            language="en",
            speaker_wav=reference_voice,
            speed=1.2
        )
        
        # Collect first chunk time
        first_chunk_time = None
        total_chunks = 0
        total_size = 0
        
        for chunk in audio_stream:
            if first_chunk_time is None:
                first_chunk_time = time.time() - start_time
            total_size += len(chunk)
            total_chunks += 1
        
        streaming_total_time = time.time() - start_time
        
        log.info(f"✅ Streaming synthesis: {streaming_total_time:.2f}s, size: {total_size} bytes")
        log.info(f"✅ Time to first chunk: {first_chunk_time:.2f}s")
        log.info(f"✅ Total chunks: {total_chunks}")
        
        # Comparison
        log.info("-" * 60)
        log.info("📊 COMPARISON RESULTS")
        log.info("-" * 60)
        log.info(f"Non-streaming time: {non_streaming_time:.2f}s")
        log.info(f"Streaming total time: {streaming_total_time:.2f}s")
        log.info(f"Time to first chunk: {first_chunk_time:.2f}s")
        
        if first_chunk_time:
            improvement = non_streaming_time / first_chunk_time
            log.info(f"Speedup to first audio: {improvement:.2f}x")
        
    except Exception as e:
        log.error(f"❌ Performance comparison failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run tests
    test_optimized_streaming()
    test_performance_comparison()
    
    log.info("\n🎉 All tests completed!")

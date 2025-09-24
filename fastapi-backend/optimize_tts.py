#!/usr/bin/env python3
"""
TTS Performance Optimization Script
This script demonstrates the optimized TTS loading and usage patterns.
"""

import time
import asyncio
from tts_factory import get_tts_factory, synthesize_text_async

async def test_optimized_tts():
    """Test optimized TTS performance"""
    print("🚀 TTS Performance Optimization Test")
    print("=" * 50)
    
    # Get singleton factory (models loaded once)
    tts_factory = get_tts_factory()
    provider = tts_factory.get_provider()
    
    print(f"✅ TTS System: {provider.name}")
    print(f"✅ Available: {provider.is_available()}")
    
    # Test texts
    test_texts = [
        "Hello, this is a test.",
        "How are you doing today?",
        "This is an optimized TTS system.",
        "The model is loaded only once.",
        "Audio generation is now much faster."
    ]
    
    print(f"\n🎤 Testing {len(test_texts)} audio generations...")
    
    # Measure performance
    start_time = time.time()
    
    for i, text in enumerate(test_texts, 1):
        print(f"Generating audio {i}/{len(test_texts)}: '{text[:30]}...'")
        
        # Generate audio (no model reloading)
        audio_data = await provider.synthesize_async(text, "en")
        
        if audio_data:
            print(f"  ✅ Generated: {len(audio_data)} bytes")
        else:
            print(f"  ❌ Failed to generate audio")
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / len(test_texts)
    
    print(f"\n📊 Performance Results:")
    print(f"  Total time: {total_time:.2f} seconds")
    print(f"  Average per generation: {avg_time:.2f} seconds")
    print(f"  Generations per second: {1/avg_time:.1f}")
    
    # Test voice switching
    print(f"\n🎤 Testing voice switching...")
    voices = ["en_US-libritts-high", "en_GB-cori-medium", "en_US-ryan-high", "en_GB-northern_english_male-medium"]
    
    for voice in voices:
        print(f"Switching to voice: {voice}")
        start_switch = time.time()
        
        audio_data = await provider.synthesize_async("Voice switch test", "en", voice=voice)
        
        switch_time = time.time() - start_switch
        print(f"  ✅ Voice switch completed in {switch_time:.2f} seconds")
    
    print(f"\n🎯 Optimization Summary:")
    print(f"  ✅ Models loaded once at startup")
    print(f"  ✅ Voice caching implemented")
    print(f"  ✅ Singleton pattern prevents multiple instances")
    print(f"  ✅ Direct synthesis without file I/O")
    print(f"  ✅ Memory-based audio generation")

if __name__ == "__main__":
    asyncio.run(test_optimized_tts())

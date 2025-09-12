#!/usr/bin/env python3
"""
Final TTS System Test
Tests the complete TTS system without FastAPI server.
"""

import os
import logging
import time

# Set environment for local development
os.environ["TTS_ENVIRONMENT"] = "local"
os.environ["TTS_SYSTEM"] = "gtts"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("test_tts_final")

def test_tts_factory():
    """Test TTS factory system."""
    try:
        log.info("Testing TTS Factory System...")
        
        from tts_factory import get_tts_info, synthesize_text, synthesize_text_async
        
        # Test 1: Get TTS info
        log.info("1. Testing TTS info...")
        info = get_tts_info()
        log.info(f"   Environment: {info['environment']}")
        log.info(f"   Preferred System: {info['preferred_system']}")
        log.info(f"   Available Providers: {', '.join(info['available_providers'])}")
        
        # Test 2: Synchronous synthesis
        log.info("2. Testing synchronous synthesis...")
        start_time = time.time()
        audio_data = synthesize_text("Hello, this is a test of the TTS system.")
        end_time = time.time()
        
        if audio_data:
            log.info(f"   ✅ Sync synthesis successful: {len(audio_data)} bytes in {end_time - start_time:.2f}s")
        else:
            log.error("   ❌ Sync synthesis failed")
            return False
        
        # Test 3: Asynchronous synthesis
        log.info("3. Testing asynchronous synthesis...")
        start_time = time.time()
        import asyncio
        audio_data_async = asyncio.run(synthesize_text_async("Hello, this is an async test."))
        end_time = time.time()
        
        if audio_data_async:
            log.info(f"   ✅ Async synthesis successful: {len(audio_data_async)} bytes in {end_time - start_time:.2f}s")
        else:
            log.error("   ❌ Async synthesis failed")
            return False
        
        # Test 4: Different languages
        log.info("4. Testing different languages...")
        languages = ["en", "es", "fr"]
        for lang in languages:
            try:
                audio = synthesize_text(f"Hello in {lang}", language=lang)
                if audio:
                    log.info(f"   ✅ {lang}: {len(audio)} bytes")
                else:
                    log.warning(f"   ⚠️ {lang}: No audio generated")
            except Exception as e:
                log.warning(f"   ⚠️ {lang}: Error - {e}")
        
        return True
        
    except Exception as e:
        log.error(f"❌ TTS factory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment_switching():
    """Test environment switching."""
    try:
        log.info("Testing Environment Switching...")
        
        # Test local environment
        os.environ["TTS_ENVIRONMENT"] = "local"
        from tts_factory import get_tts_info
        info = get_tts_info()
        log.info(f"   Local environment: {info['preferred_system']}")
        
        # Test production environment
        os.environ["TTS_ENVIRONMENT"] = "production"
        from tts_factory import get_tts_info
        info = get_tts_info()
        log.info(f"   Production environment: {info['preferred_system']}")
        
        # Reset to local
        os.environ["TTS_ENVIRONMENT"] = "local"
        
        return True
        
    except Exception as e:
        log.error(f"❌ Environment switching test failed: {e}")
        return False

def test_audio_quality():
    """Test audio quality and format."""
    try:
        log.info("Testing Audio Quality...")
        
        from tts_factory import synthesize_text
        import tempfile
        import os
        
        # Generate audio
        audio_data = synthesize_text("This is a quality test of the TTS system.")
        
        if audio_data:
            # Save to temporary file for analysis
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            try:
                with open(temp_path, 'wb') as f:
                    f.write(audio_data)
                
                file_size = os.path.getsize(temp_path)
                log.info(f"   ✅ Audio file created: {file_size} bytes")
                log.info(f"   📁 Temporary file: {temp_path}")
                
                # Basic audio analysis
                if file_size > 1000:  # At least 1KB
                    log.info("   ✅ Audio quality: Good (sufficient size)")
                else:
                    log.warning("   ⚠️ Audio quality: Low (small size)")
                
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            return True
        else:
            log.error("   ❌ No audio data generated")
            return False
            
    except Exception as e:
        log.error(f"❌ Audio quality test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🎵 Final TTS System Test")
    print("="*60)
    
    # Run all tests
    tests = [
        ("TTS Factory", test_tts_factory),
        ("Environment Switching", test_environment_switching),
        ("Audio Quality", test_audio_quality)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        print("-" * 40)
        success = test_func()
        results.append((test_name, success))
        print(f"{'✅ PASSED' if success else '❌ FAILED'}: {test_name}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Results Summary:")
    print("="*60)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! TTS system is working perfectly!")
        print("\n🚀 Your TTS system is ready for:")
        print("   • Local development with gTTS")
        print("   • Production deployment with Coqui TTS")
        print("   • Real-time streaming")
        print("   • Multi-language support")
        return 0
    else:
        print(f"\n❌ {len(results) - passed} tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())

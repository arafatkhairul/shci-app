#!/usr/bin/env python3
"""
XTTS Test Script - Test XTTS functionality
"""

import asyncio
import logging
from xtts_wrapper import xtts_wrapper

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("xtts_test")

async def test_xtts():
    """Test XTTS functionality"""
    try:
        log.info("🧪 Starting XTTS test...")
        
        # Initialize XTTS
        log.info("1. Initializing XTTS...")
        success = await xtts_wrapper.initialize()
        if not success:
            log.error("❌ Failed to initialize XTTS")
            return False
        
        log.info("✅ XTTS initialized successfully")
        
        # Test synthesis
        log.info("2. Testing text synthesis...")
        test_texts = [
            "Hello, this is a test of the XTTS system.",
            "XTTS provides high-quality multilingual speech synthesis.",
            "This is professional text-to-speech technology."
        ]
        
        for i, text in enumerate(test_texts, 1):
            log.info(f"   Test {i}: '{text[:30]}...'")
            audio_bytes = await xtts_wrapper.synthesize_async(text, "en")
            
            if audio_bytes:
                log.info(f"   ✅ Generated {len(audio_bytes)} bytes")
            else:
                log.error(f"   ❌ Failed to generate audio")
                return False
        
        # Test different languages
        log.info("3. Testing different languages...")
        languages = ["en", "es", "fr", "de"]
        
        for lang in languages:
            log.info(f"   Testing language: {lang}")
            success = await xtts_wrapper.set_language_async(lang)
            if success:
                audio_bytes = await xtts_wrapper.synthesize_async("Hello world", lang)
                if audio_bytes:
                    log.info(f"   ✅ {lang}: Generated {len(audio_bytes)} bytes")
                else:
                    log.error(f"   ❌ {lang}: Failed to generate audio")
            else:
                log.error(f"   ❌ {lang}: Unsupported language")
        
        # Test parameters
        log.info("4. Testing synthesis parameters...")
        params = {"speed": 1.2, "temperature": 0.8}
        success = await xtts_wrapper.update_params_async(**params)
        if success:
            log.info("   ✅ Parameters updated successfully")
        else:
            log.error("   ❌ Failed to update parameters")
        
        # Health check
        log.info("5. Performing health check...")
        health = await xtts_wrapper.health_check_async()
        log.info(f"   Health status: {health}")
        
        # Get system info
        log.info("6. Getting system information...")
        info = await xtts_wrapper.get_info_async()
        log.info(f"   System info: {info.get('tts_system', 'Unknown')}")
        log.info(f"   Model: {info.get('model_name', 'Unknown')}")
        log.info(f"   Device: {info.get('device', 'Unknown')}")
        
        log.info("🎉 All XTTS tests completed successfully!")
        return True
        
    except Exception as e:
        log.error(f"❌ Test failed: {e}")
        return False

async def main():
    """Main test function"""
    try:
        success = await test_xtts()
        if success:
            log.info("✅ XTTS test suite passed!")
        else:
            log.error("❌ XTTS test suite failed!")
    except Exception as e:
        log.error(f"❌ Test suite error: {e}")
    finally:
        # Cleanup
        await xtts_wrapper.cleanup_async()

if __name__ == "__main__":
    asyncio.run(main())

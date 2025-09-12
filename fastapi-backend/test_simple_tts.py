#!/usr/bin/env python3
"""
Simple TTS Test
Tests the TTS system without complex imports.
"""

import os
import logging

# Set environment for local development
os.environ["TTS_ENVIRONMENT"] = "local"
os.environ["TTS_SYSTEM"] = "gtts"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("test_simple_tts")

def test_gtts_direct():
    """Test gTTS directly."""
    try:
        from gtts import gTTS
        import tempfile
        import os
        
        log.info("Testing gTTS directly...")
        
        # Create gTTS object
        tts = gTTS(text="Hello, this is a test.", lang="en", slow=False)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            tts.save(temp_path)
            
            # Check file size
            file_size = os.path.getsize(temp_path)
            log.info(f"✅ gTTS test successful: {file_size} bytes")
            
            return True
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        log.error(f"❌ gTTS test failed: {e}")
        return False

def test_tts_factory():
    """Test TTS factory."""
    try:
        log.info("Testing TTS factory...")
        
        from tts_factory import get_tts_info, synthesize_text
        
        # Get info
        info = get_tts_info()
        log.info(f"TTS Info: {info}")
        
        # Test synthesis
        audio_data = synthesize_text("Hello, this is a test.")
        
        if audio_data:
            log.info(f"✅ TTS factory test successful: {len(audio_data)} bytes")
            return True
        else:
            log.error("❌ TTS factory test failed: No audio data")
            return False
            
    except Exception as e:
        log.error(f"❌ TTS factory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🎵 Simple TTS Test")
    print("="*50)
    
    # Test gTTS directly
    gtts_success = test_gtts_direct()
    
    # Test TTS factory
    factory_success = test_tts_factory()
    
    print("\n" + "="*50)
    print("📊 Test Results:")
    print(f"gTTS Direct: {'✅ Success' if gtts_success else '❌ Failed'}")
    print(f"TTS Factory: {'✅ Success' if factory_success else '❌ Failed'}")
    
    if gtts_success and factory_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())

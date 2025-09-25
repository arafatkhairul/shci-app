#!/usr/bin/env python3
"""
Test script to verify RealtimeSTT is working properly
"""

import time
import logging
from RealtimeSTT import AudioToTextRecorder

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def on_realtime_transcription_update(text: str):
    """Handle real-time transcription updates."""
    print(f"🔄 Realtime: {text}")

def on_sentence_finish(text: str):
    """Handle sentence completion."""
    print(f"✅ Final: {text}")

def main():
    """Test RealtimeSTT functionality."""
    print("🎤 Testing RealtimeSTT...")
    
    try:
        # Create recorder with callbacks
        recorder = AudioToTextRecorder(
            model="base.en",
            language="en",
            use_microphone=True,
            on_realtime_transcription_update=on_realtime_transcription_update,
            on_realtime_transcription_stabilized=on_sentence_finish,
            spinner=False
        )
        
        print("✅ RealtimeSTT recorder created successfully")
        print("🎤 Start speaking... (Press Ctrl+C to stop)")
        
        # Start the recorder
        recorder.start()
        
        # Test for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping test...")
                break
        
    except Exception as e:
        print(f"❌ Failed to create RealtimeSTT recorder: {e}")
        return False
    
    finally:
        try:
            recorder.shutdown()
            print("✅ RealtimeSTT recorder shutdown complete")
        except:
            pass
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ RealtimeSTT test completed successfully")
    else:
        print("❌ RealtimeSTT test failed")

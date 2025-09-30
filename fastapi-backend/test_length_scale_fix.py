#!/usr/bin/env python3
"""
Test script to verify length_scale fix works in the actual application
"""
import os
import sys
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tts_service():
    """Test TTS service with different length_scale values"""
    
    print("🔍 Testing TTS Service with different length_scale values...")
    print("=" * 60)
    
    try:
        from app.services.tts_service import TTSService
        
        # Initialize TTS service
        tts_service = TTSService()
        
        test_text = "Hello, this is a test of the TTS service with different speech speeds."
        
        # Test different length_scale values
        test_values = [
            (0.4, "Very Fast"),
            (1.0, "Normal"),
            (1.5, "Slow"),
            (3.0, "Very Slow")
        ]
        
        for length_scale, description in test_values:
            print(f"🎵 Testing length_scale = {length_scale} ({description})")
            
            try:
                start_time = time.time()
                
                # Test async synthesis
                import asyncio
                audio_data = asyncio.run(tts_service.synthesize_text(
                    text=test_text,
                    language="en",
                    length_scale=length_scale
                ))
                
                synthesis_time = time.time() - start_time
                
                if audio_data:
                    # Save test file
                    output_file = f"tts_service_test_{length_scale}.wav"
                    with open(output_file, 'wb') as f:
                        f.write(audio_data)
                    
                    # Get audio duration
                    import wave
                    with wave.open(output_file, 'rb') as wf:
                        duration = wf.getnframes() / wf.getframerate()
                    
                    print(f"   ✅ Success: {len(audio_data)} bytes, {duration:.2f}s duration, {synthesis_time:.2f}s synthesis time")
                    print(f"   📁 Saved: {output_file}")
                else:
                    print(f"   ❌ Failed: No audio data returned")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            print()
        
        print("=" * 60)
        print("🎯 TTS Service testing complete!")
        
    except Exception as e:
        print(f"❌ Error initializing TTS service: {e}")
        import traceback
        traceback.print_exc()

def test_environment_variables():
    """Test different environment variable values"""
    
    print("\n🔍 Testing environment variable changes...")
    print("=" * 60)
    
    # Test different PIPER_LENGTH_SCALE values
    test_values = [0.4, 1.0, 1.5, 3.0]
    
    for length_scale in test_values:
        print(f"🎵 Testing PIPER_LENGTH_SCALE = {length_scale}")
        
        # Set environment variable
        os.environ["PIPER_LENGTH_SCALE"] = str(length_scale)
        
        try:
            # Reimport settings to get new value
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            print(f"   Settings value: {settings.PIPER_LENGTH_SCALE}")
            
            # Test synthesis with new setting
            from tts_factory import synthesize_text
            
            test_text = "This is a test with environment variable length scale."
            
            start_time = time.time()
            audio_data = synthesize_text(test_text, "en")
            synthesis_time = time.time() - start_time
            
            if audio_data:
                # Save test file
                output_file = f"env_test_{length_scale}.wav"
                with open(output_file, 'wb') as f:
                    f.write(audio_data)
                
                # Get audio duration
                import wave
                with wave.open(output_file, 'rb') as wf:
                    duration = wf.getnframes() / wf.getframerate()
                
                print(f"   ✅ Success: {len(audio_data)} bytes, {duration:.2f}s duration, {synthesis_time:.2f}s synthesis time")
                print(f"   📁 Saved: {output_file}")
            else:
                print(f"   ❌ Failed: No audio data returned")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()

if __name__ == "__main__":
    print("🚀 Starting length_scale fix verification...")
    
    # Test TTS service
    test_tts_service()
    
    # Test environment variables
    test_environment_variables()
    
    print("\n🎉 All tests complete!")

#!/usr/bin/env python3
"""
Test script to generate audio with all 4 voices
This will help identify if Ryan voice is working properly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_all_voices():
    """Test all 4 voices and generate audio files"""
    
    from tts_factory import synthesize_text
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing All 4 Voices")
    print("=" * 50)
    
    # Test voices
    voices = [
        "en_US-libritts-high",      # Sarah (Female)
        "en_GB-cori-medium",        # Cori (Female) 
        "en_US-ryan-high",          # Ryan (Male)
        "en_GB-northern_english_male-medium"  # Northern English Male
    ]
    
    test_text = "Hello, this is a test of the voice system. My name is Ryan and I am a male voice."
    
    for i, voice_id in enumerate(voices, 1):
        print(f"\n{i}. Testing voice: {voice_id}")
        try:
            # Generate audio
            audio_data = synthesize_text(test_text, "en", voice_id)
            
            if audio_data:
                # Save audio file
                filename = f"test_voice_{i}_{voice_id.replace('-', '_')}.wav"
                with open(filename, 'wb') as f:
                    f.write(audio_data)
                print(f"  ✅ Success: {len(audio_data)} bytes saved to {filename}")
            else:
                print(f"  ❌ Failed: No audio data generated")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n🎉 All voice tests completed!")
    print(f"Check the generated .wav files to verify audio quality")

if __name__ == "__main__":
    test_all_voices()

#!/usr/bin/env python3
"""
Create Default Speaker Audio for XTTS
"""

import numpy as np
import soundfile as sf
import os

def create_default_speaker():
    """Create a simple default speaker audio file"""
    try:
        # Create a simple sine wave as default speaker
        sample_rate = 22050
        duration = 3.0  # 3 seconds
        frequency = 440  # A4 note
        
        # Generate sine wave
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = np.sin(2 * np.pi * frequency * t) * 0.3  # Reduce amplitude
        
        # Add some variation to make it more natural
        audio += np.sin(2 * np.pi * frequency * 1.5 * t) * 0.1
        audio += np.sin(2 * np.pi * frequency * 0.5 * t) * 0.05
        
        # Normalize
        audio = audio / np.max(np.abs(audio)) * 0.8
        
        # Save as WAV file
        output_path = "models/speakers/default_speaker.wav"
        sf.write(output_path, audio, sample_rate)
        
        print(f"✅ Default speaker audio created: {output_path}")
        print(f"   Duration: {duration}s")
        print(f"   Sample Rate: {sample_rate}Hz")
        print(f"   File Size: {os.path.getsize(output_path)} bytes")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error creating default speaker: {e}")
        return None

if __name__ == "__main__":
    create_default_speaker()

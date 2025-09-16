#!/usr/bin/env python3
"""
TTS Configuration Script
Choose between Piper TTS (fast) and Coqui TTS (high-quality)
"""

import os
import sys
from pathlib import Path

def create_env_file(tts_system: str):
    """Create .env file with TTS configuration"""
    
    env_content = f"""# TTS Configuration
TTS_SYSTEM={tts_system}

# Piper TTS Configuration (for speed)
PIPER_MODEL_NAME=en_US-ljspeech-high
PIPER_LENGTH_SCALE=1.5
PIPER_NOISE_SCALE=1.0
PIPER_NOISE_W=0.8

# Coqui TTS Configuration (for quality)
USE_DEEPSPEED=false
CUDA_VISIBLE_DEVICES=0

# Application Configuration
ENVIRONMENT=development
LLM_API_URL=http://173.208.167.147:11434/v1/chat/completions
LLM_MODEL=qwen2.5-14b-gpu
LLM_TIMEOUT=10.0
LLM_RETRIES=1

# Voice Activity Detection
TRIGGER_VOICED_FRAMES=2
END_SILENCE_MS=250
MAX_UTTER_MS=7000

# Assistant Configuration
ASSISTANT_NAME=Self Hosted Conversational Interface
ASSISTANT_AUTHOR=NZR DEV
DEFAULT_LANGUAGE=en
"""
    
    env_file = Path(".env")
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print(f"✅ Created .env file with TTS_SYSTEM={tts_system}")

def show_tts_options():
    """Show available TTS options"""
    print("🎤 TTS Engine Selection")
    print("=" * 50)
    print("1. Piper TTS (Fast)")
    print("   - Speed: ⚡ Very Fast (0.07s)")
    print("   - Quality: 🎯 Good")
    print("   - Memory: 💾 Low")
    print("   - Best for: Real-time applications")
    print()
    print("2. Coqui TTS (High Quality)")
    print("   - Speed: 🎤 Medium (1-2s)")
    print("   - Quality: 🌟 Excellent")
    print("   - Memory: 💾 Medium")
    print("   - Best for: High-quality voice synthesis")
    print()
    print("3. Integrated TTS (Auto-select)")
    print("   - Speed: ⚡ Auto-optimized")
    print("   - Quality: 🌟 Best available")
    print("   - Memory: 💾 Optimized")
    print("   - Best for: Production with fallback")
    print()

def main():
    """Main configuration function"""
    print("🚀 SHCI TTS Configuration")
    print("=" * 50)
    
    show_tts_options()
    
    while True:
        choice = input("Select TTS engine (1/2/3): ").strip()
        
        if choice == "1":
            create_env_file("piper")
            print("\n🎯 Configuration Complete!")
            print("✅ Using Piper TTS for maximum speed")
            print("🚀 Run: python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
            break
            
        elif choice == "2":
            create_env_file("coqui")
            print("\n🎯 Configuration Complete!")
            print("✅ Using Coqui TTS for maximum quality")
            print("🚀 Run: python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
            break
            
        elif choice == "3":
            create_env_file("integrated")
            print("\n🎯 Configuration Complete!")
            print("✅ Using Integrated TTS with auto-selection")
            print("🚀 Run: python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
            break
            
        else:
            print("❌ Invalid choice. Please select 1, 2, or 3.")
    
    print("\n📋 Additional Commands:")
    print("  Test TTS: python test_coqui_integration.py")
    print("  Check status: curl http://localhost:8000/health/")
    print("  TTS endpoint: curl -X POST http://localhost:8000/tts/synthesize")

if __name__ == "__main__":
    main()

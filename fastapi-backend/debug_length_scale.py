#!/usr/bin/env python3
"""
Debug script to test length_scale functionality in Piper TTS
"""
import os
import sys
import time
import wave
import tempfile
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_length_scale_values():
    """Test different length_scale values to see if they work"""
    
    print("🔍 Testing length_scale functionality...")
    print("=" * 60)
    
    # Test text
    test_text = "Hello, this is a test of speech synthesis with different speeds."
    
    # Test different length_scale values
    test_values = [
        (0.4, "Very Fast"),
        (1.0, "Normal"),
        (1.5, "Slow"),
        (3.0, "Very Slow")
    ]
    
    try:
        from tts_factory import get_tts_factory
        
        # Get TTS factory
        tts_factory = get_tts_factory()
        provider = tts_factory.get_provider()
        
        if not provider.is_available():
            print("❌ TTS provider not available")
            return
        
        print(f"✅ Using TTS provider: {provider.name}")
        print(f"✅ Current voice: {provider.current_voice}")
        print()
        
        for length_scale, description in test_values:
            print(f"🎵 Testing length_scale = {length_scale} ({description})")
            
            try:
                # Test synthesis with specific length_scale
                start_time = time.time()
                
                audio_data = provider.synthesize_sync(
                    text=test_text,
                    language="en",
                    length_scale=length_scale,
                    noise_scale=1.0,
                    noise_w=0.5
                )
                
                synthesis_time = time.time() - start_time
                
                if audio_data:
                    # Save test file
                    output_file = f"test_length_scale_{length_scale}.wav"
                    with open(output_file, 'wb') as f:
                        f.write(audio_data)
                    
                    # Get audio duration
                    with wave.open(output_file, 'rb') as wf:
                        duration = wf.getnframes() / wf.getframerate()
                    
                    print(f"   ✅ Success: {len(audio_data)} bytes, {duration:.2f}s duration, {synthesis_time:.2f}s synthesis time")
                    print(f"   📁 Saved: {output_file}")
                else:
                    print(f"   ❌ Failed: No audio data returned")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            print()
        
        print("=" * 60)
        print("🎯 Testing complete!")
        
    except Exception as e:
        print(f"❌ Error initializing TTS: {e}")
        import traceback
        traceback.print_exc()

def test_piper_direct():
    """Test Piper TTS directly to isolate the issue"""
    
    print("\n🔍 Testing Piper TTS directly...")
    print("=" * 60)
    
    try:
        from piper.voice import PiperVoice, SynthesisConfig
        
        model_path = "en_US-libritts_r-medium.onnx"
        config_path = "en_US-libritts_r-medium.onnx.json"
        
        if not os.path.exists(model_path):
            print(f"❌ Model file not found: {model_path}")
            return
        
        # Load voice
        print(f"📥 Loading model: {model_path}")
        voice = PiperVoice.load(model_path, use_cuda=False)
        print("✅ Model loaded successfully")
        
        test_text = "This is a direct test of Piper TTS with different speeds."
        
        # Test different length_scale values
        test_values = [0.4, 1.0, 1.5, 3.0]
        
        for length_scale in test_values:
            print(f"\n🎵 Testing length_scale = {length_scale}")
            
            try:
                # Create temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                    temp_path = tmp_file.name
                
                # Test with SynthesisConfig
                with wave.open(temp_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(voice.config.sample_rate)
                    
                    # Try different API methods
                    try:
                        # Method 1: Direct parameters
                        voice.synthesize(
                            test_text,
                            wf,
                            length_scale=length_scale,
                            noise_scale=1.0,
                            noise_w=0.5
                        )
                        method = "Direct parameters"
                    except Exception as e1:
                        try:
                            # Method 2: SynthesisConfig
                            cfg = SynthesisConfig(
                                length_scale=length_scale,
                                noise_scale=1.0,
                                noise_w=0.5
                            )
                            voice.synthesize(test_text, wf, syn_config=cfg)
                            method = "SynthesisConfig"
                        except Exception as e2:
                            try:
                                # Method 3: synthesize_wav
                                voice.synthesize_wav(test_text, wf, syn_config=cfg)
                                method = "synthesize_wav"
                            except Exception as e3:
                                print(f"   ❌ All methods failed: {e1}, {e2}, {e3}")
                                continue
                
                # Check result
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    with wave.open(temp_path, 'rb') as wf:
                        duration = wf.getnframes() / wf.getframerate()
                    
                    # Save with descriptive name
                    output_file = f"direct_test_length_scale_{length_scale}.wav"
                    os.rename(temp_path, output_file)
                    
                    print(f"   ✅ Success with {method}: {duration:.2f}s duration")
                    print(f"   📁 Saved: {output_file}")
                else:
                    print(f"   ❌ Failed: No audio generated")
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                        
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("🎯 Direct testing complete!")
        
    except Exception as e:
        print(f"❌ Error in direct test: {e}")
        import traceback
        traceback.print_exc()

def check_piper_version():
    """Check Piper TTS version and API"""
    
    print("\n🔍 Checking Piper TTS version and API...")
    print("=" * 60)
    
    try:
        import piper
        print(f"✅ Piper version: {piper.__version__}")
        
        from piper.voice import PiperVoice, SynthesisConfig
        import inspect
        
        # Check PiperVoice.synthesize signature
        sig = inspect.signature(PiperVoice.synthesize)
        print(f"✅ PiperVoice.synthesize signature: {sig}")
        
        # Check SynthesisConfig
        sig_config = inspect.signature(SynthesisConfig.__init__)
        print(f"✅ SynthesisConfig signature: {sig_config}")
        
        # Check available methods
        methods = [method for method in dir(PiperVoice) if not method.startswith('_')]
        print(f"✅ Available PiperVoice methods: {methods}")
        
    except Exception as e:
        print(f"❌ Error checking Piper version: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting length_scale debugging...")
    
    # Check Piper version first
    check_piper_version()
    
    # Test with TTS factory
    test_length_scale_values()
    
    # Test Piper directly
    test_piper_direct()
    
    print("\n🎉 Debugging complete!")

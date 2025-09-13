#!/usr/bin/env python3
"""
Test gTTS performance vs XTTS
"""

import time
import os
import sys
from gtts import gTTS
from pydub import AudioSegment
import io

def test_gtts_performance(text, iterations=3):
    """Test gTTS performance"""
    print(f"🧪 Testing gTTS Performance")
    print(f"📝 Text: '{text[:50]}...'")
    print(f"📊 Iterations: {iterations}")
    print("-" * 60)
    
    times = []
    
    for i in range(iterations):
        print(f"🔄 Iteration {i+1}/{iterations}")
        start_time = time.time()
        
        try:
            # Create gTTS object
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Generate audio to memory
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            # Convert to WAV
            audio = AudioSegment.from_mp3(audio_buffer)
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_data = wav_buffer.getvalue()
            
            end_time = time.time()
            duration = end_time - start_time
            times.append(duration)
            
            print(f"✅ Success: {duration:.2f}s, Audio size: {len(wav_data)} bytes")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print("-" * 60)
        print(f"📈 gTTS Performance Results:")
        print(f"   Average: {avg_time:.2f}s")
        print(f"   Min: {min_time:.2f}s")
        print(f"   Max: {max_time:.2f}s")
        print(f"   Success rate: {len(times)}/{iterations}")
        
        return avg_time
    else:
        print("❌ No successful iterations")
        return None

def test_xtts_performance(text, iterations=3):
    """Test XTTS performance"""
    print(f"\n🧪 Testing XTTS Performance")
    print(f"📝 Text: '{text[:50]}...'")
    print(f"📊 Iterations: {iterations}")
    print("-" * 60)
    
    try:
        # Import XTTS manager
        from xtts_manager import xtts_manager
        
        # Load model if not loaded
        if not xtts_manager.is_loaded:
            print("🔄 Loading XTTS model...")
            xtts_manager.load_model()
        
        times = []
        
        for i in range(iterations):
            print(f"🔄 Iteration {i+1}/{iterations}")
            start_time = time.time()
            
            try:
                # Synthesize with XTTS
                audio_data = xtts_manager.synthesize_text(
                    text=text,
                    language='en',
                    speaker_wav='00005.wav',
                    speed=2.0
                )
                
                end_time = time.time()
                duration = end_time - start_time
                times.append(duration)
                
                print(f"✅ Success: {duration:.2f}s, Audio size: {len(audio_data)} bytes")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print("-" * 60)
            print(f"📈 XTTS Performance Results:")
            print(f"   Average: {avg_time:.2f}s")
            print(f"   Min: {min_time:.2f}s")
            print(f"   Max: {max_time:.2f}s")
            print(f"   Success rate: {len(times)}/{iterations}")
            
            return avg_time
        else:
            print("❌ No successful iterations")
            return None
            
    except Exception as e:
        print(f"❌ XTTS test failed: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 TTS Performance Comparison Test")
    print("=" * 60)
    
    # Test texts of different lengths
    test_texts = [
        "Hello there! How can I help you today, friend?",  # 50 chars
        "My name is SHCI.",  # 17 chars
        "This is a longer text to test performance with more characters and see how both systems handle it.",  # 100+ chars
    ]
    
    results = {}
    
    for text in test_texts:
        print(f"\n📝 Testing text: '{text}'")
        print(f"📏 Length: {len(text)} characters")
        print("=" * 60)
        
        # Test gTTS
        gtts_time = test_gtts_performance(text, iterations=2)
        
        # Test XTTS
        xtts_time = test_xtts_performance(text, iterations=2)
        
        # Store results
        results[len(text)] = {
            'text': text,
            'gtts_time': gtts_time,
            'xtts_time': xtts_time
        }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    for length, result in results.items():
        print(f"\n📝 Text Length: {length} chars")
        print(f"   Text: '{result['text'][:30]}...'")
        
        if result['gtts_time'] and result['xtts_time']:
            speedup = result['xtts_time'] / result['gtts_time']
            print(f"   gTTS: {result['gtts_time']:.2f}s")
            print(f"   XTTS: {result['xtts_time']:.2f}s")
            print(f"   Speedup: {speedup:.2f}x {'(gTTS faster)' if speedup > 1 else '(XTTS faster)'}")
        else:
            gtts_status = 'Failed' if not result['gtts_time'] else f"{result['gtts_time']:.2f}s"
            xtts_status = 'Failed' if not result['xtts_time'] else f"{result['xtts_time']:.2f}s"
            print(f"   gTTS: {gtts_status}")
            print(f"   XTTS: {xtts_status}")

if __name__ == "__main__":
    main()

import wave
from piper import PiperVoice, SynthesisConfig  # SynthesisConfig আবার ইম্পোর্ট করতে হবে

MODEL_PATH = "en_US-libritts_r-medium.onnx"
OUT_WAV    = "test.wav"
TEXT       = "Welcome to the world of speech synthesis!"

# Force CPU
voice = PiperVoice.load(MODEL_PATH, use_cuda=False)

# 1. ডকুমেন্টেশন অনুযায়ী SynthesisConfig অবজেক্ট তৈরি করুন
syn_config = SynthesisConfig(
    length_scale=4.40,    # Slower speech
    noise_scale=1.0,     # More variation
    noise_w_scale=1.0,   # More speaking variation
)

# 2. synthesize_wav ব্যবহার করে syn_config পাস করুন
with wave.open(OUT_WAV, "wb") as wav_file:
    voice.synthesize_wav(TEXT, wav_file, syn_config=syn_config)

print(f"✅ Done! Saved: {OUT_WAV}")

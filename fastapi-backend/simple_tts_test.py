#!/usr/bin/env python3
"""
A script to convert text to speech using a reference audio file for voice cloning.
It falls back to a default speaker if the reference file is not found.
"""

import os
import torch
from TTS.api import TTS
import warnings
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig
from TTS.config.shared_configs import BaseDatasetConfig
from TTS.tts.models.xtts import XttsArgs  # <-- Add this import

# --- PyTorch 2.6+ FIX ---
# The xtts_v2 model file contains multiple configuration objects
# which PyTorch's new security protocol blocks by default.
# We need to explicitly allowlist all of them.
torch.serialization.add_safe_globals([
    XttsConfig,
    XttsAudioConfig,
    BaseDatasetConfig,
    XttsArgs  # <-- Add this class to the safe globals
])

# --- Configuration ---
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
OUTPUT_DIR = "outputs"
OUTPUT_FILENAME = "output_cloned_voice.wav"

# --- আপনার দেওয়া রেফারেন্স অডিও ফাইলের পাথ ---
REFERENCE_VOICE_PATH = "00005.wav"
# REFERENCE_VOICE_PATH = "00005.wav"

# রেফারেন্স ফাইল খুঁজে না পেলে এই ডিফল্ট ভয়েসটি ব্যবহার করা হবে
FALLBACK_SPEAKER = "Tammie Ema"

TEXT_TO_SYNTHESIZE = """Little Light
A tiny star begins to glow,
Softly shining, calm and slow.
Though it seems so small and bright,
It warms the dark and paints the night."""

def main():
    """
    Initializes the TTS model and converts text into a high-quality audio file,
    using voice cloning if a reference audio is provided.
    """
    # Suppress unnecessary warnings from libraries
    warnings.filterwarnings("ignore", category=UserWarning)

    # 1. Initialize the TTS Model
    print("🚀 Initializing TTS model...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    try:
        # Alternative approach: Use context manager for safer loading
        with torch.serialization.safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs]):
            tts_model = TTS(MODEL_NAME).to(device)
        print("✅ TTS model initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize TTS model: {e}")
        # Try one more approach with weights_only=False as fallback
        try:
            print("Trying alternative loading method...")
            tts_model = TTS(MODEL_NAME, weights_only=False).to(device)
            print("✅ TTS model initialized successfully with weights_only=False.")
        except Exception as e2:
            print(f"❌ All initialization attempts failed: {e2}")
            return

    # 2. Check for Reference Voice and Synthesize Audio
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    speaker_wav_param = None
    speaker_param = None

    # Check if the reference audio file exists at the specified path
    if os.path.exists(REFERENCE_VOICE_PATH):
        print(f"🎙️  Reference file found at '{REFERENCE_VOICE_PATH}'. Using it for voice output.")
        speaker_wav_param = REFERENCE_VOICE_PATH
    else:
        print(f"⚠️  Warning: Reference file not found at '{REFERENCE_VOICE_PATH}'.")
        print(f"--> Using fallback default speaker: '{FALLBACK_SPEAKER}'")
        speaker_param = FALLBACK_SPEAKER

    print(f"\nSynthesizing audio for: '{TEXT_TO_SYNTHESIZE}'")

    try:
        # Use the appropriate parameter based on whether the reference file was found
        tts_model.tts_to_file(
            text=TEXT_TO_SYNTHESIZE,
            file_path=output_path,
            speaker_wav=speaker_wav_param,
            speaker=speaker_param,
            language="en",
        )
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"\n🎉 Success! Audio saved to: {output_path}")
        else:
            print("❌ Audio generation failed. The output file was not created.")

    except Exception as e:
        print(f"❌ An error occurred during audio generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

import queue
import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

# -------- Config --------
MODEL_SIZE   = "base"      # tiny/base/small/medium ; base == faster on Apple CPU
DEVICE       = "cpu"       # Apple Silicon -> "cpu" (faster-whisper has no MPS)
COMPUTE_TYPE = "int8"      # Apple CPU best; fallback to float32 below if needed
SAMPLE_RATE  = 16000
FRAME_MS     = 250         # 250ms chunk
PROCESS_SEC  = 0.8         # every ~0.8s run STT (reduce CPU load)
LANG         = "bn"        # "bn" for Bengali; try "en" or None (auto) if you want
VAD_MIN_RMS  = 0.004       # simple silence gate
PRINT_DBG    = True
# ------------------------

def make_model():
    for ct in (COMPUTE_TYPE, "float32"):
        try:
            print(f"[model] loading: {MODEL_SIZE}, compute_type={ct}")
            m = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=ct)
            print(f"[model] ready with compute_type={ct}")
            return m
        except Exception as e:
            print(f"[model] failed compute_type={ct}: {e}")
    raise RuntimeError("Could not load WhisperModel")

def list_inputs():
    print("\n[devices] Available input devices:")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            print(f"  #{i}: {d['name']}  (default_samplerate={int(d['default_samplerate'])})")
    print(f"[devices] Current default input index: {sd.default.device[0]}\n")

def rms(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(x), dtype=np.float64)))

def audio_callback(indata, frames, time_info, status):
    if status:
        print("⚠️", status)
    f32 = (indata[:, 0].astype(np.float32) / 32768.0).copy()  # int16 -> float32 mono
    q.put(f32)

def stt_worker(model: WhisperModel):
    buf = np.zeros(0, dtype=np.float32)
    last_process = 0.0
    window_secs = 8.0
    last_printed = ""   # simple de-dupe

    while running[0]:
        try:
            chunk = q.get(timeout=0.15)
            buf = np.concatenate([buf, chunk])
            # rolling window
            max_len = int((window_secs + 1.0) * SAMPLE_RATE)
            if buf.size > max_len:
                buf = buf[-max_len:]
        except queue.Empty:
            pass

        now = time.time()
        if now - last_process < PROCESS_SEC:
            continue
        last_process = now

        if buf.size < int(0.5 * SAMPLE_RATE):  # need at least ~0.5s
            continue

        if rms(buf[-int(1.0 * SAMPLE_RATE):]) < VAD_MIN_RMS:
            if PRINT_DBG:
                print(f"[audio] silent (rms<{VAD_MIN_RMS:.3f})")
            continue

        if PRINT_DBG:
            print(f"[audio] len={buf.size/SAMPLE_RATE:.2f}s, rms={rms(buf):.3f}")

        # IMPORTANT: turn off vad_filter for debugging; force language to bn
        try:
            segments, info = model.transcribe(
                buf,
                beam_size=1,
                temperature=0.0,
                vad_filter=False,                 # <-- off to verify output
                condition_on_previous_text=False,
                language=LANG,                    # <-- force language
                word_timestamps=False,
            )
            text = " ".join(s.text.strip() for s in segments if s.text.strip()).strip()
            if text and text != last_printed:
                print("👉", text)
                last_printed = text
        except Exception as e:
            print("[stt] error:", e)

if __name__ == "__main__":
    try:
        list_inputs()
    except Exception as e:
        print("❌ mic list error:", e)
        print("➡️ System Settings → Privacy & Security → Microphone → your Terminal app → Allow, then restart.")
        raise

    model = make_model()

    blocksize = int(SAMPLE_RATE * (FRAME_MS / 1000.0))

    q: "queue.Queue[np.ndarray]" = queue.Queue()
    running = [True]
    th = threading.Thread(target=stt_worker, args=(model,), daemon=True)
    th.start()

    print("🎤 বলুন (Ctrl+C চাপলে বন্ধ হবে)…")
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=blocksize,
            callback=audio_callback,
        ):
            while True:
                time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n🛑 বন্ধ করা হল।")
    finally:
        running[0] = False
        th.join(timeout=1.0)

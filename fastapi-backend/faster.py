import time
import queue
import threading
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

# -------- Settings (সহজে বদলাতে পারবেন) --------
MODEL_SIZE   = "base"     # tiny / base / small / medium
LANGUAGE     = None       # None = auto, বা "bn" / "en" দিন
SAMPLE_RATE  = 16000      # faster-whisper 16kHz ভালো কাজ করে
FRAME_MS     = 250        # প্রতি 250ms করে মাইক থেকে ফ্রেম নেব
PROCESS_EVERY_SEC = 0.8   # কতক্ষণ পরপর ট্রান্সক্রাইব চালাব
ROLLING_WINDOW_SEC = 8.0  # শেষ ৮ সেকেন্ড অডিওতে রান করব
# -------------------------------------------------

def load_model():
    """
    CUDA থাকলে FP16, না হলে CPU int8/float32-এ fallback.
    """
    try:
        import torch
        if torch.cuda.is_available():
            print("[model] CUDA detected → FP16")
            return WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
    except Exception:
        pass

    # CPU path
    for ct in ("int8", "float32"):
        try:
            print(f"[model] CPU → compute_type={ct}")
            return WhisperModel(MODEL_SIZE, device="cpu", compute_type=ct)
        except Exception as e:
            print(f"[model] {ct} failed: {e}")
    # last resort
    return WhisperModel(MODEL_SIZE, device="cpu")

def list_inputs():
    print("\n[devices] input devices:")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            print(f"  #{i}: {d['name']}  (default_sr={int(d['default_samplerate'])})")
    print(f"[devices] default input index: {sd.default.device[0]}\n")

def audio_callback(indata, frames, time_info, status):
    if status:
        print("⚠️", status)
    # int16 → float32 [-1,1]
    f32 = (indata[:, 0].astype(np.float32) / 32768.0).copy()
    q.put(f32)

def stt_loop(model: WhisperModel):
    """
    কিউ থেকে অডিও নিয়ে নির্দিষ্ট ইন্টারভ্যালে ট্রান্সক্রাইব করে প্রিন্ট করবে।
    """
    buf = np.zeros(0, dtype=np.float32)
    last_process = 0.0
    last_print = ""

    while running[0]:
        # কিউ থেকে নতুন ফ্রেম জোড়া লাগাই
        try:
            chunk = q.get(timeout=0.1)
            buf = np.concatenate([buf, chunk])
            # রোলিং উইন্ডো রেখে দিই
            max_len = int((ROLLING_WINDOW_SEC + 1.0) * SAMPLE_RATE)
            if buf.size > max_len:
                buf = buf[-max_len:]
        except queue.Empty:
            pass

        now = time.time()
        if now - last_process < PROCESS_EVERY_SEC:
            continue
        last_process = now

        if buf.size < int(0.5 * SAMPLE_RATE):
            continue  # অতি ছোট হলে স্কিপ

        # খুব দ্রুত সেটিংস: beam_size=1, temperature=0.0
        segments, info = model.transcribe(
            buf,
            beam_size=1,
            temperature=0.0,
            vad_filter=False,                 # চাইলে True করতে পারেন
            condition_on_previous_text=False,
            language=LANGUAGE,                # None=auto, বা "bn"/"en"
            word_timestamps=False,
        )

        text = " ".join(s.text.strip() for s in segments if s.text.strip()).strip()
        if text and text != last_print:
            print("👉", text)
            last_print = text

if __name__ == "__main__":
    # মাইক ডিভাইস লিস্ট দেখাই (পারমিশন ইস্যু হলে এখানেই ধরা পড়বে)
    try:
        list_inputs()
    except Exception as e:
        print("❌ মাইক লিস্ট করা যায়নি:", e)
        print("➡️ macOS: System Settings → Privacy & Security → Microphone → আপনার Terminal/iTerm/VSCode-কে Allow করে দিন, তারপর টার্মিনাল রিস্টার্ট করুন।")
        raise

    # মডেল লোড
    model = load_model()

    # কিউ + থ্রেড
    q: "queue.Queue[np.ndarray]" = queue.Queue()
    running = [True]
    worker = threading.Thread(target=stt_loop, args=(model,), daemon=True)
    worker.start()

    # ইনপুট স্ট্রিম খুলে দিই
    blocksize = int(SAMPLE_RATE * (FRAME_MS / 1000.0))
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
        worker.join(timeout=1.0)

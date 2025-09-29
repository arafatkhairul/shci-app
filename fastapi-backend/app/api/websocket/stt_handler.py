"""
Real-time Speech-to-Text WebSocket Handler using RealtimeSTT
Patched for Apple Silicon (M2) with safe compute_type/device fallbacks,
and proper readiness gating + bounded buffering.
"""
import os
import json
import platform
import asyncio
import threading
from collections import deque
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from RealtimeSTT import AudioToTextRecorder

from app.utils.logger import get_logger, log_exception
log = get_logger("stt_handler")

# ---------------- Platform helpers ----------------
def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine().lower() in ("arm64", "aarch64")

def _pick_fallback_chain():
    env_device = os.getenv("RT_DEVICE")
    env_compute = os.getenv("RT_COMPUTE")
    if env_device and env_compute:
        return [(env_device, env_compute)]
    if _is_apple_silicon():
        return [("metal", "int8"), ("metal", "float32"), ("cpu", "int8"), ("cpu", "float32")]
    else:
        return [("cuda", "float16"), ("cuda", "float32"), ("cpu", "int8"), ("cpu", "float32")]

def _build_recorder_with_fallbacks(callbacks: dict, language: str = "en") -> AudioToTextRecorder:
    # Disable RealtimeSTT internal logging
    import logging
    logging.getLogger('RealtimeSTT').setLevel(logging.CRITICAL)
    logging.getLogger('RealtimeSTT.safepipe').setLevel(logging.CRITICAL)
    logging.getLogger('faster_whisper').setLevel(logging.WARNING)
    
    errors = []
    for device, compute in _pick_fallback_chain():
        try:
            log.info(f"[RealtimeSTT] Trying device={device} compute_type={compute}")
            rec = AudioToTextRecorder(
                use_microphone=False,
                device=device,
                compute_type=compute,
                gpu_device_index=int(os.getenv("RT_GPU_INDEX", "0")),
                # ---- Models / language ----
                model=os.getenv("RT_MODEL", "base.en" if language == "en" else "base"),   # Use base.en for English, base for Italian
                language=language,     # Use the selected language
                # ---- Realtime partials ----
                enable_realtime_transcription=True,
                use_main_model_for_realtime=True,  # Use main model for better quality
                realtime_model_type=os.getenv("RT_REALTIME_MODEL", "base.en" if language == "en" else "base"),
                realtime_processing_pause=float(os.getenv("RT_REALTIME_PAUSE", "0.05")),  # Faster processing
                on_realtime_transcription_update=callbacks["on_partial"],
                on_realtime_transcription_stabilized=callbacks["on_stabilized"],
                # ---- VAD / endpointing ----
                webrtc_sensitivity=int(os.getenv("RT_VAD_SENS", "2")),  # More sensitive for faster detection
                silero_deactivity_detection=bool(int(os.getenv("RT_SILERO_DEACT", "1"))),
                pre_recording_buffer_duration=float(os.getenv("RT_PRE_ROLL", "0.05")),  # Reduced for faster start
                post_speech_silence_duration=float(os.getenv("RT_POST_SILENCE", "0.3")),  # Reduced for faster finalization
                min_length_of_recording=float(os.getenv("RT_MIN_UTT", "0.2")),  # Reduced minimum utterance
                # ---- Text polish ----
                ensure_sentence_starting_uppercase=True,
                ensure_sentence_ends_with_period=True,
                spinner=bool(int(os.getenv("RT_SPINNER", "0"))),
                level=int(os.getenv("RT_LOG_LEVEL", "50")),  # CRITICAL level logging only
                no_log_file=bool(int(os.getenv("RT_NO_LOG_FILE", "1"))),
            )
            log.info(f"[RealtimeSTT] Using device={device}, compute_type={compute}")
            return rec
        except Exception as e:
            msg = f"{device}/{compute} failed: {e}"
            errors.append(msg)
            log.warning(msg)
    raise RuntimeError("RealtimeSTT backend init failed. Attempts: " + " | ".join(errors))

# ---------------- Session ----------------
class RTSession:
    """Real-time STT session handler"""

    # hard cap on pre-init buffered chunks (protect memory & latency)
    BUFFER_MAX = int(os.getenv("RT_BUFFER_MAX", "400"))  # ~8s if 20ms frames

    def __init__(self, ws: WebSocket, loop: asyncio.AbstractEventLoop, stt_handler: 'STTHandler' = None, language: str = "en"):
        self.ws = ws
        self.loop = loop
        self.running = True
        self.rec: Optional[AudioToTextRecorder] = None
        self.stt_handler = stt_handler
        self.language = language

        # readiness gate
        self._ready_event: asyncio.Event = asyncio.Event()

        # bounded buffer for early audio
        self.audio_buffer: deque[bytes] = deque(maxlen=self.BUFFER_MAX)

        # async init (non-blocking to WS accept)
        self.init_task = asyncio.create_task(self._async_init())

        # final thread handle
        self.final_thread: Optional[threading.Thread] = None

    async def _async_init(self):
        try:
            self._send_json({"type": "status", "text": "initializing"})
            
            # Check if we have a pre-validated config
            if self.stt_handler and self.stt_handler.is_pre_initialized():
                log.info("[RTSession] Using pre-validated RealtimeSTT config - FAST INITIALIZATION!")
                # Use the pre-validated config for faster initialization
                def init_recorder():
                    return _build_recorder_with_fallbacks({
                        "on_partial": self._cb_partial,
                        "on_stabilized": self._cb_stabilized
                    }, self.language)
                self.rec = await asyncio.get_running_loop().run_in_executor(None, init_recorder)
            else:
                log.info("[RTSession] Creating new RealtimeSTT recorder with fallback")
                # Fallback to normal initialization
                def init_recorder():
                    return _build_recorder_with_fallbacks({
                        "on_partial": self._cb_partial,
                        "on_stabilized": self._cb_stabilized
                    }, self.language)
                self.rec = await asyncio.get_running_loop().run_in_executor(None, init_recorder)

            # start finalization thread
            self.final_thread = threading.Thread(target=self._final_loop, daemon=True)
            self.final_thread.start()

            # drain buffered audio (preserve order)
            if self.audio_buffer:
                log.info(f"[RTSession] Draining {len(self.audio_buffer)} buffered chunks")
                while self.audio_buffer:
                    self.rec.feed_audio(self.audio_buffer.popleft())

            self._ready_event.set()
            self._send_json({"type": "status", "text": "ready"})
            log.info("[RTSession] RealtimeSTT ready")
        except Exception as e:
            log.error(f"RealtimeSTT initialization failed: {e}")
            self._send_json({"type": "error", "text": f"initialization_failed: {e}"})
            self.running = False

    async def wait_ready(self, timeout: float = 5.0) -> bool:
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    # ---------- WS send helpers ----------
    def _send_json(self, obj: dict):
        try:
            asyncio.run_coroutine_threadsafe(self.ws.send_text(json.dumps(obj)), self.loop)
        except Exception as e:
            log.error(f"Failed to send JSON message: {e}")

    # ---------- Realtime callbacks ----------
    def _cb_partial(self, text: str):
        if text and text.strip():
            log.debug(f"[RTSession] Partial: {text}")
            self._send_json({"type": "partial", "text": text.strip()})

    def _cb_stabilized(self, text: str):
        if text and text.strip():
            log.debug(f"[RTSession] Stabilized: {text}")
            self._send_json({"type": "stabilized", "text": text.strip()})

    # ---------- Finalization loop ----------
    def _final_loop(self):
        while self.running and self.rec:
            try:
                def on_final(sentence: str):
                    s = (sentence or "").strip()
                    if s:
                        log.debug(f"[RTSession] Final Text: {s}")
                        self._send_json({"type": "final", "text": s})
                self.rec.text(on_final)  # blocks until next final sentence
            except Exception as e:
                if self.running:
                    log.error(f"Final transcription loop error: {e}")
                    self._send_json({"type": "error", "text": f"final_loop: {e}"})
                break

    # ---------- Audio feeding ----------
    def feed_pcm16(self, chunk: bytes):
        # If not ready yet, enqueue (bounded) instead of spamming logs
        if not self._ready_event.is_set() or not self.rec:
            if len(self.audio_buffer) == self.audio_buffer.maxlen:
                # drop oldest (deque already drops), but we log once in a while
                if (getattr(self, "_drop_logged", 0) % 50) == 0:
                    log.warning("[RTSession] Buffer full, dropping oldest chunks to protect latency")
                self._drop_logged = getattr(self, "_drop_logged", 0) + 1
            self.audio_buffer.append(chunk)
            return
        try:
            self.rec.feed_audio(chunk)
        except Exception as e:
            log.error(f"Failed to feed audio data: {e}")
            self._send_json({"type": "error", "text": f"audio_feed: {e}"})

    # ---------- Cleanup ----------
    def stop(self):
        self.running = False
        # cancel init if still pending
        if self.init_task and not self.init_task.done():
            self.init_task.cancel()
        self.audio_buffer.clear()
        if self.rec:
            try:
                if hasattr(self.rec, "abort"):
                    self.rec.abort()
            except Exception as e:
                log.warning(f"Error aborting recorder: {e}")
            try:
                if hasattr(self.rec, "shutdown"):
                    self.rec.shutdown()
            except Exception as e:
                log.warning(f"Error shutting down recorder: {e}")
        if self.final_thread and self.final_thread.is_alive():
            self.final_thread.join(timeout=2.0)

# ---------------- Handler ----------------
class STTHandler:
    """Handles WebSocket STT connections"""

    def __init__(self):
        self._pre_initialized = False
        self._initialization_lock = asyncio.Lock()
        self._is_initializing = False
        self._working_config = None  # Store the working device/compute config

    async def pre_initialize(self):
        """Pre-validate RealtimeSTT configuration on application startup"""
        if self._pre_initialized:
            return True
            
        async with self._initialization_lock:
            if self._is_initializing:
                return False
            if self._pre_initialized:
                return True
                
            self._is_initializing = True
            try:
                log.info("[STTHandler] Pre-validating RealtimeSTT configuration...")
                
                # Test initialization to find working device/compute combination
                def test_init():
                    return _build_recorder_with_fallbacks({
                        "on_partial": lambda text: None,  # Dummy callbacks for testing
                        "on_stabilized": lambda text: None
                    })
                
                # Test initialize in executor to avoid blocking
                loop = asyncio.get_running_loop()
                test_recorder = await loop.run_in_executor(None, test_init)
                
                # Store the working configuration
                self._working_config = {
                    "device": getattr(test_recorder, 'device', None),
                    "compute_type": getattr(test_recorder, 'compute_type', None),
                }
                
                # Clean up test recorder
                try:
                    if hasattr(test_recorder, "abort"):
                        test_recorder.abort()
                    if hasattr(test_recorder, "shutdown"):
                        test_recorder.shutdown()
                except:
                    pass
                
                self._pre_initialized = True
                log.info(f"[STTHandler] RealtimeSTT configuration pre-validated: {self._working_config}")
                return True
            except Exception as e:
                log.error(f"[STTHandler] Failed to pre-validate RealtimeSTT config: {e}")
                return False
            finally:
                self._is_initializing = False

    def get_working_config(self):
        """Get the pre-validated working config if available"""
        return self._working_config

    def is_pre_initialized(self):
        """Check if configuration has been pre-validated"""
        return self._pre_initialized

    def clear_pre_initialized_config(self):
        """Clear the pre-validated config"""
        self._working_config = None
        self._pre_initialized = False

    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept()
        conn_id = f"stt_{id(websocket)}"
        log.info(f"STT WebSocket connected: {conn_id}")

        # Default language
        language = "en"
        
        # Wait for language parameter from client
        try:
            # Wait for initial message with language
            msg = await websocket.receive()
            if "text" in msg:
                data = json.loads(msg["text"])
                if "language" in data:
                    language = data["language"]
                    log.info(f"STT Language set to: {language}")
        except Exception as e:
            log.warning(f"Failed to get language parameter: {e}, using default: {language}")

        loop = asyncio.get_running_loop()
        sess = RTSession(websocket, loop, self, language)

        try:
            # Tell client to wait for 'ready' before streaming (best practice)
            await websocket.send_text(json.dumps({"type": "status", "text": "initializing"}))

            while True:
                msg = await websocket.receive()

                if "bytes" in msg:
                    # Gate on readiness to avoid endless buffering
                    if not sess._ready_event.is_set():
                        # Optional: wait briefly for init to finish (up to 2s)
                        ready = await sess.wait_ready(timeout=2.0)
                        # If still not ready, buffer (bounded) and continue
                    sess.feed_pcm16(msg["bytes"])

                elif "text" in msg:
                    try:
                        data = json.loads(msg["text"])
                        if data.get("type") == "close":
                            break
                        elif data.get("type") == "ping":
                            await websocket.send_text(json.dumps({"type": "pong", "text": "pong"}))
                    except json.JSONDecodeError:
                        log.warning(f"Invalid JSON received: {msg['text']}")
                else:
                    pass

        except WebSocketDisconnect:
            log.info(f"STT WebSocket disconnected: {conn_id}")
        except Exception as e:
            log_exception(f"STT WebSocket error: {e}")
            try:
                await websocket.send_text(json.dumps({"type": "error", "text": str(e)}))
            except Exception:
                pass
        finally:
            sess.stop()
            log.info(f"STT session cleaned up: {conn_id}")

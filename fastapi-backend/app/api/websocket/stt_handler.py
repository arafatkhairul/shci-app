"""
Real-time Speech-to-Text WebSocket Handler using RealtimeSTT
Patched for Apple Silicon (M2) with safe compute_type/device fallbacks.
"""
import os
import json
import platform
import asyncio
import threading
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from RealtimeSTT import AudioToTextRecorder

from app.utils.logger import get_logger, log_exception
log = get_logger("stt_handler")


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine().lower() in ("arm64", "aarch64")


def _pick_fallback_chain():
    """
    Returns a list of (device, compute_type) tuples to try in order.
    - On Apple Silicon: prefer Metal int8 → Metal float32 → CPU int8 → CPU float32
    - Elsewhere: respect ENV if provided; otherwise CUDA float16 → CUDA float32 → CPU int8 → CPU float32
    """
    env_device = os.getenv("RT_DEVICE")
    env_compute = os.getenv("RT_COMPUTE")

    if env_device and env_compute:
        return [(env_device, env_compute)]

    if _is_apple_silicon():
        return [("metal", "int8"), ("metal", "float32"), ("cpu", "int8"), ("cpu", "float32")]
    else:
        # If you're on a 5090 server, CUDA float16 is ideal.
        return [("cuda", "float16"), ("cuda", "float32"), ("cpu", "int8"), ("cpu", "float32")]


def _build_recorder_with_fallbacks(callbacks: dict) -> AudioToTextRecorder:
    """
    Try a small matrix of device/compute combinations until one works.
    Logs the chosen backend so you can verify.
    """
    errors = []
    for device, compute in _pick_fallback_chain():
        try:
            log.info(f"[RealtimeSTT] Trying device={device} compute_type={compute}")
            rec = AudioToTextRecorder(
                use_microphone=False,
                device=device,
                compute_type=compute,
                # GPU index is ignored on metal/cpu; safe to leave
                gpu_device_index=int(os.getenv("RT_GPU_INDEX", "0")),
                # ---- Model choices ----
                # 'medium' balances speed/accuracy on M2; you can switch to 'large-v3' on the 5090 box.
                model=os.getenv("RT_MODEL", "medium"),
                language=os.getenv("RT_LANG", ""),  # "" = auto-detect; or set "bn"/"en"
                # ---- Realtime partials ----
                enable_realtime_transcription=True,
                use_main_model_for_realtime=False,
                realtime_model_type=os.getenv("RT_REALTIME_MODEL", "small"),
                realtime_processing_pause=float(os.getenv("RT_REALTIME_PAUSE", "0.5")),
                on_realtime_transcription_update=callbacks["on_partial"],
                on_realtime_transcription_stabilized=callbacks["on_stabilized"],
                # ---- VAD & endpointing ----
                webrtc_sensitivity=int(os.getenv("RT_VAD_SENS", "2")),
                silero_deactivity_detection=bool(int(os.getenv("RT_SILERO_DEACT", "1"))),
                post_speech_silence_duration=float(os.getenv("RT_POST_SILENCE", "0.25")),
                pre_recording_buffer_duration=float(os.getenv("RT_PRE_ROLL", "0.2")),
                min_length_of_recording=float(os.getenv("RT_MIN_UTT", "0.8")),
                # ---- Text polishing ----
                ensure_sentence_starting_uppercase=True,
                ensure_sentence_ends_with_period=True,
                spinner=False,
                no_log_file=True,
            )
            log.info(f"[RealtimeSTT] Using device={device}, compute_type={compute}")
            return rec
        except Exception as e:
            msg = f"{device}/{compute} failed: {e}"
            errors.append(msg)
            log.warning(msg)

    # If none worked, raise a compact error with the attempts we tried
    raise RuntimeError("RealtimeSTT backend init failed. Attempts: " + " | ".join(errors))


class RTSession:
    """Real-time STT session handler"""

    def __init__(self, ws: WebSocket, loop: asyncio.AbstractEventLoop):
        self.ws = ws
        self.loop = loop
        self.running = True
        self.rec = None
        self.initialized = False
        self.final_thread = None

        # Initialize RealtimeSTT asynchronously to avoid blocking WebSocket handshake
        self.init_task = asyncio.create_task(self._async_init())

    async def _async_init(self):
        """Initialize RealtimeSTT asynchronously"""
        try:
            log.info("🔄 Initializing RealtimeSTT...")
            self._send_json({"type": "status", "text": "initializing"})
            
            # Run the heavy initialization in a thread pool
            def init_recorder():
                return _build_recorder_with_fallbacks({
                    "on_partial": self._cb_partial,
                    "on_stabilized": self._cb_stabilized
                })
            
            # Run in thread pool to avoid blocking
            self.rec = await asyncio.get_event_loop().run_in_executor(None, init_recorder)
            
            # Start final transcription thread
            self.final_thread = threading.Thread(target=self._final_loop, daemon=True)
            self.final_thread.start()
            
            self.initialized = True
            log.info("✅ RealtimeSTT initialized successfully")
            self._send_json({"type": "status", "text": "ready"})
            
            # Process any buffered audio data
            if hasattr(self, 'audio_buffer') and self.audio_buffer:
                log.info(f"Processing {len(self.audio_buffer)} buffered audio chunks after initialization")
                for buffered_chunk in self.audio_buffer:
                    try:
                        self.rec.feed_audio(buffered_chunk)
                    except Exception as e:
                        log.error(f"Failed to process buffered audio: {e}")
                self.audio_buffer.clear()
            
        except Exception as e:
            log.error(f"❌ RealtimeSTT initialization failed: {e}")
            self._send_json({"type": "error", "text": f"initialization_failed: {e}"})
            self.running = False

    # ---------- WS send helpers ----------
    def _send_json(self, obj: dict):
        try:
            asyncio.run_coroutine_threadsafe(self.ws.send_text(json.dumps(obj)), self.loop)
        except Exception as e:
            log.error(f"Failed to send JSON message: {e}")

    # ---------- Realtime callbacks ----------
    def _cb_partial(self, text: str):
        if text:
            self._send_json({"type": "partial", "text": text})

    def _cb_stabilized(self, text: str):
        if text:
            self._send_json({"type": "stabilized", "text": text})

    # ---------- Finalization loop ----------
    def _final_loop(self):
        while self.running:
            try:
                def on_final(sentence: str):
                    if sentence:
                        self._send_json({"type": "final", "text": sentence})
                # Blocks until a full sentence is available
                self.rec.text(on_final)
            except Exception as e:
                log.error(f"Final transcription loop error: {e}")
                self._send_json({"type": "error", "text": f"final_loop: {e}"})
                break

    # ---------- Audio feeding ----------
    def feed_pcm16(self, chunk: bytes):
        if not self.initialized or not self.rec:
            # Store audio data in buffer until initialization is complete
            if not hasattr(self, 'audio_buffer'):
                self.audio_buffer = []
            self.audio_buffer.append(chunk)
            log.debug("RealtimeSTT not initialized yet, buffering audio data")
            return
            
        try:
            # Process any buffered audio first
            if hasattr(self, 'audio_buffer') and self.audio_buffer:
                log.info(f"Processing {len(self.audio_buffer)} buffered audio chunks")
                for buffered_chunk in self.audio_buffer:
                    self.rec.feed_audio(buffered_chunk)
                self.audio_buffer.clear()
            
            # Process current audio chunk
            self.rec.feed_audio(chunk)
        except Exception as e:
            log.error(f"Failed to feed audio data: {e}")
            self._send_json({"type": "error", "text": f"audio_feed: {e}"})

    # ---------- Cleanup ----------
    def stop(self):
        self.running = False
        
        # Cancel initialization task if still running
        if hasattr(self, 'init_task') and not self.init_task.done():
            self.init_task.cancel()
        
        # Clear audio buffer
        if hasattr(self, 'audio_buffer'):
            self.audio_buffer.clear()
        
        # Shutdown recorder if initialized
        if self.rec:
            try:
                self.rec.abort()
            except Exception as e:
                log.warning(f"Error aborting recorder: {e}")
            try:
                self.rec.shutdown()
            except Exception as e:
                log.warning(f"Error shutting down recorder: {e}")


class STTHandler:
    """Handles WebSocket STT connections"""

    def __init__(self):
        pass

    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept()
        conn_id = f"stt_{id(websocket)}"
        log.info(f"STT WebSocket connected: {conn_id}")

        loop = asyncio.get_running_loop()
        sess = RTSession(websocket, loop)

        try:
            # Send immediate connection status
            await websocket.send_text(json.dumps({"type": "status", "text": "connected"}))

            while True:
                msg = await websocket.receive()

                if "bytes" in msg:
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
                    # Ignore other message types
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

"""
WebSocket Chat Handler
"""
import json
import uuid
import asyncio
import base64
import re
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from collections import deque

from app.config.settings import settings
from app.config.languages import LANGUAGES, DEFAULT_LANGUAGE
from app.utils.logger import get_logger, log_exception
from app.models.session_memory import SessionMemory, MemoryStore
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.services.database_service import DatabaseService

log = get_logger("chat_handler")

class ChatHandler:
    """Handles WebSocket chat connections and AI interactions"""
    
    def __init__(self, llm_service: LLMService, tts_service: TTSService, db_service: DatabaseService):
        self.llm_service = llm_service
        self.tts_service = tts_service
        self.db_service = db_service

    async def handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connection"""
        await websocket.accept()
        conn_id = uuid.uuid4().hex[:8]
        
        # Initialize session memory
        mem = SessionMemory(language=DEFAULT_LANGUAGE)
        server_tts_enabled = True
        mem_store: Optional[MemoryStore] = None
        
        try:
            # Send intro message
            intro_text = LANGUAGES[mem.language]["intro_line"]
            await self.send_json(websocket, {"type": "ai_text", "text": intro_text})
            mem.add_history("assistant", intro_text)
            mem.greeted = True
        except Exception as e:
            log_exception(log, f"[{conn_id}] intro_send", e)

        # Audio processing variables
        pre_buffer: deque = deque(maxlen=int(900 / settings.FRAME_MS))  # 900ms pre-roll
        triggered = False
        voiced_frames: deque = deque()
        voiced_count = 0
        silence_count = 0
        utter_frames = 0

        try:
            while True:
                msg = await websocket.receive()

                # Handle control messages (JSON text)
                if msg["type"] == "websocket.receive" and msg.get("text") is not None:
                    try:
                        data = json.loads(msg["text"])
                        typ = data.get("type")
                        
                        if typ == "final_transcript":
                            log.info(f"[{conn_id}] 🎤 FINAL_TRANSCRIPT MESSAGE RECEIVED: {data}")
                            await self.handle_final_transcript(websocket, data, mem, mem_store, conn_id)
                        elif typ == "client_prefs":
                            await self.handle_client_prefs(websocket, data, mem, mem_store, conn_id)
                            
                    except Exception as e:
                        log_exception(log, f"[{conn_id}] control_message", e)

                # Handle audio data
                elif msg["type"] == "websocket.receive" and msg.get("bytes") is not None:
                    await self.handle_audio_data(websocket, msg, mem, conn_id, 
                                               pre_buffer, triggered, voiced_frames, 
                                               voiced_count, silence_count, utter_frames)

        except WebSocketDisconnect:
            log.info(f"[{conn_id}] WebSocket disconnected")
        except Exception as e:
            log_exception(log, f"[{conn_id}] websocket_error", e)

    async def send_json(self, websocket: WebSocket, payload: dict):
        """Send JSON message through WebSocket"""
        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.send_text(json.dumps(payload))
            else:
                log.warning("WebSocket connection is closed, cannot send message")
        except Exception as e:
            log.warning(f"Failed to send WebSocket message: {e}")

    async def handle_final_transcript(self, websocket: WebSocket, data: dict, mem: SessionMemory, 
                                    mem_store: Optional[MemoryStore], conn_id: str):
        """Handle final transcript from client"""
        try:
            transcript = data.get("text", "").strip()
            if not transcript:
                return

            log.info(f"[{conn_id}] 📝 Processing transcript: {transcript}")
            
            # Add to memory
            mem.add_history("user", transcript)
            
            # Generate AI response
            await self.generate_and_send_response(websocket, transcript, mem, conn_id)
            
            # Save memory
            if mem_store:
                mem_store.save(mem)
                
        except Exception as e:
            log_exception(log, f"[{conn_id}] final_transcript", e)

    async def handle_client_prefs(self, websocket: WebSocket, data: dict, mem: SessionMemory, 
                                mem_store: Optional[MemoryStore], conn_id: str):
        """Handle client preferences"""
        try:
            changed = False
            
            if "client_id" in data and not mem.client_id:
                cid = re.sub(r"[^A-Za-z0-9_\-\.]", "_", str(data["client_id"]))[:64]
                mem.client_id = cid
                mem_store = MemoryStore(cid)
                
                # Load persisted memory
                persisted = mem_store.load()
                if persisted:
                    mem.load_from_dict(persisted)
                    log.info(f"[{conn_id}] Loaded memory for {cid}")
                
                # Load role play config from database
                mem.load_role_play_from_db(cid)
                
                # If role play is enabled in DB, ensure memory reflects it
                db_config = self.db_service.get_role_play_config(cid)
                if db_config and db_config.role_play_enabled:
                    mem.role_play_enabled = True
                    mem.role_play_template = db_config.role_play_template
                    mem.organization_name = db_config.organization_name
                    mem.organization_details = db_config.organization_details
                    mem.role_title = db_config.role_title

            if "language" in data:
                new_language = data["language"]
                if new_language in LANGUAGES and new_language != mem.language:
                    mem.language = new_language
                    changed = True
                    log.info(f"[{conn_id}] Language={new_language}")

            if "voice" in data:
                new_voice = data["voice"]
                if hasattr(mem, 'voice') and mem.voice != new_voice:
                    mem.voice = new_voice
                    changed = True
                    log.info(f"[{conn_id}] Voice={new_voice}")
                elif not hasattr(mem, 'voice'):
                    mem.voice = new_voice
                    changed = True
                    log.info(f"[{conn_id}] Voice={new_voice} (initial)")

            if "use_local_tts" in data:
                server_tts_enabled = not data["use_local_tts"]

            if "level" in data:
                new_level = data["level"]
                if new_level in ("easy", "medium", "fast") and new_level != mem.level:
                    old_level = mem.level
                    mem.level = new_level
                    mem._recent_level_change_ts = asyncio.get_event_loop().time()
                    # Context isolation: keep last few turns only
                    if len(mem.history) > mem._context_isolation_threshold:
                        mem.history = mem.history[-mem._context_isolation_threshold:]
                    changed = True
                    log.info(f"[{conn_id}] Level={new_level} (was {old_level})")

        except Exception as e:
            log_exception(log, f"[{conn_id}] client_prefs", e)

    async def handle_audio_data(self, websocket: WebSocket, msg: dict, mem: SessionMemory, 
                              conn_id: str, pre_buffer: deque, triggered: bool, 
                              voiced_frames: deque, voiced_count: int, silence_count: int, utter_frames: int):
        """Handle incoming audio data"""
        # This is a simplified version - you can expand this based on your VAD needs
        pass

    async def generate_and_send_response(self, websocket: WebSocket, transcript: str, 
                                       mem: SessionMemory, conn_id: str):
        """Generate AI response and send it"""
        try:
            # Get language configuration
            lang_config = LANGUAGES[mem.language]
            persona = lang_config["persona"]
            
            # Create context messages
            context_messages = self.llm_service.create_context_messages(mem.get_recent_context())
            
            # Generate AI response
            ai_response = await self.llm_service.generate_with_context(
                user_message=transcript,
                context=context_messages,
                persona=persona,
                language=mem.language
            )
            
            if ai_response:
                # Add to memory
                mem.add_history("assistant", ai_response)
                
                # Send text response
                await self.send_json(websocket, {"type": "ai_text", "text": ai_response})
                
                # Generate and send audio
                await self.generate_and_send_audio(websocket, ai_response, mem, conn_id)
            else:
                log.warning(f"[{conn_id}] No AI response generated")
                
        except Exception as e:
            log_exception(log, f"[{conn_id}] generate_response", e)

    async def generate_and_send_audio(self, websocket: WebSocket, text: str, 
                                    mem: SessionMemory, conn_id: str):
        """Generate and send audio response"""
        try:
            # Synthesize audio
            audio_data = await self.tts_service.synthesize_with_level(
                text=text,
                language=mem.language,
                voice=mem.voice,
                level=mem.level
            )
            
            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                await self.send_json(websocket, {
                    "type": "ai_audio",
                    "audio_base64": audio_b64
                })
                log.info(f"[{conn_id}] 🔊 Audio sent ({len(audio_data)} bytes)")
            else:
                log.warning(f"[{conn_id}] Failed to generate audio")
                
        except Exception as e:
            log_exception(log, f"[{conn_id}] generate_audio", e)


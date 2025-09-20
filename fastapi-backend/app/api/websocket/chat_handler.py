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
        """Generate AI response with real-time streaming TTS"""
        try:
            # Get language configuration
            lang_config = LANGUAGES[mem.language]
            persona = lang_config["persona"]
            
            # Create context messages
            context_messages = self.llm_service.create_context_messages(mem.get_recent_context())
            
            # Add user message to memory
            mem.add_history("user", transcript)
            
            # Generate streaming AI response with real-time audio
            full_response = ""
            is_first_chunk = True
            text_buffer = ""
            word_count = 0
            
            # Send audio start signal
            await self.send_json(websocket, {
                "type": "ai_audio_start",
                "is_final": False
            })
            
            # Pre-warm TTS for faster first response
            try:
                await self.tts_service.synthesize_text("", mem.language, mem.voice)
            except:
                pass  # Ignore pre-warm errors
            
            # Create messages with system prompt for voice agent
            messages = [
                {"role": "system", "content": persona},
                {"role": "system", "content": "IMPORTANT: You are a VOICE agent. Keep responses SHORT (1-2 sentences max). Speak naturally and concisely. No long explanations or detailed lists."}
            ]
            
            # Add grammar correction prompt
            grammar_prompt = """IMPORTANT: If the user's input contains grammatical errors, spelling mistakes, or unclear language, respond in this EXACT format:

🔴 GRAMMAR_CORRECTION_START 🔴
INCORRECT: [exactly what the user said]
CORRECT: [the grammatically correct version]
🔴 GRAMMAR_CORRECTION_END 🔴

Then provide your normal response to their question.

EXAMPLE:
User says: "what your name"
You respond:
🔴 GRAMMAR_CORRECTION_START 🔴
INCORRECT: what your name
CORRECT: What is your name?
🔴 GRAMMAR_CORRECTION_END 🔴

My name is SHCI. How can I help you?

If the input is grammatically correct, respond normally without any grammar correction."""
            
            messages.append({"role": "system", "content": grammar_prompt})
            messages.extend(context_messages)
            messages.append({"role": "user", "content": transcript})
            
            async for text_chunk in self.llm_service.generate_streaming_response(
                messages=messages,
                temperature=0.7,
                max_tokens=100  # Reduced for faster response
            ):
                if text_chunk:
                    full_response += text_chunk
                    text_buffer += text_chunk
                    
                    # Send text chunk to frontend for real-time display
                    await self.send_json(websocket, {
                        "type": "ai_text_chunk", 
                        "text": text_chunk,
                        "is_final": False,
                        "is_first_chunk": is_first_chunk
                    })
                    is_first_chunk = False
                    
                    # Generate audio for text chunk if it contains complete sentences
                    if self.should_generate_audio_chunk(text_buffer):
                        # Clean up text for better speech
                        clean_text = text_buffer.strip()
                        # Remove extra spaces and normalize text
                        clean_text = ' '.join(clean_text.split())
                        
                        audio_chunk = await self.generate_audio_for_text_chunk(
                            clean_text, mem, conn_id
                        )
                        if audio_chunk:
                            await self.send_json(websocket, {
                                "type": "ai_audio_chunk",
                                "text": clean_text,
                                "audio_base64": audio_chunk,
                                "audio_size": len(audio_chunk),
                                "is_final": False
                            })
                            text_buffer = ""  # Clear buffer after generating audio
            
            # Generate audio for any remaining text
            if text_buffer.strip():
                # Clean up final text for better speech
                clean_text = text_buffer.strip()
                clean_text = ' '.join(clean_text.split())
                
                audio_chunk = await self.generate_audio_for_text_chunk(
                    clean_text, mem, conn_id
                )
                if audio_chunk:
                    await self.send_json(websocket, {
                        "type": "ai_audio_chunk",
                        "text": clean_text,
                        "audio_base64": audio_chunk,
                        "audio_size": len(audio_chunk),
                        "is_final": False
                    })
            
            if full_response:
                # Send final complete text
                await self.send_json(websocket, {
                    "type": "ai_text", 
                    "text": full_response,
                    "is_final": True
                })
                
                # Send audio complete signal
                await self.send_json(websocket, {
                    "type": "ai_audio_complete",
                    "is_final": True
                })
                
                # Add complete response to memory
                mem.add_history("assistant", full_response)
            else:
                log.warning(f"[{conn_id}] No AI response generated")
                
        except Exception as e:
            log_exception(log, f"[{conn_id}] generate_response", e)

    def should_generate_audio_chunk(self, text_buffer: str) -> bool:
        """Determine if we should generate audio for the current text buffer"""
        if not text_buffer.strip():
            return False
        
        # Generate audio only for complete sentences to sound natural
        words = text_buffer.split()
        sentence_endings = ['.', '!', '?', ';', ':', '\n']
        
        # Check for sentence endings - this is the main trigger for natural speech
        if any(text_buffer.rstrip().endswith(ending) for ending in sentence_endings):
            return True
        
        # Only generate audio for longer phrases (8+ words) to avoid robotic word-by-word playback
        # This ensures natural human-like speech flow
        if len(words) >= 8:
            return True
            
        return False

    def split_text_into_sentences(self, text: str) -> list:
        """Split text into natural sentence chunks for better audio flow"""
        import re
        
        # Split by sentence endings but keep the punctuation
        sentences = re.split(r'([.!?;:]+)', text)
        
        # Recombine sentences with their punctuation
        result = []
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
                if sentence.strip():
                    result.append(sentence.strip())
            elif sentences[i].strip():
                result.append(sentences[i].strip())
        
        return result

    async def generate_audio_for_text_chunk(self, text: str, mem: SessionMemory, conn_id: str) -> str:
        """Generate audio for a text chunk and return base64 encoded audio"""
        try:
            if not text.strip():
                return None
                
            # Generate audio using TTS service
            audio_data = await self.tts_service.synthesize_text(
                text=text,
                language=mem.language,
                voice=mem.voice,
                length_scale=self.tts_service.length_scale * self.tts_service.adjust_speed_for_level(mem.level)
            )
            
            if audio_data:
                # Convert to base64
                import base64
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                log.info(f"[{conn_id}] 🔊 Generated audio for text chunk: '{text[:50]}...' ({len(audio_data)} bytes)")
                return audio_b64
            else:
                log.warning(f"[{conn_id}] Failed to generate audio for text chunk")
                return None
                
        except Exception as e:
            log_exception(log, f"[{conn_id}] generate_audio_for_text_chunk", e)
            return None

    async def generate_and_send_streaming_audio(self, websocket: WebSocket, text: str, 
                                              mem: SessionMemory, conn_id: str):
        """Generate and send streaming audio chunks"""
        try:
            # Send audio start signal to clear previous audio
            await self.send_json(websocket, {
                "type": "ai_audio_start",
                "is_final": False
            })
            
            # Create a simple text stream from the complete text
            async def text_stream():
                # Split text into chunks for streaming
                words = text.split()
                chunk_size = 8  # Process 8 words at a time
                
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i + chunk_size])
                    if i + chunk_size < len(words):
                        chunk += " "  # Add space if not the last chunk
                    yield chunk
                    await asyncio.sleep(0.1)  # Small delay between chunks
            
            # Generate streaming audio chunks
            async for audio_chunk in self.tts_service.synthesize_streaming_chunks(
                text_stream=text_stream(),
                language=mem.language,
                voice=mem.voice,
                level=mem.level,
                chunk_size=50
            ):
                if audio_chunk and audio_chunk.get('audio_data'):
                    audio_b64 = base64.b64encode(audio_chunk['audio_data']).decode("utf-8")
                    await self.send_json(websocket, {
                        "type": "ai_audio_chunk",
                        "text": audio_chunk['text'],
                        "audio_base64": audio_b64,
                        "audio_size": audio_chunk['audio_size'],
                        "is_final": False
                    })
                    log.info(f"[{conn_id}] 🔊 Audio chunk sent ({audio_chunk['audio_size']} bytes)")
            
            # Send final audio completion signal
            await self.send_json(websocket, {
                "type": "ai_audio_complete",
                "is_final": True
            })
            log.info(f"[{conn_id}] 🔊 Audio streaming completed")
                
        except Exception as e:
            log_exception(log, f"[{conn_id}] generate_streaming_audio", e)

    async def generate_and_send_audio(self, websocket: WebSocket, text: str, 
                                    mem: SessionMemory, conn_id: str):
        """Generate and send audio response (legacy method)"""
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


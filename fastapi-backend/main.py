# main.py
import os, io, json, base64, asyncio, logging, time, traceback, uuid, re, pathlib
import sqlite3
from collections import deque
from typing import Deque, Optional, Dict, Any, List

import numpy as np
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# faster-whisper removed - using WebkitSpeechRecognition instead
# import webrtcvad
from xtts_wrapper import xtts_wrapper
from xtts_manager import xtts_manager
from realtime_tts_streaming import streaming_manager, start_tts_stream, stop_tts_stream, get_streaming_stats
from tts_factory import tts_factory, synthesize_text, synthesize_text_async, get_tts_info, TTSSystem

# ===================== Logging =====================
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("main")

def log_exception(where: str, e: Exception):
    tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    log.error(f"[EXC] {where}: {e}\n{tb}")

# ===================== Env / Config =====================
load_dotenv()

# ---- LLM ----
LLM_API_URL   = os.getenv("LLM_API_URL", "http://173.208.167.147:11434/v1/chat/completions").strip()
LLM_MODEL     = os.getenv("LLM_MODEL", "qwen2.5-14b-gpu").strip()
LLM_API_KEY   = os.getenv("LLM_API_KEY", "").strip()  # optional
LLM_TIMEOUT   = float(os.getenv("LLM_TIMEOUT", "10.0"))  # Reduced for faster responses
LLM_RETRIES   = int(os.getenv("LLM_RETRIES", "1"))  # Reduced retries for faster failure
log.info(f"Using self-hosted LLM at: {LLM_API_URL} (model={LLM_MODEL}) timeout={LLM_TIMEOUT}s, retries={LLM_RETRIES}")

# ---- LanguageTool ----
# LanguageTool COMMENTED OUT for direct LLM → gTTS flow
# LT_API_URL = os.getenv("LT_API_URL", "https://languagetool.nodecel.cloud/v2/check")
# log.info(f"Using LanguageTool at: {LT_API_URL}")

# ---- Whisper ----
# Whisper removed - using WebkitSpeechRecognition instead
# WHISPER_MODEL   = os.getenv("WHISPER_MODEL", "small")
# WHISPER_DEVICE  = os.getenv("WHISPER_DEVICE", "cpu")
# WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")
# log.info(f"Loading Whisper model ({WHISPER_MODEL}) on {WHISPER_DEVICE} compute={WHISPER_COMPUTE} ...")
# stt = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
# log.info("Whisper loaded with multilingual support.")

# ---- TTS (XTTS - Coqui TTS) ----
XTTS_MODEL = os.getenv("XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2").strip()
XTTS_LANGUAGE = os.getenv("XTTS_LANGUAGE", "en").strip()
XTTS_SPEAKER_WAV = os.getenv("XTTS_SPEAKER_WAV", "").strip()
XTTS_SPEED = float(os.getenv("XTTS_SPEED", "1.0"))
XTTS_TEMPERATURE = float(os.getenv("XTTS_TEMPERATURE", "0.75"))
TTS_OUTPUT_FORMAT = os.getenv("TTS_OUTPUT_FORMAT", "wav").strip()
TTS_SAMPLE_RATE = int(os.getenv("TTS_SAMPLE_RATE", "22050"))
TTS_USE_CUDA = os.getenv("TTS_USE_CUDA", "true").lower().strip() == "true"

log.info(f"XTTS Configuration:")
log.info(f"  Model: {XTTS_MODEL}")
log.info(f"  Language: {XTTS_LANGUAGE}")
log.info(f"  Speaker: {XTTS_SPEAKER_WAV or 'Default'}")
log.info(f"  Speed: {XTTS_SPEED}")
log.info(f"  Temperature: {XTTS_TEMPERATURE}")
log.info(f"  Device: {'CUDA' if TTS_USE_CUDA else 'CPU'}")

# ---- Memory store ----
MEM_ROOT = pathlib.Path(os.getenv("MEM_DB_DIR", "memdb"))
MEM_ROOT.mkdir(parents=True, exist_ok=True)

# ---- SQLite Database ----
DB_PATH = pathlib.Path("roleplay.db")
log.info(f"Using SQLite database: {DB_PATH.absolute()}")

# ===================== FastAPI =====================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# ===================== Startup Events =====================
@app.on_event("startup")
async def startup_event():
    """Initialize TTS system on startup"""
    try:
        log.info("🚀 Starting TTS system initialization...")
        
        # Initialize TTS factory
        tts_info = get_tts_info()
        log.info(f"TTS Environment: {tts_info['environment']}")
        log.info(f"Preferred TTS System: {tts_info['preferred_system']}")
        log.info(f"Available TTS Providers: {', '.join(tts_info['available_providers'])}")
        
        # Initialize XTTS system only if Coqui TTS is preferred
        if tts_info['preferred_system'] == 'coqui':
            log.info("🚀 Starting XTTS initialization...")
            try:
                success = await xtts_wrapper.initialize()
                if success:
                    log.info("✅ XTTS system initialized successfully")
                else:
                    log.error("❌ Failed to initialize XTTS system")
            except Exception as xtts_error:
                log.error(f"❌ XTTS initialization error: {xtts_error}")
                log.info("ℹ️ Continuing with fallback TTS system")
        else:
            log.info("ℹ️ Using alternative TTS system (gTTS/Fallback)")
        
        log.info("✅ TTS system initialization complete")
    except Exception as e:
        log.error(f"❌ TTS startup error: {e}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup XTTS resources on shutdown"""
    try:
        log.info("🔄 Shutting down XTTS system...")
        await xtts_wrapper.cleanup_async()
        
        # Cleanup streaming resources
        log.info("🔄 Cleaning up TTS streaming resources...")
        from realtime_tts_streaming import cleanup_streaming
        cleanup_streaming()
        
        log.info("✅ XTTS system shutdown complete")
    except Exception as e:
        log.error(f"❌ XTTS shutdown error: {e}")

# ===================== Audio / VAD =====================
SR = 16000
FRAME_MS = 30
SAMPLES_PER_FRAME = SR * FRAME_MS // 1000
BYTES_PER_FRAME   = SAMPLES_PER_FRAME * 2

# Tuned endpointing
# VAD_AGGR              = int(os.getenv("VAD_AGGR", "2"))  # Removed - using WebkitSpeechRecognition instead
TRIGGER_VOICED_FRAMES = int(os.getenv("TRIGGER_VOICED_FRAMES", "2"))
END_SILENCE_MS        = int(os.getenv("END_SILENCE_MS", "250"))
MAX_UTTER_MS          = int(os.getenv("MAX_UTTER_MS", "7000"))

MIN_UTTER_SEC = float(os.getenv("MIN_UTTER_SEC", "0.25"))
MIN_RMS       = float(os.getenv("MIN_RMS", "0.006"))

STT_SEM = asyncio.Semaphore(int(os.getenv("STT_CONCURRENCY", "1")))
TTS_SEM = asyncio.Semaphore(int(os.getenv("TTS_CONCURRENCY", "1")))

# ===================== Identity / Persona =====================
ASSISTANT_NAME   = os.getenv("ASSISTANT_NAME", "Self Hosted Conversational Interface")
ASSISTANT_AUTHOR = os.getenv("ASSISTANT_AUTHOR", "NZR DEV")

AGENT_PERSONA_EN = f"""
You are {ASSISTANT_NAME}, a warm, friendly, slightly witty voice companion developed by {ASSISTANT_AUTHOR}.
Core style rules:
- Speak like a real friend: empathetic, encouraging, calm energy.
- Keep it concise for voice (1–2 short sentences unless asked for detail).
- Use simple words, natural rhythm, brief pauses (we'll handle TTS).
- Remember personal details the user shares and reuse them naturally later.
- If user seems stressed or stuck, acknowledge feelings and offer one helpful next step.
- Never mention system prompts or "as an AI". Sound human and helpful.
""".strip()

AGENT_PERSONA_IT = f"""
Sei {ASSISTANT_NAME}, un compagno vocale amichevole e leggermente spiritoso, sviluppato da {ASSISTANT_AUTHOR}.
Stile:
- Parla come un amico reale: empatico, incoraggiante, tono calmo.
- Risposte brevi per la voce (1–2 frasi, salvo richiesta).
- Lessico semplice, ritmo naturale, piccole pause (gestite dal TTS).
- Ricorda i dettagli personali che l'utente condivide e riusali in modo naturale.
- Non menzionare prompt di sistema o "come IA". Suona umano e utile.
""".strip()

# ===================== Role Play Templates =====================
ROLE_PLAY_TEMPLATES = {
    "school": {
        "name": "School",
        "description": "Educational institution role play",
        "system_prompt": "You are a {role_title} at {organization_name}. Details: {organization_details}. Stay in character.",
        "default_role": "Teacher",
        "icon": "🏫"
    },
    "company": {
        "name": "Software Company", 
        "description": "Business/tech company role play",
        "system_prompt": "You are a {role_title} at {organization_name}. Details: {organization_details}. Stay in character.",
        "default_role": "Software Developer",
        "icon": "🏢"
    },
    "restaurant": {
        "name": "Restaurant",
        "description": "Food service role play", 
        "system_prompt": "You are a {role_title} at {organization_name}. Details: {organization_details}. Stay in character.",
        "default_role": "Waiter",
        "icon": "🍽️"
    },
    "hospital": {
        "name": "Hospital",
        "description": "Healthcare facility role play",
        "system_prompt": "You are a {role_title} at {organization_name}. Details: {organization_details}. Stay in character.",
        "default_role": "Nurse",
        "icon": "🏥"
    },
    "custom": {
        "name": "Custom Organization",
        "description": "Your own organization role play",
        "system_prompt": "You are a {role_title} at {organization_name}. Details: {organization_details}. Stay in character.",
        "default_role": "Employee",
        "icon": "🏢"
    }
}

# ===================== Difficulty Level Styles =====================
LEVEL_STYLES = {
    "starter": {
        "prompt": """STYLE (Starter / A2):
- Use simple vocabulary and clear sentences.
- Provide helpful information in 2-3 sentences.
- Be friendly and encouraging. Use simple present tense.
- Give practical details about your role and organization.""",
        "temperature": 0.3,
        "max_tokens": 120,
    },
    "medium": {
        "prompt": """STYLE (Medium / B1–B2):
- Provide detailed, informative responses in 3-4 sentences.
- Use natural, conversational language with some variety.
- Include relevant details about your organization and role.
- Be helpful and professional in your responses.""",
        "temperature": 0.5,
        "max_tokens": 180,
    },
    "advanced": {
        "prompt": """STYLE (Advanced / C1):
- Give comprehensive, detailed responses in 4-5 sentences.
- Use rich vocabulary and natural expressions.
- Provide thorough information about your role and organization.
- Be articulate and professional while maintaining character.""",
        "temperature": 0.7,
        "max_tokens": 250,
    },
}

# ===================== Language Pack =====================
LANGUAGES = {
    "en": {
        "name": "English",
        "assistant_name": ASSISTANT_NAME,
        "intro_line": f'Hi — I\'m "{ASSISTANT_NAME}", developed by {ASSISTANT_AUTHOR}. What\'s your name?',
        "shortcut_patterns": {
            "name": r"\b(what('?s| is)\s+your\s+name|who\s+are\s+you)\b",
            "destination": r"\b(where\s+did\s+i\s+(?:want|plan)\s+to\s+go)\b",
            "my_name": r"\bwhat('?s| is)\s+my\s+name\b",
        },
        "responses": {
            "destination_remembered": "You said {name} wanted to go to {destination}.",
            "no_destination": "I don't have a destination remembered yet.",
            "name_remembered": "Your name is {name}.",
            "no_name": "You haven't told me your name yet."
        },
        "persona": AGENT_PERSONA_EN,
        # "languagetool_code": "en-US",  # COMMENTED OUT
    },
    "it": {
        "name": "Italiano",
        "assistant_name": "Interfaccia Conversazionale Self-Hosted",
        "intro_line": f'Ciao — Sono "{ASSISTANT_NAME}", sviluppata da {ASSISTANT_AUTHOR}. Come ti chiami?',
        "shortcut_patterns": {
            "name": r"\b(come\s+ti\s+chiami|chi\s+sei|qual\s+è\s+il\s+tuo\s+nome)\b",
            "destination": r"\b(dove\s+volevo\s+andare|dove\s+avevo\s+programmato\s+di\s+andare)\b",
            "my_name": r"\b(come\s+mi\s+chiamo|qual\s+è\s+il\s+mio\s+nome)\b",
        },
        "responses": {
            "destination_remembered": "Hai detto che {name} voleva andare a {destination}.",
            "no_destination": "Non ho ancora ricordato una destinazione.",
            "name_remembered": "Il tuo nome è {name}.",
            "no_name": "Non mi hai ancora detto il tuo nome."
        },
        "persona": AGENT_PERSONA_IT,
        # "languagetool_code": "it",  # COMMENTED OUT
    },
}
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")

# ===================== Database Manager =====================
from roleplay_database import RolePlayDatabase
from organization_database import OrganizationDatabase

# Initialize databases
roleplay_db = RolePlayDatabase(DB_PATH)
organization_db = OrganizationDatabase(DB_PATH)

# ===================== Memory: Session + Persistent =====================
class SessionMemory:
    def __init__(self, language: str = "en"):
        self.user_name: Optional[str] = None
        self.last_destination: Optional[str] = None
        self.facts: Dict[str, Any] = {}
        self.traits: Dict[str, Any] = {}
        self.history: List[Dict[str, str]] = []
        self.greeted: bool = False
        self.language: str = language
        self.client_id: Optional[str] = None
        self.level: str = "starter"
        self._recent_level_change_ts: float = 0.0  # NEW: for context trim on level change
        
        # Role play settings
        self.role_play_enabled: bool = False
        self.role_play_template: str = "school"
        self.organization_name: str = ""
        self.organization_details: str = ""
        self.role_title: str = ""
        
        # RAG context for customer organization context
        self.rag_context: str = ""

    def add_history(self, role: str, text: str):
        text = (text or "").strip()
        if not text:
            return
        role_map = {"User": "user", "Assistant": "assistant"}
        self.history.append({"role": role_map.get(role, role), "content": text})
        if len(self.history) > 24:
            self.history = self.history[-24:]

    def to_dict(self):
        return {
            "user_name": self.user_name,
            "last_destination": self.last_destination,
            "facts": self.facts,
            "traits": self.traits,
            "language": self.language,
            "level": self.level,
            "role_play_enabled": self.role_play_enabled,
            "role_play_template": self.role_play_template,
            "organization_name": self.organization_name,
            "organization_details": self.organization_details,
            "role_title": self.role_title,
        }

    def load_from_dict(self, d: Dict[str, Any]):
        self.user_name = d.get("user_name") or self.user_name
        self.last_destination = d.get("last_destination") or self.last_destination
        self.facts.update(d.get("facts") or {})
        self.traits.update(d.get("traits") or {})
        self.level = d.get("level", self.level)
        
        # Load role play settings
        self.role_play_enabled = d.get("role_play_enabled", self.role_play_enabled)
        self.role_play_template = d.get("role_play_template", self.role_play_template)
        self.organization_name = d.get("organization_name", self.organization_name)
        self.organization_details = d.get("organization_details", self.organization_details)
        self.role_title = d.get("role_title", self.role_title)
    
    def load_role_play_from_db(self, client_id: str):
        """Load role play configuration from database"""
        if not client_id:
            return
        
        config = roleplay_db.get_role_play_config(client_id)
        if config:
            self.role_play_enabled = config['role_play_enabled']
            self.role_play_template = config['role_play_template']
            self.organization_name = config['organization_name']
            self.organization_details = config['organization_details']
            self.role_title = config['role_title']
            log.info(f"Loaded role play config from DB: {config}")
        else:
            log.info(f"No role play config found in DB for client: {client_id}")
    
    def save_role_play_to_db(self, client_id: str):
        """Save role play configuration to database"""
        if not client_id:
            return False
        
        config = {
            'role_play_enabled': self.role_play_enabled,
            'role_play_template': self.role_play_template,
            'organization_name': self.organization_name,
            'organization_details': self.organization_details,
            'role_title': self.role_title
        }
        
        success = roleplay_db.save_role_play_config(client_id, config)
        if success:
            log.info(f"Saved role play config to DB for client: {client_id}")
        else:
            log.error(f"Failed to save role play config to DB for client: {client_id}")
        return success

class MemoryStore:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.path = MEM_ROOT / f"{client_id}.json"
    def load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as e:
                log_exception("MemoryStore.load", e)
        return {}
    def save(self, mem: SessionMemory):
        try:
            self.path.write_text(json.dumps(mem.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            log_exception("MemoryStore.save", e)

# ===================== Extractors =====================
NAME_CLAIM_EN = re.compile(r"\b(?:my\s+name\s+is|call\s+me)\s+([A-Za-z][A-Za-z\-']{1,30})\b", re.I)
DEST_CLAIM_EN = re.compile(r"\b(?:want(?:\s+to)?\s+go\s+to|going\s+to|travel(?:ling)?\s+to|go\s+to)\s+([A-Za-z][A-Za-z\s\-']{2,60})\b", re.I)
LIKES_EN      = re.compile(r"\bI\s+(?:really\s+)?(?:like|love)\s+([A-Za-z0-9\s\-']{2,60})\b", re.I)
REMEMBER_EN   = re.compile(r"\bremember\s+that\s+(.+)$", re.I)
BIRTHDAY_EN   = re.compile(r"\bmy\s+birthday\s+is\s+([A-Za-z0-9\s,\/\-]+)", re.I)

NAME_CLAIM_IT = re.compile(r"\b(?:mi\s+chiamo|sono|il\s+mio\s+nome\s+è)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-']{1,30})\b", re.I)
DEST_CLAIM_IT = re.compile(r"\b(?:voglio\s+andare\s+a|sto\s+andando\s+a|viaggio\s+a|vado\s+a|pianifico\s+di\s+andare\s+a)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-']{2,60})\b", re.I)
LIKES_IT      = re.compile(r"\b(?:mi\s+piace|adoro)\s+([A-Za-zÀ-ÿ0-9\s\-']{2,60})\b", re.I)
REMEMBER_IT   = re.compile(r"\bricorda\s+che\s+(.+)$", re.I)
BIRTHDAY_IT   = re.compile(r"\bil\s+mio\s+compleanno\s+è\s+([A-Za-zÀ-ÿ0-9\s,\/\-]+)", re.I)

WHERE_DID_I_WANT_TO_GO = re.compile(r"\b(where\s+did\s+i\s+(?:want|plan)\s+to\s+go|dove\s+volevo\s+andare|dove\s+avevo\s+programmato\s+di\s+andare)\b", re.I)
WHAT_WAS_MY_DEST       = re.compile(r"\b(what\s+was\s+my\s+(?:destination|plan)|qual\s+era\s+la\s+mia\s+(?:destinazione|meta))\b", re.I)

def extract_memory_updates(text: str, mem: SessionMemory):
    t = text.strip()
    if mem.language == "en":
        if m := NAME_CLAIM_EN.search(t): mem.user_name = m.group(1).strip().title()
        if m := DEST_CLAIM_EN.search(t): mem.last_destination = m.group(1).strip().rstrip("?.,!")
        if m := LIKES_EN.search(t):      mem.traits.setdefault("likes", []).append(m.group(1).strip().rstrip("?.,!"))
        if m := BIRTHDAY_EN.search(t):   mem.facts["birthday"] = m.group(1).strip()
        if m := REMEMBER_EN.search(t):   mem.facts.setdefault("notes", []).append(m.group(1).strip())
    else:
        if m := NAME_CLAIM_IT.search(t): mem.user_name = m.group(1).strip().title()
        if m := DEST_CLAIM_IT.search(t): mem.last_destination = m.group(1).strip().rstrip("?.,!")
        if m := LIKES_IT.search(t):      mem.traits.setdefault("likes", []).append(m.group(1).strip().rstrip("?.,!"))
        if m := BIRTHDAY_IT.search(t):   mem.facts["birthday"] = m.group(1).strip()
        if m := REMEMBER_IT.search(t):   mem.facts.setdefault("notes", []).append(m.group(1).strip())

def shortcut_answer(text: str, mem: SessionMemory) -> Optional[str]:
    current_lang = LANGUAGES[mem.language]
    if re.search(current_lang["shortcut_patterns"]["name"], text, re.I):
        who = current_lang["assistant_name"]
        if mem.level == "starter":
            return f"I'm {who}. Nice to meet you."
        elif mem.level == "medium":
            return f"I'm {who}. It's a pleasure to make your acquaintance."
        else:
            return f"I'm {who}. Delighted to meet you and begin our conversation."
    if WHERE_DID_I_WANT_TO_GO.search(text) or WHAT_WAS_MY_DEST.search(text):
        if mem.last_destination:
            who = mem.user_name or ("tu" if mem.language == "it" else "you")
            base_response = current_lang["responses"]["destination_remembered"].format(name=who, destination=mem.last_destination)
            if mem.level == "starter":
                return base_response
            elif mem.level == "medium":
                return f"I remember! {base_response}"
            else:
                return f"Ah yes, I recall that {base_response}"
        return current_lang["responses"]["no_destination"]
    if re.search(current_lang["shortcut_patterns"]["my_name"], text, re.I):
        if mem.user_name:
            base_response = current_lang["responses"]["name_remembered"].format(name=mem.user_name)
            if mem.level == "starter":
                return base_response
            elif mem.level == "medium":
                return f"That's right! {base_response}"
            else:
                return f"Absolutely! {base_response}"
        return current_lang["responses"]["no_name"]
    return None

# ===================== LanguageTool =====================
# LanguageTool functions COMMENTED OUT for direct LLM → gTTS flow
# def _apply_languagetool_corrections(original_text: str, matches: List[Dict[str, Any]]) -> str:
#     corrected_text = list(original_text)
#     offset_change = 0
#     for match in sorted(matches, key=lambda x: x['offset']):
#         if not match.get('replacements'): continue
#         offset = match['offset']; length = match['length']
#         replacement = match['replacements'][0]['value']
#         start = offset + offset_change; end = start + length
#         error = match.get("message", "Unknown error")
#         log.info(f"LanguageTool suggestion: {error}")
#         start = offset + offset_change; end = start + length
#         corrected_text[start:end] = list(replacement)
#         offset_change += len(replacement) - length
#     return "".join(corrected_text)

# def proofread_with_languagetool(text: str, lang: str) -> str:
#     if not text: return ""
#     try:
#         response = requests.post(LT_API_URL, data={'language': lang, 'text': text}, timeout=3.0)
#         response.raise_for_status()
#         data = response.json()
#         data = response.json()
#         if data.get('matches'): return _apply_languagetool_corrections(text, data['matches'])
#         return text
#     except requests.exceptions.RequestException as e:
#         log_exception(f"LanguageTool request failed for lang={lang}", e)
#         return text

# ===================== Level enforcement (NEW) =====================
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_SPLIT = re.compile(r"\s+")

def _trim_words(s: str, max_words: int) -> str:
    words = _WORD_SPLIT.split(s.strip())
    if len(words) <= max_words:
        return s.strip()
    return " ".join(words[:max_words]).rstrip(",;: ") + "."

def _first_n_sentences(text: str, n: int) -> List[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text.strip()) if p.strip()]
    return parts[:n] if parts else []

def enforce_level_style(text: str, level: str) -> str:
    if not text:
        return text
    
    # Clean the text first
    text = text.strip()
    
    # Split into sentences
    sents = _first_n_sentences(text, 5)  # Allow more sentences
    if not sents:
        sents = [text]

    if level == "starter":
        # 2-3 sentences, simple vocabulary
        if len(sents) >= 2:
            # Take first 2-3 sentences, ensure they're not too long
            result_sents = []
            total_words = 0
            for sent in sents[:3]:
                words = len(sent.split())
                if total_words + words <= 50:  # Reasonable limit for starter
                    result_sents.append(sent)
                    total_words += words
                else:
                    break
            return " ".join(result_sents) if result_sents else sents[0]
        else:
            return sents[0]

    elif level == "medium":
        # 3-4 sentences, natural language
        if len(sents) >= 3:
            # Take first 3-4 sentences
            result_sents = []
            total_words = 0
            for sent in sents[:4]:
                words = len(sent.split())
                if total_words + words <= 80:  # Reasonable limit for medium
                    result_sents.append(sent)
                    total_words += words
                else:
                    break
            return " ".join(result_sents) if result_sents else " ".join(sents[:3])
        else:
            return " ".join(sents)

    else:  # advanced
        # 4-5 sentences, rich vocabulary
        if len(sents) >= 4:
            # Take first 4-5 sentences
            result_sents = []
            total_words = 0
            for sent in sents[:5]:
                words = len(sent.split())
                if total_words + words <= 120:  # Reasonable limit for advanced
                    result_sents.append(sent)
                    total_words += words
                else:
                    break
            return " ".join(result_sents) if result_sents else " ".join(sents[:4])
        else:
            return " ".join(sents)

# ===================== LLM Integration =====================
# ===================== LLM Integration =====================
def _llm_request_sync(messages: List[Dict[str, str]], level: str = "starter") -> str:
    # headers
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    # level -> decoding params
    lvl = LEVEL_STYLES.get(level, LEVEL_STYLES["starter"])
    log.info(f"[LLM] Request level={level} temp={lvl['temperature']} max_tokens={lvl['max_tokens']}")

    # OpenAI-compatible chat payload (nodecel gateway compatible)
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": lvl["max_tokens"],
        "temperature": lvl["temperature"],
        "stream": False,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1
        # "stop": ["\nUser:", "\nAssistant:"],  # দরকার হলে রেখো
    }

    # conservative connect/read timeouts
    connect_to = max(2.0, min(5.0, LLM_TIMEOUT * 0.3))

    for attempt in range(1, LLM_RETRIES + 1):
        try:
            resp = requests.post(
                LLM_API_URL, headers=headers, json=payload,
                timeout=(connect_to, LLM_TIMEOUT)
            )
            resp.raise_for_status()
            data = resp.json()
            txt = (data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "") or "").strip()
            if txt:
                return txt
        except requests.exceptions.RequestException as e:
            log_exception(f"LLM API request (attempt {attempt}/{LLM_RETRIES})", e)
            time.sleep(0.35)

    return ""

def post_shorten(text: str, hard_limit: int = 110) -> str:
    t = (text or "").strip()
    if len(t) <= hard_limit: return t
    parts = re.split(r"(?<=[.!?])\s+", t)
    out, total = [], 0
    for p in parts:
        if not p: continue
        if total + len(p) + 1 > hard_limit: break
        out.append(p); total += len(p) + 1
        if len(out) >= 3: break
    return (" ".join(out).strip() if out else t[:hard_limit].rstrip()) + ("…" if len(t) > hard_limit else "")

async def llm_reply(user_text: str, mem: SessionMemory) -> str:
    if not user_text.strip(): return ""
    lvl = LEVEL_STYLES.get(mem.level, LEVEL_STYLES["starter"])
    log.info(f"[LLM] Using level: {mem.level} | temp: {lvl['temperature']} | max_tokens: {lvl['max_tokens']}")
    
    # Organization-based RAG approach: Check organizations table first
    organization_name = None
    organization_details = ""
    
    # Check if organization name is provided in memory
    if hasattr(mem, 'organization_name') and mem.organization_name:
        organization_name = mem.organization_name
        log.info(f"[LLM] 🔍 STEP 1: Found organization name in memory: '{organization_name}'")
    
    # If no organization name, try to extract from RAG context
    if not organization_name and hasattr(mem, 'rag_context') and mem.rag_context:
        log.info(f"[LLM] 🔍 STEP 2: Checking RAG context for organization name")
        log.info(f"[LLM] 🔍 STEP 2a: RAG context length: {len(mem.rag_context)}")
        
        # Get all organizations and check if any name appears in the RAG context
        organizations = organization_db.get_all_organizations(limit=50)
        for org in organizations:
            if org['name'].lower() in mem.rag_context.lower():
                organization_name = org['name']
                log.info(f"[LLM] 🔍 STEP 2b: Found organization '{organization_name}' in RAG context")
                break
    
    # If we found an organization, get its details from database
    if organization_name:
        log.info(f"[LLM] 🔍 STEP 3: Retrieving organization details for '{organization_name}'")
        
        org_data = organization_db.get_organization(organization_name)
        if org_data:
            organization_details = org_data['details']
            log.info(f"[LLM] 🔍 STEP 4: Retrieved organization data from database")
            log.info(f"[LLM] 🔍 STEP 4a: Organization details length: {len(organization_details)}")
            
            # Create organization-based context
            organization_context = f"""You are an AI assistant representing {org_data['name']}.

ORGANIZATION INFORMATION:
{org_data['details']}

USER QUESTION: {user_text}

RESPONSE FORMATTING INSTRUCTIONS:
- Provide a SINGLE, well-structured response (not multiple separate lines)
- Use professional formatting with clear sections if needed
- Include relevant details in a organized manner
- Use bullet points or numbered lists when appropriate
- Keep the response concise but comprehensive
- Always maintain a professional and helpful tone
- If the question is about the organization, provide detailed and accurate information
- If the question is not directly related to the organization, provide helpful general assistance
- Use the organization's details to provide contextually relevant answers
- If you don't have specific information about the organization for a question, say so honestly

IMPORTANT: Format your response as a single, well-organized paragraph or structured text block. Do not split information across multiple separate lines unless absolutely necessary for clarity."""
            
            log.info(f"[LLM] 🔍 STEP 5: Generated organization-based context")
            log.info(f"[LLM] 🔍 STEP 5a: Context length: {len(organization_context)}")
            
            system_messages = [{"role":"system","content":organization_context}]
        else:
            log.warning(f"[LLM] 🔍 STEP 4: Organization '{organization_name}' not found in database")
            # Fall back to standard persona
            persona = LANGUAGES[mem.language]["persona"]
            system_messages = [{"role":"system","content":persona}]
    else:
        log.info(f"[LLM] 🔍 STEP 1: No organization name found, using standard persona")
        # No organization specified, use standard persona
        persona = LANGUAGES[mem.language]["persona"]
        system_messages = [{"role":"system","content":persona}]

    # Grammar correction directive
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
    
    system_messages.append({"role":"system","content":grammar_prompt})
    
    # Difficulty directive
    system_messages.append({"role":"system","content":lvl["prompt"]})

    messages_to_send = system_messages + mem.history + [{"role":"user","content":user_text}]
    log.info(f"[LLM] Sending {len(messages_to_send)} messages, level: {mem.level}")
    
    loop = asyncio.get_event_loop()
    txt = await loop.run_in_executor(None,_llm_request_sync,messages_to_send,mem.level)
    
    # Process grammar correction if present
    if txt and "🔴 GRAMMAR_CORRECTION_START 🔴" in txt:
        log.info(f"[LLM] Grammar correction detected in response")
        log.info(f"[LLM] Full response before processing: {txt}")
        
        # Extract grammar correction and LLM answer separately
        start_marker = "🔴 GRAMMAR_CORRECTION_START 🔴"
        end_marker = "🔴 GRAMMAR_CORRECTION_END 🔴"
        
        if end_marker in txt:
            parts = txt.split(start_marker)
            if len(parts) >= 2:
                grammar_part = parts[1].split(end_marker)[0].strip()
                llm_answer = parts[1].split(end_marker)[1].strip() if end_marker in parts[1] else ""
                
                log.info(f"[LLM] Grammar part extracted: {grammar_part}")
                log.info(f"[LLM] LLM answer extracted: {llm_answer}")
                
                # Format the response with clear separation
                txt = f"{start_marker}\n{grammar_part}\n{end_marker}\n\n{llm_answer}"
                log.info(f"[LLM] Grammar correction formatted: {txt[:200]}...")
            else:
                log.warning(f"[LLM] Malformed grammar correction response")
        else:
            log.warning(f"[LLM] Grammar correction start found but no end marker")
            log.info(f"[LLM] Response without end marker: {txt}")
    
    # Post-process response for better formatting
    if txt:
        # Clean up fragmented responses and format them properly
        txt = format_response_professionally(txt)
    
    # Save the answer to database if organization-based RAG was used
    if organization_name and txt:
        try:
            # Note: We're not saving to roleplay_answers table anymore since we're using organizations table
            # The organization details are already in the organizations table
            log.info(f"[LLM] Organization-based response generated for '{organization_name}'")
        except Exception as e:
            log_exception(f"[LLM] Organization-based response", e)
    
    return txt or "Sorry, I didn't get that."

def format_response_professionally(text: str) -> str:
    """Format the response to be more professional and organized"""
    if not text:
        return text
    
    # Remove excessive whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # If the response is fragmented (multiple short sentences), combine them
    sentences = text.split('. ')
    if len(sentences) > 1:
        # Check if sentences are very short (likely fragmented)
        short_sentences = [s for s in sentences if len(s.split()) <= 5]
        if len(short_sentences) >= 2:
            # Combine short sentences into a more coherent response
            text = '. '.join(sentences)
            # Add proper spacing and formatting
            text = re.sub(r'\.([A-Z])', r'. \1', text)  # Add space after periods before capital letters
    
    # Ensure proper capitalization
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    
    # Add period at the end if missing
    if text and not text.endswith(('.', '!', '?')):
        text += '.'
    
    return text

# ===================== TTS (Environment-based) =====================
async def tts_bytes_async(text: str, language: str = "en", speaker_wav: str = None) -> bytes:
    """Async TTS function using environment-based TTS factory"""
    try:
        log.info(f"TTS synthesis: '{text[:50]}...' (lang={language})")
        
        # Get TTS info for logging
        tts_info = get_tts_info()
        log.info(f"Using TTS system: {tts_info['preferred_system']}")
        
        # Synthesize using TTS factory with ultra-fast mode
        audio_bytes = await synthesize_text_async(text, language, speaker_wav=speaker_wav, speed=2.0)
        
        if audio_bytes:
            log.info(f"✅ TTS synthesis successful: {len(audio_bytes)} bytes")
            return audio_bytes
        else:
            log.error("TTS synthesis failed - no audio returned")
            return b""
            
    except Exception as e:
        log_exception("tts_synthesis", e)
        return b""

def tts_bytes(text: str, language: str = "en", speaker_wav: str = None) -> bytes:
    """Main TTS function - uses environment-based TTS factory synchronously"""
    try:
        log.info(f"TTS synthesis (sync): '{text[:50]}...' (lang={language})")
        
        # Get TTS info for logging
        tts_info = get_tts_info()
        log.info(f"Using TTS system: {tts_info['preferred_system']}")
        
        # Synthesize using TTS factory with ultra-fast mode
        audio_bytes = synthesize_text(text, language, speaker_wav=speaker_wav, speed=2.0)
        
        if audio_bytes:
            log.info(f"✅ TTS synthesis successful: {len(audio_bytes)} bytes")
            return audio_bytes
        else:
            log.error("TTS synthesis failed - no audio returned")
            return b""
            
    except Exception as e:
        log_exception("tts_synthesis", e)
        return b""

# ===================== ASR Helpers =====================
def pcm16_to_float32(pcm16: bytes) -> np.ndarray:
    return np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
def pcm16_rms(pcm16: bytes) -> float:
    if not pcm16: return 0.0
    x = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
    if x.size == 0: return 0.0
    return float(np.sqrt(np.mean(x * x)))
def pcm_duration_sec(pcm16: bytes) -> float:
    return len(pcm16) / (2 * SR)

# transcribe_float32 function removed - using WebkitSpeechRecognition instead
# async def transcribe_float32(samples_f32: np.ndarray, language: str = "en") -> str:
#     if samples_f32.size == 0: return ""
#     t0 = time.time()
#     whisper_lang = "en" if language == "en" else "it"
#     segments, _ = stt.transcribe(
#         samples_f32, language=whisper_lang, task="transcribe",
#         vad_filter=False, beam_size=1, temperature=0.0, without_timestamps=True
#     )
#     text = " ".join(s.text for s in segments).strip()
#     log.info(f"[STT] done in {(time.time()-t0):.3f}s | lang={whisper_lang} | '{text[:60]}'")
#     return text

# ===================== WS helpers & Routes =====================
async def send_json(ws: WebSocket, payload: dict):
    try:
        # Check if WebSocket is still open
        if ws.client_state.name == "CONNECTED":
            await ws.send_text(json.dumps(payload))
        else:
            log.warning("WebSocket connection is closed, cannot send message")
    except Exception as e:
        log.warning(f"Failed to send WebSocket message: {e}")

@app.get("/")
async def root():
    return {"message": "Voice Agent Backend is running."}

@app.get("/test-tts")
async def test_tts(text: str = "Hello, this is a test of the XTTS system.", lang: str = "en"):
    try:
        log.info(f"Test XTTS called with text: '{text[:50]}...' and language: {lang}")
        audio_bytes = await tts_bytes_async(text, lang)
        
        if audio_bytes:
            # XTTS uses WAV format
            media_type = "audio/wav"
            return Response(content=audio_bytes, media_type=media_type)
        else:
            return JSONResponse({"error": "XTTS synthesis failed"}, status_code=500)
            
    except Exception as e:
        log_exception("test_tts", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/test-level")
async def test_level(text: str = "This is a test of the level enforcement system.", level: str = "starter"):
    try:
        log.info(f"Test level enforcement: level={level}, text='{text[:50]}...'")
        enforced_text = enforce_level_style(text, level)
        return {
            "original": text,
            "enforced": enforced_text,
            "level": level,
            "original_words": len(text.split()),
            "enforced_words": len(enforced_text.split()),
            "original_sentences": len(_first_n_sentences(text, 10)),
            "enforced_sentences": len(_first_n_sentences(enforced_text, 10))
        }
    except Exception as e:
        log_exception("test_level", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/test-roleplay")
async def test_roleplay(
    template: str = "school",
    organization_name: str = "Test School",
    organization_details: str = "A small private school with 200 students",
    role_title: str = "Teacher",
    question: str = "What do you do here?"
):
    try:
        log.info(f"Test role play: template={template}, org={organization_name}")
        
        # Create a mock SessionMemory for testing
        class MockMemory:
            def __init__(self):
                self.role_play_enabled = True
                self.role_play_template = template
                self.organization_name = organization_name
                self.organization_details = organization_details
                self.role_title = role_title
                self.language = "en"
                self.level = "medium"
                self.history = []
        
        mock_mem = MockMemory()
        
        # Test the role play context generation
        if mock_mem.role_play_enabled and mock_mem.organization_name and mock_mem.organization_details:
            template_obj = ROLE_PLAY_TEMPLATES.get(mock_mem.role_play_template, ROLE_PLAY_TEMPLATES["custom"])
            role_play_context = template_obj["system_prompt"].format(
                organization_name=mock_mem.organization_name,
                organization_details=mock_mem.organization_details,
                role_title=mock_mem.role_title or template_obj["default_role"]
            )
        else:
            role_play_context = "Role play not properly configured"
        
        return {
            "template": template,
            "organization_name": organization_name,
            "organization_details": organization_details,
            "role_title": role_title,
            "role_play_context": role_play_context,
            "templates_available": list(ROLE_PLAY_TEMPLATES.keys())
        }
    except Exception as e:
        log_exception("test_roleplay", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/tts-info")
async def get_tts_info_endpoint():
    """Get TTS system information"""
    try:
        log.info("Getting TTS info...")
        tts_info = get_tts_info()
        log.info(f"TTS info retrieved successfully: {tts_info['environment']}")
        return {
            "status": "success",
            "tts_info": tts_info,
            "timestamp": time.time()
        }
    except Exception as e:
        log.error(f"Error getting TTS info: {e}")
        import traceback
        log.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/tts-test")
async def test_tts_endpoint(
    text: str = "Hello, this is a test of the TTS system.",
    language: str = "en",
    speaker_wav: str = None,
    tts_system: str = None
):
    """Test TTS functionality with different systems"""
    try:
        log.info(f"Testing TTS: '{text[:50]}...'")
        
        # Determine TTS system
        system = None
        if tts_system:
            try:
                system = TTSSystem(tts_system.lower())
            except ValueError:
                return JSONResponse({
                    "status": "error",
                    "message": f"Invalid TTS system: {tts_system}. Available: gtts, coqui, fallback"
                }, status_code=400)
        
        # Test synthesis with ultra-fast mode
        audio_data = await synthesize_text_async(text, language, system, speaker_wav=speaker_wav, speed=2.0)
        
        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            tts_info = get_tts_info()
            
            return {
                "status": "success",
                "message": "TTS synthesis successful",
                "text": text,
                "language": language,
                "speaker_wav": speaker_wav,
                "tts_system_used": tts_info['preferred_system'],
                "audio_size": len(audio_data),
                "audio_base64": audio_b64,
                "audio_format": "wav",
                "tts_info": tts_info
            }
        else:
            return JSONResponse({
                "status": "error",
                "message": "TTS synthesis failed"
            }, status_code=500)
            
    except Exception as e:
        log_exception("test_tts", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/tts-streaming-test")
async def test_tts_streaming(
    text: str = "Hello, this is a test of real-time TTS streaming.",
    language: str = "en",
    speaker_wav: str = None
):
    """Test TTS streaming functionality"""
    try:
        log.info(f"Testing TTS streaming: '{text[:50]}...'")
        
        # Test synthesis with ultra-fast mode
        audio_data = await asyncio.get_event_loop().run_in_executor(
            None, 
            xtts_manager.synthesize_text, 
            text, 
            language, 
            speaker_wav,
            2.0  # ultra-fast speed parameter
        )
        
        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            return {
                "status": "success",
                "message": "TTS synthesis successful",
                "text": text,
                "language": language,
                "speaker_wav": speaker_wav,
                "audio_size": len(audio_data),
                "audio_base64": audio_b64,
                "audio_format": "wav",
                "sample_rate": xtts_manager.sample_rate
            }
        else:
            return JSONResponse({
                "status": "error",
                "message": "TTS synthesis failed"
            }, status_code=500)
            
    except Exception as e:
        log_exception("test_tts_streaming", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/test-roleplay-db")
async def test_roleplay_db(client_id: str = "u1zg6u8u29dmeye1eor"):
    """Test role play configuration from database"""
    try:
        log.info(f"Testing role play DB for client: {client_id}")
        
        # Get config from database
        config = roleplay_db.get_role_play_config(client_id)
        if not config:
            return {"error": f"No config found for client: {client_id}"}
        
        # Create mock memory with DB data
        class MockMemory:
            def __init__(self, config, client_id):
                self.client_id = client_id
                self.role_play_enabled = config['role_play_enabled']
                self.role_play_template = config['role_play_template']
                self.organization_name = config['organization_name']
                self.organization_details = config['organization_details']
                self.role_title = config['role_title']
                self.language = "en"
                self.level = "medium"
                self.history = []
        
        mock_mem = MockMemory(config, client_id)
        
        # Test role play context generation
        if mock_mem.role_play_enabled and mock_mem.organization_name and mock_mem.organization_details:
            template_obj = ROLE_PLAY_TEMPLATES.get(mock_mem.role_play_template, ROLE_PLAY_TEMPLATES["custom"])
            role_play_context = template_obj["system_prompt"].format(
                organization_name=mock_mem.organization_name,
                organization_details=mock_mem.organization_details,
                role_title=mock_mem.role_title or template_obj["default_role"]
            )
            
            # Test LLM reply
            test_question = "What is your organization name?"
            result = await llm_reply(test_question, mock_mem)
            
            return {
                "client_id": client_id,
                "config": config,
                "role_play_context": role_play_context,
                "test_question": test_question,
                "ai_response": result,
                "status": "success"
            }
        else:
            return {
                "client_id": client_id,
                "config": config,
                "error": "Role play not properly configured",
                "status": "incomplete"
            }
            
    except Exception as e:
        log_exception("test_roleplay_db", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/admin/roleplay-configs")
async def get_all_roleplay_configs():
    """Get all role play configurations (admin endpoint)"""
    try:
        configs = roleplay_db.get_all_configs()
        return {
            "total_configs": len(configs),
            "configs": configs
        }
    except Exception as e:
        log_exception("get_all_roleplay_configs", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/admin/roleplay-config/{client_id}")
async def get_roleplay_config(client_id: str):
    """Get role play configuration for a specific client"""
    try:
        config = roleplay_db.get_role_play_config(client_id)
        if config:
            return {"client_id": client_id, "config": config}
        else:
            return JSONResponse({"error": "Config not found"}, status_code=404)
    except Exception as e:
        log_exception(f"get_roleplay_config for {client_id}", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/admin/db-health")
async def check_database_health():
    """Check database health and role play configurations"""
    try:
        configs = roleplay_db.get_all_configs()
        total_configs = len(configs)
        enabled_configs = sum(1 for c in configs if c['role_play_enabled'])
        
        # Check database file
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        
        return {
            "database_status": "healthy" if DB_PATH.exists() else "missing",
            "database_size_bytes": db_size,
            "total_configs": total_configs,
            "enabled_configs": enabled_configs,
            "disabled_configs": total_configs - enabled_configs,
            "recent_configs": configs[:5]  # Show last 5 configs
        }
    except Exception as e:
        log_exception("check_database_health", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/test-mcp-tools")
async def test_mcp_tools(client_id: str, question: str):
    """Test MCP tools integration"""
    try:
        # Simulate MCP tool call
        db_config = roleplay_db.get_role_play_config(client_id)
        if db_config and db_config['role_play_enabled']:
            # Create role play context
            template = ROLE_PLAY_TEMPLATES.get(db_config['role_play_template'], ROLE_PLAY_TEMPLATES["custom"])
            role_play_context = template["system_prompt"].format(
                organization_name=db_config['organization_name'],
                organization_details=db_config['organization_details'],
                role_title=db_config['role_title'] or template["default_role"]
            )
            
            return {
                "client_id": client_id,
                "role_play_enabled": True,
                "context": role_play_context,
                "question": question,
                "mcp_integration": "success"
            }
        else:
            return {
                "client_id": client_id,
                "role_play_enabled": False,
                "message": "No role play configuration found",
                "question": question,
                "mcp_integration": "success"
            }
    except Exception as e:
        log_exception("test_mcp_tools", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/admin/roleplay-config/{client_id}")
async def clear_roleplay_config(client_id: str):
    """Clear role play configuration for a specific client"""
    try:
        success = roleplay_db.clear_role_play_config(client_id)
        if success:
            return {"message": f"Role play config cleared for client: {client_id}"}
        else:
            return JSONResponse({"error": "Failed to clear config"}, status_code=500)
    except Exception as e:
        log_exception(f"clear_roleplay_config for {client_id}", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/clear-roleplay/{client_id}")
async def clear_roleplay_for_client(client_id: str):
    """Clear role play configuration for a client (frontend endpoint)"""
    try:
        success = roleplay_db.clear_role_play_config(client_id)
        if success:
            log.info(f"Role play cleared for client: {client_id}")
            return {"success": True, "message": "Role play cleared successfully"}
        else:
            return JSONResponse({"error": "Failed to clear role play"}, status_code=500)
    except Exception as e:
        log_exception(f"clear_roleplay_for_client {client_id}", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/roleplay/answers/{client_id}")
async def get_roleplay_answers(client_id: str):
    """Get all stored role play answers for a client"""
    try:
        answers = roleplay_db.get_all_answers_for_client(client_id)
        return {
            "client_id": client_id,
            "total_answers": len(answers),
            "answers": answers
        }
    except Exception as e:
        log_exception(f"get_roleplay_answers for {client_id}", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/roleplay/search/{client_id}")
async def search_roleplay_answers(client_id: str, question: str = ""):
    """Search for role play answers by question"""
    try:
        if not question:
            return {"error": "Question parameter is required"}
        
        # Get client's role play config
        config = roleplay_db.get_role_play_config(client_id)
        if not config or not config.get('role_play_enabled'):
            return {"error": "Role play not enabled for this client"}
        
        # Search for stored answer
        stored_answer = roleplay_db.get_role_play_answer(client_id, question)
        if stored_answer:
            return {
                "client_id": client_id,
                "found": True,
                "answer": stored_answer,
                "source": "database"
            }
        
        # Search for similar answers
        similar_answers = roleplay_db.search_similar_answers(
            client_id, question, 
            config['organization_name'], config['role_title']
        )
        
        return {
            "client_id": client_id,
            "found": False,
            "similar_answers": similar_answers,
            "source": "similar_search"
        }
        
    except Exception as e:
        log_exception(f"search_roleplay_answers for {client_id}", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/roleplay/stats")
async def get_roleplay_stats():
    """Get role play database statistics"""
    try:
        stats = roleplay_db.get_database_stats()
        return {
            "database_stats": stats,
            "status": "success"
        }
    except Exception as e:
        log_exception("get_roleplay_stats", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/test-roleplay-detailed")
async def test_roleplay_detailed(
    client_id: str = "test_client",
    organization_name: str = "ABC International School",
    organization_details: str = "A modern school with 500 students, focusing on technology and innovation. We have state-of-the-art facilities including computer labs, science laboratories, and a library.",
    role_title: str = "Technology Teacher",
    question: str = "What do you teach and what facilities do you have?"
):
    """Test detailed role play responses"""
    try:
        log.info(f"Testing detailed role play: org={organization_name}, role={role_title}")
        
        # Create mock SessionMemory for testing
        class MockMemory:
            def __init__(self):
                self.client_id = client_id
                self.role_play_enabled = True
                self.role_play_template = "school"
                self.organization_name = organization_name
                self.organization_details = organization_details
                self.role_title = role_title
                self.language = "en"
                self.level = "medium"
                self.history = []
        
        mock_mem = MockMemory()
        
        # Test the detailed role play response
        result = await llm_reply(question, mock_mem)
        
        return {
            "client_id": client_id,
            "organization_name": organization_name,
            "role_title": role_title,
            "question": question,
            "detailed_response": result,
            "response_length": len(result),
            "word_count": len(result.split()),
            "status": "success"
        }
    except Exception as e:
        log_exception("test_roleplay_detailed", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/tts/info")
async def get_xtts_info():
    """Get XTTS system information"""
    try:
        info = await xtts_wrapper.get_info_async()
        return {
            "tts_system": "XTTS (Coqui TTS)",
            "info": info,
            "status": "success"
        }
    except Exception as e:
        log_exception("get_xtts_info", e)
        return JSONResponse({"error": str(e)}, status_code=500)

# ===================== XTTS API Endpoints =====================
@app.get("/tts/models")
async def list_xtts_models():
    """List available XTTS models"""
    try:
        models = xtts_wrapper.manager.list_available_models()
        return {
            "available_models": models,
            "total_count": len(models),
            "status": "success"
        }
    except Exception as e:
        log_exception("list_xtts_models", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/tts/load-model")
async def load_xtts_model(model_name: str):
    """Load a specific XTTS model"""
    try:
        success = await xtts_wrapper.initialize()
        if success:
            return {
                "message": f"XTTS model loaded successfully: {model_name}",
                "model_name": model_name,
                "status": "success"
            }
        else:
            return JSONResponse({"error": f"Failed to load XTTS model: {model_name}"}, status_code=500)
    except Exception as e:
        log_exception("load_xtts_model", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/tts/set-language")
async def set_xtts_language(language: str):
    """Set XTTS synthesis language"""
    try:
        success = await xtts_wrapper.set_language_async(language)
        if success:
            return {
                "message": f"Language set to: {language}",
                "language": language,
                "status": "success"
            }
        else:
            return JSONResponse({"error": f"Unsupported language: {language}"}, status_code=400)
    except Exception as e:
        log_exception("set_xtts_language", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/tts/set-speaker")
async def set_xtts_speaker(speaker_wav_path: str):
    """Set XTTS speaker reference file"""
    try:
        success = await xtts_wrapper.set_speaker_async(speaker_wav_path)
        if success:
            return {
                "message": f"Speaker set to: {speaker_wav_path}",
                "speaker_wav": speaker_wav_path,
                "status": "success"
            }
        else:
            return JSONResponse({"error": f"Invalid speaker file: {speaker_wav_path}"}, status_code=400)
    except Exception as e:
        log_exception("set_xtts_speaker", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/tts/set-params")
async def set_xtts_params(params: dict):
    """Set XTTS synthesis parameters"""
    try:
        success = await xtts_wrapper.update_params_async(**params)
        if success:
            return {
                "message": "Synthesis parameters updated",
                "parameters": params,
                "status": "success"
            }
        else:
            return JSONResponse({"error": "Invalid parameters"}, status_code=400)
    except Exception as e:
        log_exception("set_xtts_params", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/tts/synthesize")
async def synthesize_text_xtts(request: dict):
    """Synthesize text to speech using XTTS"""
    try:
        text = request.get("text", "")
        language = request.get("language", "en")
        speaker_wav = request.get("speaker_wav", None)
        
        if not text:
            return JSONResponse({"error": "Text is required"}, status_code=400)
        
        audio_bytes = await xtts_wrapper.synthesize_async(text, language, speaker_wav)
        
        if not audio_bytes:
            return JSONResponse({"error": "Failed to synthesize audio"}, status_code=500)
        
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename=synthesized.wav"}
        )
        
    except Exception as e:
        log_exception("synthesize_text_xtts", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/health")
async def health_check():
    """Main application health check"""
    try:
        return {
            "status": "healthy",
            "service": "SHCI Voice Assistant",
            "version": "1.0.0",
            "timestamp": time.time()
        }
    except Exception as e:
        log_exception("health_check", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/tts/health")
async def xtts_health_check():
    """XTTS system health check"""
    try:
        health = await xtts_wrapper.health_check_async()
        return health
    except Exception as e:
        log_exception("xtts_health_check", e)
        return JSONResponse({"error": str(e)}, status_code=500)

# ===================== Organization Management =====================
@app.post("/api/organizations")
async def create_organization(request: dict):
    """Create a new organization"""
    try:
        name = request.get("name", "").strip()
        details = request.get("details", "").strip()
        
        if not name:
            return JSONResponse({"error": "Organization name is required"}, status_code=400)
        
        result = organization_db.create_organization(name, details)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Organization created successfully",
                "organization": result["organization"]
            }
        else:
            return JSONResponse({"error": result["error"]}, status_code=400)
            
    except Exception as e:
        log_exception("create_organization", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/organizations/{name}")
async def get_organization(name: str):
    """Get organization by name"""
    try:
        org = organization_db.get_organization(name)
        if org:
            return {"success": True, "organization": org}
        else:
            return JSONResponse({"error": "Organization not found"}, status_code=404)
            
    except Exception as e:
        log_exception("get_organization", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/organizations/by-id/{org_id}")
async def get_organization_by_id(org_id: int):
    """Get organization by ID"""
    try:
        org = organization_db.get_organization_by_id(org_id)
        if org:
            return {"success": True, "organization": org}
        else:
            return JSONResponse({"error": "Organization not found"}, status_code=404)
            
    except Exception as e:
        log_exception("get_organization_by_id", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/organizations")
async def list_organizations(limit: int = 100, offset: int = 0):
    """List all organizations with pagination"""
    try:
        orgs = organization_db.get_all_organizations(limit, offset)
        stats = organization_db.get_organization_stats()
        
        return {
            "success": True,
            "organizations": orgs,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": stats.get("total_organizations", 0)
            },
            "stats": stats
        }
        
    except Exception as e:
        log_exception("list_organizations", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.put("/api/organizations/{org_id}")
async def update_organization(org_id: int, request: dict):
    """Update organization details"""
    try:
        name = request.get("name")
        details = request.get("details")
        
        result = organization_db.update_organization(org_id, name, details)
        
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            return JSONResponse({"error": result["error"]}, status_code=400)
            
    except Exception as e:
        log_exception("update_organization", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/api/organizations/{org_id}")
async def delete_organization(org_id: int):
    """Delete organization by ID"""
    try:
        result = organization_db.delete_organization(org_id)
        
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            return JSONResponse({"error": result["error"]}, status_code=400)
            
    except Exception as e:
        log_exception("delete_organization", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/organizations/check/{name}")
async def check_organization_exists(name: str):
    """Check if organization name exists"""
    try:
        exists = organization_db.organization_exists(name)
        return {
            "success": True,
            "name": name,
            "exists": exists,
            "message": "Organization name already exists" if exists else "Organization name is available"
        }
        
    except Exception as e:
        log_exception("check_organization_exists", e)
        return JSONResponse({"error": str(e)}, status_code=500)

# ===================== WebSocket =====================
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    conn_id = uuid.uuid4().hex[:8]
    log.info(f"[{conn_id}] 🔌 NEW CLIENT CONNECTED - WebSocket established")

    mem = SessionMemory(language=DEFAULT_LANGUAGE)
    server_tts_enabled = True
    mem_store: Optional[MemoryStore] = None

    try:
        intro_text = LANGUAGES[mem.language]["intro_line"]
        # Introও এখন লেভেলের সাথে মিলিয়ে enforce (যদি ফ্রন্টে লেভেল সেট করে পাঠায় পরে, intro ততক্ষণ generic)
        await send_json(ws, {"type": "ai_text", "text": intro_text})
        mem.add_history("assistant", intro_text)
        mem.greeted = True
    except Exception as e:
        log_exception(f"[{conn_id}] intro_send", e)

    # vad = webrtcvad.Vad(VAD_AGGR)  # Removed - using WebkitSpeechRecognition instead
    pre_buffer: Deque[bytes] = deque(maxlen=int(900 / FRAME_MS))  # 900ms pre-roll
    triggered = False
    voiced_frames: Deque[bytes] = deque()
    voiced_count = 0
    silence_count = 0
    utter_frames = 0

    try:
        while True:
            msg = await ws.receive()

            # ---------- control messages (JSON text) ----------
            if msg["type"] == "websocket.receive" and msg.get("text") is not None:
                try:
                    data = json.loads(msg["text"])
                    typ = data.get("type")
                    log.info(f"[{conn_id}] 📨 Received WebSocket message: {typ}")
                    if typ == "final_transcript":
                        log.info(f"[{conn_id}] 🎤 FINAL_TRANSCRIPT MESSAGE RECEIVED: {data}")
                    elif typ == "client_prefs":
                        log.info(f"[{conn_id}] ⚙️ CLIENT_PREFS MESSAGE RECEIVED: {data}")
                    else:
                        log.debug(f"[{conn_id}] 📨 Message data: {data}")
                    if typ == "client_prefs":
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
                        log.info(f"[{conn_id}] Loaded role play config for {cid}")
                        
                        # If role play is enabled in DB, ensure memory reflects it
                        db_config = roleplay_db.get_role_play_config(cid)
                        if db_config and db_config['role_play_enabled']:
                            mem.role_play_enabled = True
                            mem.role_play_template = db_config['role_play_template']
                            mem.organization_name = db_config['organization_name']
                            mem.organization_details = db_config['organization_details']
                            mem.role_title = db_config['role_title']
                            log.info(f"[{conn_id}] Force-enabled role play from DB: org='{mem.organization_name}', role='{mem.role_title}'")

                        if "language" in data:
                            new_language = data["language"]
                            if new_language in LANGUAGES and new_language != mem.language:
                                mem.language = new_language
                                changed = True
                                log.info(f"[{conn_id}] Language={new_language}")

                        if "use_local_tts" in data:
                            server_tts_enabled = not data["use_local_tts"]
                            log.info(f"[{conn_id}] Server TTS: {'enabled' if server_tts_enabled else 'disabled'}")

                        if "level" in data:
                            new_level = data["level"]
                            if new_level in ("starter", "medium", "advanced") and new_level != mem.level:
                                old_level = mem.level
                                mem.level = new_level
                                mem._recent_level_change_ts = time.time()
                                # Context isolation: keep last few turns only
                                if len(mem.history) > 8:
                                    mem.history = mem.history[-8:]
                                # Add a system breadcrumb so the model sees the change
                                mem.history.append({"role": "system", "content": f"[style level changed from {old_level} to {mem.level}]"})
                                log.info(f"[{conn_id}] Level changed: {old_level} → {mem.level}")
                                await send_json(ws, {"type": "level_changed", "level": mem.level})
                                changed = True
                            elif new_level not in ("starter", "medium", "advanced"):
                                log.warning(f"[{conn_id}] Invalid level: {new_level}")
                        
                        # Handle RAG context for organization-based RAG
                        if "rag_context" in data:
                            rag_context = data["rag_context"]
                            log.info(f"[{conn_id}] 🔍 STEP 12: Received rag_context from frontend")
                            log.info(f"[{conn_id}] 🔍 STEP 12a: RAG context content: {rag_context[:200]}...")
                            log.info(f"[{conn_id}] 🔍 STEP 12b: RAG context length: {len(rag_context)}")
                            log.info(f"[{conn_id}] 🔍 STEP 12c: Current mem.rag_context: {mem.rag_context[:200]}...")
                            
                            if rag_context and rag_context != mem.rag_context:
                                mem.rag_context = rag_context
                                log.info(f"[{conn_id}] 🔍 STEP 13: RAG context updated successfully!")
                                log.info(f"[{conn_id}] 🔍 STEP 13a: New RAG context length: {len(rag_context)}")
                                
                                # Try to extract organization name from RAG context
                                organizations = organization_db.get_all_organizations(limit=50)
                                for org in organizations:
                                    if org['name'].lower() in rag_context.lower():
                                        mem.organization_name = org['name']
                                        log.info(f"[{conn_id}] 🔍 STEP 13b: Extracted organization name: '{org['name']}'")
                                        break
                                
                                changed = True
                            else:
                                log.info(f"[{conn_id}] 🔍 STEP 13: RAG context unchanged or empty")
                        
                        # Handle direct organization name setting
                        if "organization_name" in data:
                            org_name = data["organization_name"]
                            log.info(f"[{conn_id}] 🔍 STEP 14: Received organization_name from frontend: '{org_name}'")
                            
                            if org_name and org_name != mem.organization_name:
                                mem.organization_name = org_name
                                log.info(f"[{conn_id}] 🔍 STEP 15: Organization name updated to: '{org_name}'")
                                changed = True
                        
                        # Real-time TTS streaming commands
                        elif typ == "start_tts_stream":
                            text = data.get("text", "")
                            language = data.get("language", mem.language)
                            speaker_wav = data.get("speaker_wav", None)
                            stream_id = data.get("stream_id", str(uuid.uuid4()))
                            
                            if text.strip():
                                success = await start_tts_stream(ws, stream_id, text, language, speaker_wav, conn_id)
                                await send_json(ws, {
                                    "type": "tts_stream_response",
                                    "stream_id": stream_id,
                                    "success": success,
                                    "message": "TTS stream started" if success else "Failed to start TTS stream"
                                })
                            else:
                                await send_json(ws, {
                                    "type": "tts_stream_response",
                                    "stream_id": stream_id,
                                    "success": False,
                                    "message": "Empty text provided"
                                })
                        
                        elif typ == "stop_tts_stream":
                            stream_id = data.get("stream_id")
                            if stream_id:
                                success = await stop_tts_stream(stream_id, conn_id)
                                await send_json(ws, {
                                    "type": "tts_stream_response",
                                    "stream_id": stream_id,
                                    "success": success,
                                    "message": "TTS stream stopped" if success else "Failed to stop TTS stream"
                                })
                        
                        elif typ == "get_streaming_stats":
                            stats = get_streaming_stats()
                            await send_json(ws, {
                                "type": "streaming_stats",
                                "stats": stats
                            })

                        # Send role play status updates AFTER processing all role play fields
                        if any(key in data for key in ["role_play_enabled", "role_play_template", "organization_name", "organization_details", "role_title"]):
                            # Wait a bit to ensure all fields are processed
                            await asyncio.sleep(0.1)
                            await send_json(ws, {
                                "type": "role_play_updated",
                                "enabled": mem.role_play_enabled,
                                "template": mem.role_play_template,
                                "organization_name": mem.organization_name,
                                "role_title": mem.role_title
                            })
                            log.info(f"[{conn_id}] Sent role play update: enabled={mem.role_play_enabled}, org={mem.organization_name}")

                        # Role play settings - Update memory first
                        if "role_play_enabled" in data:
                            mem.role_play_enabled = data["role_play_enabled"]
                            changed = True
                            log.info(f"[{conn_id}] Role play {'enabled' if mem.role_play_enabled else 'disabled'}")

                        if "role_play_template" in data:
                            new_template = data["role_play_template"]
                            if new_template in ROLE_PLAY_TEMPLATES:
                                mem.role_play_template = new_template
                                changed = True
                                log.info(f"[{conn_id}] Role play template: {mem.role_play_template}")

                        if "organization_name" in data:
                            mem.organization_name = data["organization_name"]
                            changed = True
                            log.info(f"[{conn_id}] Organization: {mem.organization_name}")

                        if "organization_details" in data:
                            mem.organization_details = data["organization_details"]
                            changed = True
                            log.info(f"[{conn_id}] Organization details updated")

                        if "role_title" in data:
                            mem.role_title = data["role_title"]
                            changed = True
                            log.info(f"[{conn_id}] Role title: {mem.role_title}")
                        
                        # Save role play config to database when any role play field changes
                        if any(key in data for key in ["role_play_enabled", "role_play_template", "organization_name", "organization_details", "role_title"]):
                            if mem.client_id:
                                mem.save_role_play_to_db(mem.client_id)
                                log.info(f"[{conn_id}] Saved role play config to DB: enabled={mem.role_play_enabled}, org={mem.organization_name}, role={mem.role_title}")

                        # Debug: Log all role play data received
                        if any(key in data for key in ["role_play_enabled", "role_play_template", "organization_name", "organization_details", "role_title"]):
                            log.info(f"[{conn_id}] Role play data received: enabled={data.get('role_play_enabled')}, template={data.get('role_play_template')}, org={data.get('organization_name')}, role={data.get('role_title')}")
                            log.info(f"[{conn_id}] Current mem state: enabled={mem.role_play_enabled}, template={mem.role_play_template}, org={mem.organization_name}, role={mem.role_title}")
                            
                            # Log the exact data being saved to DB
                            db_config = {
                                'role_play_enabled': mem.role_play_enabled,
                                'role_play_template': mem.role_play_template,
                                'organization_name': mem.organization_name,
                                'organization_details': mem.organization_details,
                                'role_title': mem.role_title
                            }
                            log.info(f"[{conn_id}] Saving to DB: {db_config}")

                        if mem_store and changed:
                            mem_store.save(mem)

                    elif typ == "tts_request":
                        try:
                            text = data.get("text", "")
                            if text:
                                log.info(f"[{conn_id}] XTTS request: {text[:60]}...")
                                async with TTS_SEM:
                                    audio = await tts_bytes_async(text, mem.language)
                                b64 = base64.b64encode(audio).decode("utf-8")
                                # XTTS uses WAV format
                                audio_format = "wav"
                                
                                await send_json(ws, {
                                    "type": "ai_audio", 
                                    "audio_base64": b64,
                                    "audio_format": audio_format
                                })
                        except Exception as e:
                            log_exception(f"[{conn_id}] tts_request", e)
                            await send_json(ws, {"type": "error", "message": "TTS generation failed"})
                    
                    elif typ == "clear_roleplay":
                            try:
                                if mem.client_id:
                                    success = roleplay_db.clear_role_play_config(mem.client_id)
                                    if success:
                                        # Clear memory state
                                        mem.role_play_enabled = False
                                        mem.organization_name = ""
                                        mem.organization_details = ""
                                        mem.role_title = ""
                                        
                                        # Send confirmation
                                        await send_json(ws, {
                                            "type": "role_play_cleared",
                                            "success": True,
                                            "message": "Role play cleared successfully"
                                        })
                                        
                                        log.info(f"[{conn_id}] Role play cleared for client: {mem.client_id}")
                                    else:
                                        await send_json(ws, {
                                            "type": "role_play_cleared",
                                            "success": False,
                                            "message": "Failed to clear role play"
                                        })
                                else:
                                    await send_json(ws, {
                                        "type": "role_play_cleared",
                                        "success": False,
                                        "message": "No client ID available"
                                    })
                            except Exception as e:
                                log_exception(f"[{conn_id}] clear_roleplay", e)
                                await send_json(ws, {"type": "error", "message": "Failed to clear role play"})
                        
                    elif typ == "get_roleplay_state":
                        try:
                            log.info(f"[{conn_id}] Received get_roleplay_state request")
                            if mem.client_id:
                                # Get latest state from database
                                db_config = roleplay_db.get_role_play_config(mem.client_id)
                                log.info(f"[{conn_id}] Database config for {mem.client_id}: {db_config}")
                                
                                if db_config:
                                    # Update memory with DB state
                                    mem.role_play_enabled = bool(db_config.get('role_play_enabled', False))
                                    mem.role_play_template = db_config.get('role_play_template', 'school')
                                    mem.organization_name = db_config.get('organization_name', '')
                                    mem.organization_details = db_config.get('organization_details', '')
                                    mem.role_title = db_config.get('role_title', '')
                                    
                                    log.info(f"[{conn_id}] Updated memory: enabled={mem.role_play_enabled}, org='{mem.organization_name}', role='{mem.role_title}'")
                                    
                                    # Send current state to frontend
                                    response_data = {
                                        "type": "role_play_updated",
                                        "enabled": mem.role_play_enabled,
                                        "template": mem.role_play_template,
                                        "organization_name": mem.organization_name,
                                        "organization_details": mem.organization_details,
                                        "role_title": mem.role_title
                                    }
                                    
                                    await send_json(ws, response_data)
                                    log.info(f"[{conn_id}] Sent role play state to frontend: {response_data}")
                                else:
                                    # No config found, send disabled state
                                    log.info(f"[{conn_id}] No role play config found for client {mem.client_id}")
                                    await send_json(ws, {
                                        "type": "role_play_updated",
                                        "enabled": False,
                                        "template": "school",
                                        "organization_name": "",
                                        "organization_details": "",
                                        "role_title": ""
                                    })
                            else:
                                log.warning(f"[{conn_id}] No client ID available for get_roleplay_state")
                                await send_json(ws, {"type": "error", "message": "No client ID available"})
                        except Exception as e:
                            log_exception(f"[{conn_id}] get_roleplay_state", e)
                            await send_json(ws, {"type": "error", "message": "Failed to get role play state"})

                    elif typ == "remember":
                        k = (data.get("key") or "").strip()
                        v = data.get("value")
                        if k:
                            mem.facts[k] = v
                            if mem_store: mem_store.save(mem)
                            ack = {"en": f"Got it. I’ll remember {k}.", "it": f"Fatto. Ricorderò {k}."}.get(mem.language)
                            await send_json(ws, {"type": "ai_text", "text": enforce_level_style(ack, mem.level)})
                            mem.add_history("assistant", ack)

                    elif typ == "final_transcript":
                        # Handle text from WebkitSpeechRecognition
                        text = data.get("text", "").strip()
                        log.info(f"[{conn_id}] 🎤 PROCESSING FINAL_TRANSCRIPT: '{text}'")
                        log.info(f"[{conn_id}] 📝 Full message data: {data}")
                        
                        if text:
                            log.info(f"[{conn_id}] ✅ Valid transcript received: '{text[:60]}...'")
                            
                            # Process the text with AI
                            async def process_text():
                                try:
                                    log.info(f"[{conn_id}] 🤖 Starting LLM processing for: '{text[:60]}...'")
                                    log.info(f"[{conn_id}] 📊 Memory state: level={mem.level}, language={mem.language}")
                                    log.info(f"[{conn_id}] 🔍 STEP 16: About to call LLM with RAG context")
                                    log.info(f"[{conn_id}] 🔍 STEP 16a: mem.rag_context length: {len(mem.rag_context)}")
                                    log.info(f"[{conn_id}] 🔍 STEP 16b: mem.organization_name: {mem.organization_name}")
                                    
                                    ai_text = await llm_reply(text, mem)
                                    if not ai_text:
                                        log.warning(f"[{conn_id}] ❌ LLM returned empty response")
                                        return
                                    
                                    log.info(f"[{conn_id}] ✅ LLM response received: '{ai_text[:60]}...'")
                                    log.info(f"[{conn_id}] 🔍 STEP 17: Full LLM response: {ai_text}")
                                    log.info(f"[{conn_id}] 🔍 STEP 17a: Response length: {len(ai_text)}")
                                    
                                    # Direct LLM response with level enforcement
                                    corrected_ai_text = enforce_level_style(ai_text, mem.level)
                                    log.info(f"[{conn_id}] 🎯 Level {mem.level} enforced: '{ai_text[:60]}...' → '{corrected_ai_text[:60]}...'")

                                    # Separate grammar correction from TTS text
                                    tts_text = corrected_ai_text
                                    if "🔴 GRAMMAR_CORRECTION_START 🔴" in corrected_ai_text:
                                        # Extract only the LLM answer part for TTS (after grammar correction end)
                                        end_marker = "🔴 GRAMMAR_CORRECTION_END 🔴"
                                        if end_marker in corrected_ai_text:
                                            tts_text = corrected_ai_text.split(end_marker)[1].strip()
                                            # Clean up the TTS text
                                            tts_lines = [line.strip() for line in tts_text.split('\n') if line.strip()]
                                            tts_text = ' '.join(tts_lines)
                                        else:
                                            # Fallback: remove grammar correction markers
                                            tts_text = corrected_ai_text.replace("🔴 GRAMMAR_CORRECTION_START 🔴", "").replace("🔴 GRAMMAR_CORRECTION_END 🔴", "").strip()
                                    
                                    log.info(f"[{conn_id}] 📤 Sending AI response to frontend: '{corrected_ai_text[:60]}...'")
                                    await send_json(ws, {"type": "ai_text", "text": corrected_ai_text})
                                    mem.add_history("assistant", corrected_ai_text)
                                    log.info(f"[{conn_id}] ✅ AI response sent successfully")

                                    if server_tts_enabled:
                                        try:
                                            async with TTS_SEM:
                                                log.info(f"[{conn_id}] 🔊 TTS text (grammar correction removed): '{tts_text[:60]}...'")
                                                audio = await tts_bytes_async(tts_text, mem.language)
                                                
                                                if audio:
                                                    b64 = base64.b64encode(audio).decode("utf-8")
                                                    audio_format = "wav"
                                                    
                                                    await send_json(ws, {
                                                        "type": "ai_audio",
                                                        "id": str(uuid.uuid4()),
                                                        "audio_base64": b64,
                                                        "audio_format": audio_format
                                                    })
                                                    log.info(f"[{conn_id}] 🔊 TTS audio sent to frontend")
                                                else:
                                                    log.error(f"[{conn_id}] TTS generation returned no audio.")
                                        except Exception as e:
                                            log_exception(f"[{conn_id}] tts_auto", e)
                                            await send_json(ws, {"type": "error", "message": "TTS generation failed"})

                                    if mem.client_id and mem_store:
                                        mem_store.save(mem)
                                        
                                except Exception as e:
                                    log_exception(f"[{conn_id}] process_text", e)
                                    await send_json(ws, {"type": "error", "message": "Text processing failed"})
                            
                            asyncio.create_task(process_text())
                        else:
                            log.warning(f"[{conn_id}] ❌ Empty or invalid transcript received: '{text}'")

                    elif typ == "ping":
                        await send_json(ws, {"type": "pong"})
                except Exception as e:
                    log_exception(f"[{conn_id}] text_parse", e)
                continue

            # ---------- binary audio frames ----------
            if msg["type"] == "websocket.receive":
                data = msg.get("bytes", None)
                if data is None:
                    continue

                usable = len(data) - (len(data) % BYTES_PER_FRAME)
                for i in range(0, usable, BYTES_PER_FRAME):
                    frame = data[i: i + BYTES_PER_FRAME]
                    try:
                        is_speech = vad.is_speech(frame, SR)
                    except Exception:
                        continue

                    if not triggered:
                        pre_buffer.append(frame)
                        if is_speech:
                            voiced_count += 1
                            if voiced_count >= TRIGGER_VOICED_FRAMES:
                                triggered = True
                                try:
                                    await send_json(ws, {"type": "stop_audio"})
                                except Exception:
                                    pass
                                voiced_frames.extend(pre_buffer)
                                pre_buffer.clear()
                                voiced_frames.append(frame)
                                utter_frames = len(voiced_frames)
                                voiced_count = 0
                                silence_count = 0
                        else:
                            voiced_count = 0
                    else:
                        voiced_frames.append(frame)
                        utter_frames += 1
                        if is_speech:
                            silence_count = 0
                        else:
                            silence_count += 1

                        end_by_silence = silence_count * FRAME_MS >= END_SILENCE_MS
                        end_by_maxlen  = utter_frames  * FRAME_MS >= MAX_UTTER_MS

                        if end_by_silence or end_by_maxlen:
                            utter_pcm = b"".join(voiced_frames)
                            voiced_frames.clear()
                            silence_count = 0
                            utter_frames = 0
                            triggered = False

                            async def process_utterance(pcm_bytes: bytes):
                                utt_id = uuid.uuid4().hex[:6]
                                dur = pcm_duration_sec(pcm_bytes)
                                rms = pcm16_rms(pcm_bytes)
                                # Audio processing removed - using WebkitSpeechRecognition instead
                                log.info(f"[{conn_id}/{utt_id}] audio chunk received (STT handled by frontend)")
                                # STT is now handled by WebkitSpeechRecognition in the frontend
                                # No backend transcription needed
                                return

                                # Audio processing removed - STT handled by frontend WebkitSpeechRecognition
                                # No backend processing needed

            elif False:  # final_transcript moved to JSON text message handling
                # Handle text from WebkitSpeechRecognition
                text = msg.get("text", "").strip()
                log.info(f"[{conn_id}] 🎤 PROCESSING FINAL_TRANSCRIPT: '{text}'")
                log.info(f"[{conn_id}] 📝 Full message data: {msg}")
                
                if text:
                    log.info(f"[{conn_id}] ✅ Valid transcript received: '{text[:60]}...'")
                    
                    # Process the text with AI
                    async def process_text():
                        try:
                            log.info(f"[{conn_id}] 🤖 Starting LLM processing for: '{text[:60]}...'")
                            log.info(f"[{conn_id}] 📊 Memory state: level={mem.level}, language={mem.language}")
                            
                            ai_text = await llm_reply(text, mem)
                            if not ai_text:
                                log.warning(f"[{conn_id}] ❌ LLM returned empty response")
                                return
                            
                            log.info(f"[{conn_id}] ✅ LLM response received: '{ai_text[:60]}...'")
                            
                            # Direct LLM response with level enforcement
                            corrected_ai_text = enforce_level_style(ai_text, mem.level)
                            log.info(f"[{conn_id}] 🎯 Level {mem.level} enforced: '{ai_text[:60]}...' → '{corrected_ai_text[:60]}...'")

                            log.info(f"[{conn_id}] 📤 Sending AI response to frontend: '{corrected_ai_text[:60]}...'")
                            await send_json(ws, {"type": "ai_text", "text": corrected_ai_text})
                            mem.add_history("assistant", corrected_ai_text)
                            log.info(f"[{conn_id}] ✅ AI response sent successfully")

                            if server_tts_enabled:
                                try:
                                    async with TTS_SEM:
                                        audio = await tts_bytes_async(corrected_ai_text, mem.language)
                                        
                                        if audio:
                                            b64 = base64.b64encode(audio).decode("utf-8")
                                            audio_format = "wav"
                                            
                                            await send_json(ws, {
                                                "type": "ai_audio",
                                                "id": str(uuid.uuid4()),
                                                "audio_base64": b64,
                                                "audio_format": audio_format
                                            })
                                        else:
                                            log.error(f"[{conn_id}] TTS generation returned no audio.")
                                except Exception as e:
                                    log_exception(f"[{conn_id}] tts_auto", e)
                                    await send_json(ws, {"type": "error", "message": "TTS generation failed"})

                            if mem.client_id and mem_store:
                                mem_store.save(mem)
                                
                        except Exception as e:
                            log_exception(f"[{conn_id}] process_text", e)
                            await send_json(ws, {"type": "error", "message": "Text processing failed"})
                    
                    asyncio.create_task(process_text())
                else:
                    log.warning(f"[{conn_id}] ❌ Empty or invalid transcript received: '{text}'")

            elif msg["type"] == "websocket.disconnect":
                raise WebSocketDisconnect()

    except WebSocketDisconnect:
        log.info(f"[{conn_id}] 🔌 Client disconnected")
    except Exception as e:
        log_exception(f"[{conn_id}] WS loop", e)
    finally:
        try:
            await ws.close()
        except Exception:
            pass
        try:
            if mem.client_id and mem_store:
                mem_store.save(mem)
        except Exception as e:
            log_exception(f"[{conn_id}] mem_save_on_close", e)
        log.info(f"[{conn_id}] Connection closed")

@app.get("/api/test-grammar")
async def test_grammar():
    """Test grammar correction format"""
    test_text = "what your name"
    
    # Create a test memory
    test_mem = SessionMemory("en")
    test_mem.level = "starter"
    
    # Test the LLM response
    try:
        ai_response = await llm_reply(test_text, test_mem)
        return {
            "input": test_text,
            "ai_response": ai_response,
            "has_grammar_correction": "🔴 GRAMMAR_CORRECTION_START 🔴" in ai_response,
            "has_incorrect": "INCORRECT:" in ai_response,
            "has_correct": "CORRECT:" in ai_response
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

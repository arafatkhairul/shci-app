"""
Application Configuration Settings
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings and configuration"""
    
    # ---- Application Environment ----
    TTS_ENVIRONMENT = os.getenv("TTS_ENVIRONMENT", "local").lower()
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    NODE_ENV = os.getenv("NODE_ENV", "development").lower()
    
    # ---- LLM Configuration ----
    LLM_API_URL = os.getenv("LLM_API_URL", "http://69.197.183.130:11434/v1/chat/completions").strip()
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-14b-gpu").strip()
    LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60.0"))
    LLM_RETRIES = int(os.getenv("LLM_RETRIES", "1"))
    
    # ---- TTS System Configuration ----
    TTS_SYSTEM = os.getenv("TTS_SYSTEM", "piper").lower()
    
    # ---- Piper TTS Configuration ----
    PIPER_MODEL_NAME = os.getenv("PIPER_MODEL_NAME", "en_US-libritts-high").strip()
    PIPER_LENGTH_SCALE = float(os.getenv("PIPER_LENGTH_SCALE", "1.5"))
    PIPER_NOISE_SCALE = float(os.getenv("PIPER_NOISE_SCALE", "1.0"))
    PIPER_NOISE_W = float(os.getenv("PIPER_NOISE_W", "0.8"))
    
    # ---- Audio Configuration ----
    SR = 16000
    FRAME_MS = 30
    SAMPLES_PER_FRAME = SR * FRAME_MS // 1000
    BYTES_PER_FRAME = SAMPLES_PER_FRAME * 2
    
    # ---- Voice Activity Detection (VAD) Configuration ----
    TRIGGER_VOICED_FRAMES = int(os.getenv("TRIGGER_VOICED_FRAMES", "2"))
    END_SILENCE_MS = int(os.getenv("END_SILENCE_MS", "250"))
    MAX_UTTER_MS = int(os.getenv("MAX_UTTER_MS", "7000"))
    
    # ---- Database Configuration ----
    DB_PATH = os.getenv("DB_PATH", "roleplay.db")
    
    # ---- Assistant Configuration ----
    ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Self Hosted Conversational Interface")
    ASSISTANT_AUTHOR = os.getenv("ASSISTANT_AUTHOR", "NZR DEV")
    
    # ---- Default Language Configuration ----
    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")

# Create global settings instance
settings = Settings()


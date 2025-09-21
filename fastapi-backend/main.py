"""
Main FastAPI Application
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid
import json
import asyncio
from collections import deque
from typing import Optional

from app.config.settings import settings
from app.config.languages import LANGUAGES, DEFAULT_LANGUAGE
from app.utils.logger import get_logger, log_exception
from app.models.session_memory import SessionMemory, MemoryStore
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.services.database_service import DatabaseService
from app.api.endpoints import router as endpoints_router
from app.api.websocket.chat_handler import ChatHandler

# Initialize logger
log = get_logger("main")

# Create FastAPI app
app = FastAPI(
    title="SHCI Voice Agent API",
    description="Self-Hosted Conversational Interface with Voice Agent",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(endpoints_router)

# Initialize services
llm_service = LLMService()
tts_service = TTSService()
db_service = DatabaseService()

# Initialize chat handler
chat_handler = ChatHandler(llm_service, tts_service, db_service)

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    log.info(f"🚀 Starting SHCI Voice Agent API")
    log.info(f"🔧 Environment: {settings.ENVIRONMENT}")
    log.info(f"🤖 LLM: {settings.LLM_API_URL} (model={settings.LLM_MODEL})")
    log.info(f"👤 Assistant: {settings.ASSISTANT_NAME} by {settings.ASSISTANT_AUTHOR}")
    log.info(f"🎤 VAD: trigger={settings.TRIGGER_VOICED_FRAMES}, silence={settings.END_SILENCE_MS}ms")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    log.info("🛑 Shutting down SHCI Voice Agent API")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat"""
    await chat_handler.handle_websocket(websocket)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SHCI Voice Agent API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "assistant": settings.ASSISTANT_NAME
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

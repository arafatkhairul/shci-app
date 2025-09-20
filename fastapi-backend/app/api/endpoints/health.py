"""
Health Check Endpoints
"""
from fastapi import APIRouter
from app.config.settings import settings
from app.utils.logger import get_logger
from app.services.llm_service import LLMService

log = get_logger("health_endpoints")
router = APIRouter()

@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "tts_system": settings.TTS_SYSTEM
    }

@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with system info"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "tts_system": settings.TTS_SYSTEM,
        "llm_model": settings.LLM_MODEL,
        "piper_model": settings.PIPER_MODEL_NAME,
        "database_path": settings.DB_PATH
    }

@router.get("/test-grammar")
async def test_grammar_correction():
    """Test grammar correction functionality"""
    try:
        # Test with a grammatically incorrect sentence
        test_input = "what your name"
        
        # Create LLM service
        llm_service = LLMService()
        
        # Create test messages with grammar correction prompt
        grammar_prompt = """IMPORTANT: If the user's input contains grammatical errors, spelling mistakes, or unclear language, respond in this EXACT format:

GRAMMAR_CORRECTION_START
INCORRECT: [exactly what the user said]
CORRECT: [the grammatically correct version]
GRAMMAR_CORRECTION_END

Then provide your normal response to their question.

EXAMPLE:
User says: "what your name"
You respond:
GRAMMAR_CORRECTION_START
INCORRECT: what your name
CORRECT: What is your name?
GRAMMAR_CORRECTION_END

My name is SHCI. How can I help you?

If the input is grammatically correct, respond normally without any grammar correction."""
        
        messages = [
            {"role": "system", "content": "You are a helpful voice assistant."},
            {"role": "system", "content": grammar_prompt},
            {"role": "user", "content": test_input}
        ]
        
        # Get response
        response = await llm_service.generate_response(messages)
        
        # Check if grammar correction is present
        has_grammar_correction = "GRAMMAR_CORRECTION_START" in response
        has_incorrect = "INCORRECT:" in response
        has_correct = "CORRECT:" in response
        
        return {
            "status": "success",
            "test_input": test_input,
            "ai_response": response,
            "has_grammar_correction": has_grammar_correction,
            "has_incorrect": has_incorrect,
            "has_correct": has_correct,
            "grammar_working": has_grammar_correction and has_incorrect and has_correct
        }
        
    except Exception as e:
        log.error(f"Grammar test error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "grammar_working": False
        }

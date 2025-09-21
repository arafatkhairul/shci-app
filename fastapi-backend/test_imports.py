#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all critical imports"""
    try:
        print("Testing imports...")
        
        # Test app module imports
        from app.models.session_memory import SessionMemory, MemoryStore
        print("✅ app.models.session_memory imported successfully")
        
        from app.config.settings import settings
        print("✅ app.config.settings imported successfully")
        
        from app.utils.logger import get_logger
        print("✅ app.utils.logger imported successfully")
        
        from app.services.llm_service import LLMService
        print("✅ app.services.llm_service imported successfully")
        
        from app.services.tts_service import TTSService
        print("✅ app.services.tts_service imported successfully")
        
        from app.services.database_service import DatabaseService
        print("✅ app.services.database_service imported successfully")
        
        from app.api.endpoints import router as endpoints_router
        print("✅ app.api.endpoints imported successfully")
        
        from app.api.websocket.chat_handler import ChatHandler
        print("✅ app.api.websocket.chat_handler imported successfully")
        
        # Test main app import
        from main import app
        print("✅ main app imported successfully")
        
        print("\n🎉 All imports successful! The application should work correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"Python path: {sys.path}")
        print(f"Current working directory: {os.getcwd()}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

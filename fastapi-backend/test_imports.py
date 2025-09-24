#!/usr/bin/env python3
"""
Test Python imports for production deployment
This script verifies that all required modules can be imported successfully
"""

import sys
import os

def test_imports():
    """Test all critical imports for the application"""
    
    print("Testing Python imports...")
    
    # Add the current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Test FastAPI and related imports
        print("  - Testing FastAPI imports...")
        import fastapi
        import uvicorn
        import aiohttp
        import websockets
        print("    ✅ FastAPI ecosystem imports successful")
        
        # Test TTS related imports
        print("  - Testing TTS imports...")
        import piper
        import soundfile
        import numpy as np
        print("    ✅ TTS imports successful")
        
        # Test ONNX Runtime
        print("  - Testing ONNX Runtime...")
        import onnxruntime
        print("    ✅ ONNX Runtime import successful")
        
        # Test PyTorch (if available)
        print("  - Testing PyTorch...")
        try:
            import torch
            # Check CUDA availability and compatibility
            if torch.cuda.is_available():
                try:
                    # Test CUDA with error handling
                    device = torch.device("cuda")
                    test_tensor = torch.tensor([1.0]).to(device)
                    print("    ✅ PyTorch with CUDA import successful")
                except Exception as cuda_error:
                    print(f"    ⚠️  PyTorch CUDA error (using CPU): {str(cuda_error)[:100]}...")
                    print("    ✅ PyTorch CPU mode available")
            else:
                print("    ✅ PyTorch CPU mode available")
        except ImportError:
            print("    ⚠️  PyTorch not available (optional)")
        
        # Test application specific imports
        print("  - Testing application imports...")
        from tts_factory import synthesize_text
        from app.main import app
        from app.config.settings import Settings
        print("    ✅ Application imports successful")
        
        # Test database imports
        print("  - Testing database imports...")
        import sqlite3
        from app.models.session_memory import SessionMemory
        print("    ✅ Database imports successful")
        
        print("\n🎉 All critical imports successful!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

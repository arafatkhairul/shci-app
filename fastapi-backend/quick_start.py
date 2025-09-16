#!/usr/bin/env python3
"""
Quick Start Script for SHCI Voice Agent
Choose TTS engine and start the application
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import fastapi
        import uvicorn
        print("✅ FastAPI and Uvicorn available")
    except ImportError:
        print("❌ FastAPI/Uvicorn not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]"])
    
    # Check TTS dependencies
    try:
        import piper
        print("✅ Piper TTS available")
    except ImportError:
        print("⚠️ Piper TTS not found. Install with: pip install piper-tts")
    
    try:
        import TTS
        print("✅ Coqui TTS available")
    except ImportError:
        print("⚠️ Coqui TTS not found. Install with: pip install TTS")

def show_startup_options():
    """Show startup options"""
    print("\n🚀 SHCI Voice Agent - Quick Start")
    print("=" * 50)
    print("Choose how to start the application:")
    print()
    print("1. 🎯 Piper TTS (Fast)")
    print("   - Ultra-fast voice synthesis (0.07s)")
    print("   - Low memory usage")
    print("   - Best for real-time applications")
    print()
    print("2. 🌟 Coqui TTS (High Quality)")
    print("   - High-quality voice synthesis")
    print("   - Multiple voice options")
    print("   - Best for quality-focused applications")
    print()
    print("3. 🔄 Integrated TTS (Auto-select)")
    print("   - Automatically chooses best available provider")
    print("   - Fallback system for reliability")
    print("   - Best for production deployment")
    print()
    print("4. ⚙️ Configure TTS (Advanced)")
    print("   - Manual configuration")
    print("   - Custom settings")
    print()

def start_with_piper():
    """Start application with Piper TTS"""
    print("🎯 Starting with Piper TTS...")
    
    # Set environment variable
    os.environ["TTS_SYSTEM"] = "piper"
    
    # Start server
    print("🚀 Starting FastAPI server...")
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])

def start_with_coqui():
    """Start application with Coqui TTS"""
    print("🌟 Starting with Coqui TTS...")
    
    # Set environment variable
    os.environ["TTS_SYSTEM"] = "coqui"
    
    # Start server
    print("🚀 Starting FastAPI server...")
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])

def start_with_integrated():
    """Start application with Integrated TTS"""
    print("🔄 Starting with Integrated TTS...")
    
    # Set environment variable
    os.environ["TTS_SYSTEM"] = "integrated"
    
    # Start server
    print("🚀 Starting FastAPI server...")
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])

def configure_tts():
    """Run TTS configuration"""
    print("⚙️ Running TTS configuration...")
    subprocess.run([sys.executable, "configure_tts.py"])

def test_tts():
    """Test TTS integration"""
    print("🧪 Testing TTS integration...")
    subprocess.run([sys.executable, "test_coqui_integration.py"])

def main():
    """Main function"""
    check_dependencies()
    show_startup_options()
    
    while True:
        choice = input("Select option (1/2/3/4/5): ").strip()
        
        if choice == "1":
            start_with_piper()
            break
        elif choice == "2":
            start_with_coqui()
            break
        elif choice == "3":
            start_with_integrated()
            break
        elif choice == "4":
            configure_tts()
            break
        elif choice == "5":
            test_tts()
            break
        else:
            print("❌ Invalid choice. Please select 1, 2, 3, 4, or 5.")
    
    print("\n🎉 Application started!")
    print("📱 Web interface: http://localhost:8000")
    print("🔗 API docs: http://localhost:8000/docs")
    print("❤️ Health check: http://localhost:8000/health/")

if __name__ == "__main__":
    main()

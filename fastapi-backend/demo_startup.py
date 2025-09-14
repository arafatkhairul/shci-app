#!/usr/bin/env python3
"""
Demo script to show beautiful startup logs
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def demo_startup():
    """Demo the startup process"""
    print("🚀 Starting SHCI Voice Assistant Demo...")
    print("="*60)
    
    try:
        # Import and initialize the app
        from main import app, startup_event
        
        # Run the startup event
        await startup_event()
        
        print("\n🎉 Demo completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_startup())

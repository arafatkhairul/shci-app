#!/usr/bin/env python3
"""
Test script for STT WebSocket endpoint
"""
import asyncio
import websockets
import json
import numpy as np
import wave
import io

async def test_stt_websocket():
    """Test the STT WebSocket endpoint"""
    uri = "ws://localhost:8000/ws/stt"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to STT WebSocket")
            
            # Wait for connection message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 Received: {data}")
            
            if data.get("type") == "status" and data.get("text") == "connected":
                print("✅ STT WebSocket connected")
                
                # Wait for initialization messages
                print("🔄 Waiting for initialization...")
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"📨 Received: {data}")
                    
                    if data.get("type") == "status" and data.get("text") == "ready":
                        print("✅ STT service is ready")
                        break
                    elif data.get("type") == "error":
                        print(f"❌ STT initialization error: {data.get('text')}")
                        return
                
                # Send a ping message
                ping_msg = {"type": "ping"}
                await websocket.send(json.dumps(ping_msg))
                print("📤 Sent ping")
                
                # Wait for pong response
                pong_message = await websocket.recv()
                pong_data = json.loads(pong_message)
                print(f"📨 Received pong: {pong_data}")
                
                # Generate some test audio data (silence)
                sample_rate = 16000
                duration = 1.0  # 1 second
                samples = int(sample_rate * duration)
                
                # Generate silence (zeros)
                audio_data = np.zeros(samples, dtype=np.int16)
                
                # Convert to bytes
                audio_bytes = audio_data.tobytes()
                
                print(f"📤 Sending {len(audio_bytes)} bytes of audio data...")
                await websocket.send(audio_bytes)
                
                # Wait a bit for processing
                await asyncio.sleep(2)
                
                print("✅ STT WebSocket test completed successfully")
            else:
                print(f"❌ Unexpected ready message: {data}")
                
    except Exception as e:
        print(f"❌ Error testing STT WebSocket: {e}")

if __name__ == "__main__":
    print("🧪 Testing STT WebSocket endpoint...")
    asyncio.run(test_stt_websocket())

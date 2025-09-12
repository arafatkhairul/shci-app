#!/usr/bin/env python3
"""
Real-time TTS Streaming Module
Provides real-time text-to-speech streaming capabilities for FastAPI backend.
Based on Coqui TTS with reference audio support.
"""

import asyncio
import logging
import time
import io
import base64
from typing import AsyncGenerator, Optional, Dict, Any
from fastapi import WebSocket
import json

from xtts_manager import xtts_manager

log = logging.getLogger("realtime_tts_streaming")

class RealTimeTTSStreamer:
    """
    Real-time TTS streaming handler for WebSocket connections.
    Provides chunked audio streaming for real-time speech synthesis.
    """
    
    def __init__(self):
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.chunk_size = 1024  # Audio chunk size in bytes
        self.stream_delay = 0.1  # Delay between chunks in seconds
        
    async def start_stream(self, websocket: WebSocket, stream_id: str, text: str, 
                          language: str = "en", speaker_wav: Optional[str] = None) -> bool:
        """
        Start a new TTS stream.
        
        Args:
            websocket: WebSocket connection
            stream_id: Unique stream identifier
            text: Text to synthesize
            language: Language code
            speaker_wav: Optional speaker reference file
            
        Returns:
            bool: True if stream started successfully
        """
        try:
            if stream_id in self.active_streams:
                log.warning(f"Stream {stream_id} already exists")
                return False
            
            # Initialize stream info
            self.active_streams[stream_id] = {
                "websocket": websocket,
                "text": text,
                "language": language,
                "speaker_wav": speaker_wav,
                "start_time": time.time(),
                "status": "starting"
            }
            
            log.info(f"Starting TTS stream {stream_id} for text: '{text[:50]}...'")
            
            # Start streaming in background
            asyncio.create_task(self._stream_audio(stream_id))
            
            return True
            
        except Exception as e:
            log.error(f"Failed to start stream {stream_id}: {e}")
            return False
    
    async def _stream_audio(self, stream_id: str):
        """
        Stream audio chunks to WebSocket.
        
        Args:
            stream_id: Stream identifier
        """
        try:
            stream_info = self.active_streams.get(stream_id)
            if not stream_info:
                log.error(f"Stream {stream_id} not found")
                return
            
            websocket = stream_info["websocket"]
            text = stream_info["text"]
            language = stream_info["language"]
            speaker_wav = stream_info["speaker_wav"]
            
            # Update status
            stream_info["status"] = "synthesizing"
            
            # Send start message
            await websocket.send_text(json.dumps({
                "type": "stream_start",
                "stream_id": stream_id,
                "message": "Starting audio synthesis..."
            }))
            
            # Synthesize audio
            log.info(f"Synthesizing audio for stream {stream_id}")
            audio_data = await asyncio.get_event_loop().run_in_executor(
                None, 
                xtts_manager.synthesize_text, 
                text, 
                language, 
                speaker_wav
            )
            
            if not audio_data:
                log.error(f"Failed to synthesize audio for stream {stream_id}")
                await websocket.send_text(json.dumps({
                    "type": "stream_error",
                    "stream_id": stream_id,
                    "message": "Audio synthesis failed"
                }))
                return
            
            # Update status
            stream_info["status"] = "streaming"
            
            # Send audio info
            await websocket.send_text(json.dumps({
                "type": "audio_info",
                "stream_id": stream_id,
                "audio_size": len(audio_data),
                "sample_rate": xtts_manager.sample_rate,
                "format": "wav"
            }))
            
            # Stream audio in chunks
            total_chunks = len(audio_data) // self.chunk_size + (1 if len(audio_data) % self.chunk_size else 0)
            chunk_index = 0
            
            for i in range(0, len(audio_data), self.chunk_size):
                chunk = audio_data[i:i + self.chunk_size]
                chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                
                # Send audio chunk
                await websocket.send_text(json.dumps({
                    "type": "audio_chunk",
                    "stream_id": stream_id,
                    "chunk_index": chunk_index,
                    "total_chunks": total_chunks,
                    "data": chunk_b64,
                    "is_final": chunk_index == total_chunks - 1
                }))
                
                chunk_index += 1
                
                # Small delay between chunks for real-time feel
                await asyncio.sleep(self.stream_delay)
            
            # Update status
            stream_info["status"] = "completed"
            stream_info["end_time"] = time.time()
            
            # Send completion message
            await websocket.send_text(json.dumps({
                "type": "stream_complete",
                "stream_id": stream_id,
                "message": "Audio streaming completed",
                "duration": stream_info["end_time"] - stream_info["start_time"]
            }))
            
            log.info(f"Stream {stream_id} completed successfully")
            
        except Exception as e:
            log.error(f"Error in stream {stream_id}: {e}")
            stream_info = self.active_streams.get(stream_id)
            if stream_info:
                stream_info["status"] = "error"
                try:
                    await stream_info["websocket"].send_text(json.dumps({
                        "type": "stream_error",
                        "stream_id": stream_id,
                        "message": f"Stream error: {str(e)}"
                    }))
                except:
                    pass
        finally:
            # Clean up stream
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
    
    async def stop_stream(self, stream_id: str) -> bool:
        """
        Stop an active stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            bool: True if stream was stopped
        """
        try:
            if stream_id in self.active_streams:
                stream_info = self.active_streams[stream_id]
                stream_info["status"] = "stopped"
                
                # Send stop message
                await stream_info["websocket"].send_text(json.dumps({
                    "type": "stream_stopped",
                    "stream_id": stream_id,
                    "message": "Stream stopped by user"
                }))
                
                del self.active_streams[stream_id]
                log.info(f"Stream {stream_id} stopped")
                return True
            else:
                log.warning(f"Stream {stream_id} not found")
                return False
                
        except Exception as e:
            log.error(f"Error stopping stream {stream_id}: {e}")
            return False
    
    def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Dict containing stream status or None if not found
        """
        stream_info = self.active_streams.get(stream_id)
        if not stream_info:
            return None
        
        return {
            "stream_id": stream_id,
            "status": stream_info["status"],
            "start_time": stream_info["start_time"],
            "duration": time.time() - stream_info["start_time"] if stream_info["status"] != "completed" else stream_info.get("end_time", 0) - stream_info["start_time"],
            "text": stream_info["text"][:50] + "..." if len(stream_info["text"]) > 50 else stream_info["text"],
            "language": stream_info["language"],
            "speaker_wav": stream_info["speaker_wav"]
        }
    
    def get_all_streams(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all active streams.
        
        Returns:
            Dict containing all stream statuses
        """
        return {
            stream_id: self.get_stream_status(stream_id)
            for stream_id in self.active_streams.keys()
        }
    
    def cleanup_streams(self):
        """Clean up all active streams."""
        try:
            for stream_id in list(self.active_streams.keys()):
                asyncio.create_task(self.stop_stream(stream_id))
            log.info("All streams cleaned up")
        except Exception as e:
            log.error(f"Error cleaning up streams: {e}")

class TTSStreamingManager:
    """
    Manager for multiple TTS streaming instances.
    Provides centralized control and monitoring.
    """
    
    def __init__(self):
        self.streamers: Dict[str, RealTimeTTSStreamer] = {}
        self.max_concurrent_streams = 10
        
    def create_streamer(self, streamer_id: str) -> RealTimeTTSStreamer:
        """
        Create a new TTS streamer instance.
        
        Args:
            streamer_id: Unique streamer identifier
            
        Returns:
            RealTimeTTSStreamer instance
        """
        if streamer_id in self.streamers:
            log.warning(f"Streamer {streamer_id} already exists")
            return self.streamers[streamer_id]
        
        streamer = RealTimeTTSStreamer()
        self.streamers[streamer_id] = streamer
        log.info(f"Created streamer {streamer_id}")
        return streamer
    
    def get_streamer(self, streamer_id: str) -> Optional[RealTimeTTSStreamer]:
        """
        Get an existing streamer instance.
        
        Args:
            streamer_id: Streamer identifier
            
        Returns:
            RealTimeTTSStreamer instance or None
        """
        return self.streamers.get(streamer_id)
    
    def remove_streamer(self, streamer_id: str) -> bool:
        """
        Remove a streamer instance.
        
        Args:
            streamer_id: Streamer identifier
            
        Returns:
            bool: True if streamer was removed
        """
        if streamer_id in self.streamers:
            self.streamers[streamer_id].cleanup_streams()
            del self.streamers[streamer_id]
            log.info(f"Removed streamer {streamer_id}")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get streaming statistics.
        
        Returns:
            Dict containing streaming statistics
        """
        total_streams = sum(len(streamer.active_streams) for streamer in self.streamers.values())
        active_streamers = len(self.streamers)
        
        return {
            "active_streamers": active_streamers,
            "total_active_streams": total_streams,
            "max_concurrent_streams": self.max_concurrent_streams,
            "streamers": {
                streamer_id: {
                    "active_streams": len(streamer.active_streams),
                    "streams": streamer.get_all_streams()
                }
                for streamer_id, streamer in self.streamers.items()
            }
        }
    
    def cleanup_all(self):
        """Clean up all streamers and streams."""
        try:
            for streamer in self.streamers.values():
                streamer.cleanup_streams()
            self.streamers.clear()
            log.info("All streamers cleaned up")
        except Exception as e:
            log.error(f"Error cleaning up streamers: {e}")

# Global streaming manager instance
streaming_manager = TTSStreamingManager()

# Convenience functions
async def start_tts_stream(websocket: WebSocket, stream_id: str, text: str, 
                          language: str = "en", speaker_wav: Optional[str] = None,
                          streamer_id: str = "default") -> bool:
    """
    Start a TTS stream.
    
    Args:
        websocket: WebSocket connection
        stream_id: Unique stream identifier
        text: Text to synthesize
        language: Language code
        speaker_wav: Optional speaker reference file
        streamer_id: Streamer identifier
        
    Returns:
        bool: True if stream started successfully
    """
    streamer = streaming_manager.get_streamer(streamer_id)
    if not streamer:
        streamer = streaming_manager.create_streamer(streamer_id)
    
    return await streamer.start_stream(websocket, stream_id, text, language, speaker_wav)

async def stop_tts_stream(stream_id: str, streamer_id: str = "default") -> bool:
    """
    Stop a TTS stream.
    
    Args:
        stream_id: Stream identifier
        streamer_id: Streamer identifier
        
    Returns:
        bool: True if stream was stopped
    """
    streamer = streaming_manager.get_streamer(streamer_id)
    if not streamer:
        return False
    
    return await streamer.stop_stream(stream_id)

def get_streaming_stats() -> Dict[str, Any]:
    """Get streaming statistics."""
    return streaming_manager.get_stats()

def cleanup_streaming():
    """Clean up all streaming resources."""
    streaming_manager.cleanup_all()

if __name__ == "__main__":
    # Test the streaming system
    print("=== Real-time TTS Streaming Test ===")
    
    # Test streaming manager
    manager = TTSStreamingManager()
    streamer = manager.create_streamer("test_streamer")
    
    print(f"Created streamer: {streamer}")
    print(f"Manager stats: {manager.get_stats()}")
    
    # Cleanup
    manager.cleanup_all()
    print("✅ Streaming system test completed")

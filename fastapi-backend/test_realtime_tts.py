#!/usr/bin/env python3
"""
Real-time TTS Performance Test
Tests the real-time TTS streaming system for performance and reliability.
"""

import asyncio
import time
import json
import base64
import logging
from typing import List, Dict, Any
import websockets
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("realtime_tts_test")

class TTSPerformanceTest:
    """
    Comprehensive performance testing for real-time TTS streaming.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", ws_url: str = "ws://localhost:8000/ws"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.results = []
        
    async def test_websocket_connection(self) -> Dict[str, Any]:
        """Test WebSocket connection and basic functionality."""
        log.info("🔌 Testing WebSocket connection...")
        
        start_time = time.time()
        try:
            async with websockets.connect(self.ws_url) as websocket:
                connection_time = time.time() - start_time
                
                # Send test message
                test_message = {
                    "type": "get_streaming_stats"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                response_time = time.time() - start_time
                
                result = {
                    "test": "websocket_connection",
                    "status": "success",
                    "connection_time": connection_time,
                    "response_time": response_time,
                    "response_type": response_data.get("type"),
                    "error": None
                }
                
                log.info(f"✅ WebSocket connection successful ({connection_time:.3f}s)")
                return result
                
        except Exception as e:
            result = {
                "test": "websocket_connection",
                "status": "failed",
                "connection_time": time.time() - start_time,
                "response_time": None,
                "response_type": None,
                "error": str(e)
            }
            log.error(f"❌ WebSocket connection failed: {e}")
            return result
    
    async def test_tts_streaming(self, text: str, language: str = "en", speaker_wav: str = None) -> Dict[str, Any]:
        """Test TTS streaming functionality."""
        log.info(f"🎵 Testing TTS streaming: '{text[:50]}...'")
        
        start_time = time.time()
        stream_id = f"test_stream_{int(time.time())}"
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Start TTS stream
                stream_message = {
                    "type": "start_tts_stream",
                    "stream_id": stream_id,
                    "text": text,
                    "language": language,
                    "speaker_wav": speaker_wav
                }
                
                await websocket.send(json.dumps(stream_message))
                
                # Collect responses
                responses = []
                audio_chunks = []
                stream_start_time = None
                stream_complete_time = None
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        response_data = json.loads(response)
                        responses.append(response_data)
                        
                        if response_data.get("type") == "stream_start":
                            stream_start_time = time.time()
                            log.info(f"📡 Stream started: {stream_id}")
                            
                        elif response_data.get("type") == "audio_chunk":
                            audio_chunks.append(response_data)
                            log.info(f"📦 Received chunk {response_data.get('chunk_index', 0) + 1}/{response_data.get('total_chunks', 0)}")
                            
                        elif response_data.get("type") == "stream_complete":
                            stream_complete_time = time.time()
                            log.info(f"✅ Stream completed: {stream_id}")
                            break
                            
                        elif response_data.get("type") == "stream_error":
                            raise Exception(f"Stream error: {response_data.get('message', 'Unknown error')}")
                            
                    except asyncio.TimeoutError:
                        raise Exception("Stream timeout")
                
                total_time = time.time() - start_time
                synthesis_time = stream_complete_time - stream_start_time if stream_start_time and stream_complete_time else None
                
                result = {
                    "test": "tts_streaming",
                    "status": "success",
                    "stream_id": stream_id,
                    "text": text,
                    "language": language,
                    "speaker_wav": speaker_wav,
                    "total_time": total_time,
                    "synthesis_time": synthesis_time,
                    "audio_chunks": len(audio_chunks),
                    "responses": len(responses),
                    "error": None
                }
                
                log.info(f"✅ TTS streaming successful ({total_time:.3f}s, {len(audio_chunks)} chunks)")
                return result
                
        except Exception as e:
            result = {
                "test": "tts_streaming",
                "status": "failed",
                "stream_id": stream_id,
                "text": text,
                "language": language,
                "speaker_wav": speaker_wav,
                "total_time": time.time() - start_time,
                "synthesis_time": None,
                "audio_chunks": 0,
                "responses": 0,
                "error": str(e)
            }
            log.error(f"❌ TTS streaming failed: {e}")
            return result
    
    async def test_concurrent_streams(self, num_streams: int = 5) -> Dict[str, Any]:
        """Test concurrent TTS streaming."""
        log.info(f"🔄 Testing {num_streams} concurrent streams...")
        
        start_time = time.time()
        
        # Create test tasks
        tasks = []
        for i in range(num_streams):
            text = f"This is concurrent stream number {i + 1}. Testing real-time TTS performance."
            task = self.test_tts_streaming(text, "en", None)
            tasks.append(task)
        
        # Run concurrent tests
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            successful_streams = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
            failed_streams = num_streams - successful_streams
            
            result = {
                "test": "concurrent_streams",
                "status": "success" if failed_streams == 0 else "partial",
                "num_streams": num_streams,
                "successful_streams": successful_streams,
                "failed_streams": failed_streams,
                "total_time": total_time,
                "average_time": total_time / num_streams,
                "results": results,
                "error": None
            }
            
            log.info(f"✅ Concurrent streams test completed ({successful_streams}/{num_streams} successful)")
            return result
            
        except Exception as e:
            result = {
                "test": "concurrent_streams",
                "status": "failed",
                "num_streams": num_streams,
                "successful_streams": 0,
                "failed_streams": num_streams,
                "total_time": time.time() - start_time,
                "average_time": None,
                "results": [],
                "error": str(e)
            }
            log.error(f"❌ Concurrent streams test failed: {e}")
            return result
    
    def test_rest_api(self) -> Dict[str, Any]:
        """Test REST API endpoints."""
        log.info("🌐 Testing REST API endpoints...")
        
        results = []
        
        # Test streaming stats endpoint
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/tts-streaming-stats", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                stats_data = response.json()
                results.append({
                    "endpoint": "/tts-streaming-stats",
                    "status": "success",
                    "response_time": response_time,
                    "data": stats_data
                })
                log.info(f"✅ Stats endpoint successful ({response_time:.3f}s)")
            else:
                results.append({
                    "endpoint": "/tts-streaming-stats",
                    "status": "failed",
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}"
                })
                log.error(f"❌ Stats endpoint failed: HTTP {response.status_code}")
                
        except Exception as e:
            results.append({
                "endpoint": "/tts-streaming-stats",
                "status": "failed",
                "response_time": None,
                "error": str(e)
            })
            log.error(f"❌ Stats endpoint error: {e}")
        
        # Test TTS streaming test endpoint
        try:
            start_time = time.time()
            test_data = {
                "text": "This is a REST API test for TTS streaming.",
                "language": "en",
                "speaker_wav": None
            }
            
            response = requests.post(f"{self.base_url}/tts-streaming-test", 
                                   json=test_data, timeout=30)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                tts_data = response.json()
                results.append({
                    "endpoint": "/tts-streaming-test",
                    "status": "success",
                    "response_time": response_time,
                    "audio_size": tts_data.get("audio_size", 0),
                    "data": tts_data
                })
                log.info(f"✅ TTS test endpoint successful ({response_time:.3f}s)")
            else:
                results.append({
                    "endpoint": "/tts-streaming-test",
                    "status": "failed",
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}"
                })
                log.error(f"❌ TTS test endpoint failed: HTTP {response.status_code}")
                
        except Exception as e:
            results.append({
                "endpoint": "/tts-streaming-test",
                "status": "failed",
                "response_time": None,
                "error": str(e)
            })
            log.error(f"❌ TTS test endpoint error: {e}")
        
        return {
            "test": "rest_api",
            "status": "success" if all(r["status"] == "success" for r in results) else "partial",
            "results": results,
            "total_endpoints": len(results),
            "successful_endpoints": sum(1 for r in results if r["status"] == "success")
        }
    
    async def run_performance_test(self) -> Dict[str, Any]:
        """Run comprehensive performance test."""
        log.info("🚀 Starting comprehensive TTS performance test...")
        
        test_results = []
        
        # Test 1: WebSocket Connection
        ws_result = await self.test_websocket_connection()
        test_results.append(ws_result)
        
        # Test 2: Basic TTS Streaming
        tts_result = await self.test_tts_streaming(
            "Hello! This is a test of real-time TTS streaming with Coqui TTS.",
            "en",
            None
        )
        test_results.append(tts_result)
        
        # Test 3: TTS with Reference Audio (if available)
        try:
            ref_result = await self.test_tts_streaming(
                "This is a test with reference audio for voice cloning.",
                "en",
                "00005.wav"
            )
            test_results.append(ref_result)
        except Exception as e:
            log.warning(f"Reference audio test skipped: {e}")
        
        # Test 4: Concurrent Streams
        concurrent_result = await self.test_concurrent_streams(3)
        test_results.append(concurrent_result)
        
        # Test 5: REST API
        rest_result = self.test_rest_api()
        test_results.append(rest_result)
        
        # Calculate overall results
        total_tests = len(test_results)
        successful_tests = sum(1 for r in test_results if r.get("status") == "success")
        partial_tests = sum(1 for r in test_results if r.get("status") == "partial")
        failed_tests = total_tests - successful_tests - partial_tests
        
        overall_result = {
            "test_suite": "realtime_tts_performance",
            "timestamp": time.time(),
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "partial_tests": partial_tests,
            "failed_tests": failed_tests,
            "success_rate": (successful_tests + partial_tests * 0.5) / total_tests * 100,
            "results": test_results
        }
        
        log.info(f"📊 Performance test completed: {successful_tests}/{total_tests} successful ({overall_result['success_rate']:.1f}%)")
        
        return overall_result
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test results summary."""
        print("\n" + "="*60)
        print("🎵 REAL-TIME TTS PERFORMANCE TEST SUMMARY")
        print("="*60)
        
        print(f"📊 Overall Results:")
        print(f"   Total Tests: {results['total_tests']}")
        print(f"   Successful: {results['successful_tests']}")
        print(f"   Partial: {results['partial_tests']}")
        print(f"   Failed: {results['failed_tests']}")
        print(f"   Success Rate: {results['success_rate']:.1f}%")
        
        print(f"\n📋 Test Details:")
        for result in results['results']:
            test_name = result.get('test', 'unknown')
            status = result.get('status', 'unknown')
            status_icon = "✅" if status == "success" else "⚠️" if status == "partial" else "❌"
            
            print(f"   {status_icon} {test_name}: {status}")
            
            if test_name == "tts_streaming" and result.get('status') == 'success':
                print(f"      Synthesis Time: {result.get('synthesis_time', 0):.3f}s")
                print(f"      Audio Chunks: {result.get('audio_chunks', 0)}")
                
            elif test_name == "concurrent_streams" and result.get('status') in ['success', 'partial']:
                print(f"      Streams: {result.get('successful_streams', 0)}/{result.get('num_streams', 0)}")
                print(f"      Average Time: {result.get('average_time', 0):.3f}s")
                
            elif test_name == "rest_api":
                successful = result.get('successful_endpoints', 0)
                total = result.get('total_endpoints', 0)
                print(f"      Endpoints: {successful}/{total}")
        
        print("\n" + "="*60)

async def main():
    """Main test function."""
    print("🎵 Real-time TTS Performance Test")
    print("="*50)
    
    # Initialize test
    tester = TTSPerformanceTest()
    
    try:
        # Run performance test
        results = await tester.run_performance_test()
        
        # Print summary
        tester.print_summary(results)
        
        # Save results to file
        with open("tts_performance_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: tts_performance_test_results.json")
        
    except Exception as e:
        log.error(f"❌ Performance test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

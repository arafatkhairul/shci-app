# Real-time TTS Integration Guide

## Overview

This guide explains how to integrate real-time Text-to-Speech (TTS) streaming using Coqui TTS with reference audio support. The system is based on the `simple_tts_test.py` implementation and provides professional-grade TTS capabilities for real-time applications.

## Features

- ✅ **Coqui TTS Integration**: Based on XTTS v2 model
- ✅ **Reference Audio Support**: Voice cloning with custom speaker audio
- ✅ **Real-time Streaming**: WebSocket-based audio streaming
- ✅ **Multiple Languages**: Support for 16+ languages
- ✅ **Professional Configuration**: Comprehensive configuration system
- ✅ **Frontend Integration**: Complete JavaScript client library
- ✅ **Performance Optimization**: Real-time optimizations and caching

## Architecture

```
Frontend (JavaScript) ←→ WebSocket ←→ FastAPI Backend ←→ Coqui TTS
                                ↓
                        Real-time Streaming
                                ↓
                        Audio Chunks → Frontend
```

## Files Structure

```
fastapi-backend/
├── simple_tts_test.py              # Original TTS test implementation
├── xtts_manager.py                 # Updated XTTS manager (Coqui TTS)
├── xtts_wrapper.py                 # FastAPI wrapper for XTTS
├── realtime_tts_streaming.py      # Real-time streaming module
├── professional_tts_config.py     # Professional configuration system
├── main.py                         # Updated FastAPI main with TTS streaming
├── frontend_tts_integration.js     # JavaScript client library
├── tts_frontend_example.html       # Complete frontend example
├── tts_config.env                  # Configuration template
└── TTS_INTEGRATION_README.md       # This guide
```

## Quick Start

### 1. Backend Setup

1. **Install Dependencies**:
   ```bash
   pip install TTS torch torchaudio soundfile numpy fastapi websockets
   ```

2. **Configure Environment**:
   ```bash
   cp tts_config.env .env
   # Edit .env with your settings
   ```

3. **Start Backend**:
   ```bash
   python main.py
   ```

### 2. Frontend Integration

1. **Include JavaScript Library**:
   ```html
   <script src="frontend_tts_integration.js"></script>
   ```

2. **Basic Usage**:
   ```javascript
   // Initialize TTS client
   const ttsClient = new RealTimeTTSClient('ws://localhost:8000/ws');
   
   // Connect to server
   await ttsClient.connect();
   
   // Speak text
   const streamId = await ttsClient.startTTSStream('Hello, world!');
   ```

3. **Complete Example**:
   Open `tts_frontend_example.html` in your browser for a full working example.

## Configuration

### Environment Variables

Key configuration options in `tts_config.env`:

```bash
# TTS Model
TTS_MODEL_NAME=tts_models/multilingual/multi-dataset/xtts_v2
TTS_DEVICE=auto
TTS_PRECISION=fp16

# Voice Settings
TTS_SPEAKER_WAV=00005.wav  # Reference audio file
TTS_LANGUAGE=en
TTS_SPEED=1.0

# Real-time Settings
TTS_REALTIME=true
TTS_LATENCY_TARGET=0.5
TTS_STREAMING=true
TTS_CHUNK_SIZE=1024
```

### Reference Audio Setup

1. **Place Reference Audio**: Put your reference audio file (e.g., `00005.wav`) in the backend directory
2. **Configure Path**: Set `TTS_SPEAKER_WAV` in your `.env` file
3. **Fallback Speaker**: Configure `FALLBACK_SPEAKER` for when reference audio is not available

## API Reference

### WebSocket Commands

#### Start TTS Stream
```json
{
  "type": "start_tts_stream",
  "stream_id": "unique_stream_id",
  "text": "Text to synthesize",
  "language": "en",
  "speaker_wav": "path/to/speaker.wav"
}
```

#### Stop TTS Stream
```json
{
  "type": "stop_tts_stream",
  "stream_id": "stream_id_to_stop"
}
```

#### Get Streaming Stats
```json
{
  "type": "get_streaming_stats"
}
```

### WebSocket Responses

#### Stream Start
```json
{
  "type": "stream_start",
  "stream_id": "stream_id",
  "message": "Starting audio synthesis..."
}
```

#### Audio Chunk
```json
{
  "type": "audio_chunk",
  "stream_id": "stream_id",
  "chunk_index": 0,
  "total_chunks": 10,
  "data": "base64_encoded_audio_data",
  "is_final": false
}
```

#### Stream Complete
```json
{
  "type": "stream_complete",
  "stream_id": "stream_id",
  "message": "Audio streaming completed",
  "duration": 2.5
}
```

### REST API Endpoints

#### Test TTS Streaming
```bash
POST /tts-streaming-test
Content-Type: application/json

{
  "text": "Hello, world!",
  "language": "en",
  "speaker_wav": "00005.wav"
}
```

#### Get Streaming Statistics
```bash
GET /tts-streaming-stats
```

## JavaScript Client API

### RealTimeTTSClient

```javascript
const client = new RealTimeTTSClient(websocketUrl);

// Connection
await client.connect();
client.disconnect();

// Streaming
const streamId = await client.startTTSStream(text, options);
client.stopTTSStream(streamId);

// Configuration
client.updateConfig({
  language: 'en',
  speakerWav: 'path/to/speaker.wav',
  volume: 1.0,
  autoPlay: true
});

// Events
client.on('onConnect', () => console.log('Connected'));
client.on('onStreamStart', (data) => console.log('Stream started'));
client.on('onAudioChunk', (data) => console.log('Audio chunk received'));
client.on('onStreamComplete', (data) => console.log('Stream completed'));
```

### TTSIntegrationExample

```javascript
const ttsExample = new TTSIntegrationExample();

// Connect
await ttsExample.connect();

// Speak
const streamId = await ttsExample.speak('Hello, world!');

// Configuration
ttsExample.setLanguage('en');
ttsExample.setSpeakerWav('path/to/speaker.wav');
ttsExample.setVolume(0.8);
```

## Performance Optimization

### Real-time Configuration

```bash
# Optimize for real-time performance
TTS_REALTIME=true
TTS_LATENCY_TARGET=0.3
TTS_STREAMING=true
TTS_CHUNK_SIZE=512
TTS_PRECISION=fp16
```

### Quality Configuration

```bash
# Optimize for maximum quality
TTS_PRECISION=fp32
TTS_SAMPLE_RATE=44100
TTS_BIT_DEPTH=24
TTS_STREAMING=false
```

### Caching Configuration

```bash
# Enable caching for better performance
TTS_CACHE=true
TTS_CACHE_TTL=3600
CACHE_SIZE=200
```

## Troubleshooting

### Common Issues

1. **Model Loading Failed**:
   - Check if TTS model is properly installed
   - Verify PyTorch compatibility
   - Check device availability (CUDA/CPU)

2. **Reference Audio Not Found**:
   - Verify file path in configuration
   - Check file permissions
   - Ensure audio format is supported (WAV)

3. **WebSocket Connection Failed**:
   - Check server is running
   - Verify WebSocket URL
   - Check firewall settings

4. **Audio Playback Issues**:
   - Check browser audio permissions
   - Verify Web Audio API support
   - Check audio context state

### Debug Mode

Enable debug logging:

```bash
TTS_VERBOSE_LOGGING=true
STREAMING_VERBOSE_LOGGING=true
DEBUG_TTS=true
DEBUG_STREAMING=true
```

### Performance Monitoring

Monitor streaming statistics:

```javascript
// Get real-time stats
client.getStreamingStats();

// Listen for stats updates
client.on('streaming_stats', (stats) => {
  console.log('Active streams:', stats.total_active_streams);
  console.log('Cache hit rate:', stats.cache_hit_rate);
});
```

## Advanced Usage

### Custom Voice Cloning

1. **Prepare Reference Audio**:
   - Use high-quality WAV files
   - Keep duration between 3-10 seconds
   - Ensure clear speech without background noise

2. **Configure Speaker**:
   ```javascript
   client.updateConfig({
     speakerWav: 'path/to/your/speaker.wav'
   });
   ```

3. **Test Voice**:
   ```javascript
   const streamId = await client.startTTSStream(
     'This is a test of my custom voice.',
     { speakerWav: 'path/to/speaker.wav' }
   );
   ```

### Multi-language Support

```javascript
// Switch languages dynamically
client.updateConfig({ language: 'es' });
await client.startTTSStream('Hola, mundo!');

client.updateConfig({ language: 'fr' });
await client.startTTSStream('Bonjour, le monde!');
```

### Batch Processing

```javascript
// Process multiple texts
const texts = ['Hello', 'World', 'Test'];
const streamIds = [];

for (const text of texts) {
  const streamId = await client.startTTSStream(text);
  streamIds.push(streamId);
}
```

## Security Considerations

1. **File Upload**: Validate reference audio files
2. **Rate Limiting**: Implement request rate limiting
3. **Authentication**: Add WebSocket authentication if needed
4. **CORS**: Configure CORS properly for production

## Production Deployment

### Docker Configuration

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

### Environment Variables

```bash
# Production settings
TTS_DEVICE=cuda
TTS_PRECISION=fp16
TTS_MAX_WORKERS=8
MAX_CONCURRENT_STREAMS=50
```

### Monitoring

- Set up logging aggregation
- Monitor streaming statistics
- Track performance metrics
- Set up alerts for failures

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for errors
3. Test with the provided examples
4. Create an issue with detailed information

---

**Note**: This integration is based on the `simple_tts_test.py` implementation and provides a professional, production-ready TTS streaming solution with Coqui TTS and reference audio support.

/**
 * Frontend TTS Integration Example
 * Real-time TTS streaming integration for frontend applications.
 * Based on Coqui TTS with reference audio support.
 */

class RealTimeTTSClient {
    constructor(websocketUrl = 'ws://localhost:8000/ws') {
        this.websocketUrl = websocketUrl;
        this.ws = null;
        this.isConnected = false;
        this.activeStreams = new Map();
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        
        // Configuration
        this.config = {
            language: 'en',
            speakerWav: null, // Path to reference audio file
            chunkSize: 1024,
            autoPlay: true,
            volume: 1.0
        };
        
        // Event listeners
        this.listeners = {
            onConnect: [],
            onDisconnect: [],
            onStreamStart: [],
            onStreamComplete: [],
            onStreamError: [],
            onAudioChunk: [],
            onAudioComplete: []
        };
    }
    
    /**
     * Connect to WebSocket server
     */
    async connect() {
        try {
            this.ws = new WebSocket(this.websocketUrl);
            
            this.ws.onopen = () => {
                this.isConnected = true;
                console.log('✅ Connected to TTS server');
                this.emit('onConnect');
                
                // Initialize audio context
                this.initAudioContext();
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };
            
            this.ws.onclose = () => {
                this.isConnected = false;
                console.log('❌ Disconnected from TTS server');
                this.emit('onDisconnect');
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('onStreamError', { error: 'WebSocket connection error' });
            };
            
        } catch (error) {
            console.error('Failed to connect:', error);
            throw error;
        }
    }
    
    /**
     * Initialize Web Audio API context
     */
    initAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            console.log('✅ Audio context initialized');
        } catch (error) {
            console.error('Failed to initialize audio context:', error);
        }
    }
    
    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(data) {
        const { type, stream_id, ...payload } = data;
        
        switch (type) {
            case 'stream_start':
                console.log(`🎵 Stream ${stream_id} started`);
                this.emit('onStreamStart', { stream_id, ...payload });
                break;
                
            case 'audio_info':
                console.log(`📊 Audio info for stream ${stream_id}:`, payload);
                this.activeStreams.set(stream_id, {
                    ...payload,
                    chunks: [],
                    receivedChunks: 0
                });
                break;
                
            case 'audio_chunk':
                this.handleAudioChunk(stream_id, payload);
                break;
                
            case 'stream_complete':
                console.log(`✅ Stream ${stream_id} completed`);
                this.handleStreamComplete(stream_id, payload);
                break;
                
            case 'stream_error':
                console.error(`❌ Stream ${stream_id} error:`, payload);
                this.emit('onStreamError', { stream_id, ...payload });
                break;
                
            case 'tts_stream_response':
                console.log(`TTS Stream Response:`, payload);
                break;
                
            case 'streaming_stats':
                console.log('📈 Streaming stats:', payload.stats);
                break;
                
            default:
                console.log('Unknown message type:', type, payload);
        }
    }
    
    /**
     * Handle incoming audio chunks
     */
    async handleAudioChunk(streamId, { chunk_index, total_chunks, data, is_final }) {
        try {
            const streamInfo = this.activeStreams.get(streamId);
            if (!streamInfo) {
                console.warn(`Stream ${streamId} not found`);
                return;
            }
            
            // Decode base64 audio data
            const audioData = this.base64ToArrayBuffer(data);
            
            // Store chunk
            streamInfo.chunks[chunk_index] = audioData;
            streamInfo.receivedChunks++;
            
            console.log(`📦 Received chunk ${chunk_index + 1}/${total_chunks} for stream ${streamId}`);
            
            // Emit chunk event
            this.emit('onAudioChunk', {
                stream_id: streamId,
                chunk_index,
                total_chunks,
                is_final,
                audio_data: audioData
            });
            
            // Play chunk if auto-play is enabled
            if (this.config.autoPlay) {
                await this.playAudioChunk(audioData);
            }
            
            // Check if all chunks received
            if (streamInfo.receivedChunks === total_chunks) {
                console.log(`🎯 All chunks received for stream ${streamId}`);
                this.handleStreamComplete(streamId, { duration: 0 });
            }
            
        } catch (error) {
            console.error(`Error handling audio chunk for stream ${streamId}:`, error);
        }
    }
    
    /**
     * Handle stream completion
     */
    handleStreamComplete(streamId, payload) {
        const streamInfo = this.activeStreams.get(streamId);
        if (streamInfo) {
            // Combine all chunks into complete audio
            const completeAudio = this.combineAudioChunks(streamInfo.chunks);
            
            this.emit('onStreamComplete', {
                stream_id: streamId,
                audio_data: completeAudio,
                duration: payload.duration,
                audio_size: streamInfo.audio_size,
                sample_rate: streamInfo.sample_rate
            });
            
            this.emit('onAudioComplete', {
                stream_id: streamId,
                audio_data: completeAudio
            });
            
            // Clean up stream
            this.activeStreams.delete(streamId);
        }
    }
    
    /**
     * Start TTS streaming
     */
    async startTTSStream(text, options = {}) {
        if (!this.isConnected) {
            throw new Error('Not connected to server');
        }
        
        const streamId = this.generateStreamId();
        const config = { ...this.config, ...options };
        
        const message = {
            type: 'start_tts_stream',
            stream_id: streamId,
            text: text,
            language: config.language,
            speaker_wav: config.speakerWav
        };
        
        console.log(`🚀 Starting TTS stream ${streamId}:`, message);
        
        this.ws.send(JSON.stringify(message));
        
        return streamId;
    }
    
    /**
     * Stop TTS streaming
     */
    stopTTSStream(streamId) {
        if (!this.isConnected) {
            throw new Error('Not connected to server');
        }
        
        const message = {
            type: 'stop_tts_stream',
            stream_id: streamId
        };
        
        console.log(`🛑 Stopping TTS stream ${streamId}`);
        
        this.ws.send(JSON.stringify(message));
    }
    
    /**
     * Get streaming statistics
     */
    getStreamingStats() {
        if (!this.isConnected) {
            throw new Error('Not connected to server');
        }
        
        const message = {
            type: 'get_streaming_stats'
        };
        
        this.ws.send(JSON.stringify(message));
    }
    
    /**
     * Play audio chunk using Web Audio API
     */
    async playAudioChunk(audioData) {
        if (!this.audioContext || this.audioContext.state === 'closed') {
            console.warn('Audio context not available');
            return;
        }
        
        try {
            // Resume audio context if suspended
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            // Decode audio data
            const audioBuffer = await this.audioContext.decodeAudioData(audioData.slice());
            
            // Create audio source
            const source = this.audioContext.createBufferSource();
            const gainNode = this.audioContext.createGain();
            
            source.buffer = audioBuffer;
            gainNode.gain.value = this.config.volume;
            
            // Connect nodes
            source.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            // Play audio
            source.start();
            
            console.log(`🔊 Playing audio chunk (${audioBuffer.duration.toFixed(2)}s)`);
            
        } catch (error) {
            console.error('Error playing audio chunk:', error);
        }
    }
    
    /**
     * Play complete audio data
     */
    async playCompleteAudio(audioData) {
        if (!this.audioContext || this.audioContext.state === 'closed') {
            console.warn('Audio context not available');
            return;
        }
        
        try {
            // Resume audio context if suspended
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            // Decode audio data
            const audioBuffer = await this.audioContext.decodeAudioData(audioData.slice());
            
            // Create audio source
            const source = this.audioContext.createBufferSource();
            const gainNode = this.audioContext.createGain();
            
            source.buffer = audioBuffer;
            gainNode.gain.value = this.config.volume;
            
            // Connect nodes
            source.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            // Play audio
            source.start();
            
            console.log(`🔊 Playing complete audio (${audioBuffer.duration.toFixed(2)}s)`);
            
            return new Promise((resolve) => {
                source.onended = () => resolve();
            });
            
        } catch (error) {
            console.error('Error playing complete audio:', error);
            throw error;
        }
    }
    
    /**
     * Combine audio chunks into complete audio
     */
    combineAudioChunks(chunks) {
        const totalLength = chunks.reduce((sum, chunk) => sum + chunk.byteLength, 0);
        const combined = new Uint8Array(totalLength);
        
        let offset = 0;
        for (const chunk of chunks) {
            if (chunk) {
                combined.set(new Uint8Array(chunk), offset);
                offset += chunk.byteLength;
            }
        }
        
        return combined.buffer;
    }
    
    /**
     * Convert base64 to ArrayBuffer
     */
    base64ToArrayBuffer(base64) {
        const binaryString = atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }
    
    /**
     * Generate unique stream ID
     */
    generateStreamId() {
        return 'stream_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * Add event listener
     */
    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
        }
    }
    
    /**
     * Remove event listener
     */
    off(event, callback) {
        if (this.listeners[event]) {
            const index = this.listeners[event].indexOf(callback);
            if (index > -1) {
                this.listeners[event].splice(index, 1);
            }
        }
    }
    
    /**
     * Emit event to listeners
     */
    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in ${event} listener:`, error);
                }
            });
        }
    }
    
    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        console.log('📝 Configuration updated:', this.config);
    }
    
    /**
     * Disconnect from server
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
    }
}

// Usage Example
class TTSIntegrationExample {
    constructor() {
        this.ttsClient = new RealTimeTTSClient();
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        this.ttsClient.on('onConnect', () => {
            console.log('🎉 TTS Client connected!');
            this.updateUI('connected');
        });
        
        this.ttsClient.on('onDisconnect', () => {
            console.log('😞 TTS Client disconnected');
            this.updateUI('disconnected');
        });
        
        this.ttsClient.on('onStreamStart', (data) => {
            console.log('🎵 Stream started:', data);
            this.updateUI('streaming');
        });
        
        this.ttsClient.on('onStreamComplete', (data) => {
            console.log('✅ Stream completed:', data);
            this.updateUI('idle');
        });
        
        this.ttsClient.on('onStreamError', (data) => {
            console.error('❌ Stream error:', data);
            this.updateUI('error');
        });
        
        this.ttsClient.on('onAudioChunk', (data) => {
            console.log(`📦 Audio chunk ${data.chunk_index + 1}/${data.total_chunks}`);
        });
    }
    
    async connect() {
        try {
            await this.ttsClient.connect();
        } catch (error) {
            console.error('Failed to connect:', error);
        }
    }
    
    async speak(text, options = {}) {
        try {
            const streamId = await this.ttsClient.startTTSStream(text, options);
            console.log(`Speaking: "${text}" (Stream: ${streamId})`);
            return streamId;
        } catch (error) {
            console.error('Failed to start TTS stream:', error);
            throw error;
        }
    }
    
    stopSpeaking(streamId) {
        try {
            this.ttsClient.stopTTSStream(streamId);
        } catch (error) {
            console.error('Failed to stop TTS stream:', error);
        }
    }
    
    updateUI(status) {
        // Update UI based on connection status
        const statusElement = document.getElementById('tts-status');
        if (statusElement) {
            statusElement.textContent = `Status: ${status}`;
            statusElement.className = `status-${status}`;
        }
    }
    
    setLanguage(language) {
        this.ttsClient.updateConfig({ language });
    }
    
    setSpeakerWav(speakerWav) {
        this.ttsClient.updateConfig({ speakerWav });
    }
    
    setVolume(volume) {
        this.ttsClient.updateConfig({ volume });
    }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { RealTimeTTSClient, TTSIntegrationExample };
}

// Auto-initialize if running in browser
if (typeof window !== 'undefined') {
    window.RealTimeTTSClient = RealTimeTTSClient;
    window.TTSIntegrationExample = TTSIntegrationExample;
    
    // Example usage
    document.addEventListener('DOMContentLoaded', () => {
        const ttsExample = new TTSIntegrationExample();
        
        // Connect on page load
        ttsExample.connect();
        
        // Example buttons
        const speakButton = document.getElementById('speak-button');
        const textInput = document.getElementById('text-input');
        
        if (speakButton && textInput) {
            speakButton.addEventListener('click', () => {
                const text = textInput.value;
                if (text.trim()) {
                    ttsExample.speak(text);
                }
            });
        }
        
        // Make available globally
        window.ttsExample = ttsExample;
    });
}

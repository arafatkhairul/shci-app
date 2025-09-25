/**
 * Whisper Speech-to-Text Service
 * ==============================
 * 
 * This service provides Whisper-based speech-to-text functionality for the frontend.
 * It handles audio recording, streaming to backend, and real-time transcription.
 * 
 * Features:
 * - Real-time audio recording
 * - WebSocket streaming to backend
 * - Continuous transcription
 * - Language detection
 * - Confidence scoring
 * 
 * Author: SHCI Development Team
 * Date: 2025
 */

export interface WhisperSTTConfig {
  language?: string;
  task: 'transcribe' | 'translate';
  sampleRate: number;
  chunkSize: number;
  continuous: boolean;
}

export interface WhisperSTTCallbacks {
  onTranscription?: (transcript: string, confidence: number, isFinal: boolean) => void;
  onError?: (error: string) => void;
  onStateChange?: (isRecording: boolean) => void;
  onLanguageDetected?: (language: string) => void;
}

export interface TranscriptionResult {
  success: boolean;
  transcript: string;
  confidence: number;
  language?: string;
  duration?: number;
  error?: string;
}

class WhisperSTTService {
  private config: WhisperSTTConfig;
  private callbacks: WhisperSTTCallbacks;
  private isRecording: boolean = false;
  private isInitialized: boolean = false;
  private mediaRecorder: MediaRecorder | null = null;
  private audioStream: MediaStream | null = null;
  private websocket: WebSocket | null = null;
  private audioChunks: Blob[] = [];
  private recordingInterval: NodeJS.Timeout | null = null;
  private backendUrl: string;

  constructor(
    config: Partial<WhisperSTTConfig> = {},
    callbacks: WhisperSTTCallbacks = {},
    backendUrl: string = 'ws://localhost:8000'
  ) {
    this.config = {
      language: undefined,
      task: 'transcribe',
      sampleRate: 16000,
      chunkSize: 1024,
      continuous: true,
      ...config
    };
    
    this.callbacks = callbacks;
    this.backendUrl = backendUrl;
  }

  /**
   * Initialize the Whisper STT service
   */
  public async initialize(): Promise<boolean> {
    try {
      console.log('Whisper STT: Initializing service...');
      
      // Check if MediaRecorder is supported
      if (!window.MediaRecorder) {
        console.error('Whisper STT: MediaRecorder not supported');
        this.callbacks.onError?.('MediaRecorder not supported in this browser');
        return false;
      }

      // Check if WebSocket is supported
      if (!window.WebSocket) {
        console.error('Whisper STT: WebSocket not supported');
        this.callbacks.onError?.('WebSocket not supported in this browser');
        return false;
      }

      this.isInitialized = true;
      console.log('Whisper STT: Service initialized successfully');
      return true;

    } catch (error) {
      console.error('Whisper STT: Initialization failed:', error);
      this.callbacks.onError?.(`Initialization failed: ${error}`);
      return false;
    }
  }

  /**
   * Start recording and transcription
   */
  public async start(): Promise<boolean> {
    if (!this.isInitialized) {
      console.error('Whisper STT: Service not initialized');
      return false;
    }

    if (this.isRecording) {
      console.log('Whisper STT: Already recording');
      return true;
    }

    try {
      console.log('Whisper STT: Starting recording...');
      
      // Get microphone access
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // Create MediaRecorder
      this.mediaRecorder = new MediaRecorder(this.audioStream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      // Set up event handlers
      this.setupMediaRecorderHandlers();
      
      // Connect to WebSocket
      await this.connectWebSocket();

      // Start recording
      this.mediaRecorder.start(this.config.chunkSize);
      this.isRecording = true;
      this.callbacks.onStateChange?.(true);

      console.log('Whisper STT: Recording started successfully');
      return true;

    } catch (error) {
      console.error('Whisper STT: Failed to start recording:', error);
      this.callbacks.onError?.(`Failed to start recording: ${error}`);
      return false;
    }
  }

  /**
   * Stop recording and transcription
   */
  public stop(): void {
    if (!this.isRecording) {
      console.log('Whisper STT: Not recording');
      return;
    }

    console.log('Whisper STT: Stopping recording...');

    // Stop MediaRecorder
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    // Stop audio stream
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(track => track.stop());
      this.audioStream = null;
    }

    // Close WebSocket
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }

    // Clear recording interval
    if (this.recordingInterval) {
      clearInterval(this.recordingInterval);
      this.recordingInterval = null;
    }

    this.isRecording = false;
    this.callbacks.onStateChange?.(false);
    console.log('Whisper STT: Recording stopped');
  }

  /**
   * Set up MediaRecorder event handlers
   */
  private setupMediaRecorderHandlers(): void {
    if (!this.mediaRecorder) return;

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
        
        // Send audio data to backend via WebSocket
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
          this.websocket.send(event.data);
        }
      }
    };

    this.mediaRecorder.onstop = () => {
      console.log('Whisper STT: MediaRecorder stopped');
    };

    this.mediaRecorder.onerror = (event) => {
      console.error('Whisper STT: MediaRecorder error:', event);
      this.callbacks.onError?.(`Recording error: ${event}`);
    };
  }

  /**
   * Connect to WebSocket for real-time transcription
   */
  private async connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${this.backendUrl.replace('http', 'ws')}/stt/stream`;
        console.log('Whisper STT: Connecting to WebSocket:', wsUrl);
        
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
          console.log('Whisper STT: WebSocket connected');
          resolve();
        };

        this.websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'transcription') {
              const result: TranscriptionResult = data.data;
              
              if (result.success && result.transcript) {
                console.log('Whisper STT: Transcription received:', result.transcript);
                
                // Call transcription callback
                this.callbacks.onTranscription?.(
                  result.transcript,
                  result.confidence,
                  true // Always final for Whisper
                );

                // Call language detection callback
                if (result.language) {
                  this.callbacks.onLanguageDetected?.(result.language);
                }
              } else if (result.error) {
                console.error('Whisper STT: Transcription error:', result.error);
                this.callbacks.onError?.(result.error);
              }
            } else if (data.type === 'error') {
              console.error('Whisper STT: WebSocket error:', data.message);
              this.callbacks.onError?.(data.message);
            }
          } catch (error) {
            console.error('Whisper STT: Error parsing WebSocket message:', error);
          }
        };

        this.websocket.onclose = () => {
          console.log('Whisper STT: WebSocket disconnected');
        };

        this.websocket.onerror = (error) => {
          console.error('Whisper STT: WebSocket error:', error);
          reject(error);
        };

      } catch (error) {
        console.error('Whisper STT: Failed to create WebSocket:', error);
        reject(error);
      }
    });
  }

  /**
   * Transcribe audio file
   */
  public async transcribeFile(file: File, language?: string): Promise<TranscriptionResult> {
    try {
      console.log('Whisper STT: Transcribing file:', file.name);
      
      const formData = new FormData();
      formData.append('audio_file', file);
      if (language) {
        formData.append('language', language);
      }
      formData.append('task', this.config.task);

      const response = await fetch(`${this.backendUrl.replace('ws', 'http')}/stt/transcribe`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result: TranscriptionResult = await response.json();
      console.log('Whisper STT: File transcription result:', result);
      
      return result;

    } catch (error) {
      console.error('Whisper STT: File transcription failed:', error);
      return {
        success: false,
        transcript: '',
        confidence: 0,
        error: `File transcription failed: ${error}`
      };
    }
  }

  /**
   * Get supported languages
   */
  public async getSupportedLanguages(): Promise<string[]> {
    try {
      const response = await fetch(`${this.backendUrl.replace('ws', 'http')}/stt/languages`);
      const data = await response.json();
      return data.languages || [];
    } catch (error) {
      console.error('Whisper STT: Failed to get languages:', error);
      return [];
    }
  }

  /**
   * Get model information
   */
  public async getModelInfo(): Promise<any> {
    try {
      const response = await fetch(`${this.backendUrl.replace('ws', 'http')}/stt/model-info`);
      const data = await response.json();
      return data.model_info || {};
    } catch (error) {
      console.error('Whisper STT: Failed to get model info:', error);
      return {};
    }
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<WhisperSTTConfig>): void {
    this.config = { ...this.config, ...newConfig };
    console.log('Whisper STT: Configuration updated:', this.config);
  }

  /**
   * Get current status
   */
  public getStatus(): { isRecording: boolean; isInitialized: boolean; isConnected: boolean } {
    return {
      isRecording: this.isRecording,
      isInitialized: this.isInitialized,
      isConnected: this.websocket?.readyState === WebSocket.OPEN
    };
  }

  /**
   * Check if service is ready
   */
  public isReady(): boolean {
    return this.isInitialized && !this.isRecording;
  }

  /**
   * Destroy the service
   */
  public destroy(): void {
    this.stop();
    this.isInitialized = false;
    console.log('Whisper STT: Service destroyed');
  }
}

export default WhisperSTTService;

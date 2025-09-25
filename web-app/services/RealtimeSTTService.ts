/**
 * Professional RealtimeSTT Service for Real-time Speech Recognition
 * Replaces faster-whisper with RealtimeSTT for better real-time performance
 */

export interface RealtimeSTTConfig {
  model: string;
  language: string;
  useMicrophone: boolean;
  postSpeechSilenceDuration: number;
  spinner: boolean;
  enableRealtimeTranscription: boolean;
  enableFinalTranscription: boolean;
  sampleRate: number;
  chunkSize: number;
}

export interface RealtimeSTTCallbacks {
  onRealtimeTranscription?: (text: string, confidence: number, isFinal: boolean) => void;
  onFinalTranscription?: (text: string, confidence: number) => void;
  onError?: (error: string) => void;
  onStateChange?: (isRecording: boolean) => void;
  onLanguageDetected?: (language: string) => void;
}

export interface RealtimeSTTStatus {
  isInitialized: boolean;
  isRecording: boolean;
  isConnected: boolean;
  model: string;
  language: string;
  totalTranscriptions: number;
  successfulTranscriptions: number;
  failedTranscriptions: number;
  uptimeSeconds: number;
  successRate: number;
}

export class RealtimeSTTService {
  private ws: WebSocket | null = null;
  private config: RealtimeSTTConfig;
  private callbacks: RealtimeSTTCallbacks;
  private isInitialized = false;
  private isRecording = false;
  private isConnected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // 1 second
  private pingInterval: NodeJS.Timeout | null = null;
  private status: RealtimeSTTStatus | null = null;

  constructor(config: RealtimeSTTConfig, callbacks: RealtimeSTTCallbacks) {
    this.config = config;
    this.callbacks = callbacks;
  }

  /**
   * Initialize the RealtimeSTT service
   */
  async initialize(): Promise<boolean> {
    try {
      console.log('🎤 Initializing RealtimeSTT service...');
      
      // Connect to WebSocket
      const success = await this.connect();
      if (!success) {
        console.error('❌ Failed to connect to RealtimeSTT service');
        return false;
      }

      this.isInitialized = true;
      console.log('✅ RealtimeSTT service initialized successfully');
      return true;
    } catch (error) {
      console.error('❌ Error initializing RealtimeSTT service:', error);
      this.callbacks.onError?.(`Initialization failed: ${error}`);
      return false;
    }
  }

  /**
   * Connect to the RealtimeSTT WebSocket
   */
  private async connect(): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        const wsUrl = `${this.getWebSocketUrl()}/realtime-stt/stream`;
        console.log('🔌 Connecting to RealtimeSTT WebSocket:', wsUrl);
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
          console.log('✅ RealtimeSTT WebSocket connected');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.startPingInterval();
          resolve(true);
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onclose = (event) => {
          console.log('🔌 RealtimeSTT WebSocket closed:', event.code, event.reason);
          this.isConnected = false;
          this.stopPingInterval();
          
          // Attempt to reconnect if not intentionally closed
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('❌ RealtimeSTT WebSocket error:', error);
          this.callbacks.onError?.(`WebSocket error: ${error}`);
          resolve(false);
        };

        // Timeout after 10 seconds
        setTimeout(() => {
          if (!this.isConnected) {
            console.error('❌ RealtimeSTT WebSocket connection timeout');
            this.ws?.close();
            resolve(false);
          }
        }, 10000);

      } catch (error) {
        console.error('❌ Error connecting to RealtimeSTT WebSocket:', error);
        resolve(false);
      }
    });
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'realtime_transcription':
          this.callbacks.onRealtimeTranscription?.(
            data.text,
            data.confidence,
            data.is_final
          );
          break;
          
        case 'final_transcription':
          this.callbacks.onFinalTranscription?.(
            data.text,
            data.confidence
          );
          break;
          
        case 'state_change':
          this.isRecording = data.is_recording;
          this.callbacks.onStateChange?.(data.is_recording);
          break;
          
        case 'language_detected':
          this.callbacks.onLanguageDetected?.(data.language);
          break;
          
        case 'status':
          this.status = data.status;
          break;
          
        case 'error':
          console.error('❌ RealtimeSTT error:', data.message);
          this.callbacks.onError?.(data.message);
          break;
          
        case 'pong':
          // Ping response received
          break;
          
        default:
          console.log('📨 Unknown RealtimeSTT message type:', data.type);
      }
    } catch (error) {
      console.error('❌ Error parsing RealtimeSTT message:', error);
    }
  }

  /**
   * Start the RealtimeSTT service
   */
  async start(): Promise<boolean> {
    try {
      if (!this.isConnected || !this.ws) {
        console.error('❌ RealtimeSTT not connected, cannot start');
        return false;
      }

      console.log('🎤 Starting RealtimeSTT service...');
      
      // Send start command
      this.sendMessage({
        type: 'start'
      });

      return true;
    } catch (error) {
      console.error('❌ Error starting RealtimeSTT service:', error);
      this.callbacks.onError?.(`Start failed: ${error}`);
      return false;
    }
  }

  /**
   * Stop the RealtimeSTT service
   */
  stop(): void {
    try {
      if (!this.isConnected || !this.ws) {
        console.log('⚠️ RealtimeSTT not connected, cannot stop');
        return;
      }

      console.log('🛑 Stopping RealtimeSTT service...');
      
      // Send stop command
      this.sendMessage({
        type: 'stop'
      });

      this.isRecording = false;
    } catch (error) {
      console.error('❌ Error stopping RealtimeSTT service:', error);
    }
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<RealtimeSTTConfig>): void {
    try {
      this.config = { ...this.config, ...newConfig };
      
      if (this.isConnected && this.ws) {
        this.sendMessage({
          type: 'update_config',
          ...newConfig
        });
      }
      
      console.log('⚙️ RealtimeSTT configuration updated');
    } catch (error) {
      console.error('❌ Error updating RealtimeSTT configuration:', error);
    }
  }

  /**
   * Get current status
   */
  async getStatus(): Promise<RealtimeSTTStatus | null> {
    try {
      if (this.isConnected && this.ws) {
        this.sendMessage({
          type: 'get_status'
        });
      }
      return this.status;
    } catch (error) {
      console.error('❌ Error getting RealtimeSTT status:', error);
      return null;
    }
  }

  /**
   * Send message to WebSocket
   */
  private sendMessage(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('⚠️ RealtimeSTT WebSocket not connected, cannot send message');
    }
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      if (this.isConnected && this.ws) {
        this.sendMessage({ type: 'ping' });
      }
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Attempt to reconnect
   */
  private async attemptReconnect(): Promise<void> {
    this.reconnectAttempts++;
    console.log(`🔄 Attempting to reconnect RealtimeSTT (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    setTimeout(async () => {
      const success = await this.connect();
      if (success) {
        console.log('✅ RealtimeSTT reconnected successfully');
        // Restart if it was recording before
        if (this.isRecording) {
          await this.start();
        }
      } else {
        console.error('❌ RealtimeSTT reconnection failed');
      }
    }, this.reconnectDelay * this.reconnectAttempts);
  }

  /**
   * Get WebSocket URL based on environment
   */
  private getWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = process.env.NODE_ENV === 'production' ? '' : ':8000';
    return `${protocol}//${host}${port}`;
  }

  /**
   * Destroy the service and clean up resources
   */
  destroy(): void {
    try {
      console.log('🧹 Destroying RealtimeSTT service...');
      
      this.stop();
      this.stopPingInterval();
      
      if (this.ws) {
        this.ws.close(1000, 'Service destroyed');
        this.ws = null;
      }
      
      this.isInitialized = false;
      this.isRecording = false;
      this.isConnected = false;
      
      console.log('✅ RealtimeSTT service destroyed');
    } catch (error) {
      console.error('❌ Error destroying RealtimeSTT service:', error);
    }
  }
}

// Default configuration
export const defaultRealtimeSTTConfig: RealtimeSTTConfig = {
  model: 'base.en',
  language: 'en',
  useMicrophone: true,
  postSpeechSilenceDuration: 1.0,
  spinner: false,
  enableRealtimeTranscription: true,
  enableFinalTranscription: true,
  sampleRate: 16000,
  chunkSize: 1024
};

// Default callbacks
export const defaultRealtimeSTTCallbacks: RealtimeSTTCallbacks = {
  onRealtimeTranscription: (text: string, confidence: number, isFinal: boolean) => {
    console.log('🎤 Realtime transcription:', text, `(${confidence.toFixed(2)})`);
  },
  onFinalTranscription: (text: string, confidence: number) => {
    console.log('✅ Final transcription:', text, `(${confidence.toFixed(2)})`);
  },
  onError: (error: string) => {
    console.error('❌ RealtimeSTT error:', error);
  },
  onStateChange: (isRecording: boolean) => {
    console.log('🔄 RealtimeSTT state changed:', isRecording ? 'Recording' : 'Stopped');
  },
  onLanguageDetected: (language: string) => {
    console.log('🌍 Language detected:', language);
  }
};

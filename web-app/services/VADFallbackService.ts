/**
 * Server-side STT Fallback VAD Service
 * Provides Voice Activity Detection using server-side WhisperX STT
 * No browser native SpeechRecognition API used
 */

export interface FallbackVADConfig {
  silenceThreshold: number;
  silenceTimeout: number;
  speechTimeout: number;
  sampleRate: number;
  fftSize: number;
  smoothingTimeConstant: number;
}

export interface FallbackVADCallbacks {
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onSpeechResult?: (transcript: string, isFinal: boolean, confidence: number) => void;
  onInterimResult?: (transcript: string, confidence: number) => void;
  onFinalResult?: (transcript: string, confidence: number) => void;
  onSilenceDetected?: () => void;
  onError?: (error: string) => void;
  onStateChange?: (isListening: boolean) => void;
  onVoiceLevelUpdate?: (level: number, source: string) => void;
}

export class FallbackVADService {
  private config: FallbackVADConfig;
  private callbacks: FallbackVADCallbacks;
  private isListening: boolean = false;
  private isInitialized: boolean = false;
  private websocket: WebSocket | null = null;
  private isSupported: boolean = true; // Always supported since we use server-side STT
  
  constructor(config: FallbackVADConfig, callbacks: FallbackVADCallbacks) {
    this.config = config;
    this.callbacks = callbacks;
    console.log('🎤 FallbackVADService: Server-side STT mode enabled');
  }

  /**
   * Check if server-side STT is supported (always true)
   */
  isVADSupported(): boolean {
    return this.isSupported;
  }

  /**
   * Initialize the service (no-op for server-side STT)
   */
  async initialize(): Promise<boolean> {
    console.log('🎤 FallbackVADService: Initializing server-side STT mode');
    this.isInitialized = true;
    return true;
  }

  /**
   * Start listening (no-op for server-side STT)
   * Audio processing is handled by the main audio pipeline
   */
  start(): boolean {
    if (!this.isInitialized) {
      console.warn('🎤 FallbackVADService: Not initialized');
      return false;
    }

    if (this.isListening) {
      console.log('🎤 FallbackVADService: Already listening');
      return true;
    }

    this.isListening = true;
    this.callbacks.onStateChange?.(true);
    console.log('🎤 FallbackVADService: Server-side STT listening started');
    return true;
  }

  /**
   * Stop listening
   */
  stop(): boolean {
    if (!this.isListening) {
      return true;
    }

    this.isListening = false;
    this.callbacks.onStateChange?.(false);
    console.log('🎤 FallbackVADService: Server-side STT listening stopped');
    return true;
  }

  /**
   * Set WebSocket connection for server communication
   */
  setWebSocket(websocket: WebSocket): void {
    this.websocket = websocket;
    console.log('🎤 FallbackVADService: WebSocket connection set for server-side STT');
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<FallbackVADConfig>): void {
    this.config = { ...this.config, ...newConfig };
    console.log('🎤 FallbackVADService: Configuration updated for server-side STT');
  }

  /**
   * Get current state
   */
  getState(): { isListening: boolean; isInitialized: boolean; isSupported: boolean } {
    return {
      isListening: this.isListening,
      isInitialized: this.isInitialized,
      isSupported: this.isSupported
    };
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.stop();
    this.websocket = null;
    console.log('🎤 FallbackVADService: Cleaned up server-side STT resources');
  }

  /**
   * Handle server-side STT results
   * This method is called by the main audio pipeline when server sends STT results
   */
  handleServerSTTResult(transcript: string, isFinal: boolean, confidence: number): void {
    if (!this.isListening) {
      return;
    }

    // Call appropriate callbacks
    if (isFinal) {
      this.callbacks.onFinalResult?.(transcript, confidence);
      this.callbacks.onSpeechResult?.(transcript, true, confidence);
    } else {
      this.callbacks.onInterimResult?.(transcript, confidence);
      this.callbacks.onSpeechResult?.(transcript, false, confidence);
    }

    console.log(`🎤 FallbackVADService: Server STT result - "${transcript}" (${isFinal ? 'final' : 'interim'}, conf: ${confidence.toFixed(2)})`);
  }

  /**
   * Handle server-side STT errors
   */
  handleServerSTTError(error: string): void {
    this.callbacks.onError?.(error);
    console.error('🎤 FallbackVADService: Server STT error:', error);
  }
}

export default FallbackVADService;

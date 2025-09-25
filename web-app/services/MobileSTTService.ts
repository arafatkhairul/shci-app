export interface MobileSTTConfig {
  language: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  confidenceThreshold: number;
}

export interface MobileSTTCallbacks {
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onResult?: (transcript: string, confidence: number, isFinal: boolean) => void;
  onError?: (error: string) => void;
  onStateChange?: (isListening: boolean) => void;
  onVoiceLevelUpdate?: (level: number, source: string) => void;
}

class MobileSTTService {
  private recognition: any = null;
  private config: MobileSTTConfig;
  private callbacks: MobileSTTCallbacks;
  private isListening: boolean = false;
  private isInitialized: boolean = false;
  private isSupported: boolean = false;
  private websocket: WebSocket | null = null;
  
  // Mobile-specific state
  private isMobile: boolean = false;
  private lastProcessedTranscript: string = '';
  private lastProcessedTime: number = 0;
  private processingTimeout: NodeJS.Timeout | null = null;
  private restartTimeout: NodeJS.Timeout | null = null;
  private isRestarting: boolean = false;

  constructor(config: Partial<MobileSTTConfig> = {}, callbacks: MobileSTTCallbacks = {}) {
    this.config = {
      language: 'en-US',
      continuous: true,
      interimResults: true,
      maxAlternatives: 1,
      confidenceThreshold: 0.3, // Lower threshold for better detection
      ...config
    };
    
    this.callbacks = callbacks;
    this.isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    this.checkSupport();
  }

  /**
   * Check if WebkitSpeechRecognition is supported
   */
  private checkSupport(): void {
    this.isSupported = !!(window as any).webkitSpeechRecognition || !!(window as any).SpeechRecognition;
    console.log('Mobile STT: Support check result:', this.isSupported, {
      webkitSpeechRecognition: !!(window as any).webkitSpeechRecognition,
      SpeechRecognition: !!(window as any).SpeechRecognition,
      userAgent: navigator.userAgent
    });
  }

  /**
   * Initialize the mobile STT service
   */
  public async initialize(): Promise<boolean> {
    console.log('Mobile STT: Initialize called, isSupported:', this.isSupported);
    
    if (!this.isSupported) {
      console.log('Mobile STT: Speech recognition not supported');
      return false;
    }

    try {
      console.log('Mobile STT: Creating SpeechRecognition instance...');
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      this.recognition = new SpeechRecognition();
      
      console.log('Mobile STT: Setting up recognition configuration...', {
        continuous: this.config.continuous,
        interimResults: this.config.interimResults,
        lang: this.config.language,
        maxAlternatives: this.config.maxAlternatives
      });
      
      this.recognition.continuous = this.config.continuous;
      this.recognition.interimResults = this.config.interimResults;
      this.recognition.lang = this.config.language;
      this.recognition.maxAlternatives = this.config.maxAlternatives;

      // Mobile-specific: Add serviceURI for better mobile support
      if (this.isMobile && this.recognition.serviceURI === undefined) {
        // Try to set serviceURI for better mobile compatibility
        try {
          this.recognition.serviceURI = 'wss://www.google.com/speech-api/full-duplex/v1/up';
        } catch (e) {
          console.log('Mobile STT: Could not set serviceURI, continuing without it');
        }
      }

      // Mobile-specific: Add additional configuration for better voice detection
      if (this.isMobile) {
        try {
          // Set additional properties for better mobile compatibility
          if (this.recognition.grammars) {
            this.recognition.grammars = new (window as any).SpeechGrammarList();
          }
          
          // Set timeout for better mobile handling
          if (this.recognition.timeout) {
            this.recognition.timeout = 10000; // 10 seconds
          }
          
          // Set end silence timeout
          if (this.recognition.endSilenceTimeout) {
            this.recognition.endSilenceTimeout = 3000; // 3 seconds
          }
        } catch (e) {
          console.log('Mobile STT: Could not set additional properties:', e);
        }
      }

      // Mobile-specific event handlers
      this.recognition.onstart = () => {
        console.log('Mobile STT: Speech recognition started');
        this.isListening = true;
        this.isRestarting = false;
        this.callbacks.onStateChange?.(true);
        this.callbacks.onSpeechStart?.();
      };

      this.recognition.onend = () => {
        console.log('Mobile STT: Speech recognition ended');
        this.isListening = false;
        this.callbacks.onStateChange?.(false);
        this.callbacks.onSpeechEnd?.();
        
        // Auto-restart for continuous listening (mobile-specific)
        if (!this.isRestarting && this.isMobile) {
          console.log('Mobile STT: Auto-restarting for continuous listening...');
          setTimeout(() => {
            if (!this.isRestarting) {
              this.restartRecognition();
            }
          }, 100); // Shorter delay for mobile
        }
      };

      this.recognition.onresult = (event: any) => {
        this.handleResult(event);
      };

      this.recognition.onerror = (event: any) => {
        console.error('Mobile STT Error:', event.error, event);
        console.log('Mobile STT Error Details:', {
          error: event.error,
          type: event.type,
          timeStamp: event.timeStamp,
          isListening: this.isListening,
          isRestarting: this.isRestarting,
          isMobile: this.isMobile
        });
        
        this.callbacks.onError?.(event.error);
        
        // Handle specific errors with better mobile support
        if (event.error === 'no-speech' || event.error === 'audio-capture' || event.error === 'network') {
          // Restart after a short delay for these common mobile errors
          console.log('Mobile STT: Attempting to restart after error:', event.error);
          setTimeout(() => {
            if (!this.isRestarting && this.isListening) {
              console.log('Mobile STT: Restarting after error recovery');
              this.restartRecognition();
            }
          }, 1000);
        } else if (event.error === 'not-allowed') {
          console.error('Mobile STT: Microphone permission denied - user needs to grant permission');
          this.isListening = false;
          this.callbacks.onStateChange?.(false);
          // Show user-friendly error message
          this.callbacks.onError?.('Microphone permission denied. Please allow microphone access and try again.');
        } else if (event.error === 'service-not-allowed') {
          console.error('Mobile STT: Speech recognition service not allowed');
          this.isListening = false;
          this.callbacks.onStateChange?.(false);
          this.callbacks.onError?.('Speech recognition service not allowed. Please check your browser settings.');
        } else if (event.error === 'aborted') {
          console.log('Mobile STT: Recognition aborted - this is normal on mobile');
          // Don't treat aborted as an error on mobile, but try to restart
          if (this.isMobile && !this.isRestarting) {
            console.log('Mobile STT: Auto-restarting after abort (mobile)');
            setTimeout(() => {
              if (!this.isRestarting) {
                this.restartRecognition();
              }
            }, 500);
          }
        } else if (event.error === 'language-not-supported') {
          console.error('Mobile STT: Language not supported:', this.config.language);
          this.callbacks.onError?.('Language not supported. Please try a different language.');
        } else {
          // For any other error, try to restart on mobile
          console.log('Mobile STT: Unknown error, attempting restart:', event.error);
          if (this.isMobile && !this.isRestarting) {
            setTimeout(() => {
              if (!this.isRestarting) {
                this.restartRecognition();
              }
            }, 2000);
          }
        }
      };

      this.recognition.onnomatch = () => {
        console.log('Mobile STT: No speech was recognized');
      };

      this.isInitialized = true;
      console.log('Mobile STT: Service initialized successfully');
      return true;
    } catch (error) {
      console.error('Mobile STT: Initialization failed:', error);
      return false;
    }
  }

  /**
   * Start speech recognition
   */
  public start(): boolean {
    console.log('Mobile STT: Start called', {
      isInitialized: this.isInitialized,
      recognitionExists: !!this.recognition,
      isListening: this.isListening,
      isRestarting: this.isRestarting,
      isMobile: this.isMobile,
      isSupported: this.isSupported
    });
    
    if (!this.isSupported) {
      console.log('Mobile STT: Speech recognition not supported on this device');
      return false;
    }
    
    if (!this.isInitialized || !this.recognition) {
      console.log('Mobile STT: Service not initialized');
      return false;
    }

    if (this.isListening) {
      console.log('Mobile STT: Already listening');
      return true;
    }

    if (this.isRestarting) {
      console.log('Mobile STT: Currently restarting, will start after restart completes');
      return false;
    }

    try {
      console.log('Mobile STT: Calling recognition.start()...');
      this.isRestarting = false;
      
      // Mobile-specific: Handle Chrome recording conflicts
      if (this.isMobile) {
        console.log('Mobile STT: Mobile device detected, handling Chrome conflicts...');
        
        // Try to stop any existing audio contexts that might conflict
        this.stopConflictingAudio();
        
        // Use a longer delay for mobile to ensure audio cleanup
        setTimeout(() => {
          try {
            console.log('Mobile STT: Attempting to start recognition on mobile...');
            this.recognition.start();
            console.log('Mobile STT: Started successfully (mobile)');
          } catch (error) {
            console.error('Mobile STT: Start failed (mobile):', error);
            
            // If it's a Chrome recording conflict, try again with longer delay
            if (error && typeof error === 'object' && 'message' in error && 
                typeof error.message === 'string' && error.message.includes('recording')) {
              console.log('Mobile STT: Chrome recording conflict detected, retrying...');
              setTimeout(() => {
                try {
                  this.recognition.start();
                  console.log('Mobile STT: Retry successful after Chrome conflict');
                } catch (retryError) {
                  console.error('Mobile STT: Retry failed:', retryError);
                  this.handleStartError(retryError);
                }
              }, 2000);
            } else {
              this.handleStartError(error);
            }
          }
        }, 500); // Longer delay for mobile
        return true; // Return true immediately for mobile
      } else {
        console.log('Mobile STT: Desktop device, starting immediately');
        this.recognition.start();
        console.log('Mobile STT: Started successfully');
        return true;
      }
    } catch (error) {
      console.error('Mobile STT: Start failed:', error);
      this.handleStartError(error);
      return false;
    }
  }

  /**
   * Stop conflicting audio contexts that might interfere with speech recognition
   */
  private stopConflictingAudio(): void {
    try {
      // Get all audio contexts from the global scope
      const audioContexts = (window as any).audioContexts || [];
      
      // Close any existing audio contexts
      audioContexts.forEach((ctx: AudioContext) => {
        if (ctx && ctx.state !== 'closed') {
          ctx.close();
          console.log('Mobile STT: Closed conflicting audio context');
        }
      });
      
      // Clear the global audio contexts array
      (window as any).audioContexts = [];
      
      // Also try to stop any media streams
      if (navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function') {
        // This will help release any active microphone streams
        console.log('Mobile STT: Attempting to release microphone resources...');
      }
      
    } catch (error) {
      console.log('Mobile STT: Error stopping conflicting audio:', error);
    }
  }

  /**
   * Handle start errors
   */
  private handleStartError(error: any): void {
    console.error('Mobile STT: Handling start error:', error);
    
    // Try to restart if start fails
    setTimeout(() => {
      if (!this.isRestarting) {
        console.log('Mobile STT: Attempting restart after start error');
        this.restartRecognition();
      }
    }, 1000);
  }

  /**
   * Stop speech recognition
   */
  public stop(): void {
    if (this.recognition && this.isListening) {
      this.isRestarting = true;
      this.recognition.stop();
      console.log('Mobile STT: Stopped');
    }
    
    if (this.restartTimeout) {
      clearTimeout(this.restartTimeout);
      this.restartTimeout = null;
    }
  }

  /**
   * Restart speech recognition (mobile-specific)
   */
  private restartRecognition(): void {
    if (this.isRestarting || !this.recognition) {
      console.log('Mobile STT: Restart skipped - already restarting or no recognition');
      return;
    }
    
    console.log('Mobile STT: Starting restart process...');
    this.isRestarting = true;
    
    // Clear any existing restart timeout
    if (this.restartTimeout) {
      clearTimeout(this.restartTimeout);
    }
    
    this.restartTimeout = setTimeout(() => {
      try {
        console.log('Mobile STT: Attempting to restart recognition...');
        this.recognition.start();
        console.log('Mobile STT: Restarted successfully');
        this.isRestarting = false;
      } catch (error) {
        console.error('Mobile STT: Restart failed:', error);
        this.isRestarting = false;
        
        // Try again after a longer delay, but limit retries
        setTimeout(() => {
          if (this.isListening) {
            console.log('Mobile STT: Retrying restart after failure...');
            this.restartRecognition();
          }
        }, 2000);
      }
    }, 100);
  }

  /**
   * Handle speech recognition results
   */
  private handleResult(event: any): void {
    let interimTranscript = '';
    let finalTranscript = '';
    let maxConfidence = 0;

    console.log('Mobile STT: Processing results', {
      resultIndex: event.resultIndex,
      resultsLength: event.results.length
    });

    // Process all results
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const transcript = result[0].transcript;
      const confidence = result[0].confidence || 0.3; // Lower default confidence for mobile
      
      console.log('Mobile STT: Processing result', {
        index: i,
        transcript,
        confidence,
        isFinal: result.isFinal
      });
      
      maxConfidence = Math.max(maxConfidence, confidence);
      
      if (result.isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }

    // Handle interim results - send immediately for instant feedback
    if (interimTranscript && interimTranscript.trim()) {
      console.log('Mobile STT: Sending interim result:', interimTranscript);
      this.callbacks.onResult?.(interimTranscript.trim(), maxConfidence, false);
    }

    // Handle final results with mobile-specific debouncing
    if (finalTranscript) {
      const trimmedTranscript = finalTranscript.trim();
      
      console.log('Mobile STT: Processing final result:', trimmedTranscript);
      
      // Mobile-specific debouncing to prevent duplicate processing
      const currentTime = Date.now();
      
      // Check if this is a duplicate transcript within 1 second (shorter for mobile)
      if (trimmedTranscript === this.lastProcessedTranscript && 
          currentTime - this.lastProcessedTime < 1000) {
        console.log('Mobile STT: Ignoring duplicate transcript:', trimmedTranscript);
        return;
      }
      
      // Check for empty or very short transcripts (more lenient for mobile)
      if (trimmedTranscript.length < 1) {
        console.log('Mobile STT: Ignoring short transcript:', trimmedTranscript);
        return;
      }
      
      // Clear any existing processing timeout
      if (this.processingTimeout) {
        clearTimeout(this.processingTimeout);
      }
      
      // Set processing timeout to prevent rapid duplicates (shorter for mobile)
      this.processingTimeout = setTimeout(() => {
        console.log('Mobile STT: Sending final result:', trimmedTranscript);
        this.callbacks.onResult?.(trimmedTranscript, maxConfidence, true);
        this.lastProcessedTranscript = trimmedTranscript;
        this.lastProcessedTime = currentTime;
      }, 50); // Shorter timeout for mobile
    }
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<MobileSTTConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    if (this.recognition) {
      this.recognition.lang = this.config.language;
      this.recognition.continuous = this.config.continuous;
      this.recognition.interimResults = this.config.interimResults;
      this.recognition.maxAlternatives = this.config.maxAlternatives;
    }
  }

  /**
   * Set WebSocket connection (optional for mobile STT)
   */
  public setWebSocket(websocket: WebSocket): void {
    this.websocket = websocket;
    console.log('Mobile STT: WebSocket set (optional for basic functionality)');
  }

  /**
   * Get current status
   */
  public getStatus(): { isListening: boolean; isInitialized: boolean; isSupported: boolean; isRestarting: boolean } {
    return {
      isListening: this.isListening,
      isInitialized: this.isInitialized,
      isSupported: this.isSupported,
      isRestarting: this.isRestarting
    };
  }

  /**
   * Check if service is ready to start
   */
  public isReady(): boolean {
    return this.isInitialized && !this.isRestarting && this.recognition !== null;
  }

  /**
   * Destroy the service
   */
  public destroy(): void {
    this.stop();
    
    if (this.processingTimeout) {
      clearTimeout(this.processingTimeout);
      this.processingTimeout = null;
    }
    
    if (this.restartTimeout) {
      clearTimeout(this.restartTimeout);
      this.restartTimeout = null;
    }
    
    this.recognition = null;
    this.isInitialized = false;
    this.isListening = false;
    this.websocket = null;
    
    console.log('Mobile STT: Service destroyed');
  }
}

export default MobileSTTService;

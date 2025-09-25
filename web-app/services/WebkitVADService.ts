/**
 * Professional WebkitSpeechRecognition VAD Service
 * Provides Voice Activity Detection with real-time speech recognition
 */

export interface VADConfig {
  language: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  confidenceThreshold: number;
  silenceTimeout: number;
  speechTimeout: number;
  restartDelay: number;
}

export interface VADCallbacks {
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

export interface SpeechResult {
  transcript: string;
  isFinal: boolean;
  confidence: number;
  timestamp: number;
}

export class WebkitVADService {
  private recognition: any = null;
  private config: VADConfig;
  private callbacks: VADCallbacks;
  private isListening: boolean = false;
  private isInitialized: boolean = false;
  private silenceTimer: number | null = null;
  private speechTimer: number | null = null;
  private lastSpeechTime: number = 0;
  private currentTranscript: string = '';
  private isSupported: boolean = false;
  private websocket: WebSocket | null = null;
  
  // Mobile-specific fixes
  private isMobile: boolean = false;
  private lastProcessedTranscript: string = '';
  private lastProcessedTime: number = 0;
  private processingTimeout: NodeJS.Timeout | null = null;
  
  // Voice Level Monitoring
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private microphone: MediaStream | null = null;
  private animationFrame: number | null = null;

  constructor(config: Partial<VADConfig> = {}, callbacks: VADCallbacks = {}) {
    // Detect mobile device first
    this.isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    this.config = {
      language: 'en-US',
      continuous: true,
      interimResults: true,
      maxAlternatives: 1,
      confidenceThreshold: 0.7,
      silenceTimeout: this.isMobile ? 999999999 : 8000, // Never timeout on mobile (~11 days), 8 seconds on desktop
      speechTimeout: this.isMobile ? 999999999 : 30000, // Never timeout on mobile, 30 seconds on desktop
      restartDelay: 100,
      ...config
    };
    
    this.callbacks = callbacks;
    this.checkSupport();
  }

  /**
   * Check if WebkitSpeechRecognition is supported
   */
  private checkSupport(): void {
    this.isSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
    
    if (!this.isSupported) {
      console.warn('WebkitSpeechRecognition not supported in this browser');
      this.callbacks.onError?.('Speech recognition not supported');
    }
  }

  /**
   * Initialize the speech recognition service
   */
  public async initialize(): Promise<boolean> {
    if (!this.isSupported) {
      return false;
    }

    try {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      this.recognition = new SpeechRecognition();
      
      this.setupRecognition();
      this.isInitialized = true;
      
      return true;
    } catch (error) {
      console.error('Failed to initialize WebkitVADService:', error);
      this.callbacks.onError?.('Failed to initialize speech recognition');
      return false;
    }
  }

  /**
   * Setup recognition configuration and event handlers
   */
  private setupRecognition(): void {
    if (!this.recognition) return;

    // Configure recognition
    this.recognition.continuous = this.config.continuous;
    this.recognition.interimResults = this.config.interimResults;
    this.recognition.lang = this.config.language;
    this.recognition.maxAlternatives = this.config.maxAlternatives;

    // Event handlers
    this.recognition.onstart = this.handleStart.bind(this);
    this.recognition.onresult = this.handleResult.bind(this);
    this.recognition.onerror = this.handleError.bind(this);
    this.recognition.onend = this.handleEnd.bind(this);
    this.recognition.onspeechstart = this.handleSpeechStart.bind(this);
    this.recognition.onspeechend = this.handleSpeechEnd.bind(this);
    this.recognition.onsoundstart = this.handleSoundStart.bind(this);
    this.recognition.onsoundend = this.handleSoundEnd.bind(this);
    this.recognition.onnomatch = this.handleNoMatch.bind(this);
  }

  /**
   * Start voice activity detection
   */
  public start(): boolean {
    if (!this.isInitialized || !this.isSupported) {
      console.error('WebkitVADService not initialized or not supported');
      return false;
    }

    if (this.isListening) {
      console.warn('VAD is already listening');
      return true;
    }

    try {
      // Ensure recognition is properly set up before starting
      if (!this.recognition) {
        const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.setupRecognition();
      }

      this.recognition.start();
      this.isListening = true;
      this.callbacks.onStateChange?.(true);
      
      // Initialize and start Voice Level monitoring (disabled on Android Chrome)
      this.initializeVoiceLevelMonitoring().then((success) => {
        if (success) {
          this.startVoiceLevelMonitoring();
        } else {
          // Provide a fallback voice level for Android Chrome
          this.provideFallbackVoiceLevel();
        }
      });
      
      return true;
    } catch (error) {
      console.error('Failed to start VAD:', error);
      this.callbacks.onError?.('Failed to start speech recognition');
      
      // Try to reinitialize if start fails
      setTimeout(() => {
        this.initialize().then((success) => {
          if (success) {
          }
        });
      }, 1000);
      
      return false;
    }
  }

  /**
   * Stop voice activity detection
   */
  public stop(): void {
    if (!this.isListening) return;

    try {
      if (this.recognition) {
        this.recognition.stop();
      }
      this.isListening = false;
      this.clearTimers();
      
      // Stop Voice Level monitoring
      this.stopVoiceLevelMonitoring();
      
      this.callbacks.onStateChange?.(false);
    } catch (error) {
      console.error('Failed to stop VAD:', error);
      // Force cleanup even if stop fails
      this.isListening = false;
      this.clearTimers();
      this.stopVoiceLevelMonitoring();
    }
  }


  /**
   * Restart voice activity detection (disabled for manual control)
   */
  private restart(): void {
    // Disabled auto-restart - only restart manually via start() method
    return;
  }

  /**
   * Handle recognition start
   */
  private handleStart(): void {
    this.lastSpeechTime = Date.now();
    this.startSpeechTimeout();
  }

  /**
   * Process final transcript (extracted for mobile debouncing)
   */
  private processFinalTranscript(transcript: string, confidence: number): void {
    const speechResult: SpeechResult = {
      transcript: transcript,
      isFinal: true,
      confidence: confidence,
      timestamp: Date.now()
    };

    // Call all relevant callbacks
    this.callbacks.onSpeechResult?.(speechResult.transcript, true, speechResult.confidence);
    this.callbacks.onFinalResult?.(speechResult.transcript, speechResult.confidence);
    
    // Send individual transcript to WebSocket immediately for instant processing
    this.sendToWebSocket('final_transcript', speechResult.transcript, speechResult.confidence);
  }

  /**
   * Handle speech recognition results
   */
  private handleResult(event: any): void {
    // CRITICAL: Check if we should ignore results (e.g., during AI speaking)
    // This prevents audio loop where AI speech gets transcribed again
    if (!this.isListening) {
      console.log('VAD: Ignoring speech result - not listening');
      return;
    }

    let interimTranscript = '';
    let finalTranscript = '';
    let maxConfidence = 0;

    // Process all results
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const transcript = result[0].transcript;
      const confidence = result[0].confidence || 0;

      maxConfidence = Math.max(maxConfidence, confidence);

      if (result.isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }

    // Update current transcript
    this.currentTranscript = finalTranscript || interimTranscript;

    // Handle final results - send individual speech (not accumulated)
    if (finalTranscript) {
      this.lastSpeechTime = Date.now();
      this.clearSilenceTimer();
      this.startSpeechTimeout();

      // Mobile-specific debouncing to prevent duplicate processing
      if (this.isMobile) {
        const trimmedTranscript = finalTranscript.trim();
        const currentTime = Date.now();
        
        // Check if this is a duplicate transcript within 2 seconds
        if (trimmedTranscript === this.lastProcessedTranscript && 
            currentTime - this.lastProcessedTime < 2000) {
          console.log('Mobile: Ignoring duplicate transcript:', trimmedTranscript);
          return;
        }
        
        // Clear any existing processing timeout
        if (this.processingTimeout) {
          clearTimeout(this.processingTimeout);
        }
        
        // Set processing timeout to prevent rapid duplicates
        this.processingTimeout = setTimeout(() => {
          this.processFinalTranscript(trimmedTranscript, maxConfidence);
          this.lastProcessedTranscript = trimmedTranscript;
          this.lastProcessedTime = currentTime;
        }, 100); // 100ms delay for mobile
      } else {
        // Desktop: process immediately
        this.processFinalTranscript(finalTranscript.trim(), maxConfidence);
      }
    }

    // Handle interim results - send immediately for instant feedback
    if (interimTranscript && !finalTranscript) {
      this.lastSpeechTime = Date.now();
      this.clearSilenceTimer();
      this.startSpeechTimeout();

      // Send individual interim transcript (not accumulated)
      const speechResult: SpeechResult = {
        transcript: interimTranscript.trim(),
        isFinal: false,
        confidence: maxConfidence,
        timestamp: Date.now()
      };

      // Call all relevant callbacks
      this.callbacks.onSpeechResult?.(speechResult.transcript, false, speechResult.confidence);
      this.callbacks.onInterimResult?.(speechResult.transcript, speechResult.confidence);
      
      // Send interim result to WebSocket immediately for instant feedback
      this.sendToWebSocket('interim_transcript', speechResult.transcript, speechResult.confidence);
    }
  }

  /**
   * Handle speech start
   */
  private handleSpeechStart(): void {
    this.lastSpeechTime = Date.now();
    this.clearSilenceTimer();
    this.startSpeechTimeout();
    this.callbacks.onSpeechStart?.();
  }

  /**
   * Handle speech end
   */
  private handleSpeechEnd(): void {
    this.startSilenceTimer();
    this.callbacks.onSpeechEnd?.();
  }

  /**
   * Handle sound start
   */
  private handleSoundStart(): void {
    this.lastSpeechTime = Date.now();
    this.clearSilenceTimer();
  }

  /**
   * Handle sound end
   */
  private handleSoundEnd(): void {
    this.startSilenceTimer();
  }

  /**
   * Handle no match
   */
  private handleNoMatch(): void {
    // On mobile, don't start silence timer to keep mic active
    if (!this.isMobile) {
      this.startSilenceTimer();
    }
  }

  /**
   * Handle errors
   */
  private handleError(event: any): void {
    console.error('Speech recognition error:', event.error);
    
    let errorMessage = 'Unknown error';
    switch (event.error) {
      case 'no-speech':
        errorMessage = 'No speech detected';
        // On mobile, don't start silence timer to keep mic active
        if (!this.isMobile) {
          this.startSilenceTimer();
        }
        break;
      case 'audio-capture':
        errorMessage = 'Microphone not accessible';
        break;
      case 'not-allowed':
        errorMessage = 'Microphone permission denied';
        break;
      case 'network':
        errorMessage = 'Network error';
        break;
      case 'aborted':
        errorMessage = 'Speech recognition aborted';
        break;
      default:
        errorMessage = `Speech recognition error: ${event.error}`;
    }

    this.callbacks.onError?.(errorMessage);
    
    // Always restart on mobile to keep mic active, restart on desktop for recoverable errors
    if (this.isMobile || ['no-speech', 'aborted'].includes(event.error)) {
      this.restart();
    }
  }

  /**
   * Handle recognition end
   */
  private handleEnd(): void {
    const wasListening = this.isListening;
    this.isListening = false;
    this.clearTimers();
    this.callbacks.onStateChange?.(false);
    
    // Mobile-specific: Auto-restart to prevent microphone from turning off
    if (this.isMobile && wasListening) {
      console.log('VAD: Auto-restarting on mobile to keep microphone active');
      setTimeout(() => {
        if (!this.isListening) {
          this.restart();
        }
      }, this.config.restartDelay);
    }
    
    // Disabled auto-restart for manual control
  }

  /**
   * Start silence detection timer
   */
  private startSilenceTimer(): void {
    // Disabled silence timer for manual control
    return;
  }

  /**
   * Clear silence timer
   */
  private clearSilenceTimer(): void {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
  }

  /**
   * Start speech timeout timer (disabled for manual control)
   */
  private startSpeechTimeout(): void {
    // Disabled speech timeout for manual control
    return;
  }

  /**
   * Clear speech timer
   */
  private clearSpeechTimer(): void {
    if (this.speechTimer) {
      clearTimeout(this.speechTimer);
      this.speechTimer = null;
    }
  }

  /**
   * Clear all timers
   */
  private clearTimers(): void {
    this.clearSilenceTimer();
    this.clearSpeechTimer();
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<VADConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    if (this.recognition) {
      this.recognition.lang = this.config.language;
      this.recognition.continuous = this.config.continuous;
      this.recognition.interimResults = this.config.interimResults;
      this.recognition.maxAlternatives = this.config.maxAlternatives;
    }
  }

  /**
   * Get current status
   */
  public getStatus() {
    return {
      isSupported: this.isSupported,
      isInitialized: this.isInitialized,
      isListening: this.isListening,
      currentTranscript: this.currentTranscript,
      config: this.config
    };
  }

  /**
   * Set WebSocket connection for sending transcripts
   */
  public setWebSocket(websocket: WebSocket): void {
    this.websocket = websocket;
  }

  /**
   * Send transcript to WebSocket
   */
  private sendToWebSocket(type: string, text: string, confidence?: number): void {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      const message = {
        type,
        text: text.trim(),
        ...(confidence !== undefined && { confidence })
      };
      this.websocket.send(JSON.stringify(message));
    }
  }

  /**
   * Initialize Voice Level Monitoring
   */
  private async initializeVoiceLevelMonitoring(): Promise<boolean> {
    try {
      
      // Check if we're on Android Chrome - disable voice level monitoring to avoid microphone conflict
      const isAndroidChrome = /Android.*Chrome/.test(navigator.userAgent);
      if (isAndroidChrome) {
        return false;
      }
      
      // Get microphone access
      this.microphone = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          sampleRate: 48000,
        },
      });

      // Create audio context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // Create analyser
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.2;

      // Connect microphone to analyser
      const source = this.audioContext.createMediaStreamSource(this.microphone);
      source.connect(this.analyser);


      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Start Voice Level Monitoring with Advanced Detection
   */
  private startVoiceLevelMonitoring(): void {
    if (!this.analyser || !this.isListening) return;

    
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    const timeDomainArray = new Uint8Array(this.analyser.frequencyBinCount);
    let frameCount = 0;
    let silenceFrames = 0;
    let voiceFrames = 0;
    let lastVoiceLevel = 0;
    let noiseFloor = 0.01; // Initial noise floor estimate
    let voiceThreshold = 0.02; // Minimum threshold for voice detection

    const monitor = () => {
      if (!this.isListening || !this.analyser) return;

      // Get both frequency and time domain data
      this.analyser.getByteFrequencyData(dataArray);
      this.analyser.getByteTimeDomainData(timeDomainArray);
      
      // Calculate RMS from frequency data
      const rms = Math.sqrt(dataArray.reduce((sum, value) => sum + (value * value), 0) / dataArray.length) / 255;
      
      // Calculate RMS from time domain data (more accurate for voice)
      const timeRms = Math.sqrt(timeDomainArray.reduce((sum, value) => sum + ((value - 128) * (value - 128)), 0) / timeDomainArray.length) / 128;
      
      // Advanced voice detection algorithm
      const isVoiceDetected = this.detectVoice(dataArray, timeDomainArray, rms, timeRms, noiseFloor);
      
      // Update noise floor (adaptive threshold)
      if (!isVoiceDetected && rms < noiseFloor * 2) {
        noiseFloor = Math.max(noiseFloor * 0.99, rms * 0.5); // Slowly adapt noise floor
      }
      
      // Calculate final voice level
      let finalVoiceLevel = 0;
      if (isVoiceDetected) {
        voiceFrames++;
        silenceFrames = 0;
        
        // Use time domain RMS for more accurate voice level
        finalVoiceLevel = Math.min(timeRms / 0.1, 1.0); // Normalize to 0-1 range
        
        // Apply smoothing to prevent rapid fluctuations
        finalVoiceLevel = lastVoiceLevel * 0.7 + finalVoiceLevel * 0.3;
        lastVoiceLevel = finalVoiceLevel;
      } else {
        silenceFrames++;
        voiceFrames = Math.max(0, voiceFrames - 1);
        
        // Gradually decrease voice level during silence
        finalVoiceLevel = Math.max(0, lastVoiceLevel * 0.9);
        lastVoiceLevel = finalVoiceLevel;
      }
      
      // Enhanced debugging every 30 frames
      if (frameCount % 30 === 0) {
        // Debug information available but not logged
      }

      // Update voice level via callback only if voice is detected
      if (this.callbacks.onVoiceLevelUpdate) {
        this.callbacks.onVoiceLevelUpdate(finalVoiceLevel, 'vad-analyser');
      }
      
      frameCount++;
      this.animationFrame = requestAnimationFrame(monitor);
    };

    monitor();
  }

  /**
   * Advanced Voice Detection Algorithm
   */
  private detectVoice(freqData: Uint8Array, timeData: Uint8Array, rms: number, timeRms: number, noiseFloor: number): boolean {
    // Check basic thresholds
    if (rms < noiseFloor * 1.5 || timeRms < 0.01) {
      return false;
    }

    // Check frequency distribution (voice has specific frequency characteristics)
    const lowFreq = freqData.slice(0, Math.floor(freqData.length * 0.3)).reduce((sum, val) => sum + val, 0);
    const midFreq = freqData.slice(Math.floor(freqData.length * 0.3), Math.floor(freqData.length * 0.7)).reduce((sum, val) => sum + val, 0);
    const highFreq = freqData.slice(Math.floor(freqData.length * 0.7)).reduce((sum, val) => sum + val, 0);
    
    const totalFreq = lowFreq + midFreq + highFreq;
    if (totalFreq === 0) return false;
    
    const lowRatio = lowFreq / totalFreq;
    const midRatio = midFreq / totalFreq;
    const highRatio = highFreq / totalFreq;
    
    // Voice typically has more energy in mid frequencies (300Hz - 3400Hz)
    const voiceFrequencyScore = midRatio * 2 + lowRatio * 1.5 + highRatio * 0.5;
    
    // Check time domain characteristics (voice has more variation)
    const timeVariation = this.calculateTimeVariation(timeData);
    
    // Check for voice-like patterns
    const voicePatternScore = this.detectVoicePatterns(freqData);
    
    // Combined voice detection score
    const voiceScore = voiceFrequencyScore * 0.4 + timeVariation * 0.3 + voicePatternScore * 0.3;
    
    // Voice detection threshold
    const isVoice = voiceScore > 0.3 && rms > noiseFloor * 2 && timeRms > 0.015;
    
    return isVoice;
  }

  /**
   * Calculate time domain variation (voice has more variation than noise)
   */
  private calculateTimeVariation(timeData: Uint8Array): number {
    let variation = 0;
    for (let i = 1; i < timeData.length; i++) {
      variation += Math.abs(timeData[i] - timeData[i - 1]);
    }
    return variation / (timeData.length * 255);
  }

  /**
   * Detect voice-like patterns in frequency data
   */
  private detectVoicePatterns(freqData: Uint8Array): number {
    // Look for harmonic patterns typical of voice
    let patternScore = 0;
    const windowSize = 8;
    
    for (let i = 0; i < freqData.length - windowSize; i += windowSize) {
      const window = freqData.slice(i, i + windowSize);
      const max = Math.max(...window);
      const avg = window.reduce((sum, val) => sum + val, 0) / window.length;
      
      // Voice has peaks and valleys
      if (max > avg * 1.5) {
        patternScore += 0.1;
      }
    }
    
    return Math.min(patternScore, 1.0);
  }

  /**
   * Provide fallback voice level for Android Chrome
   */
  private provideFallbackVoiceLevel(): void {
    
    // Simulate voice level based on speech recognition events
    let fallbackLevel = 0;
    const fallbackInterval = setInterval(() => {
      if (!this.isListening) {
        clearInterval(fallbackInterval);
        return;
      }
      
      // Gradually increase voice level when speech is detected
      if (this.lastSpeechTime > 0 && Date.now() - this.lastSpeechTime < 2000) {
        fallbackLevel = Math.min(fallbackLevel + 0.1, 0.8);
      } else {
        fallbackLevel = Math.max(fallbackLevel - 0.05, 0);
      }
      
      // Update voice level via callback
      if (this.callbacks.onVoiceLevelUpdate) {
        this.callbacks.onVoiceLevelUpdate(fallbackLevel, 'fallback-android');
      }
    }, 100);
  }

  /**
   * Stop Voice Level Monitoring
   */
  private stopVoiceLevelMonitoring(): void {
    
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }

    if (this.microphone) {
      this.microphone.getTracks().forEach(track => track.stop());
      this.microphone = null;
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.analyser = null;
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    this.stop();
    this.stopVoiceLevelMonitoring();
    this.clearTimers();
    this.recognition = null;
    this.websocket = null;
    this.isInitialized = false;
  }
}

export default WebkitVADService;

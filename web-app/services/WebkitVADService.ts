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
  
  // Voice Level Monitoring
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private microphone: MediaStream | null = null;
  private animationFrame: number | null = null;

  constructor(config: Partial<VADConfig> = {}, callbacks: VADCallbacks = {}) {
    this.config = {
      language: 'en-US',
      continuous: true,
      interimResults: true,
      maxAlternatives: 1,
      confidenceThreshold: 0.7,
      silenceTimeout: 8000, // 8 seconds
      speechTimeout: 30000, // 30 seconds
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
      
      console.log('WebkitVADService initialized successfully');
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
        console.log('Reinitializing recognition...');
        const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.setupRecognition();
      }

      this.recognition.start();
      this.isListening = true;
      this.callbacks.onStateChange?.(true);
      console.log('✅ WebkitVADService started successfully');
      
      // Initialize and start Voice Level monitoring (disabled on Android Chrome)
      this.initializeVoiceLevelMonitoring().then((success) => {
        if (success) {
          this.startVoiceLevelMonitoring();
        } else {
          console.log("📱 Voice level monitoring disabled - using fallback voice level");
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
        console.log('Attempting to reinitialize WebkitVADService...');
        this.initialize().then((success) => {
          if (success) {
            console.log('WebkitVADService reinitialized successfully');
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
      console.log('✅ WebkitVADService stopped successfully');
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
    console.log('VAD restart requested but disabled for manual control');
    return;
  }

  /**
   * Handle recognition start
   */
  private handleStart(): void {
    console.log('Speech recognition started');
    this.lastSpeechTime = Date.now();
    this.startSpeechTimeout();
  }

  /**
   * Handle speech recognition results
   */
  private handleResult(event: any): void {
    console.log('🎤 Speech recognition result received:', event);
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
        console.log('🎤 Final transcript detected:', transcript);
      } else {
        interimTranscript += transcript;
        console.log('🎤 Interim transcript:', transcript);
      }
    }

    // Update current transcript
    this.currentTranscript = finalTranscript || interimTranscript;

    // Handle final results - send individual speech (not accumulated)
    if (finalTranscript) {
      this.lastSpeechTime = Date.now();
      this.clearSilenceTimer();
      this.startSpeechTimeout();

      // Send individual final transcript (not accumulated)
      const speechResult: SpeechResult = {
        transcript: finalTranscript.trim(), // Send individual transcript
        isFinal: true,
        confidence: maxConfidence,
        timestamp: Date.now()
      };

      // Call all relevant callbacks
      this.callbacks.onSpeechResult?.(speechResult.transcript, true, speechResult.confidence);
      this.callbacks.onFinalResult?.(speechResult.transcript, speechResult.confidence);
      
      // Send individual transcript to WebSocket immediately for instant processing
      this.sendToWebSocket('final_transcript', speechResult.transcript, speechResult.confidence);
      console.log('🎤 Individual transcript sent:', speechResult.transcript);
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
      console.log('🎤 Interim transcript sent immediately:', speechResult.transcript);
    }
  }

  /**
   * Handle speech start
   */
  private handleSpeechStart(): void {
    console.log('Speech started');
    this.lastSpeechTime = Date.now();
    this.clearSilenceTimer();
    this.startSpeechTimeout();
    this.callbacks.onSpeechStart?.();
  }

  /**
   * Handle speech end
   */
  private handleSpeechEnd(): void {
    console.log('Speech ended');
    this.startSilenceTimer();
    this.callbacks.onSpeechEnd?.();
  }

  /**
   * Handle sound start
   */
  private handleSoundStart(): void {
    console.log('Sound detected');
    this.lastSpeechTime = Date.now();
    this.clearSilenceTimer();
  }

  /**
   * Handle sound end
   */
  private handleSoundEnd(): void {
    console.log('Sound ended');
    this.startSilenceTimer();
  }

  /**
   * Handle no match
   */
  private handleNoMatch(): void {
    console.log('No speech match');
    this.startSilenceTimer();
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
        this.startSilenceTimer();
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
    
    // Restart if it's a recoverable error
    if (['no-speech', 'aborted'].includes(event.error)) {
      this.restart();
    }
  }

  /**
   * Handle recognition end
   */
  private handleEnd(): void {
    console.log('Speech recognition ended');
    const wasListening = this.isListening;
    this.isListening = false;
    this.clearTimers();
    this.callbacks.onStateChange?.(false);
    
    // Disabled auto-restart for manual control
    console.log('VAD ended - manual restart required');
  }

  /**
   * Start silence detection timer
   */
  private startSilenceTimer(): void {
    // Disabled silence timer for manual control
    console.log('Silence timer disabled for manual control');
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
    console.log('Speech timeout disabled for manual control');
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
    console.log('WebSocket set for VAD service');
  }

  /**
   * Send transcript to WebSocket
   */
  private sendToWebSocket(type: string, text: string, confidence?: number): void {
    console.log(`🎤 Attempting to send ${type} to WebSocket:`, {
      websocketExists: !!this.websocket,
      websocketState: this.websocket?.readyState,
      websocketOpen: this.websocket?.readyState === WebSocket.OPEN,
      text: text.trim()
    });
    
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      const message = {
        type,
        text: text.trim(),
        ...(confidence !== undefined && { confidence })
      };
      this.websocket.send(JSON.stringify(message));
      console.log(`✅ Sent to WebSocket: ${type}`, message);
    } else {
      console.error(`❌ Cannot send ${type} to WebSocket:`, {
        websocketExists: !!this.websocket,
        websocketState: this.websocket?.readyState,
        websocketOpen: this.websocket?.readyState === WebSocket.OPEN
      });
    }
  }

  /**
   * Initialize Voice Level Monitoring
   */
  private async initializeVoiceLevelMonitoring(): Promise<boolean> {
    try {
      console.log("🎤 Initializing Voice Level Monitoring...");
      
      // Check if we're on Android Chrome - disable voice level monitoring to avoid microphone conflict
      const isAndroidChrome = /Android.*Chrome/.test(navigator.userAgent);
      if (isAndroidChrome) {
        console.log("📱 Android Chrome detected - disabling voice level monitoring to prevent microphone conflict");
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

      console.log("✅ Voice Level Monitoring Initialized:", {
        sampleRate: this.audioContext.sampleRate,
        fftSize: this.analyser.fftSize,
        frequencyBinCount: this.analyser.frequencyBinCount
      });

      return true;
    } catch (error) {
      console.log("❌ Voice Level Monitoring Failed:", error);
      return false;
    }
  }

  /**
   * Start Voice Level Monitoring with Advanced Detection
   */
  private startVoiceLevelMonitoring(): void {
    if (!this.analyser || !this.isListening) return;

    console.log("🎤 Starting Advanced Voice Level Monitoring...");
    
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
        console.log("🎤 Advanced Voice Detection:", {
          frame: frameCount,
          rms: rms.toFixed(4),
          timeRms: timeRms.toFixed(4),
          isVoiceDetected,
          finalVoiceLevel: finalVoiceLevel.toFixed(4),
          noiseFloor: noiseFloor.toFixed(4),
          voiceThreshold: voiceThreshold.toFixed(4),
          voiceFrames,
          silenceFrames,
          maxValue: Math.max(...dataArray),
          avgValue: dataArray.reduce((a, b) => a + b, 0) / dataArray.length
        });
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
    console.log("📱 Providing fallback voice level for Android Chrome");
    
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
    console.log("🎤 Stopping Voice Level Monitoring...");
    
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
    console.log('WebkitVADService destroyed');
  }
}

export default WebkitVADService;

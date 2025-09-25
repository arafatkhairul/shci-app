/**
 * Fallback VAD Service for browsers that don't support WebkitSpeechRecognition
 * Uses Web Audio API for basic voice activity detection
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
  // Updated interface to include speech result callbacks
}

export class FallbackVADService {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private microphone: MediaStreamAudioSourceNode | null = null;
  private stream: MediaStream | null = null;
  private config: FallbackVADConfig;
  private callbacks: FallbackVADCallbacks;
  private isListening: boolean = false;
  private isInitialized: boolean = false;
  private silenceTimer: number | null = null;
  private speechTimer: number | null = null;
  private animationFrame: number | null = null;
  private lastSpeechTime: number = 0;
  private isSpeechActive: boolean = false;

  constructor(config: Partial<FallbackVADConfig> = {}, callbacks: FallbackVADCallbacks = {}) {
    // Detect mobile device
    const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    this.config = {
      silenceThreshold: 0.01,
      silenceTimeout: isMobile ? 999999999 : 3000, // Never timeout on mobile (~11 days), 3 seconds on desktop
      speechTimeout: isMobile ? 999999999 : 10000, // Never timeout on mobile, 10 seconds on desktop
      sampleRate: 48000,
      fftSize: 256,
      smoothingTimeConstant: 0.8,
      ...config
    };
    
    this.callbacks = callbacks;
  }

  /**
   * Initialize the fallback VAD service
   */
  public async initialize(): Promise<boolean> {
    try {
      // Check if Web Audio API is supported
      if (!window.AudioContext && !(window as any).webkitAudioContext) {
        console.warn('Web Audio API not supported');
        return false;
      }

      // Request microphone access
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: this.config.sampleRate,
        },
      });

      // Create audio context
      const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioContext();
      
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // Create audio nodes
      this.microphone = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      
      // Configure analyser
      this.analyser.fftSize = this.config.fftSize;
      this.analyser.smoothingTimeConstant = this.config.smoothingTimeConstant;
      
      // Connect nodes
      this.microphone.connect(this.analyser);

      this.isInitialized = true;
      console.log('Fallback VAD Service initialized successfully');
      return true;
    } catch (error) {
      console.error('Failed to initialize Fallback VAD Service:', error);
      this.callbacks.onError?.('Failed to initialize fallback VAD service');
      return false;
    }
  }

  /**
   * Start voice activity detection
   */
  public start(): boolean {
    if (!this.isInitialized || this.isListening) {
      return false;
    }

    try {
      this.isListening = true;
      this.lastSpeechTime = Date.now();
      this.startSpeechTimeout();
      this.startAudioAnalysis();
      this.callbacks.onStateChange?.(true);
      console.log('Fallback VAD started');
      return true;
    } catch (error) {
      console.error('Failed to start Fallback VAD:', error);
      this.callbacks.onError?.('Failed to start fallback VAD');
      return false;
    }
  }

  /**
   * Stop voice activity detection
   */
  public stop(): void {
    if (!this.isListening) return;

    this.isListening = false;
    this.isSpeechActive = false;
    this.clearTimers();
    this.stopAudioAnalysis();
    this.callbacks.onStateChange?.(false);
    console.log('Fallback VAD stopped');
  }

  /**
   * Start audio analysis loop with Advanced Voice Detection
   */
  private startAudioAnalysis(): void {
    if (!this.analyser) return;

    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    const timeDomainArray = new Uint8Array(this.analyser.frequencyBinCount);
    let frameCount = 0;
    let silenceFrames = 0;
    let voiceFrames = 0;
    let lastVoiceLevel = 0;
    let noiseFloor = 0.01; // Initial noise floor estimate
    
    const analyzeAudio = () => {
      if (!this.isListening || !this.analyser) return;

      // Get both frequency and time domain data
      this.analyser.getByteFrequencyData(dataArray);
      this.analyser.getByteTimeDomainData(timeDomainArray);
      
      // Calculate RMS from frequency data
      const rms = Math.sqrt(
        dataArray.reduce((sum, value) => sum + (value * value), 0) / dataArray.length
      ) / 255;

      // Calculate RMS from time domain data (more accurate for voice)
      const timeRms = Math.sqrt(
        timeDomainArray.reduce((sum, value) => sum + ((value - 128) * (value - 128)), 0) / timeDomainArray.length
      ) / 128;

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
        console.log("🎤 Fallback Advanced Voice Detection:", {
          frame: frameCount,
          rms: rms.toFixed(4),
          timeRms: timeRms.toFixed(4),
          isVoiceDetected,
          finalVoiceLevel: finalVoiceLevel.toFixed(4),
          noiseFloor: noiseFloor.toFixed(4),
          voiceFrames,
          silenceFrames,
          maxValue: Math.max(...dataArray),
          avgValue: dataArray.reduce((a, b) => a + b, 0) / dataArray.length
        });
      }

      // Update Voice Level via callback only if voice is detected
      if (this.callbacks.onVoiceLevelUpdate) {
        this.callbacks.onVoiceLevelUpdate(finalVoiceLevel, 'fallback-analyser');
      }

      // Check if speech is detected for VAD functionality
      if (rms > this.config.silenceThreshold) {
        this.handleSpeechDetected();
      } else {
        this.handleSilenceDetected();
      }

      frameCount++;
      this.animationFrame = requestAnimationFrame(analyzeAudio);
    };

    analyzeAudio();
  }

  /**
   * Advanced Voice Detection Algorithm for Fallback VAD
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
   * Stop audio analysis loop
   */
  private stopAudioAnalysis(): void {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
  }

  /**
   * Handle speech detection
   */
  private handleSpeechDetected(): void {
    this.lastSpeechTime = Date.now();
    this.clearSilenceTimer();
    this.startSpeechTimeout();

    if (!this.isSpeechActive) {
      this.isSpeechActive = true;
      this.callbacks.onSpeechStart?.();
      console.log('Fallback VAD: Speech detected');
    }
  }

  /**
   * Handle silence detection
   */
  private handleSilenceDetected(): void {
    if (this.isSpeechActive) {
      this.startSilenceTimer();
    }
  }

  /**
   * Start silence detection timer
   */
  private startSilenceTimer(): void {
    this.clearSilenceTimer();
    this.silenceTimer = window.setTimeout(() => {
      if (this.isSpeechActive) {
        this.isSpeechActive = false;
        this.callbacks.onSpeechEnd?.();
        this.callbacks.onSilenceDetected?.();
        console.log('Fallback VAD: Silence detected');
      }
    }, this.config.silenceTimeout);
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
   * Start speech timeout timer
   */
  private startSpeechTimeout(): void {
    this.clearSpeechTimer();
    this.speechTimer = window.setTimeout(() => {
      console.log('Fallback VAD: Speech timeout reached');
      this.stop();
    }, this.config.speechTimeout);
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
  public updateConfig(newConfig: Partial<FallbackVADConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    if (this.analyser) {
      this.analyser.fftSize = this.config.fftSize;
      this.analyser.smoothingTimeConstant = this.config.smoothingTimeConstant;
    }
  }

  /**
   * Get current status
   */
  public getStatus() {
    return {
      isInitialized: this.isInitialized,
      isListening: this.isListening,
      isSpeechActive: this.isSpeechActive,
      config: this.config
    };
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    this.stop();
    
    if (this.microphone) {
      try { this.microphone.disconnect(); } catch { }
      this.microphone = null;
    }
    
    if (this.analyser) {
      try { this.analyser.disconnect(); } catch { }
      this.analyser = null;
    }
    
    if (this.audioContext) {
      try { this.audioContext.close(); } catch { }
      this.audioContext = null;
    }
    
    if (this.stream) {
      try { this.stream.getTracks().forEach(track => track.stop()); } catch { }
      this.stream = null;
    }
    
    this.isInitialized = false;
    console.log('Fallback VAD Service destroyed');
  }
}

export default FallbackVADService;

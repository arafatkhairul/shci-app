"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import {
    Bot, Brain, Mic, Pause, Activity, Headphones, User, Database
} from "lucide-react";

// Environment Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://173.208.167.147:8000';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL || 'ws://173.208.167.147:8000';
const WS_PRODUCTION_URL = process.env.NEXT_PUBLIC_WS_PRODUCTION_URL || 'wss://api-llm.nodecel.cloud';
import { 
    FaGraduationCap, 
    FaUserTie, 
    FaCog, 
    FaPlay, 
    FaPause, 
    FaMicrophone,
    FaBuilding,
    FaSchool,
    FaUserGraduate,
    FaStar,
    FaStarHalfAlt,
    FaStarOfLife,
    FaChevronDown,
    FaTimes
} from "react-icons/fa";
import RolePlayAnswers from "./RolePlayAnswers";
import WebkitVADService, { VADConfig, VADCallbacks, SpeechResult } from "../services/WebkitVADService";
import FallbackVADService, { FallbackVADConfig, FallbackVADCallbacks } from "../services/VADFallbackService";

export default function VoiceAgent() {
    // ---------- State ----------
    const [connected, setConnected] = useState(false);
    const [listening, setListening] = useState(false);

    // Default: server TTS ON (local TTS OFF)
    const [useLocalTTS, setUseLocalTTS] = useState(false);

    // VAD Service State
    const [useWebkitVAD, setUseWebkitVAD] = useState(false);
    const [vadSupported, setVadSupported] = useState(false);
    const [vadInitialized, setVadInitialized] = useState(false);
    const [vadTranscript, setVadTranscript] = useState("");
    const [vadConfidence, setVadConfidence] = useState(0);
    const [useFallbackVAD, setUseFallbackVAD] = useState(false);
    const [fallbackVADInitialized, setFallbackVADInitialized] = useState(false);
    
    // Real-time Transcription State
    const [interimTranscript, setInterimTranscript] = useState("");
    const [finalTranscript, setFinalTranscript] = useState("");
    const [transcriptionHistory, setTranscriptionHistory] = useState<Array<{
        text: string;
        timestamp: number;
        confidence: number;
        isFinal: boolean;
    }>>([]);
    const [showTranscription, setShowTranscription] = useState(false);

    // Difficulty level state
    const [level, setLevel] = useState<"starter" | "medium" | "advanced">("starter");
    const [levelChangeNotification, setLevelChangeNotification] = useState(false);
    
    // Role play state
    const [rolePlayEnabled, setRolePlayEnabled] = useState(false);
    const [rolePlayTemplate, setRolePlayTemplate] = useState<"school" | "company" | "restaurant" | "hospital" | "custom">("school");
    const [organizationName, setOrganizationName] = useState("");
    const [organizationDetails, setOrganizationDetails] = useState("");
    const [roleTitle, setRoleTitle] = useState("");
    const [showRolePlayModal, setShowRolePlayModal] = useState(false);
    const [showRolePlayAnswers, setShowRolePlayAnswers] = useState(false);

    const [status, setStatus] = useState("Connecting…");
    const [transcript, setTranscript] = useState("");
    const [aiText, setAiText] = useState("");
    const [displayedAiText, setDisplayedAiText] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const [micLevel, setMicLevel] = useState(0);
    const [micLevelDebug, setMicLevelDebug] = useState({
        rawValue: 0,
        normalizedValue: 0,
        source: 'none',
        timestamp: 0
    });
    
    // Audio wave animation state
    const [waveAnimationFrame, setWaveAnimationFrame] = useState(0);
    
    // TTS Audio wave animation state
    const [ttsWaveAnimationFrame, setTtsWaveAnimationFrame] = useState(0);
    const [ttsAudioLevel, setTtsAudioLevel] = useState(0);

    // Professional mic level update function with advanced filtering
    const updateMicLevel = useCallback((rawValue: number, source: string) => {
        // Advanced filtering to prevent false positives
        let filteredValue = rawValue;
        
        // Apply source-specific filtering
        if (source === 'vad-analyser' || source === 'fallback-analyser') {
            // These sources already have advanced voice detection
            filteredValue = rawValue;
        } else {
            // For other sources, apply basic filtering
            filteredValue = rawValue > 0.01 ? rawValue : 0;
        }
        
        // Apply smoothing to prevent rapid fluctuations
        const currentLevel = micLevel;
        const smoothedValue = currentLevel * 0.8 + filteredValue * 0.2;
        
        const normalizedValue = Math.min(smoothedValue / 0.05, 1.0);
        
        setMicLevel(normalizedValue);
        setMicLevelDebug({
            rawValue: filteredValue,
            normalizedValue,
            source,
            timestamp: Date.now()
        });
        
        // Enhanced console logging with different levels
        if (filteredValue > 0.001) {
            console.log(`🎤 VOICE DETECTED [${source}]:`, {
                raw: filteredValue.toFixed(4),
                normalized: normalizedValue.toFixed(4),
                percentage: (normalizedValue * 100).toFixed(1) + '%',
                timestamp: new Date().toLocaleTimeString(),
                level: filteredValue > 0.01 ? 'HIGH' : filteredValue > 0.005 ? 'MEDIUM' : 'LOW',
                smoothed: smoothedValue.toFixed(4)
            });
        } else if (source === 'vad-analyser' && Math.random() < 0.01) { // Log 1% of silence frames
            console.log(`🔇 Silence [${source}]:`, {
                raw: filteredValue.toFixed(4),
                normalized: normalizedValue.toFixed(4),
                timestamp: new Date().toLocaleTimeString()
            });
        }
    }, [micLevel]);
    
    // Wave animation update effect
    useEffect(() => {
        if (listening) {
            const interval = setInterval(() => {
                setWaveAnimationFrame(prev => prev + 1);
            }, 100); // Update every 100ms for smooth animation
            
            return () => clearInterval(interval);
        } else {
            setWaveAnimationFrame(0);
        }
    }, [listening]);
    
    const [aiSpeaking, setAiSpeaking] = useState(false);
    const [selectedLanguage, setSelectedLanguage] = useState<"en" | "it">("en");
    const [isLanguageDropdownOpen, setIsLanguageDropdownOpen] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
    
    // TTS Audio wave animation effect
    useEffect(() => {
        if (aiSpeaking) {
            const interval = setInterval(() => {
                setTtsWaveAnimationFrame(prev => prev + 1);
                // Simulate audio level variation for TTS
                setTtsAudioLevel(prev => {
                    const variation = Math.sin(prev * 0.1) * 0.3 + 0.7;
                    return Math.max(0.3, Math.min(1.0, variation));
                });
            }, 100); // Update every 100ms for smooth animation
            
            return () => clearInterval(interval);
        } else {
            setTtsWaveAnimationFrame(0);
            setTtsAudioLevel(0);
        }
    }, [aiSpeaking]);

    // Track when waiting for AI response after speech
    useEffect(() => {
        // If we have a final transcript and we're not speaking or processing, we're waiting for response
        if (finalTranscript && !aiSpeaking && !isProcessing && listening) {
            setIsWaitingForResponse(true);
            console.log('🎯 Speech ended - waiting for AI response');
        } else if (aiSpeaking || isProcessing) {
            setIsWaitingForResponse(false);
        }
    }, [finalTranscript, aiSpeaking, isProcessing, listening]);

    // User type selection modal state
    const [showUserTypeModal, setShowUserTypeModal] = useState(false);
    const [userType, setUserType] = useState<"customer" | "org_owner" | null>(null);
    const [showOrgForm, setShowOrgForm] = useState(false);
    const [orgName, setOrgName] = useState("");
    const [orgNameError, setOrgNameError] = useState("");
    const [isSubmittingOrg, setIsSubmittingOrg] = useState(false);
    
    // Organization details modal state
    const [showOrgDetailsModal, setShowOrgDetailsModal] = useState(false);
    const [orgDetails, setOrgDetails] = useState("");
    const [isUpdatingDetails, setIsUpdatingDetails] = useState(false);
    
    // Customer organization selection state
    const [showOrgSelectionModal, setShowOrgSelectionModal] = useState(false);
    const [availableOrganizations, setAvailableOrganizations] = useState<Array<{id: number, name: string, details: string}>>([]);
    const [selectedOrgForCustomer, setSelectedOrgForCustomer] = useState<{id: number, name: string} | null>(null);
    const [isLoadingOrgs, setIsLoadingOrgs] = useState(false);
    
    // RAG system state - organization context for LLM
    const [organizationContext, setOrganizationContext] = useState<string>("");

    // Language dropdown ref for click outside detection
    const languageDropdownRef = useRef<HTMLDivElement>(null);

    // ---------- Refs ----------
    const ws = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<number | null>(null);
    const keepAliveTimer = useRef<number | null>(null);
    const audioCtx = useRef<AudioContext | null>(null);
    const sourceNode = useRef<MediaStreamAudioSourceNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const vadService = useRef<WebkitVADService | null>(null);
    const fallbackVADService = useRef<FallbackVADService | null>(null);
    const workletNode = useRef<AudioWorkletNode | null>(null);
    const processorNode = useRef<ScriptProcessorNode | null>(null);
    const analyser = useRef<AnalyserNode | null>(null);
    const muteGain = useRef<GainNode | null>(null);
    const listeningRef = useRef<boolean>(false);
    const currentAudioRef = useRef<HTMLAudioElement | null>(null);
    const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);
    const typingTimerRef = useRef<NodeJS.Timeout | null>(null);

    // ---------- Stable client_id ----------
    const getClientId = () => {
        try {
            const k = "shci_client_id";
            let id = localStorage.getItem(k);
            if (!id) {
                id = Math.random().toString(36).slice(2) + Date.now().toString(36);
                localStorage.setItem(k, id);
            }
            return id;
        } catch {
            return "anon";
        }
    };
    const clientIdRef = useRef<string>(getClientId());

    // ---------- Language labels ----------
    const languages = {
        en: {
            name: "English",
            flag: "🇺🇸",
            status: {
                connecting: "Connecting…",
                connected: "Connected • Ready for conversation",
                disconnected: "Disconnected • Reconnecting…",
                listening: "Listening • Speak now",
                paused: "Microphone paused",
            },
            levels: {
                starter: "Starter",
                medium: "Medium",
                advanced: "Advanced",
                starterDesc: "Slow & Simple",
                mediumDesc: "Natural & Clear",
                advancedDesc: "Fast & Rich",
                starterDetail: "CEFR A2 • Basic vocab • Simple sentences",
                mediumDetail: "CEFR B1-B2 • Intermediate • Natural flow",
                advancedDetail: "CEFR C1 • Rich vocab • Native-like",
            },
            labels: {
                title: "SHCI",
                subtitle: "Voice Agent",
                voiceControl: "Voice Control Center",
                voiceControlDesc: "Manage your voice interaction settings and controls",
                yourVoice: "Your Voice",
                yourVoiceDesc: "Real-time speech transcription",
                aiResponse: "AI Response",
                aiResponseDesc: "Intelligent conversation output",
                startConversation: "Start Conversation",
                pauseMicrophone: "Pause Microphone",
                localTTS: "Local TTS",
                localTTSDesc: "(faster response on device)",
                micLevel: "Voice Level",
                silence: "Silence",
                voiceInput: "Voice Input",
                readyToCapture: "Ready to capture your voice",
                startConversationHint: 'Click "Start Conversation" to begin',
                aiWillRespond: "AI will respond here",
                speakToGetResponse: "Start speaking to get intelligent responses",
                optimalExperience: "Optimal experience with headphones",
                naturalInterruption: "Natural voice interruption supported",
                realTimeProcessing: "Real-time voice processing",
                difficultyLevel: "Difficulty Level",
                difficultyLevelDesc: "Adjust conversation complexity and speed",
                originalText: "Original",
                correctedText: "Corrected",
                explanation: "Explanation",
            },
        },
        it: {
            name: "Italiano",
            flag: "🇮🇹",
            status: {
                connecting: "Connessione in corso…",
                connected: "Connesso • Pronto per la conversazione",
                disconnected: "Disconnesso • Riconnessione in corso…",
                listening: "In ascolto • Parla ora",
                paused: "Microfono in pausa",
            },
            levels: {
                starter: "Principiante",
                medium: "Intermedio",
                advanced: "Avanzato",
                starterDesc: "Lento & Semplice",
                mediumDesc: "Naturale & Chiaro",
                advancedDesc: "Veloce & Ricco",
                starterDetail: "CEFR A2 • Vocabolario base • Frasi semplici",
                mediumDetail: "CEFR B1-B2 • Intermedio • Flusso naturale",
                advancedDetail: "CEFR C1 • Vocabolario ricco • Come nativo",
            },
            labels: {
                title: "SHCI",
                subtitle: "Agente Vocale",
                voiceControl: "Centro di Controllo Vocale",
                voiceControlDesc: "Gestisci le impostazioni e i controlli dell'interazione vocale",
                yourVoice: "La Tua Voce",
                yourVoiceDesc: "Trascrizione vocale in tempo reale",
                aiResponse: "Risposta AI",
                aiResponseDesc: "Output conversazionale intelligente",
                startConversation: "Avvia Conversazione",
                pauseMicrophone: "Metti in Pausa il Microfono",
                localTTS: "TTS Locale",
                localTTSDesc: "(risposta più veloce sul dispositivo)",
                micLevel: "Livello della Voce",
                silence: "Silenzio",
                voiceInput: "Input Vocale",
                readyToCapture: "Pronto a catturare la tua voce",
                startConversationHint: 'Clicca "Avvia Conversazione" per iniziare',
                aiWillRespond: "L'AI risponderà qui",
                speakToGetResponse: "Inizia a parlare per ricevere risposte intelligenti",
                optimalExperience: "Esperienza ottimale con le cuffie",
                naturalInterruption: "Supportata l'interruzione vocale naturale",
                realTimeProcessing: "Elaborazione vocale in tempo reale",
                difficultyLevel: "Livello di Difficoltà",
                difficultyLevelDesc: "Regola la complessità e velocità della conversazione",
                originalText: "Originale",
                correctedText: "Corretto",
                explanation: "Spiegazione",
            },
        },
    } as const;

    const currentLang = languages[selectedLanguage];

    // Role play templates
    const rolePlayTemplates = {
        school: {
            name: "School",
            description: "Educational institution role play",
            defaultRole: "Teacher",
            icon: "🏫",
            placeholder: "e.g., ABC International School, 500 students, modern facilities..."
        },
        company: {
            name: "Software Company",
            description: "Business/tech company role play", 
            defaultRole: "Software Developer",
            icon: "🏢",
            placeholder: "e.g., TechCorp Solutions, 50 employees, web development..."
        },
        restaurant: {
            name: "Restaurant",
            description: "Food service role play",
            defaultRole: "Waiter",
            icon: "🍽️", 
            placeholder: "e.g., Golden Dragon Restaurant, Chinese cuisine, family-owned..."
        },
        hospital: {
            name: "Hospital",
            description: "Healthcare facility role play",
            defaultRole: "Nurse",
            icon: "🏥",
            placeholder: "e.g., City General Hospital, 200 beds, emergency care..."
        },
        custom: {
            name: "Custom Organization",
            description: "Your own organization role play",
            defaultRole: "Employee",
            icon: "🏢",
            placeholder: "e.g., Describe your organization..."
        }
    };

    // ---------- Load Saved Role Play State ----------
    useEffect(() => {
        // Load saved role play state from localStorage
        const savedRolePlay = localStorage.getItem('rolePlayState');
        if (savedRolePlay) {
            try {
                const rolePlayData = JSON.parse(savedRolePlay);
                setRolePlayEnabled(rolePlayData.enabled || false);
                setRolePlayTemplate(rolePlayData.template || "school");
                setOrganizationName(rolePlayData.organizationName || "");
                setOrganizationDetails(rolePlayData.organizationDetails || "");
                setRoleTitle(rolePlayData.roleTitle || "");
                console.log("Loaded role play state from localStorage:", rolePlayData);
            } catch (error) {
                console.error("Error loading role play state:", error);
            }
        }
    }, []);

    // ---------- Typing Animation Effect ----------
    useEffect(() => {
        if (typingTimerRef.current) clearTimeout(typingTimerRef.current);

        if (aiText && aiText !== displayedAiText) {
            setIsTyping(true);
            setDisplayedAiText("");
            let currentIndex = 0;
            const typeNextChar = () => {
                if (currentIndex < aiText.length) {
                    setDisplayedAiText(aiText.slice(0, currentIndex + 1));
                    currentIndex++;
                    typingTimerRef.current = setTimeout(typeNextChar, 30);
                } else {
                    setIsTyping(false);
                }
            };
            typeNextChar();
        } else if (!aiText) {
            setDisplayedAiText("");
            setIsTyping(false);
        }

        return () => {
            if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
        };
    }, [aiText]); // Remove displayedAiText from dependencies to prevent infinite loop


    // ---------- VAD Service Configuration ----------
    const vadConfig: VADConfig = {
        language: selectedLanguage === 'en' ? 'en-US' : 'it-IT',
        continuous: true,
        interimResults: true,
        maxAlternatives: 1,
        confidenceThreshold: 0.5, // Lowered for faster detection
        silenceTimeout: 2000, // Reduced to 2 seconds for instant response
        speechTimeout: 5000, // Reduced to 5 seconds for faster processing
        restartDelay: 50 // Reduced delay for faster restart
    };

    const fallbackVADConfig: FallbackVADConfig = {
        silenceThreshold: 0.01,
        silenceTimeout: 2000, // Reduced to 2 seconds for instant response
        speechTimeout: 5000, // Reduced to 5 seconds for faster processing
        sampleRate: 48000,
        fftSize: 256,
        smoothingTimeConstant: 0.8
    };

    const vadCallbacks: VADCallbacks = {
        onSpeechStart: () => {
            console.log('VAD: Speech started');
            setListening(true);
            setStatus(currentLang.status.listening);
            setShowTranscription(true);
        },
        onSpeechEnd: () => {
            console.log('VAD: Speech ended - keeping microphone active');
            // Don't automatically turn off microphone - keep it active for continuous listening
            setStatus(currentLang.status.connected);
        },
        onSpeechResult: (transcript: string, isFinal: boolean, confidence: number) => {
            console.log('VAD: Speech result', { transcript, isFinal, confidence });
            setVadTranscript(transcript);
            setVadConfidence(confidence);
            
            if (isFinal && transcript.trim()) {
                setTranscript(transcript);
                setFinalTranscript(transcript);
                setInterimTranscript("");
            }
        },
        onInterimResult: (transcript: string, confidence: number) => {
            console.log('VAD: Interim result', { transcript, confidence });
            setInterimTranscript(transcript);
            setVadTranscript(transcript);
            setVadConfidence(confidence);
        },
        onFinalResult: (transcript: string, confidence: number) => {
            console.log('VAD: Final result', { transcript, confidence });
            setFinalTranscript(transcript);
            setInterimTranscript("");
        },
        onSilenceDetected: () => {
            console.log('VAD: Silence detected - keeping microphone active');
            // Don't automatically turn off microphone - keep it active for continuous listening
            setStatus(currentLang.status.connected);
        },
        onError: (error: string) => {
            console.error('VAD Error:', error);
            setStatus(`VAD Error: ${error}`);
        },
        onStateChange: (isListening: boolean) => {
            console.log('VAD State changed:', isListening);
            // Keep listening state active throughout the session - don't let VAD control the main listening state
            // The microphone should only be controlled by Start/Stop button clicks
            if (isListening) {
                setListening(true);
            }
            // Don't set listening to false - let only the Stop button control that
        },
        onVoiceLevelUpdate: (level: number, source: string) => {
            console.log('VAD Voice Level Update:', { level, source });
            updateMicLevel(level, source);
        }
    };

    const fallbackVADCallbacks: FallbackVADCallbacks = {
        onSpeechStart: () => {
            console.log('Fallback VAD: Speech started');
            setListening(true);
            setStatus(currentLang.status.listening);
            setShowTranscription(true);
        },
        onSpeechEnd: () => {
            console.log('Fallback VAD: Speech ended - keeping microphone active');
            // Don't automatically turn off microphone - keep it active for continuous listening
            setStatus(currentLang.status.connected);
        },
        onSpeechResult: (transcript: string, isFinal: boolean, confidence: number) => {
            console.log('Fallback VAD: Speech result', { transcript, isFinal, confidence });
            setVadTranscript(transcript);
            setVadConfidence(confidence);
            
            if (isFinal && transcript.trim()) {
                setTranscript(transcript);
                setFinalTranscript(transcript);
                setInterimTranscript("");
            }
        },
        onInterimResult: (transcript: string, confidence: number) => {
            console.log('Fallback VAD: Interim result', { transcript, confidence });
            setInterimTranscript(transcript);
            setVadTranscript(transcript);
            setVadConfidence(confidence);
        },
        onFinalResult: (transcript: string, confidence: number) => {
            console.log('Fallback VAD: Final result', { transcript, confidence });
            setFinalTranscript(transcript);
            setInterimTranscript("");
        },
        onSilenceDetected: () => {
            console.log('Fallback VAD: Silence detected - keeping microphone active');
            // Don't automatically turn off microphone - keep it active for continuous listening
            setStatus(currentLang.status.connected);
        },
        onError: (error: string) => {
            console.error('Fallback VAD Error:', error);
            setStatus(`Fallback VAD Error: ${error}`);
        },
        onStateChange: (isListening: boolean) => {
            console.log('Fallback VAD State changed:', isListening);
            // Keep listening state active throughout the session - don't let VAD control the main listening state
            // The microphone should only be controlled by Start/Stop button clicks
            if (isListening) {
                setListening(true);
            }
            // Don't set listening to false - let only the Stop button control that
        },
        onVoiceLevelUpdate: (level: number, source: string) => {
            console.log('Fallback VAD Voice Level Update:', { level, source });
            updateMicLevel(level, source);
        }
    };

    // ---------- Send Level Preferences ----------
    // ✅ replace your sendPrefs with this version
    const sendPrefs = useCallback(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            // For customers, use RAG context; for org owners, use their organization details
            const currentOrgName = userType === 'customer' && selectedOrgForCustomer 
                ? selectedOrgForCustomer.name 
                : userType === 'org_owner' && orgName 
                ? orgName 
                : organizationName;
            
            const orgDetails = userType === 'customer' && organizationContext
                ? organizationContext
                : organizationDetails;
            
            const prefs = {
                type: "client_prefs",
                client_id: clientIdRef.current,
                level,
                use_local_tts: useLocalTTS,
                language: selectedLanguage,
                // role play fields (ALWAYS send)
                role_play_enabled: rolePlayEnabled,
                role_play_template: rolePlayTemplate,
                organization_name: currentOrgName,
                organization_details: orgDetails,
                role_title: roleTitle,
                // RAG context for customers
                rag_context: userType === 'customer' ? organizationContext : "",
            };
            console.log("🔍 STEP 11: Preparing to send prefs with RAG context");
            console.log("🔍 STEP 11a: User type:", userType);
            console.log("🔍 STEP 11b: Organization context:", organizationContext);
            console.log("🔍 STEP 11c: RAG context being sent:", prefs.rag_context);
            console.log("🔍 STEP 11d: RAG context length:", prefs.rag_context.length);
            console.log("🔍 STEP 11e: Full prefs object:", prefs);
            ws.current.send(JSON.stringify(prefs));
        }
    }, [
        level,
        useLocalTTS,
        selectedLanguage,
        rolePlayEnabled,
        rolePlayTemplate,
        organizationName,
        organizationDetails,
        roleTitle,
        userType,
        selectedOrgForCustomer,
        organizationContext,
    ]);

    // Monitor organization context changes and send preferences
    useEffect(() => {
        console.log('🔍 RAG DEBUG: Organization context changed:', organizationContext);
        console.log('🔍 RAG DEBUG: Context length:', organizationContext.length);
        
        // Send preferences to backend when organization context changes
        if (organizationContext && ws.current?.readyState === WebSocket.OPEN) {
            console.log('🔍 RAG DEBUG: Sending preferences due to context change');
            setTimeout(() => {
                sendPrefs();
            }, 200); // Small delay to ensure state is fully updated
        }
    }, [organizationContext, sendPrefs]);


    // ---------- VAD Service Management ----------
    const initializeVAD = useCallback(async () => {
        if (!vadService.current) {
            vadService.current = new WebkitVADService(vadConfig, vadCallbacks);
        }
        
        const success = await vadService.current.initialize();
        setVadSupported(success);
        setVadInitialized(success);
        
        if (success) {
            console.log('VAD Service initialized successfully');
            // Set WebSocket connection when available
            if (ws.current?.readyState === WebSocket.OPEN) {
                vadService.current.setWebSocket(ws.current);
            }
        } else {
            console.log('VAD Service not supported or failed to initialize');
        }
        
        return success;
    }, [vadConfig, vadCallbacks]);

    const initializeFallbackVAD = useCallback(async () => {
        if (!fallbackVADService.current) {
            fallbackVADService.current = new FallbackVADService(fallbackVADConfig, fallbackVADCallbacks);
        }
        
        const success = await fallbackVADService.current.initialize();
        setFallbackVADInitialized(success);
        
        if (success) {
            console.log('Fallback VAD Service initialized successfully');
        } else {
            console.log('Fallback VAD Service failed to initialize');
        }
        
        return success;
    }, [fallbackVADConfig, fallbackVADCallbacks]);

    const startVAD = useCallback(() => {
        console.log('🎤 Starting VAD service...', {
            webkitVADAvailable: !!vadService.current,
            webkitVADInitialized: vadInitialized,
            fallbackVADAvailable: !!fallbackVADService.current,
            fallbackVADInitialized: fallbackVADInitialized
        });
        
        if (vadService.current && vadInitialized) {
            const success = vadService.current.start();
            if (success) {
                setUseWebkitVAD(true);
                console.log('✅ Webkit VAD started successfully - Speech-to-text enabled');
                console.log('🎤 Webkit VAD Status:', vadService.current.getStatus());
            } else {
                console.log('❌ Failed to start Webkit VAD');
            }
            return success;
        }
        return false;
    }, [vadInitialized]);

    const stopVAD = useCallback(() => {
        if (vadService.current) {
            vadService.current.stop();
            setUseWebkitVAD(false);
            setVadTranscript("");
            setVadConfidence(0);
            console.log('VAD stopped');
        }
    }, []);

    const startFallbackVAD = useCallback(() => {
        if (fallbackVADService.current && fallbackVADInitialized) {
            const success = fallbackVADService.current.start();
            if (success) {
                setUseFallbackVAD(true);
                console.log('⚠️ Fallback VAD started successfully - Voice detection only (no speech-to-text)');
                console.log('🎤 Fallback VAD Status:', fallbackVADService.current.getStatus());
            } else {
                console.log('❌ Failed to start Fallback VAD');
            }
            return success;
        }
        return false;
    }, [fallbackVADInitialized]);

    const stopFallbackVAD = useCallback(() => {
        if (fallbackVADService.current) {
            fallbackVADService.current.stop();
            setUseFallbackVAD(false);
            console.log('Fallback VAD stopped');
        }
    }, []);

    const toggleVAD = useCallback(() => {
        if (useWebkitVAD) {
            stopVAD();
        } else {
            startVAD();
        }
    }, [useWebkitVAD, startVAD, stopVAD]);

    const toggleFallbackVAD = useCallback(() => {
        if (useFallbackVAD) {
            stopFallbackVAD();
        } else {
            startFallbackVAD();
        }
    }, [useFallbackVAD, startFallbackVAD, stopFallbackVAD]);

    // Update VAD config when language changes
    useEffect(() => {
        if (vadService.current && vadInitialized) {
            vadService.current.updateConfig({
                language: selectedLanguage === 'en' ? 'en-US' : 'it-IT'
            });
        }
    }, [selectedLanguage, vadInitialized]);

    // Monitor TTS speaking state - Ensure continuous speech recognition
    useEffect(() => {
        if (aiSpeaking) {
            console.log('🔊 TTS Speaking - Temporarily pausing VAD to prevent audio loop');
            // Temporarily pause VAD services during audio playback to prevent feedback
            if (useWebkitVAD && vadService.current) {
                vadService.current.stop();
            }
            if (useFallbackVAD && fallbackVADService.current) {
                fallbackVADService.current.stop();
            }
        } else {
            console.log('🔇 TTS Stopped - Restarting VAD for continuous speech recognition');
            // Restart VAD services after audio playback to ensure speech recognition continues
            setTimeout(() => {
                if (listening && !aiSpeaking) {
                    console.log('🔄 Restarting VAD services after audio playback...');
                    
                    if (useWebkitVAD && vadService.current && vadInitialized) {
                        try {
                            // Ensure WebSocket is still connected for VAD service
                            if (ws.current?.readyState === WebSocket.OPEN) {
                                vadService.current.setWebSocket(ws.current);
                            }
                            vadService.current.start();
                            console.log('✅ Webkit VAD restarted successfully after audio');
                        } catch (error) {
                            console.log('❌ Failed to restart Webkit VAD after audio:', error);
                            // Try to reinitialize if restart fails
                            setTimeout(() => {
                                initializeVAD().then((success) => {
                                    if (success && listening) {
                                        startVAD();
                                    }
                                });
                            }, 2000);
                        }
                    }
                    
                    if (useFallbackVAD && fallbackVADService.current && fallbackVADInitialized) {
                        try {
                            fallbackVADService.current.start();
                            console.log('✅ Fallback VAD restarted successfully after audio');
                        } catch (error) {
                            console.log('❌ Failed to restart Fallback VAD after audio:', error);
                            // Try to reinitialize if restart fails
                            setTimeout(() => {
                                initializeFallbackVAD().then((success) => {
                                    if (success && listening) {
                                        startFallbackVAD();
                                    }
                                });
                            }, 2000);
                        }
                    }
                }
            }, 1000); // 1 second delay to ensure audio has completely stopped
        }
    }, [aiSpeaking, useWebkitVAD, useFallbackVAD, listening, vadInitialized, fallbackVADInitialized]);

    // VAD Health Check - Ensure speech recognition continues working
    useEffect(() => {
        if (!listening) return;

        const healthCheckInterval = setInterval(() => {
            if (listening && !aiSpeaking) {
                // Check if VAD services are still active
                const webkitVADStatus = vadService.current?.getStatus();
                const fallbackVADStatus = fallbackVADService.current?.getStatus();
                
                console.log('🔍 VAD Health Check:', {
                    webkitVADActive: webkitVADStatus?.isListening,
                    fallbackVADActive: fallbackVADStatus?.isListening,
                    useWebkitVAD,
                    useFallbackVAD
                });

                // If Webkit VAD should be active but isn't, restart it
                if (useWebkitVAD && vadService.current && vadInitialized && !webkitVADStatus?.isListening) {
                    console.log('🔄 Webkit VAD not listening - restarting...');
                    try {
                        vadService.current.start();
                        console.log('✅ Webkit VAD restarted via health check');
                    } catch (error) {
                        console.log('❌ Failed to restart Webkit VAD via health check:', error);
                    }
                }

                // If Fallback VAD should be active but isn't, restart it
                if (useFallbackVAD && fallbackVADService.current && fallbackVADInitialized && !fallbackVADStatus?.isListening) {
                    console.log('🔄 Fallback VAD not listening - restarting...');
                    try {
                        fallbackVADService.current.start();
                        console.log('✅ Fallback VAD restarted via health check');
                    } catch (error) {
                        console.log('❌ Failed to restart Fallback VAD via health check:', error);
                    }
                }
            }
        }, 10000); // Check every 10 seconds

        return () => clearInterval(healthCheckInterval);
    }, [listening, aiSpeaking, useWebkitVAD, useFallbackVAD, vadInitialized, fallbackVADInitialized]);

    // Click outside handler for language dropdown
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (languageDropdownRef.current && !languageDropdownRef.current.contains(event.target as Node)) {
                setIsLanguageDropdownOpen(false);
            }
        };

        if (isLanguageDropdownOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isLanguageDropdownOpen]);

    // Check localStorage for user type on component mount
    useEffect(() => {
        const savedUserType = localStorage.getItem('userType');
        const savedOrgName = localStorage.getItem('orgName');
        const savedSelectedOrgId = localStorage.getItem('selectedOrgId');
        const savedSelectedOrgName = localStorage.getItem('selectedOrgName');
        
        console.log('Loading from localStorage:', {
            userType: savedUserType,
            orgName: savedOrgName,
            selectedOrgId: savedSelectedOrgId,
            selectedOrgName: savedSelectedOrgName
        });
        
        if (savedUserType && (savedUserType === 'customer' || savedUserType === 'org_owner')) {
            setUserType(savedUserType as "customer" | "org_owner");
            if (savedUserType === 'org_owner' && savedOrgName) {
                setOrgName(savedOrgName);
                // Load organization details
                loadOrganizationDetails(savedOrgName);
            } else if (savedUserType === 'customer' && savedSelectedOrgId && savedSelectedOrgName) {
                // Load selected organization for customer
                setSelectedOrgForCustomer({
                    id: parseInt(savedSelectedOrgId),
                    name: savedSelectedOrgName
                });
                // Load organization context for RAG
                console.log('🔍 RAG DEBUG: Loading organization context on mount for ID:', savedSelectedOrgId);
                loadOrganizationContext(parseInt(savedSelectedOrgId));
                console.log('Restored selected organization for customer:', savedSelectedOrgName);
            }
            setShowUserTypeModal(false);
        } else {
            setShowUserTypeModal(true);
        }
    }, []);

    // Load organization details from backend
    const loadOrganizationDetails = async (orgName: string) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/organizations/${encodeURIComponent(orgName)}`);
            const data = await response.json();
            if (data.success && data.organization) {
                setOrgDetails(data.organization.details || '');
            }
        } catch (error) {
            console.error('Error loading organization details:', error);
        }
    };

    // Load organizations for customer selection
    const loadOrganizationsForCustomer = async () => {
        setIsLoadingOrgs(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/organizations`);
            const data = await response.json();
            if (data.success && data.organizations) {
                setAvailableOrganizations(data.organizations);
            } else {
                console.error('Failed to load organizations:', data.error);
            }
        } catch (error) {
            console.error('Error loading organizations:', error);
        } finally {
            setIsLoadingOrgs(false);
        }
    };

    // Handle organization details modal
    const handleConfigureRolePlay = () => {
        if (userType === 'org_owner' && orgName) {
            setShowOrgDetailsModal(true);
        } else if (userType === 'customer') {
            loadOrganizationsForCustomer();
            setShowOrgSelectionModal(true);
        }
    };

    // Load organization context for RAG system
    const loadOrganizationContext = async (orgId: number) => {
        try {
            console.log('🔍 STEP 5: Starting API call to fetch organization ID:', orgId);
            const response = await fetch(`${API_BASE_URL}/api/organizations/by-id/${orgId}`);
            console.log('🔍 STEP 6: API response status:', response.status);
            
            const data = await response.json();
            console.log('🔍 STEP 7: API response data:', data);
            
            if (data.success && data.organization) {
                const org = data.organization;
                console.log('🔍 STEP 8: Organization data received:', org);
                console.log('🔍 STEP 8a: Organization name:', org.name);
                console.log('🔍 STEP 8b: Organization details:', org.details);
                
                // Create RAG context for LLM
                const context = `You are representing ${org.name}. ${org.details ? `Organization details: ${org.details}` : 'No additional details provided.'} Always respond as if you are a staff member of ${org.name} and provide helpful, professional assistance.`;
                console.log('🔍 STEP 9: Created RAG context:', context);
                
                setOrganizationContext(context);
                console.log('🔍 STEP 10: Organization context set in state');
                console.log('🔍 STEP 10a: Context length:', context.length);
            } else {
                console.error('🔍 STEP ERROR: Failed to load organization:', data);
            }
        } catch (error) {
            console.error('🔍 STEP ERROR: Error loading organization context:', error);
        }
    };

    // Handle organization selection for customer
    const handleOrgSelection = async (org: {id: number, name: string}) => {
        console.log('🔍 STEP 1: Customer selecting organization:', org);
        setSelectedOrgForCustomer(org);
        localStorage.setItem('selectedOrgId', org.id.toString());
        localStorage.setItem('selectedOrgName', org.name);
        setShowOrgSelectionModal(false);
        
        console.log('🔍 STEP 2: Saved to localStorage - ID:', org.id, 'Name:', org.name);
        
        // Load organization context for RAG
        console.log('🔍 STEP 3: Loading organization context for RAG...');
        await loadOrganizationContext(org.id);
        
        // Send updated preferences to backend immediately
        console.log('🔍 STEP 4: Sending updated preferences to backend...');
        setTimeout(() => {
            sendPrefs();
        }, 100); // Small delay to ensure state is updated
        
        console.log('🔍 STEP 5: Organization selection complete for:', org.name);
    };

    // Handle organization details update
    const handleUpdateOrgDetails = async (e: React.FormEvent) => {
        e.preventDefault();
        
        setIsUpdatingDetails(true);
        
        try {
            const orgId = localStorage.getItem('orgId');
            if (!orgId) {
                console.error('Organization ID not found');
                return;
            }

            const response = await fetch(`${API_BASE_URL}/api/organizations/${orgId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    details: orgDetails.trim()
                })
            });

            const data = await response.json();

            if (data.success) {
                setShowOrgDetailsModal(false);
                console.log('Organization details updated successfully');
            } else {
                console.error('Failed to update organization details:', data.error);
            }
        } catch (error) {
            console.error('Error updating organization details:', error);
        } finally {
            setIsUpdatingDetails(false);
        }
    };

    // Set WebSocket connection for VAD service when connected (only once per connection)
    useEffect(() => {
        if (connected && vadService.current && vadInitialized && ws.current?.readyState === WebSocket.OPEN) {
            vadService.current.setWebSocket(ws.current);
            console.log('WebSocket set for VAD service');
        }
    }, [connected]); // Only depend on connected state

    // Auto-activate VAD when WebSocket is connected and VAD is ready (but don't start listening)
    useEffect(() => {
        if (connected && vadSupported && vadInitialized && !useWebkitVAD && vadService.current) {
            // Auto-activate VAD when everything is ready (but don't start listening)
            setUseWebkitVAD(true);
            console.log('VAD auto-activated (ready for manual start)');
        }
    }, [connected, vadSupported, vadInitialized]); // Remove useWebkitVAD from dependencies to prevent infinite loop

    const handleLevelChange = (newLevel: "starter" | "medium" | "advanced") => {
        console.log(`Frontend: Changing level from ${level} to ${newLevel}`);
        setLevel(newLevel);
        setLevelChangeNotification(true);
        setTimeout(() => setLevelChangeNotification(false), 3000);
        // send immediately (no race with effect)
        setTimeout(sendPrefs, 0);
    };

    // keep prefs in sync (any of these change)
    useEffect(() => {
        if (connected) sendPrefs();
    }, [
        useLocalTTS, 
        selectedLanguage, 
        connected,
        // rolePlayEnabled,
        // rolePlayTemplate,
        // organizationName,
        // organizationDetails,
        // roleTitle
    ]); // Removed role play dependencies to prevent re-renders
    
    // Initialize VAD services on component mount (only once)
    useEffect(() => {
        let isInitialized = false;
        
        const initializeServices = async () => {
            if (isInitialized) return;
            isInitialized = true;
            
            // Try Webkit VAD first
            const webkitSuccess = await initializeVAD();
            
            // If Webkit VAD fails, initialize fallback VAD
            if (!webkitSuccess) {
                await initializeFallbackVAD();
            }
        };
        
        initializeServices();
        
        // Cleanup on unmount
        return () => {
            if (vadService.current) {
                vadService.current.destroy();
                vadService.current = null;
            }
            if (fallbackVADService.current) {
                fallbackVADService.current.destroy();
                fallbackVADService.current = null;
            }
        };
    }, []); // Empty dependency array to run only once
    
    // Auto-refresh role play state when connected
    useEffect(() => {
        if (connected && ws.current?.readyState === WebSocket.OPEN) {
            // Request current role play state from backend
            setTimeout(() => {
                if (ws.current?.readyState === WebSocket.OPEN) {
                    console.log("Frontend: Requesting role play state from backend...");
                    ws.current.send(JSON.stringify({
                        type: "get_roleplay_state"
                    }));
                }
            }, 1000); // Increased delay to ensure backend is ready
        }
    }, [connected]);
    
    // Also refresh when WebSocket reconnects
    useEffect(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            const refreshRolePlay = () => {
                if (ws.current?.readyState === WebSocket.OPEN) {
                    console.log("Frontend: Refreshing role play state...");
                    ws.current.send(JSON.stringify({
                        type: "get_roleplay_state"
                    }));
                }
            };
            
            // Refresh after connection
            setTimeout(refreshRolePlay, 1500);
            
            // Set up periodic refresh
            const interval = setInterval(refreshRolePlay, 30000); // Every 30 seconds
            
            return () => clearInterval(interval);
        }
    }, [ws.current?.readyState]);


    // ---------- Helpers: Local TTS ----------
    const speakTextLocal = (text: string) => {
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(text);
            utter.lang = selectedLanguage === "en" ? "en-US" : "it-IT";
            utter.rate = level === "starter" ? 0.9 : level === "medium" ? 1.1 : 1.3;
            utter.onend = () => {
                setAiSpeaking(false);
                setFinalTranscript(""); // Clear transcript to prevent waiting state
                setIsWaitingForResponse(false); // Clear waiting state when audio ends
            };
            utter.onerror = () => {
                setAiSpeaking(false);
                setFinalTranscript(""); // Clear transcript to prevent waiting state
                setIsWaitingForResponse(false); // Clear waiting state when audio ends
            };
            setAiSpeaking(true);
            setIsWaitingForResponse(false); // Clear waiting state when audio starts
            window.speechSynthesis.speak(utter);
        }
    };

    // ---------- Helpers: Server TTS (MP3 base64) ----------
    const playServerMp3 = async (base64: string) => {
        try {
            if (currentAudioRef.current) {
                currentAudioRef.current.pause();
                currentAudioRef.current.src = "";
                currentAudioRef.current = null;
            }
            if (currentSourceRef.current) {
                try { currentSourceRef.current.stop(); } catch { }
                currentSourceRef.current.disconnect();
                currentSourceRef.current = null;
            }

            if (!audioCtx.current) {
                audioCtx.current = new (window.AudioContext || (window as any).webkitAudioContext)();
            }
            await audioCtx.current.resume();

            const binary = atob(base64);
            const array = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) array[i] = binary.charCodeAt(i);

            const audioBuf = await audioCtx.current.decodeAudioData(array.buffer);
            const src = audioCtx.current.createBufferSource();
            src.buffer = audioBuf;
            src.playbackRate.value = level === "starter" ? 0.9 : level === "medium" ? 1.05 : 1.2;
            src.connect(audioCtx.current.destination);
            src.onended = () => {
                setAiSpeaking(false);
                setFinalTranscript(""); // Clear transcript to prevent waiting state
                setIsWaitingForResponse(false); // Clear waiting state when audio ends
            };

            currentSourceRef.current = src;
            setAiSpeaking(true);
            setIsWaitingForResponse(false); // Clear waiting state when audio starts
            src.start(0);
        } catch {
            const el = new Audio(`data:audio/mp3;base64,${base64}`);
            if (currentAudioRef.current) {
                currentAudioRef.current.pause();
                currentAudioRef.current.src = "";
            }
            currentAudioRef.current = el;
            el.onended = () => {
                setAiSpeaking(false);
                setFinalTranscript(""); // Clear transcript to prevent waiting state
                setIsWaitingForResponse(false); // Clear waiting state when audio ends
            };
            setAiSpeaking(true);
            setIsWaitingForResponse(false); // Clear waiting state when audio starts
            await el.play();
        }
    };

    // ---------- WS URL ----------
    const buildWsUrl = () => {
        // Use environment variables for WebSocket URL configuration
        const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
        
        if (isLocalhost) {
            // Development: Use local WebSocket server
            return `${WS_BASE_URL}/ws`;
        } else {
            // Production: Use production WebSocket server
            return `${WS_PRODUCTION_URL}/ws`;
        }
    };

    // ---------- WebSocket ----------
    useEffect(() => {
        let isConnecting = false;

        const connectWebSocket = () => {
            if (isConnecting || ws.current?.readyState === WebSocket.OPEN) return;
            isConnecting = true;
            setStatus(currentLang.status.connecting);

            try {
                const url = buildWsUrl();
                ws.current = new WebSocket(url);
                ws.current.binaryType = "arraybuffer";

                ws.current.onopen = () => {
                    setConnected(true);
                    setStatus(currentLang.status.connected);
                    isConnecting = false;

                    // initial prefs (NOW including level + stable client_id)
                    try {
                        ws.current?.send(JSON.stringify({
                            type: "client_prefs",
                            client_id: clientIdRef.current,
                            level,
                            use_local_tts: useLocalTTS,
                            language: selectedLanguage,
                        }));
                    } catch { }

                    if (keepAliveTimer.current) clearInterval(keepAliveTimer.current);
                    keepAliveTimer.current = window.setInterval(() => {
                        try { ws.current?.send(JSON.stringify({ type: "ping" })); } catch { }
                    }, 15000);
                };

                ws.current.onmessage = async (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        console.log("📨 Received WebSocket message:", data.type, data);
                        switch (data.type) {
                            case "ai_text":
                                console.log("🤖 AI Response received:", data.text);
                                setAiText(data.text || "");
                                setIsProcessing(false);
                                // Don't clear waiting state here - keep "AI Thinking" until audio starts
                                if (useLocalTTS && data.text) speakTextLocal(data.text);
                                break;

                            case "ai_audio":
                                console.log("🔊 AI Audio received:", data.audio_base64 ? "Yes" : "No");
                                setIsProcessing(false);
                                // Don't clear waiting state here - let playServerMp3 handle it when audio actually starts
                                if (!useLocalTTS && data.audio_base64) {
                                    await playServerMp3(data.audio_base64);
                                }
                                break;

                            case "final_transcript":
                                console.log("📝 Final transcript received:", data.text);
                                setTranscript(data.text || "");
                                setFinalTranscript(data.text || "");
                                setInterimTranscript("");
                                if (data.text && selectedLanguage === "en") {
                                }
                                break;

                            case "interim_transcript":
                                console.log("📝 Interim transcript received:", data.text);
                                setInterimTranscript(data.text || "");
                                break;

                            case "stop_audio":
                                // Professional workflow: Microphone stays active continuously
                                console.log('🔇 Server requested audio stop - microphone remains active for continuous listening');
                                // No action needed - microphone continues to be active
                                break;

                            case "error":
                                setStatus(`❌ Backend Error: ${data.message}`);
                                setIsProcessing(false);
                                setIsWaitingForResponse(false);
                                break;

                            case "level_changed":
                                // optional: trust server echo if needed
                                // setLevel(data.level as any);
                                console.log(`Level changed to: ${data.level}`);
                                break;
                            case "role_play_updated":
                                console.log("Backend: Role play updated:", data);
                                // Update local state to match backend
                                setRolePlayEnabled(data.enabled);
                                setRolePlayTemplate(data.template);
                                setOrganizationName(data.organization_name || "");
                                setRoleTitle(data.role_title || "");
                                
                                // Save role play state to localStorage for persistence
                                localStorage.setItem('rolePlayState', JSON.stringify({
                                    enabled: data.enabled,
                                    template: data.template || "school",
                                    organizationName: data.organization_name || "",
                                    organizationDetails: data.organization_details || "",
                                    roleTitle: data.role_title || ""
                                }));
                                break;
                            
                            case "role_play_cleared":
                                console.log("Backend: Role play cleared:", data);
                                if (data.success) {
                                    // Clear local state
                                    setRolePlayEnabled(false);
                                    setOrganizationName("");
                                    setOrganizationDetails("");
                                    setRoleTitle("");
                                    
                                    // Clear localStorage
                                    localStorage.removeItem('rolePlayState');
                                    
                                    // Show success message
                                    console.log("Role play cleared successfully");
                                } else {
                                    console.error("Failed to clear role play:", data.message);
                                }
                                break;

                            case "pong":
                            default:
                                break;
                        }
                    } catch {
                        // ignore parse errors
                    }
                };

                ws.current.onerror = () => {
                    setConnected(false);
                    setStatus(currentLang.status.disconnected);
                    isConnecting = false;
                };

                ws.current.onclose = () => {
                    setConnected(false);
                    setStatus(currentLang.status.disconnected);
                    isConnecting = false;
                    if (keepAliveTimer.current) {
                        clearInterval(keepAliveTimer.current);
                        keepAliveTimer.current = null;
                    }
                    if (reconnectTimer.current) window.clearTimeout(reconnectTimer.current);
                    reconnectTimer.current = window.setTimeout(connectWebSocket, 3000);
                };
            } catch {
                setConnected(false);
                setStatus(currentLang.status.disconnected);
                isConnecting = false;
            }
        };

        connectWebSocket();

        return () => {
            isConnecting = false;
            if (reconnectTimer.current) {
                window.clearTimeout(reconnectTimer.current);
                reconnectTimer.current = null;
            }
            if (keepAliveTimer.current) {
                clearInterval(keepAliveTimer.current);
                keepAliveTimer.current = null;
            }
            if (ws.current) {
                try { ws.current.close(1000, "Component unmounting"); } catch { }
                ws.current = null;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // single connect

    // ---------- Start mic ----------
    const startMic = async () => {
        console.log("🎤 startMic called, listening:", listening, "connected:", connected);
        if (listening) {
            console.log("⚠️ Already listening, skipping startMic");
            return;
        }
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            console.log("WebSocket not connected");
            setStatus(currentLang.status.disconnected);
            return;
        }

        // Force mic level reset
        updateMicLevel(0, 'reset');

        // Auto-activate Webkit VAD if available and not already active
        if (vadSupported && vadInitialized && !useWebkitVAD && vadService.current) {
            const success = startVAD();
            if (success) {
                setUseWebkitVAD(true);
                setListening(true);
                setStatus(currentLang.status.listening);
                setShowTranscription(true);
                return;
            }
        }

        console.log("🚀 START MIC INITIATED:", {
            timestamp: new Date().toLocaleTimeString(),
            useWebkitVAD,
            useFallbackVAD,
            vadServiceExists: !!vadService.current,
            fallbackVADServiceExists: !!fallbackVADService.current,
            audioContextExists: !!audioCtx.current,
            audioContextState: audioCtx.current?.state
        });

        // If VAD is enabled, use appropriate VAD service
        if (useWebkitVAD && vadService.current) {
            const success = startVAD();
            if (success) {
                setListening(true);
                setStatus(currentLang.status.listening);
                setShowTranscription(true);
                console.log("✅ Webkit VAD Started Successfully");
                return;
            } else {
                console.log("❌ Webkit VAD Failed to Start");
            }
        }

        // If fallback VAD is enabled, use fallback service
        if (useFallbackVAD && fallbackVADService.current) {
            const success = startFallbackVAD();
            if (success) {
                setListening(true);
                setStatus(currentLang.status.listening);
                setShowTranscription(true);
                console.log("✅ Fallback VAD Started Successfully");
                return;
            } else {
                console.log("❌ Fallback VAD Failed to Start");
            }
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                    sampleRate: 48000,
                },
            });
            streamRef.current = stream;
            
            console.log("🎤 Microphone Access Granted:", {
                tracks: stream.getTracks().length,
                audioTracks: stream.getAudioTracks().length,
                trackSettings: stream.getAudioTracks()[0]?.getSettings(),
                trackConstraints: stream.getAudioTracks()[0]?.getConstraints()
            });

            if (!audioCtx.current) {
                audioCtx.current = new (window.AudioContext || (window as any).webkitAudioContext)();
                console.log("🎵 Audio Context Created:", {
                    sampleRate: audioCtx.current.sampleRate,
                    state: audioCtx.current.state,
                    baseLatency: audioCtx.current.baseLatency
                });
            }
            
            if (audioCtx.current.state === 'suspended') {
                await audioCtx.current.resume();
                console.log("🎵 Audio Context Resumed:", {
                    sampleRate: audioCtx.current.sampleRate,
                    state: audioCtx.current.state
                });
            }

            const src = new MediaStreamAudioSourceNode(audioCtx.current, { mediaStream: stream });
            sourceNode.current = src;

            analyser.current = audioCtx.current.createAnalyser();
            analyser.current.fftSize = 256;
            analyser.current.smoothingTimeConstant = 0.2;
            src.connect(analyser.current);
            
            console.log("🔊 Analyser Setup:", {
                fftSize: analyser.current.fftSize,
                frequencyBinCount: analyser.current.frequencyBinCount,
                smoothingTimeConstant: analyser.current.smoothingTimeConstant,
                connected: true
            });
            
            // Start mic level monitoring with analyser
            const micDataArray = new Uint8Array(analyser.current.frequencyBinCount);
            let frameCount = 0;
            const monitorMicLevel = () => {
                if (analyser.current && listeningRef.current) {
                    analyser.current.getByteFrequencyData(micDataArray);
                    const rms = Math.sqrt(micDataArray.reduce((sum, value) => sum + (value * value), 0) / micDataArray.length) / 255;
                    
                    // Enhanced debugging every 30 frames (about 0.5 seconds at 60fps)
                    if (frameCount % 30 === 0) {
                        console.log("🎤 Analyser Monitoring:", {
                            frame: frameCount,
                            rms: rms.toFixed(4),
                            maxValue: Math.max(...micDataArray),
                            avgValue: micDataArray.reduce((a, b) => a + b, 0) / micDataArray.length,
                            nonZeroValues: micDataArray.filter(v => v > 0).length
                        });
                    }
                    
                    updateMicLevel(rms, 'analyser');
                    frameCount++;
                    requestAnimationFrame(monitorMicLevel);
                } else {
                    console.log("🎤 Analyser Monitoring Stopped:", {
                        analyserExists: !!analyser.current,
                        listening: listeningRef.current
                    });
                }
            };
            console.log("🎤 Starting Analyser Monitoring...");
            monitorMicLevel();

            muteGain.current = audioCtx.current.createGain();
            muteGain.current.gain.value = 0.0;

            try {
                const workletUrl = `${window.location.origin}/pcm16-worklet.js`;
                console.log("🔧 Loading Audio Worklet:", workletUrl);
                await audioCtx.current.audioWorklet.addModule(workletUrl);
                console.log("✅ Audio Worklet Loaded Successfully");

                workletNode.current = new AudioWorkletNode(
                    audioCtx.current,
                    "pcm16-downsampler",
                    { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1] }
                );
                console.log("🔧 Audio Worklet Node Created:", {
                    numberOfInputs: workletNode.current.numberOfInputs,
                    numberOfOutputs: workletNode.current.numberOfOutputs,
                    channelCount: workletNode.current.channelCount
                });

                workletNode.current.port.onmessage = (ev) => {
                    const { type, value, buffer } = ev.data || {};
                    if (type === "rms" && typeof value === "number") {
                        // Enhanced mic level calculation with better sensitivity
                        updateMicLevel(value, 'worklet');
                    } else if (type === "frame" && buffer) {
                        if (listeningRef.current && ws.current?.readyState === WebSocket.OPEN) {
                            try {
                                ws.current.send(new Uint8Array(buffer));
                                console.log("🎤 Audio frame sent to backend:", buffer.byteLength, "bytes");
                            } catch (error) {
                                console.error("❌ Error sending audio frame:", error);
                            }
                        } else {
                            console.log("⚠️ Cannot send audio frame:", {
                                listening: listeningRef.current,
                                wsState: ws.current?.readyState,
                                wsOpen: ws.current?.readyState === WebSocket.OPEN
                            });
                        }
                    }
                };

                src.connect(workletNode.current);
                workletNode.current.connect(muteGain.current);
                muteGain.current.connect(audioCtx.current.destination);
                
                console.log("🔗 Audio Worklet Connected:", {
                    sourceToWorklet: true,
                    workletToGain: true,
                    gainToDestination: true,
                    audioGraphComplete: true
                });
            } catch (error) {
                console.log("⚠️ Audio Worklet Failed, Using Script Processor:", error);
                processorNode.current = audioCtx.current.createScriptProcessor(4096, 1, 1);
                const inputRate = audioCtx.current.sampleRate;
                const targetRate = 16000;
                const ratio = inputRate / targetRate;
                let floatBuf: number[] = [];
                let readIndex = 0;
                
                console.log("🔧 Script Processor Setup:", {
                    bufferSize: 4096,
                    inputRate: inputRate,
                    targetRate: targetRate,
                    ratio: ratio
                });

                processorNode.current.onaudioprocess = (e) => {
                    const ch = e.inputBuffer.getChannelData(0);
                    let sum = 0;
                    for (let i = 0; i < ch.length; i++) sum += ch[i] * ch[i];
                    const rms = Math.sqrt(sum / Math.max(1, ch.length));
                    // Enhanced mic level calculation with better sensitivity
                    updateMicLevel(rms, 'script-processor');

                    floatBuf = floatBuf.concat(Array.from(ch));
                    const out: number[] = [];
                    while (readIndex + 1 < floatBuf.length) {
                        const i0 = Math.floor(readIndex);
                        const frac = readIndex - i0;
                        const s0 = floatBuf[i0] || 0;
                        const s1 = floatBuf[i0 + 1] || s0;
                        out.push(s0 + (s1 - s0) * frac);
                        readIndex += ratio;
                    }
                    const consumed = Math.floor(readIndex);
                    if (consumed > 0) {
                        floatBuf = floatBuf.slice(consumed);
                        readIndex -= consumed;
                    }

                    const FRAME = 480;
                    while (out.length >= FRAME) {
                        const slice = out.splice(0, FRAME);
                        const i16 = new Int16Array(FRAME);
                        for (let i = 0; i < FRAME; i++) {
                            const s = Math.max(-1, Math.min(1, slice[i] || 0));
                            i16[i] = (s * 32767) | 0;
                        }
                        if (listeningRef.current && ws.current?.readyState === WebSocket.OPEN) {
                            try {
                                ws.current.send(new Uint8Array(i16.buffer));
                                console.log("🎤 Audio data sent to backend:", i16.buffer.byteLength, "bytes");
                            } catch (error) {
                                console.error("❌ Error sending audio data:", error);
                            }
                        } else {
                            console.log("⚠️ Cannot send audio data:", {
                                listening: listeningRef.current,
                                wsState: ws.current?.readyState,
                                wsOpen: ws.current?.readyState === WebSocket.OPEN
                            });
                        }
                    }
                };

                src.connect(processorNode.current);
                processorNode.current.connect(muteGain.current);
                muteGain.current.connect(audioCtx.current.destination);
                
                console.log("🔗 Script Processor Connected:", {
                    sourceToProcessor: true,
                    processorToGain: true,
                    gainToDestination: true,
                    fallbackAudioGraphComplete: true
                });
            }

            const dataArray = new Uint8Array(analyser.current.frequencyBinCount);
            const updateMic = () => {
                if (!listeningRef.current) return;
                try {
                    analyser.current?.getByteFrequencyData(dataArray);
                    const avg = dataArray.reduce((a, b) => a + b, 0) / Math.max(1, dataArray.length);
                    const normalized = Math.min(avg / 128, 1.0);
                    setMicLevel((prev) => Math.max(prev * 0.7, normalized * 0.8));
                    requestAnimationFrame(updateMic);
                } catch {
                    requestAnimationFrame(updateMic);
                }
            };

            listeningRef.current = true;
            setListening(true);
            setStatus(currentLang.status.listening);
            requestAnimationFrame(updateMic);

            console.log("✅ MICROPHONE STARTED SUCCESSFULLY:", {
                timestamp: new Date().toLocaleTimeString(),
                sampleRate: audioCtx.current.sampleRate,
                analyserExists: !!analyser.current,
                workletExists: !!workletNode.current,
                processorExists: !!processorNode.current,
                listening: listeningRef.current
            });

            try {
                ws.current.send(JSON.stringify({
                    type: "microphone_started",
                    sampleRate: audioCtx.current.sampleRate,
                    channels: 1,
                    timestamp: new Date().toISOString(),
                }));
                console.log("📡 WebSocket microphone_started message sent");
            } catch (error) {
                console.log("❌ Failed to send microphone_started message:", error);
            }
        } catch (error: any) {
            console.log("❌ MICROPHONE START FAILED:", {
                error: error.message,
                name: error.name,
                stack: error.stack,
                timestamp: new Date().toLocaleTimeString()
            });
            
            if (error?.name === "NotAllowedError") {
                setStatus("❌ Microphone access denied - please allow microphone permissions");
                console.log("🔒 Permission denied - user needs to allow microphone access");
            } else if (error?.name === "NotFoundError") {
                setStatus("❌ No microphone found - please connect a microphone");
                console.log("🎤 No microphone device found");
            } else if (error?.name === "NotReadableError") {
                setStatus("❌ Microphone in use by another application");
                console.log("🔒 Microphone already in use by another application");
            } else {
                setStatus(`❌ Microphone error: ${error?.message || "Unknown error"}`);
                console.log("❓ Unknown microphone error:", error);
            }
        }
    };

    // ---------- Stop mic ----------
    const stopMic = () => {
        console.log("stopMic called, listening:", listening, "useWebkitVAD:", useWebkitVAD);
        // If VAD is enabled, stop appropriate VAD service
        if (useWebkitVAD && vadService.current) {
            stopVAD();
            setListening(false);
            setStatus(currentLang.status.connected);
            return;
        }

        // If fallback VAD is enabled, stop fallback service
        if (useFallbackVAD && fallbackVADService.current) {
            stopFallbackVAD();
            setListening(false);
            setStatus(currentLang.status.connected);
            return;
        }

        // Stop traditional microphone
        listeningRef.current = false;
        if (sourceNode.current) { try { sourceNode.current.disconnect(); } catch { } sourceNode.current = null; }
        if (workletNode.current) { try { workletNode.current.disconnect(); } catch { } workletNode.current = null; }
        if (processorNode.current) { try { processorNode.current.disconnect(); } catch { } processorNode.current = null; }
        if (muteGain.current) { try { muteGain.current.disconnect(); } catch { } muteGain.current = null; }
        if (streamRef.current) { try { streamRef.current.getTracks().forEach(t => t.stop()); } catch { } streamRef.current = null; }
        setListening(false);
        updateMicLevel(0, 'stop');
        setStatus(currentLang.status.connected);
    };

    // Handle user type selection
    const handleUserTypeSelection = (type: "customer" | "org_owner") => {
        setUserType(type);
        
        if (type === "customer") {
            localStorage.setItem('userType', type);
            setShowUserTypeModal(false);
        } else if (type === "org_owner") {
            setShowOrgForm(true);
        }
    };

    // Validate organization name
    const validateOrgName = (name: string) => {
        if (!name.trim()) {
            return "Organization name is required";
        }
        if (name.trim().length < 2) {
            return "Organization name must be at least 2 characters long";
        }
        if (name.trim().length > 100) {
            return "Organization name must be less than 100 characters";
        }
        return "";
    };

    // Check if organization name exists
    const checkOrgNameExists = async (name: string) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/organizations/check/${encodeURIComponent(name)}`);
            const data = await response.json();
            return data.exists;
        } catch (error) {
            console.error('Error checking organization name:', error);
            return false;
        }
    };

    // Handle organization form submission
    const handleOrgFormSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        const trimmedName = orgName.trim();
        const validationError = validateOrgName(trimmedName);
        
        if (validationError) {
            setOrgNameError(validationError);
            return;
        }

        setIsSubmittingOrg(true);
        setOrgNameError("");

        try {
            // Check if organization already exists
            const exists = await checkOrgNameExists(trimmedName);
            if (exists) {
                setOrgNameError("Organization name already exists");
                setIsSubmittingOrg(false);
                return;
            }

            // Create organization in backend
            const response = await fetch(`${API_BASE_URL}/api/organizations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: trimmedName,
                    details: '' // Default empty details as requested
                })
            });

            const data = await response.json();

            if (data.success) {
                // Store in localStorage
                localStorage.setItem('userType', 'org_owner');
                localStorage.setItem('orgName', trimmedName);
                localStorage.setItem('orgId', data.organization.id.toString());
                
                // Close modals
                setShowOrgForm(false);
                setShowUserTypeModal(false);
                
                console.log('Organization created successfully:', data.organization);
            } else {
                setOrgNameError(data.error || 'Failed to create organization');
            }
        } catch (error) {
            console.error('Error creating organization:', error);
            setOrgNameError('Network error. Please try again.');
        } finally {
            setIsSubmittingOrg(false);
        }
    };

    // ---------- Dev: server TTS test ----------
    const testVoiceInput = () => {
        const text =
            selectedLanguage === "en"
                ? "Hello, how are you? This is a server TTS test."
                : "Ciao, questo è un test TTS dal client web.";
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: "tts_request", text }));
            setIsProcessing(true);
        }
    };

    const mockAIResponse = () => {
        if (!connected) return;
        setIsProcessing(true);
        setTimeout(() => {
            const msg =
                selectedLanguage === "en"
                    ? "Hello! I'm your AI assistant. How can I help you today?"
                    : "Ciao! Sono il tuo assistente AI. Come posso aiutarti oggi?";
            setAiText(msg);
            setIsProcessing(false);
            if (useLocalTTS) speakTextLocal(msg);
        }, 700);
    };

    const siriMode = aiSpeaking;

    // ---------------- UI ----------------
    return (
        <div className="min-h-screen text-zinc-100 bg-black relative overflow-hidden">
            {/* User Type Selection Modal */}
            {showUserTypeModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="relative w-full max-w-md mx-4">
                        <div className="bg-gradient-to-br from-white/[0.08] to-white/[0.02] backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl overflow-hidden">
                            {/* Modal Header */}
                            <div className="p-6 pb-4">
                                <div className="flex items-center justify-center mb-4">
                                    <div className="p-3 rounded-full bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/30">
                                        <Bot className="h-8 w-8 text-indigo-400" />
                                    </div>
                                </div>
                                <h2 className="text-2xl font-bold text-white text-center mb-2">
                                    Welcome to SHCI
                                </h2>
                                <p className="text-zinc-400 text-center text-sm">
                                    Select your role to get started
                                </p>
                            </div>

                            {/* Modal Body */}
                            <div className="px-6 pb-6">
                                <div className="space-y-3">
                                    {/* Customer Option */}
                                    <button
                                        onClick={() => handleUserTypeSelection('customer')}
                                        className="w-full group relative p-4 rounded-xl bg-white/[0.05] border border-white/10 hover:border-emerald-400/50 hover:bg-emerald-500/10 transition-all duration-300 text-left"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="p-2 rounded-lg bg-emerald-500/20 border border-emerald-500/30 group-hover:bg-emerald-500/30 transition-colors duration-300">
                                                <User className="h-5 w-5 text-emerald-400" />
                                            </div>
                                            <div className="flex-1">
                                                <h3 className="text-lg font-semibold text-white mb-1">
                                                    Customer
                                                </h3>
                                                <p className="text-sm text-zinc-400 group-hover:text-zinc-300 transition-colors duration-300">
                                                    I want to interact with the AI agent as a customer
                                                </p>
                                            </div>
                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                                <FaChevronDown className="h-4 w-4 text-emerald-400 rotate-90" />
                                            </div>
                                        </div>
                                    </button>

                                    {/* Organization Owner Option */}
                                    <button
                                        onClick={() => handleUserTypeSelection('org_owner')}
                                        className="w-full group relative p-4 rounded-xl bg-white/[0.05] border border-white/10 hover:border-blue-400/50 hover:bg-blue-500/10 transition-all duration-300 text-left"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="p-2 rounded-lg bg-blue-500/20 border border-blue-500/30 group-hover:bg-blue-500/30 transition-colors duration-300">
                                                <FaBuilding className="h-5 w-5 text-blue-400" />
                                            </div>
                                            <div className="flex-1">
                                                <h3 className="text-lg font-semibold text-white mb-1">
                                                    Organization Owner
                                                </h3>
                                                <p className="text-sm text-zinc-400 group-hover:text-zinc-300 transition-colors duration-300">
                                                    I want to manage and configure the AI agent for my organization
                                                </p>
                                            </div>
                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                                <FaChevronDown className="h-4 w-4 text-blue-400 rotate-90" />
                                            </div>
                                        </div>
                                    </button>
                                </div>

                                {/* Modal Footer */}
                                <div className="mt-6 pt-4 border-t border-white/10">
                                    <p className="text-xs text-zinc-500 text-center">
                                        You can change this preference later in settings
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Organization Name Form Modal */}
            {showOrgForm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="relative w-full max-w-md mx-4">
                        <div className="bg-gradient-to-br from-white/[0.08] to-white/[0.02] backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl overflow-hidden">
                            {/* Modal Header */}
                            <div className="p-6 pb-4">
                                <div className="flex items-center justify-center mb-4">
                                    <div className="p-3 rounded-full bg-gradient-to-r from-blue-500/20 to-indigo-500/20 border border-blue-500/30">
                                        <FaBuilding className="h-8 w-8 text-blue-400" />
                                    </div>
                                </div>
                                <h2 className="text-2xl font-bold text-white text-center mb-2">
                                    Organization Setup
                                </h2>
                                <p className="text-zinc-400 text-center text-sm">
                                    Enter your organization name
                                </p>
                            </div>

                            {/* Modal Body */}
                            <div className="px-6 pb-6">
                                <form onSubmit={handleOrgFormSubmit} className="space-y-4">
                                    <div>
                                        <label htmlFor="orgName" className="block text-sm font-medium text-zinc-300 mb-2">
                                            Organization Name
                                        </label>
                                        <input
                                            type="text"
                                            id="orgName"
                                            value={orgName}
                                            onChange={(e) => {
                                                setOrgName(e.target.value);
                                                if (orgNameError) setOrgNameError("");
                                            }}
                                            placeholder="Enter your organization name"
                                            className={`w-full px-4 py-3 rounded-lg bg-white/[0.05] border text-white placeholder-zinc-500 focus:outline-none focus:bg-white/[0.08] transition-all duration-300 ${
                                                orgNameError 
                                                    ? "border-red-400/50 focus:border-red-400/70" 
                                                    : "border-white/10 focus:border-blue-400/50"
                                            }`}
                                            required
                                            autoFocus
                                            disabled={isSubmittingOrg}
                                        />
                                        {orgNameError && (
                                            <p className="mt-2 text-sm text-red-400 flex items-center gap-2">
                                                <span className="text-red-400">⚠</span>
                                                {orgNameError}
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex gap-3 pt-2">
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setShowOrgForm(false);
                                                setUserType(null);
                                            }}
                                            className="flex-1 px-4 py-3 rounded-lg bg-white/[0.05] border border-white/10 text-zinc-300 hover:bg-white/[0.08] hover:text-white transition-all duration-300"
                                        >
                                            Back
                                        </button>
                                        <button
                                            type="submit"
                                            disabled={!orgName.trim() || isSubmittingOrg}
                                            className="flex-1 px-4 py-3 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-semibold hover:from-blue-600 hover:to-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shadow-lg flex items-center justify-center gap-2"
                                        >
                                            {isSubmittingOrg ? (
                                                <>
                                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                                    Creating...
                                                </>
                                            ) : (
                                                "Continue"
                                            )}
                                        </button>
                                    </div>
                                </form>

                                {/* Modal Footer */}
                                <div className="mt-6 pt-4 border-t border-white/10">
                                    <p className="text-xs text-zinc-500 text-center">
                                        This information will be used to personalize your experience
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Organization Details Modal */}
            {showOrgDetailsModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="relative w-full max-w-2xl mx-4">
                        <div className="bg-gradient-to-br from-white/[0.08] to-white/[0.02] backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl overflow-hidden">
                            {/* Modal Header */}
                            <div className="p-6 pb-4">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="p-3 rounded-full bg-gradient-to-r from-blue-500/20 to-indigo-500/20 border border-blue-500/30">
                                            <FaBuilding className="h-8 w-8 text-blue-400" />
                                        </div>
                                        <div>
                                            <h2 className="text-2xl font-bold text-white">
                                                Add details for {orgName}
                                            </h2>
                                            <p className="text-zinc-400 text-sm">
                                                Provide additional information about your organization
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setShowOrgDetailsModal(false)}
                                        className="text-zinc-400 hover:text-zinc-200 text-2xl transition-colors duration-300"
                                    >
                                        ×
                                    </button>
                                </div>
                            </div>

                            {/* Modal Body */}
                            <div className="px-6 pb-6">
                                <form onSubmit={handleUpdateOrgDetails} className="space-y-4">
                                    <div>
                                        <label htmlFor="orgDetails" className="block text-sm font-medium text-zinc-300 mb-2">
                                            Organization Details
                                        </label>
                                        <textarea
                                            id="orgDetails"
                                            value={orgDetails}
                                            onChange={(e) => setOrgDetails(e.target.value)}
                                            placeholder="Describe your organization, its services, mission, or any relevant information that will help the AI understand your business context..."
                                            className="w-full px-4 py-3 rounded-lg bg-white/[0.05] border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-blue-400/50 focus:bg-white/[0.08] transition-all duration-300 resize-none"
                                            rows={6}
                                            disabled={isUpdatingDetails}
                                        />
                                        <p className="mt-2 text-xs text-zinc-500">
                                            This information will help personalize the AI's responses for your organization
                                        </p>
                                    </div>

                                    <div className="flex gap-3 pt-2">
                                        <button
                                            type="button"
                                            onClick={() => setShowOrgDetailsModal(false)}
                                            className="flex-1 px-4 py-3 rounded-lg bg-white/[0.05] border border-white/10 text-zinc-300 hover:bg-white/[0.08] hover:text-white transition-all duration-300"
                                            disabled={isUpdatingDetails}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="submit"
                                            disabled={isUpdatingDetails}
                                            className="flex-1 px-4 py-3 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-semibold hover:from-blue-600 hover:to-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shadow-lg flex items-center justify-center gap-2"
                                        >
                                            {isUpdatingDetails ? (
                                                <>
                                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                                    Updating...
                                                </>
                                            ) : (
                                                "Update Details"
                                            )}
                                        </button>
                                    </div>
                                </form>

                                {/* Modal Footer */}
                                <div className="mt-6 pt-4 border-t border-white/10">
                                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                                        <FaBuilding className="h-3 w-3" />
                                        <span>Organization: {orgName}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Organization Selection Modal for Customers */}
            {showOrgSelectionModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="relative w-full max-w-2xl mx-4">
                        <div className="bg-gradient-to-br from-white/[0.08] to-white/[0.02] backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl overflow-hidden">
                            {/* Modal Header */}
                            <div className="p-6 pb-4">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="p-3 rounded-full bg-gradient-to-r from-emerald-500/20 to-green-500/20 border border-emerald-500/30">
                                            <User className="h-8 w-8 text-emerald-400" />
                                        </div>
                                        <div>
                                            <h2 className="text-2xl font-bold text-white">
                                                Select Organization
                                            </h2>
                                            <p className="text-zinc-400 text-sm">
                                                Choose which organization you want to interact with
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setShowOrgSelectionModal(false)}
                                        className="text-zinc-400 hover:text-zinc-200 text-2xl transition-colors duration-300"
                                    >
                                        ×
                                    </button>
                                </div>
                            </div>

                            {/* Modal Body */}
                            <div className="px-6 pb-6">
                                {isLoadingOrgs ? (
                                    <div className="flex items-center justify-center py-8">
                                        <div className="flex items-center gap-3">
                                            <div className="w-6 h-6 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin"></div>
                                            <span className="text-zinc-400">Loading organizations...</span>
                                        </div>
                                    </div>
                                ) : availableOrganizations.length === 0 ? (
                                    <div className="text-center py-8">
                                        <div className="p-4 rounded-full bg-zinc-800/50 mx-auto w-fit mb-4">
                                            <FaBuilding className="h-8 w-8 text-zinc-500" />
                                        </div>
                                        <h3 className="text-lg font-semibold text-zinc-300 mb-2">No Organizations Available</h3>
                                        <p className="text-zinc-500 text-sm">
                                            There are no organizations set up yet. Please contact an administrator.
                                        </p>
                                    </div>
                                ) : (
                                    <div className="space-y-3 max-h-96 overflow-y-auto">
                                        {availableOrganizations.map((org) => {
                                            const isSelected = selectedOrgForCustomer?.id === org.id;
                                            return (
                                                <button
                                                    key={org.id}
                                                    onClick={() => handleOrgSelection({id: org.id, name: org.name})}
                                                    className={`w-full group relative p-4 rounded-xl transition-all duration-300 text-left ${
                                                        isSelected
                                                            ? "bg-emerald-500/20 border border-emerald-400/50 shadow-lg"
                                                            : "bg-white/[0.05] border border-white/10 hover:border-emerald-400/50 hover:bg-emerald-500/10"
                                                    }`}
                                                >
                                                    <div className="flex items-center gap-4">
                                                        <div className={`p-2 rounded-lg border transition-colors duration-300 ${
                                                            isSelected
                                                                ? "bg-emerald-500/30 border-emerald-400/50"
                                                                : "bg-emerald-500/20 border-emerald-500/30 group-hover:bg-emerald-500/30"
                                                        }`}>
                                                            <FaBuilding className="h-5 w-5 text-emerald-400" />
                                                        </div>
                                                        <div className="flex-1">
                                                            <h3 className={`text-lg font-semibold ${
                                                                isSelected ? "text-emerald-300" : "text-white"
                                                            }`}>
                                                                {org.name}
                                                            </h3>
                                                        </div>
                                                        {isSelected ? (
                                                            <div className="flex items-center gap-2">
                                                                <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
                                                                <span className="text-xs font-semibold text-emerald-300">
                                                                    Selected
                                                                </span>
                                                            </div>
                                                        ) : (
                                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                                                <FaChevronDown className="h-4 w-4 text-emerald-400 rotate-90" />
                                                            </div>
                                                        )}
                                                    </div>
                                                </button>
                                            );
                                        })}
                                    </div>
                                )}

                                {/* Modal Footer */}
                                <div className="mt-6 pt-4 border-t border-white/10">
                                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                                        <User className="h-3 w-3" />
                                        <span>Customer Mode - Select an organization to start conversation</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Background */}
            <div className="absolute inset-0 pointer-events-none">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-purple-500/5 to-indigo-500/5 animate-pulse" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.03)_0%,transparent_50%)]" />
                {siriMode && <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/20 to-blue-500/20 animate-pulse" />}
            </div>

            {/* Boxed Layout Container */}
            <div className=" flex items-center justify-center p-4 sm:p-6 lg:p-8">
                <div className="w-full max-w-7xl rounded-3xl shadow-2xl overflow-hidden">
                    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 relative">
                {/* Minimal Enhanced Navbar */}
                <div className="bg-white/[0.02] backdrop-blur-sm rounded-xl border border-white/10 p-4 mb-6">
                    {/* Main Header Row */}
                    <div className="flex items-center justify-between mb-4">
                    {/* Logo & Title Section */}
                        <div className="flex items-center gap-3">
                        <div className="relative group">
                                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-600 to-blue-600 flex items-center justify-center shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
                                    <Bot className="h-6 w-6 text-white" />
                            </div>
                            {connected && (
                                <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-400 rounded-full border-2 border-black animate-pulse shadow-lg" />
                            )}
                        </div>
                        <div className="flex flex-col">
                            <h1 className="text-2xl font-bold text-white tracking-tight">
                                {currentLang.labels.title}
                            </h1>
                                <div className="flex items-center gap-2 mt-0.5">
                                    <Brain className="h-3 w-3 text-indigo-400" />
                                    <span className="text-xs text-zinc-400 font-medium">
                                    {currentLang.labels.subtitle}
                                </span>
                            </div>
                        </div>
                    </div>

                        {/* Language Dropdown */}
                        <div className="relative" ref={languageDropdownRef}>
                        <button
                                onClick={() => setIsLanguageDropdownOpen(!isLanguageDropdownOpen)}
                                className="group flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.05] backdrop-blur-sm border border-white/15 hover:bg-white/[0.08] hover:border-white/25 transition-all duration-300"
                        >
                                <div className="text-lg group-hover:scale-110 transition-transform duration-300">
                                {selectedLanguage === "en" ? languages.en.flag : languages.it.flag}
                            </div>
                                <span className="text-sm font-semibold text-white">
                                    {selectedLanguage === "en" ? languages.en.name : languages.it.name}
                                </span>
                                <FaChevronDown className={`h-3 w-3 text-zinc-400 group-hover:text-zinc-300 transition-all duration-300 ${
                                    isLanguageDropdownOpen ? 'rotate-180' : ''
                                }`} />
                            </button>

                            {/* Dropdown Menu */}
                            {isLanguageDropdownOpen && (
                                <div className="absolute top-full right-0 mt-2 w-48 bg-gray-900 backdrop-blur-xl rounded-lg border border-white/20 shadow-xl z-50 overflow-hidden">
                                    <div className="py-1">
                                        {/* English Option */}
                                        <button
                                            onClick={() => {
                                                setSelectedLanguage("en");
                                                setIsLanguageDropdownOpen(false);
                                            }}
                                            className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-all duration-300 ${
                                                selectedLanguage === "en"
                                                    ? "bg-indigo-500/20 text-indigo-300"
                                                    : "text-zinc-300 hover:bg-white/[0.05] hover:text-white"
                                            }`}
                                        >
                                            <div className="text-lg">
                                                {languages.en.flag}
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="text-sm font-semibold">
                                                    {languages.en.name}
                                </span>
                                <span className="text-xs text-zinc-500">
                                                    English
                                </span>
                            </div>
                                            {selectedLanguage === "en" && (
                                                <FaChevronDown className="h-3 w-3 text-indigo-300 ml-auto rotate-90" />
                                            )}
                        </button>

                                        {/* Italian Option */}
                                        <button
                                            onClick={() => {
                                                setSelectedLanguage("it");
                                                setIsLanguageDropdownOpen(false);
                                            }}
                                            className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-all duration-300 ${
                                                selectedLanguage === "it"
                                                    ? "bg-indigo-500/20 text-indigo-300"
                                                    : "text-zinc-300 hover:bg-white/[0.05] hover:text-white"
                                            }`}
                                        >
                                            <div className="text-lg">
                                                {languages.it.flag}
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="text-sm font-semibold">
                                                    {languages.it.name}
                                                </span>
                                                <span className="text-xs text-zinc-500">
                                                    Italiano
                                                </span>
                                            </div>
                                            {selectedLanguage === "it" && (
                                                <FaChevronDown className="h-3 w-3 text-indigo-300 ml-auto rotate-90" />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Controls Section */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

                        {/* Difficulty Level Section */}
                        <div className="bg-white/[0.02] backdrop-blur-sm rounded-xl border border-white/10 p-4">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                                    <FaGraduationCap className="h-4 w-4 text-indigo-400" />
                                </div>
                                <div>
                                    <h3 className="text-sm font-semibold text-white">
                                        {currentLang.labels.difficultyLevel}
                                    </h3>
                                    <p className="text-xs text-zinc-400">
                                    {currentLang.labels.difficultyLevelDesc}
                                </p>
                                </div>
                            </div>

                            <div className="flex gap-2">
                                {(["starter", "medium", "advanced"] as const).map((lvl, index) => {
                                    const icons = [FaStar, FaStarHalfAlt, FaStarOfLife];
                                    const IconComponent = icons[index];
                                    const colors = {
                                        starter: {
                                            bg: "bg-emerald-500/15",
                                            border: "border-emerald-400/40",
                                            text: "text-emerald-300",
                                            hover: "hover:bg-emerald-500/25",
                                            icon: "text-emerald-400"
                                        },
                                        medium: {
                                            bg: "bg-blue-500/15",
                                            border: "border-blue-400/40", 
                                            text: "text-blue-300",
                                            hover: "hover:bg-blue-500/25",
                                            icon: "text-blue-400"
                                        },
                                        advanced: {
                                            bg: "bg-purple-500/15",
                                            border: "border-purple-400/40",
                                            text: "text-purple-300", 
                                            hover: "hover:bg-purple-500/25",
                                            icon: "text-purple-400"
                                        }
                                    };
                                    
                                    return (
                                        <button
                                            key={lvl}
                                            onClick={() => handleLevelChange(lvl)}
                                            className={`group relative px-4 py-3 rounded-lg transition-all duration-300 flex items-center gap-2 flex-1 ${
                                                level === lvl
                                                    ? `${colors[lvl].bg} ${colors[lvl].border} ${colors[lvl].text} shadow-lg border backdrop-blur-sm`
                                                    : "text-zinc-400 hover:text-zinc-300 hover:bg-white/[0.05] border border-white/10 hover:border-white/20"
                                            }`}
                                        >
                                            <div className={`p-1 rounded-md transition-all duration-300 ${
                                                level === lvl ? colors[lvl].bg : "bg-white/[0.05]"
                                            }`}>
                                                <IconComponent className={`h-3 w-3 transition-colors duration-300 ${
                                                    level === lvl ? colors[lvl].icon : "text-zinc-500"
                                            }`} />
                                            </div>
                                            <span className="text-xs font-semibold tracking-wide">
                                                {currentLang.levels[lvl]}
                                            </span>
                                            
                                            {/* Active indicator */}
                                            {level === lvl && (
                                                <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full ${colors[lvl].bg} border-2 border-white/20`} />
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Role Play Section */}
                        <div className="bg-white/[0.02] backdrop-blur-sm rounded-lg border border-white/10 p-3">
                            <div className="flex items-center gap-2 mb-2">
                                    <FaUserTie className="h-4 w-4 text-emerald-400" />
                                <h3 className="text-sm font-semibold text-zinc-200">
                                        Role Play Mode
                                </h3>
                                </div>
                            <p className="text-xs text-zinc-500 mb-3">
                                {userType === 'customer' 
                                    ? "AI acts as staff from your selected organization"
                                    : userType === 'org_owner'
                                    ? "Configure how AI represents your organization"
                                    : "AI acts as organization staff"
                                }
                            </p>

                            <div className="flex flex-col gap-2">
                                {/* Organization Display for Customers */}
                                {userType === 'customer' && selectedOrgForCustomer && (
                                    <div className="px-3 py-2 rounded-md bg-emerald-500/10 border border-emerald-400/20">
                                        <div className="flex items-center gap-2">
                                            <FaBuilding className="h-3 w-3 text-emerald-400" />
                                            <span className="text-xs font-semibold text-emerald-300">
                                                Interacting with: {selectedOrgForCustomer.name}
                                            </span>
                            </div>
                                    </div>
                                )}

                                {/* Organization Display for Org Owners */}
                                {userType === 'org_owner' && orgName && (
                                    <div className="px-3 py-2 rounded-md bg-blue-500/10 border border-blue-400/20">
                                        <div className="flex items-center gap-2">
                                            <FaBuilding className="h-3 w-3 text-blue-400" />
                                            <span className="text-xs font-semibold text-blue-300">
                                                Managing: {orgName}
                                            </span>
                                        </div>
                                    </div>
                                )}

                                {/* Main Role Play Button */}
                            <button
                                    onClick={() => {
                                        if (userType === 'org_owner' && orgName) {
                                            handleConfigureRolePlay();
                                        } else if (userType === 'customer') {
                                            handleConfigureRolePlay();
                                        } else {
                                            setShowRolePlayModal(true);
                                        }
                                    }}
                                    className={`group flex items-center justify-center gap-2 px-3 py-2 rounded-md transition-all duration-300 ${
                                    rolePlayEnabled
                                            ? "bg-emerald-500/20 border border-emerald-400/30 text-emerald-300 shadow-md hover:bg-emerald-500/30"
                                            : "bg-white/[0.05] text-zinc-400 hover:text-zinc-300 hover:bg-white/[0.08] border border-white/15"
                                }`}
                            >
                                {rolePlayEnabled ? (
                                    <FaBuilding className="h-3 w-3 text-current" />
                                ) : (
                                    <FaCog className="h-3 w-3 text-zinc-500" />
                                )}
                                <span className="text-xs font-semibold">
                                        {rolePlayEnabled 
                                            ? rolePlayTemplates[rolePlayTemplate].name 
                                            : userType === 'customer' 
                                                ? "Select Organization"
                                                : userType === 'org_owner'
                                                ? "Configure Organization"
                                                : "Configure Role Play"
                                        }
                                </span>
                            </button>
                                
                                {/* Role Play Action Buttons */}
                                {rolePlayEnabled && (
                                    <div className="flex gap-1">
                                        <button
                                            onClick={() => setShowRolePlayAnswers(true)}
                                            className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md bg-blue-500/25 text-blue-200 border border-blue-400/30 hover:bg-blue-500/35 transition-all duration-300"
                                            title="View Database"
                                        >
                                            <Database className="h-3 w-3" />
                                            <span className="text-xs font-medium">Database</span>
                                        </button>
                                        <button
                                            onClick={() => {
                                                console.log("Clearing role play from header...");
                                                // Send WebSocket message to clear role play
                                                if (ws.current?.readyState === WebSocket.OPEN) {
                                                    ws.current.send(JSON.stringify({
                                                        type: "clear_roleplay"
                                                    }));
                                                }
                                                // Clear local state immediately for better UX
                                                setRolePlayEnabled(false);
                                                setOrganizationName("");
                                                setOrganizationDetails("");
                                                setRoleTitle("");
                                            }}
                                            className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md bg-red-500/25 text-red-200 border border-red-400/30 hover:bg-red-500/35 transition-all duration-300"
                                            title="Disable Role Play"
                                        >
                                            <FaTimes className="h-3 w-3" />
                                            <span className="text-xs font-medium">Disable</span>
                                        </button>
                            </div>
                                )}
                            
                            {/* Role Play Status */}
                            {rolePlayEnabled && (
                                    <div className="text-xs text-green-300 bg-green-500/10 px-2 py-1.5 rounded-md border border-green-400/30 text-center">
                                        <strong>Active:</strong> {organizationName} • {roleTitle}
                                </div>
                            )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Level Change Notification */}
                {levelChangeNotification && (
                    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 bg-gradient-to-r from-indigo-500/90 to-purple-500/90 backdrop-blur-xl rounded-2xl border border-indigo-400/30 px-6 py-4 shadow-2xl animate-in slide-in-from-top-2 duration-300">
                        <div className="flex items-center gap-3 text-white">
                            <Brain className="h-5 w-5 text-indigo-200" />
                            <span className="font-semibold">
                                Level changed to: {currentLang.levels[level]} • {currentLang.levels[`${level}Desc` as keyof typeof currentLang.levels]}
                            </span>
                        </div>
                    </div>
                )}

                {/* Role Play Configuration Modal */}
                {showRolePlayModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                        <div className="bg-gradient-to-br from-white/[0.05] to-white/[0.02] backdrop-blur-xl rounded-3xl border border-white/20 p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-2xl font-bold text-zinc-100">Configure Role Play</h2>
                                <button
                                    onClick={() => setShowRolePlayModal(false)}
                                    className="text-zinc-400 hover:text-zinc-200 text-2xl"
                                >
                                    ×
                                </button>
                            </div>

                            {/* Template Selection */}
                            <div className="mb-6">
                                <label className="block text-sm font-semibold text-zinc-300 mb-3">
                                    Choose Organization Type
                                </label>
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                    {Object.entries(rolePlayTemplates).map(([key, template]) => (
                                        <button
                                            key={key}
                                            onClick={() => {
                                                setRolePlayTemplate(key as any);
                                                if (!roleTitle || roleTitle === "Teacher" || roleTitle === "Software Developer" || roleTitle === "Waiter" || roleTitle === "Nurse" || roleTitle === "Employee") {
                                                    setRoleTitle(template.defaultRole);
                                                }
                                            }}
                                            className={`p-4 rounded-xl border transition-all duration-300 text-center ${
                                                rolePlayTemplate === key
                                                    ? "bg-gradient-to-r from-blue-500/25 to-indigo-500/25 border-blue-400/40 text-blue-200"
                                                    : "bg-white/[0.03] border-white/10 text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-300"
                                            }`}
                                        >
                                            <div className="text-2xl mb-2">{template.icon}</div>
                                            <div className="font-semibold text-sm">{template.name}</div>
                                            <div className="text-xs opacity-70 mt-1">{template.description}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Organization Details Form */}
                            <div className="space-y-4">
                                <div key="org-name-container">
                                    <label className="block text-sm font-semibold text-zinc-300 mb-2">
                                        Organization Name
                                    </label>
                                    <input
                                        key="org-name-input"
                                        type="text"
                                        value={organizationName}
                                        onChange={(e) => setOrganizationName(e.target.value)}
                                        placeholder="e.g., ABC International School"
                                        className="w-full px-4 py-3 bg-white/[0.05] border border-white/10 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-400/50 transition-all duration-300"
                                        autoComplete="off"
                                        spellCheck="false"
                                    />
                                </div>

                                <div key="org-details-container">
                                    <label className="block text-sm font-semibold text-zinc-300 mb-2">
                                        Organization Details
                                    </label>
                                    <textarea
                                        key="org-details-textarea"
                                        value={organizationDetails}
                                        onChange={(e) => setOrganizationDetails(e.target.value)}
                                        placeholder={rolePlayTemplates[rolePlayTemplate].placeholder}
                                        rows={4}
                                        className="w-full px-4 py-3 bg-white/[0.05] border border-white/10 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-400/50 transition-all duration-300 resize-none"
                                        autoComplete="off"
                                        spellCheck="false"
                                    />
                                </div>

                                <div key="role-title-container">
                                    <label className="block text-sm font-semibold text-zinc-300 mb-2">
                                        Your Role Title
                                    </label>
                                    <input
                                        key="role-title-input"
                                        type="text"
                                        value={roleTitle}
                                        onChange={(e) => setRoleTitle(e.target.value)}
                                        placeholder={rolePlayTemplates[rolePlayTemplate].defaultRole}
                                        className="w-full px-4 py-3 bg-white/[0.05] border border-white/10 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-400/50 transition-all duration-300"
                                        autoComplete="off"
                                        spellCheck="false"
                                    />
                                </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex gap-3 mt-8">
                                <button
                                    onClick={() => {
                                        setRolePlayEnabled(false);
                                        setOrganizationName("");
                                        setOrganizationDetails("");
                                        setRoleTitle("");
                                        setShowRolePlayModal(false);
                                        sendPrefs();
                                    }}
                                    className="flex-1 px-4 py-3 bg-white/[0.05] border border-white/10 rounded-xl text-zinc-300 hover:bg-white/[0.08] transition-all duration-300"
                                >
                                    Reset
                                </button>
                                <button
                                    onClick={() => {
                                        setRolePlayEnabled(true);
                                        setShowRolePlayModal(false);
                                        sendPrefs();
                                    }}
                                    disabled={!organizationName || !organizationDetails}
                                    className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-500/25 to-indigo-500/25 border border-blue-400/40 rounded-xl text-blue-200 hover:from-blue-500/35 hover:to-indigo-500/35 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {rolePlayEnabled ? "Update Role Play" : "Start Role Play"}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Role Play Answers Modal */}
                <RolePlayAnswers 
                    clientId={clientIdRef.current}
                    isVisible={showRolePlayAnswers}
                    onClose={() => setShowRolePlayAnswers(false)}
                />

                {/* Voice Control Center with Audio Wave Glow */}
                <div className="bg-gradient-to-br from-white/[0.03] to-white/[0.01] backdrop-blur-xl rounded-3xl border border-white/15 p-4 sm:p-6 lg:p-8 mb-10 shadow-[0_25px_80px_-25px_rgba(0,0,0,0.9)] relative overflow-hidden">
                    {/* Audio Wave Based Glowing Effects */}
                    {(() => {
                        const isSpeechActive = listening && micLevel > 0.01;
                        const isTtsActive = aiSpeaking && ttsAudioLevel > 0.01;
                        const isActive = isSpeechActive || isTtsActive;
                        
                        if (!isActive) return null;
                        
                        // Determine active source values
                        const activeLevel = isSpeechActive ? micLevel : ttsAudioLevel;
                        const activeFrame = isSpeechActive ? waveAnimationFrame : ttsWaveAnimationFrame;
                        const baseHue = isSpeechActive ? 200 : 120; // Blue for speech, Green for TTS
                        
                        return (
                            <>
                                {/* Outer Glow Ring - Synced with Audio Wave */}
                                <div 
                                    className="absolute inset-0 rounded-3xl pointer-events-none"
                                    style={{
                                        background: `conic-gradient(from ${activeFrame * 2}deg, 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 14.4) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 28.8) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 43.2) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 57.6) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 72) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 86.4) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 100.8) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 115.2) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 129.6) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 144) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 158.4) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 172.8) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 187.2) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 201.6) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 216) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 230.4) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 244.8) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 259.2) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 273.6) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 288) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 302.4) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 316.8) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 331.2) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2 + 345.6) % 360}, 70%, 50%), 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 2) % 360}, 70%, 50%))`,
                                        opacity: activeLevel * 0.4,
                                        filter: 'blur(25px)',
                                        transform: `scale(${1 + activeLevel * 0.15}) rotate(${activeFrame * 0.5}deg)`
                                    }}
                                />
                            
                                {/* Inner Glow Ring - Synced with Audio Wave */}
                                <div 
                                    className="absolute inset-2 rounded-3xl pointer-events-none"
                                    style={{
                                        background: `radial-gradient(circle at center, 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 3) % 360}, 80%, 60%) 0%, 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 3 + 60) % 360}, 70%, 50%) 30%, 
                                            hsl(${(baseHue + activeLevel * 120 + activeFrame * 3 + 120) % 360}, 60%, 40%) 60%, 
                                            transparent 80%)`,
                                        opacity: activeLevel * 0.5,
                                        filter: 'blur(20px)',
                                        transform: `scale(${1 + activeLevel * 0.1})`
                                    }}
                                />
                                
                                {/* Pulsing Border Glow - Synced with Audio Wave */}
                                <div 
                                    className="absolute inset-0 rounded-3xl pointer-events-none border-2"
                                    style={{
                                        borderColor: `hsl(${(baseHue + activeLevel * 120 + activeFrame * 4) % 360}, 90%, 70%)`,
                                        opacity: activeLevel * 0.7,
                                        boxShadow: `0 0 ${activeLevel * 40 + 25}px hsl(${(baseHue + activeLevel * 120 + activeFrame * 4) % 360}, 90%, 70%),
                                                   0 0 ${activeLevel * 60 + 35}px hsl(${(baseHue + activeLevel * 120 + activeFrame * 4 + 120) % 360}, 80%, 60%),
                                                   0 0 ${activeLevel * 80 + 45}px hsl(${(baseHue + activeLevel * 120 + activeFrame * 4 + 240) % 360}, 70%, 50%)`,
                                        animation: 'pulse 1.2s ease-in-out infinite',
                                        transform: `scale(${1 + Math.sin(activeFrame * 0.1) * activeLevel * 0.05})`
                                    }}
                                />
                            </>
                        );
                    })()}
                    
                    {/* Static Background */}
                    <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5 rounded-3xl pointer-events-none" />
                    
                    <div className="relative z-10 flex flex-col items-center">
                        {/* Role Play Test Button */}
                        {rolePlayEnabled && (
                            <div className="mb-4 text-center">
                                <div className="text-xs text-green-300 bg-green-500/10 px-3 py-2 rounded-lg border border-green-400/30 mb-2">
                                    🎭 Role Play Active: {organizationName} • {roleTitle}
                                </div>
                                <div className="text-xs text-blue-300 bg-blue-500/10 px-3 py-2 rounded-lg border border-blue-400/30 mb-2">
                                    📝 Template: {rolePlayTemplate} • Role: {roleTitle}
                                </div>
                                <div className="flex gap-2 justify-center mb-2">
                                    <button
                                        onClick={() => {
                                            console.log("Testing role play with question...");
                                            // Simulate asking about organization
                                            const testQuestion = "What is your organization name?";
                                            console.log("Test question:", testQuestion);
                                        }}
                                        className="px-3 py-2 bg-blue-500/20 text-blue-300 text-xs rounded border border-blue-400/30 hover:bg-blue-500/30 transition-all duration-300"
                                    >
                                        Test Role Play
                                    </button>
                                    <button
                                        onClick={() => {
                                            console.log("Clearing role play...");
                                            if (ws.current?.readyState === WebSocket.OPEN) {
                                                ws.current.send(JSON.stringify({
                                                    type: "clear_roleplay"
                                                }));
                                            }
                                        }}
                                        className="px-3 py-2 bg-red-500/20 text-red-300 text-xs rounded border border-red-400/30 hover:bg-red-500/30 transition-all duration-300"
                                    >
                                        Clear Role Play
                                    </button>
                                </div>
                            </div>
                        )}
                        
                        {/* Clean Audio Wave Animation */}
                        <div className="mb-8 flex justify-center">
                            <div className="flex items-center justify-center space-x-2 h-20">
                                {Array.from({ length: 25 }).map((_, i) => {
                                    const baseHeight = 12;
                                    const maxHeight = 60;
                                    
                                    // Determine if we're showing speech waves or TTS audio waves
                                    const isSpeechActive = listening && micLevel > 0.01;
                                    const isTtsActive = aiSpeaking && ttsAudioLevel > 0.01;
                                    const isActive = isSpeechActive || isTtsActive;
                                    
                                    // Calculate wave height based on active source
                                    let waveHeight = baseHeight;
                                    if (isSpeechActive) {
                                        waveHeight = Math.max(baseHeight, micLevel * maxHeight + Math.sin(waveAnimationFrame * 0.15 + i * 0.4) * (micLevel * 20 + 8));
                                    } else if (isTtsActive) {
                                        waveHeight = Math.max(baseHeight, ttsAudioLevel * maxHeight + Math.sin(ttsWaveAnimationFrame * 0.15 + i * 0.4) * (ttsAudioLevel * 20 + 8));
                                    }
                                    
                                    // Clean rainbow colors based on active source
                                    let baseHue, animationHue, saturation, lightness;
                                    
                                    if (isSpeechActive) {
                                        // Speech wave colors (blue to green spectrum)
                                        baseHue = micLevel * 120 + 200; // Blue to green
                                        animationHue = waveAnimationFrame * 2;
                                        saturation = Math.min(100, 70 + micLevel * 30);
                                        lightness = Math.min(80, 50 + micLevel * 30);
                                    } else if (isTtsActive) {
                                        // TTS audio wave colors (green to yellow spectrum)
                                        baseHue = ttsAudioLevel * 60 + 120; // Green to yellow
                                        animationHue = ttsWaveAnimationFrame * 2;
                                        saturation = Math.min(100, 70 + ttsAudioLevel * 30);
                                        lightness = Math.min(80, 50 + ttsAudioLevel * 30);
                                    } else {
                                        // Inactive state
                                        baseHue = 200;
                                        animationHue = 0;
                                        saturation = 20;
                                        lightness = 40;
                                    }
                                    
                                    const positionHue = i * 14.4; // 360/25 = 14.4 degrees per bar
                                    const hue = isActive 
                                        ? (baseHue + positionHue + animationHue) % 360 
                                        : 200; // Blue placeholder color
                                    
                                    const opacity = isActive 
                                        ? Math.max(0.6, (isSpeechActive ? micLevel : ttsAudioLevel) * 0.8 + 0.2) 
                                        : 0.3;
                                    
                                    return (
                                        <div
                                            key={i}
                                            className={`w-2 rounded-full transition-all duration-200 ease-out`}
                                            style={{
                                                height: `${waveHeight}px`,
                                                backgroundColor: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
                                                opacity: opacity,
                                                animationDelay: `${i * 60}ms`,
                                                transform: isActive 
                                                    ? `scaleY(${1 + Math.sin((isSpeechActive ? waveAnimationFrame : ttsWaveAnimationFrame) * 0.08 + i * 0.25) * 0.15}) scaleX(${1 + Math.sin((isSpeechActive ? waveAnimationFrame : ttsWaveAnimationFrame) * 0.12 + i * 0.3) * 0.1})`
                                                    : 'scaleY(1) scaleX(1)',
                                                boxShadow: 'none',
                                                filter: 'none'
                                            }}
                                        />
                                    );
                                })}
                            </div>
                        </div>

                        {/* Small Rounded Button - Fixed Click with Glass UI */}
                        <div className="flex justify-center relative z-50">
                            <button
                                onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    console.log("Button clicked, listening:", listening, "connected:", connected);
                                    if (listening) {
                                        stopMic();
                                    } else {
                                        startMic();
                                    }
                                }}
                                onMouseDown={(e) => e.stopPropagation()}
                                onMouseUp={(e) => e.stopPropagation()}
                                className={`relative z-50 px-6 py-3 rounded-full font-semibold text-sm transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer ${
                                    listening 
                                        ? listening && micLevel > 0.01
                                            ? "bg-red-600/20 backdrop-blur-xl text-white hover:bg-red-600/30 shadow-lg"
                                            : "bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white shadow-lg"
                                        : !connected
                                            ? "bg-zinc-600/80 text-white cursor-not-allowed shadow-lg"
                                            : "bg-blue-600/80 text-white hover:bg-blue-600 shadow-lg"
                                }`}
                                disabled={!connected}
                                style={{ 
                                    pointerEvents: 'auto',
                                    ...(listening && micLevel > 0.01 ? {
                                        background: `linear-gradient(135deg, 
                                            rgba(239, 68, 68, 0.2) 0%, 
                                            rgba(239, 68, 68, 0.1) 50%, 
                                            rgba(239, 68, 68, 0.2) 100%)`,
                                        backdropFilter: 'blur(20px)',
                                        boxShadow: `0 8px 32px rgba(239, 68, 68, 0.3),
                                                   inset 0 1px 0 rgba(255, 255, 255, 0.2)`,
                                        transform: `scale(${1 + micLevel * 0.05})`
                                    } : {})
                                }}
                            >
                                {listening ? (
                                    <>
                                        {aiSpeaking ? (
                                            <>
                                                <div className="h-4 w-4 rounded-full bg-green-400 animate-pulse" />
                                                <span 
                                                    style={{
                                                        color: 'white',
                                                        textShadow: `0 0 10px hsl(${((listening && micLevel > 0.01) ? (micLevel * 360 + waveAnimationFrame * 2) : (ttsAudioLevel * 60 + 120 + ttsWaveAnimationFrame * 2)) % 360}, 80%, 70%)`,
                                                        fontWeight: '600'
                                                    }}
                                                >
                                                    Speaking
                                                </span>
                                            </>
                                        ) : isWaitingForResponse ? (
                                            <>
                                                <div className="h-4 w-4 rounded-full bg-purple-400 animate-pulse" />
                                                <span 
                                                    style={{
                                                        color: 'white',
                                                        textShadow: `0 0 10px hsl(${(280 + ttsWaveAnimationFrame * 2) % 360}, 80%, 70%)`,
                                                        fontWeight: '600'
                                                    }}
                                                >
                                                    AI Thinking
                                                </span>
                                            </>
                                        ) : (
                                    <>
                                        <Pause 
                                            className="h-4 w-4" 
                                            style={{
                                                ...((listening && micLevel > 0.01) || (aiSpeaking && ttsAudioLevel > 0.01) ? {
                                                    filter: `drop-shadow(0 0 8px hsl(${((listening && micLevel > 0.01) ? (micLevel * 360 + waveAnimationFrame * 2) : (ttsAudioLevel * 60 + 120 + ttsWaveAnimationFrame * 2)) % 360}, 80%, 70%))`,
                                                    transform: `scale(${1 + ((listening && micLevel > 0.01) ? micLevel : ttsAudioLevel) * 0.1})`
                                                } : {})
                                            }}
                                        />
                                        <span 
                                            style={{
                                                ...((listening && micLevel > 0.01) || (aiSpeaking && ttsAudioLevel > 0.01) ? {
                                                    textShadow: `0 0 10px hsl(${((listening && micLevel > 0.01) ? (micLevel * 360 + waveAnimationFrame * 2) : (ttsAudioLevel * 60 + 120 + ttsWaveAnimationFrame * 2)) % 360}, 80%, 70%)`,
                                                    fontWeight: '600'
                                                } : {})
                                            }}
                                        >
                                            Stop
                                        </span>
                                            </>
                                        )}
                                    </>
                                ) : (
                                    <>
                                        {!connected ? (
                                            <>
                                                <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                <span>Connecting...</span>
                                            </>
                                        ) : (
                                            <>
                                                <Mic className="h-4 w-4" />
                                                <span>Start</span>
                                            </>
                                        )}
                                    </>
                                )}
                            </button>
                        </div>

                    </div>
                </div>


                {/* Panels */}
                <div className="grid lg:grid-cols-2 gap-6 lg:gap-8">
                    {/* Soft Mind-Blowing Voice */}
                    <div className="group relative rounded-2xl border border-white/8 bg-white/[0.02] backdrop-blur-xl shadow-[0_12px_40px_-12px_rgba(0,0,0,0.8)] overflow-hidden transition-all duration-400 hover:shadow-[0_16px_50px_-12px_rgba(0,0,0,0.9)] hover:border-white/12">
                        {/* Soft animated background */}
                        <div className="absolute inset-0 bg-white/[0.01] opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                        
                        <div className="relative px-5 py-4 border-b border-white/8 bg-white/[0.01]">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    {/* Soft Icon */}
                                    <div className="relative">
                                        <div className="h-9 w-9 rounded-lg bg-white/[0.05] flex items-center justify-center border border-white/10 shadow-sm group-hover:shadow-md transition-all duration-300">
                                            <User className="h-4.5 w-4.5 text-zinc-400 group-hover:text-zinc-300 transition-colors duration-300" />
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <h3 className="text-lg font-semibold text-zinc-200 mb-0.5 group-hover:text-zinc-100 transition-colors duration-300">
                                            {currentLang.labels.yourVoice}
                                        </h3>
                                        <p className="text-xs text-zinc-500 group-hover:text-zinc-400 transition-colors duration-300">
                                            {currentLang.labels.yourVoiceDesc}
                                        </p>
                                    </div>
                                </div>
                                
                                {/* Soft Status Indicators */}
                                <div className="flex items-center gap-2">
                                    {(useWebkitVAD || useFallbackVAD) && (
                                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/8 shadow-sm">
                                            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                                            <span className="text-xs font-medium text-emerald-300">STT</span>
                                        </div>
                                    )}
                                    {listening && (
                                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/8 shadow-sm">
                                            <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
                                            <span className="text-xs font-medium text-blue-300">Live</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Soft Organized Content */}
                        <div className="relative p-5 min-h-[180px]">
                            {/* Soft Live Processing */}
                            {(useWebkitVAD || useFallbackVAD) && (
                                <div className="mb-4">
                                    <div className="relative group">
                                        {/* Soft Live Container */}
                                        <div className="min-h-[60px] p-3 bg-white/[0.02] rounded-xl border border-white/6 hover:border-white/8 transition-all duration-300 shadow-sm hover:shadow-md">
                                            {interimTranscript && (
                                                <div className="text-sm text-blue-300 italic leading-relaxed">
                                                    {interimTranscript}
                                                    <span className="animate-pulse text-blue-400 ml-1">|</span>
                                                </div>
                                            )}
                                            {!interimTranscript && !finalTranscript && (
                                                <div className="text-sm text-zinc-500 italic leading-relaxed">
                                                    {listening ? "Listening..." : "Ready"}
                                                </div>
                                            )}
                                            {finalTranscript && !interimTranscript && (
                                                <div className="text-sm text-zinc-500 italic leading-relaxed">
                                                    Processing complete...
                                                </div>
                                            )}
                                        </div>
                                        
                                        {/* Soft Confidence Badge */}
                                        {vadConfidence > 0 && (
                                            <div className="absolute -top-1 -right-1 px-2 py-1 bg-white/[0.05] border border-white/8 rounded-lg backdrop-blur-sm shadow-sm">
                                                <span className="text-xs text-zinc-400 font-medium">
                                                    {(vadConfidence * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {transcript ? (
                                <div className="space-y-3">
                                    {/* Soft AI Status */}
                                    <div className="flex items-center gap-2 px-3 py-1.5 bg-white/[0.02] rounded-lg border border-white/6 shadow-sm">
                                        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse" />
                                        <span className="text-xs font-medium text-purple-300">AI Enhanced</span>
                                        <div className="ml-auto">
                                            <span className="text-xs text-zinc-500">Active</span>
                                        </div>
                                    </div>

                                    {/* Soft Transcript Cards */}
                                    <div className="space-y-2">
                                        {transcript.split(".").map((s, i) =>
                                            s.trim() && (
                                                <div key={i} className="bg-white/[0.02] rounded-lg p-3 border border-white/6 hover:border-white/8 transition-all duration-300 group shadow-sm hover:shadow-md">
                                                    <p className="text-sm leading-relaxed text-zinc-300 group-hover:text-zinc-200 transition-colors duration-300">{s.trim()}.</p>
                                                </div>
                                            )
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="flex items-center justify-center h-full text-zinc-500">
                                    <div className="text-center">
                                        <Mic className="h-12 w-12 mx-auto mb-3 opacity-30" />
                                        <p className="text-xs font-medium mb-1 text-zinc-400">
                                            {currentLang.labels.readyToCapture}
                                        </p>
                                        <p className="text-xs text-zinc-600 bg-white/[0.02] px-3 py-1.5 rounded-lg border border-white/6">
                                            {useWebkitVAD ? "STT Active" : 
                                             useFallbackVAD ? "VAD Active" : 
                                             "Start Conversation"}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Minimal Professional AI Response */}
                    <div className="group relative rounded-2xl border border-white/8 bg-white/[0.02] backdrop-blur-xl shadow-[0_12px_40px_-12px_rgba(0,0,0,0.8)] overflow-hidden transition-all duration-400 hover:shadow-[0_16px_50px_-12px_rgba(0,0,0,0.9)] hover:border-white/12">
                        {/* Soft animated background */}
                        <div className="absolute inset-0 bg-white/[0.01] opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                        
                        <div className="relative px-5 py-4 border-b border-white/8 bg-white/[0.01]">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    {/* Soft Icon */}
                                    <div className="relative">
                                        <div className="h-9 w-9 rounded-lg bg-white/[0.05] flex items-center justify-center border border-white/10 shadow-sm group-hover:shadow-md transition-all duration-300">
                                            <Bot className="h-4.5 w-4.5 text-zinc-400 group-hover:text-zinc-300 transition-colors duration-300" />
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <h3 className="text-lg font-semibold text-zinc-200 mb-0.5 group-hover:text-zinc-100 transition-colors duration-300">
                                            {currentLang.labels.aiResponse}
                                        </h3>
                                        <p className="text-xs text-zinc-500 group-hover:text-zinc-400 transition-colors duration-300">
                                            {currentLang.labels.aiResponseDesc}
                                        </p>
                                        {rolePlayEnabled && (
                                            <div className="mt-1 text-xs text-green-300 bg-green-500/10 px-2 py-0.5 rounded border border-green-400/30">
                                                🎭 {organizationName} • {roleTitle}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                
                                {/* Soft Status Indicators */}
                                <div className="flex items-center gap-2">
                                    {aiSpeaking && (
                                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/8 shadow-sm">
                                            <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
                                            <span className="text-xs font-medium text-indigo-300">Speaking</span>
                                        </div>
                                    )}
                                    {aiSpeaking && listening && (
                                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-orange-500/10 border border-orange-400/30 shadow-sm">
                                            <div className="w-1.5 h-1.5 bg-orange-400 rounded-full" />
                                            <span className="text-xs font-medium text-orange-300">Mic Paused</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Soft Organized Content */}
                        <div className="relative p-5 min-h-[180px]">
                            {aiText ? (
                                <div className="space-y-2">
                                    {aiText.includes("🔴 GRAMMAR_CORRECTION_START 🔴") ? (
                                        // Grammar correction display - Ultra Professional Design
                                        <div className="space-y-3">
                                            {/* Grammar correction section - Ultra Minimal Professional */}
                                            <div className="bg-slate-900/20 border border-slate-800/50 rounded-2xl overflow-hidden">
                                                {/* Ultra clean header */}
                                                <div className="px-5 py-4 border-b border-slate-800/50">
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-1.5 h-1.5 bg-blue-400 rounded-full"></div>
                                                            <span className="text-sm font-medium text-slate-300">Grammar Checker</span>
                                                        </div>
                                                        <div className="text-xs text-slate-500 font-medium">AI</div>
                                                    </div>
                                                </div>
                                                
                                                {/* Ultra clean content */}
                                                <div className="p-5 space-y-4">
                                                    {(() => {
                                                        // Extract grammar correction section
                                                        const startMarker = "🔴 GRAMMAR_CORRECTION_START 🔴";
                                                        const endMarker = "🔴 GRAMMAR_CORRECTION_END 🔴";
                                                        
                                                        if (!aiText.includes(startMarker) || !aiText.includes(endMarker)) {
                                                            return (
                                                                <div className="text-center py-6">
                                                                    <div className="w-6 h-6 mx-auto mb-3 bg-slate-800/50 rounded-full flex items-center justify-center">
                                                                        <svg className="w-3 h-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                                        </svg>
                                                                    </div>
                                                                    <p className="text-sm text-slate-500">Perfect grammar</p>
                                                                </div>
                                                            );
                                                        }
                                                        
                                                        const grammarSection = aiText.split(startMarker)[1]?.split(endMarker)[0]?.trim();
                                                        if (!grammarSection) {
                                                            return <div className="text-slate-500 text-sm">No grammar data</div>;
                                                        }
                                                        
                                                        const lines = grammarSection.split('\n').map(line => line.trim()).filter(line => line);
                                                        let incorrectText = "";
                                                        let correctText = "";
                                                        
                                                        lines.forEach(line => {
                                                            if (line.includes("INCORRECT:")) {
                                                                incorrectText = line.replace("INCORRECT:", "").trim();
                                                            } else if (line.includes("CORRECT:")) {
                                                                correctText = line.replace("CORRECT:", "").trim();
                                                            }
                                                        });
                                                        
                                                        // Handle case where both INCORRECT and CORRECT are in the same line
                                                        if (incorrectText && incorrectText.includes("CORRECT:")) {
                                                            const parts = incorrectText.split("CORRECT:");
                                                            incorrectText = parts[0].trim();
                                                            if (parts[1]) {
                                                                correctText = parts[1].trim();
                                                            }
                                                        }
                                                        
                                                        return (
                                                            <div className="space-y-3">
                                                                {/* Professional incorrect element */}
                                                                {incorrectText && (
                                                                    <div className="group">
                                                                        <div className="flex items-center gap-2 mb-3">
                                                                            <div className="w-1.5 h-1.5 bg-red-400 rounded-full"></div>
                                                                            <span className="text-xs text-red-400 font-semibold uppercase tracking-wide">INCORRECT</span>
                                                                        </div>
                                                                        <div className="bg-red-500/5 border-l-4 border-red-500/40 rounded-r-xl p-4 transition-all duration-200 group-hover:bg-red-500/8 group-hover:border-red-500/60">
                                                                            <p className="text-sm text-slate-200 font-medium leading-relaxed">
                                                                                {incorrectText}
                                                                            </p>
                                                                        </div>
                                                                    </div>
                                                                )}
                                                                
                                                                {/* Professional correct element */}
                                                                {correctText && (
                                                                    <div className="group">
                                                                        <div className="flex items-center gap-2 mb-3">
                                                                            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></div>
                                                                            <span className="text-xs text-emerald-400 font-semibold uppercase tracking-wide">CORRECT</span>
                                                                        </div>
                                                                        <div className="bg-emerald-500/5 border-l-4 border-emerald-500/40 rounded-r-xl p-4 transition-all duration-200 group-hover:bg-emerald-500/8 group-hover:border-emerald-500/60">
                                                                            <p className="text-sm text-slate-200 font-medium leading-relaxed">
                                                                                {correctText}
                                                                            </p>
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        );
                                                    })()}
                                                </div>
                                            </div>
                                            
                                            {/* LLM Answer section - Ultra Professional Design */}
                                            {aiText.split("🔴 GRAMMAR_CORRECTION_END 🔴")[1] && (
                                                <div className="bg-slate-900/20 border border-slate-800/50 rounded-2xl overflow-hidden">
                                                    {/* Ultra clean header */}
                                                    <div className="px-5 py-4 border-b border-slate-800/50">
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex items-center gap-3">
                                                                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></div>
                                                                <span className="text-sm font-medium text-slate-300">Intelligent Response</span>
                                                            </div>
                                                            <div className="text-xs text-slate-500 font-medium">AI</div>
                                                        </div>
                                                    </div>
                                                    
                                                    {/* Ultra clean content */}
                                                    <div className="p-5">
                                                        <div className="text-sm leading-relaxed text-slate-200">
                                                            {aiText.split("🔴 GRAMMAR_CORRECTION_END 🔴")[1].split('\n').filter(line => line.trim()).map((line, i) => (
                                                                <p key={i} className="mb-2 last:mb-0">{line.trim()}</p>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        // Normal response display - Single block
                                        <div className="bg-white/[0.02] rounded-lg p-4 border border-white/6 hover:bg-white/[0.04] transition-all duration-200">
                                            <p className="text-sm leading-relaxed text-zinc-300 whitespace-pre-wrap">{aiText}</p>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="flex items-center justify-center h-full text-zinc-500">
                                    <div className="text-center px-4">
                                        <Bot className="h-12 w-12 mx-auto mb-3 opacity-30" />
                                        <p className="text-sm font-semibold mb-1">
                                            {currentLang.labels.aiWillRespond}
                                        </p>
                                        <p className="text-xs text-zinc-600">
                                            {currentLang.labels.speakToGetResponse}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="mt-12 text-center px-4">
                    <div className="grid gap-3 sm:gap-4 md:gap-6 mb-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 place-items-stretch max-w-6xl mx-auto px-2">
                        <div className="flex items-center justify-center gap-2 sm:gap-3 bg-white/[0.03] px-3 py-2 sm:px-4 sm:py-2 rounded-xl border border-white/10">
                            <Headphones className="h-5 w-5 text-emerald-400 shrink-0" aria-hidden="true" />
                            <span className="text-xs sm:text-sm font-medium leading-tight truncate">
                                {currentLang.labels.optimalExperience}
                            </span>
                        </div>
                        <div className="flex items-center justify-center gap-2 sm:gap-3 bg-white/[0.03] px-3 py-2 sm:px-4 sm:py-2 rounded-xl border border-white/10">
                            <Mic className="h-5 w-5 text-blue-400 shrink-0" aria-hidden="true" />
                            <span className="text-xs sm:text-sm font-medium leading-tight truncate">
                                {currentLang.labels.naturalInterruption}
                            </span>
                        </div>
                        <div className="flex items-center justify-center gap-2 sm:gap-3 bg-white/[0.03] px-3 py-2 sm:px-4 sm:py-2 rounded-xl border border-white/10">
                            <Activity className="h-5 w-5 text-purple-400 shrink-0" aria-hidden="true" />
                            <span className="text-xs sm:text-sm font-medium leading-tight truncate">
                                {currentLang.labels.realTimeProcessing}
                            </span>
                        </div>
                        <div className="flex items-center justify-center gap-2 sm:gap-3 bg-white/[0.03] px-3 py-2 sm:px-4 sm:py-2 rounded-xl border border-white/10">
                            <Brain className="h-5 w-5 text-indigo-400 shrink-0" aria-hidden="true" />
                            <span className="text-xs sm:text-sm font-medium leading-tight truncate">
                                {currentLang.levels[level]} • {currentLang.levels[`${level}Desc` as keyof typeof currentLang.levels]}
                            </span>
                        </div>

                        {/* Role Play Status */}
                        <div className="flex items-center justify-center gap-2 sm:gap-3 bg-white/[0.03] px-3 py-2 sm:px-4 sm:py-2 rounded-xl border border-white/10">
                            <span className="text-lg">{rolePlayTemplates[rolePlayTemplate].icon}</span>
                            <span className="text-xs sm:text-sm font-medium leading-tight truncate">
                                {rolePlayEnabled 
                                    ? `${rolePlayTemplates[rolePlayTemplate].name} • ${roleTitle}`
                                    : "Role Play Disabled"
                                }
                            </span>
                        </div>
                    </div>

                    <p className="text-xs sm:text-sm text-zinc-600 bg-white/5 px-4 sm:px-6 py-2.5 sm:py-3 rounded-xl border border-white/10 inline-block max-w-full">
                        SHCI Voice Assistant • Professional • Self-Hosted • Intelligent
                    </p>
                </div>
                </div>
                    </div>
                </div>
            </div>
    );
}

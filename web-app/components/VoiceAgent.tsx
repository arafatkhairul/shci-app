"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import {
    Bot, Brain, Mic, Pause, Activity, Headphones, User, Database
} from "lucide-react";

// Environment Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://nodecel.com';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL || 'ws://nodecel.com';
const WS_PRODUCTION_URL = process.env.NEXT_PUBLIC_WS_PRODUCTION_URL || 'wss://nodecel.com';
import {
    FaGraduationCap,
    FaUserTie,
    FaCog,
    FaPlay,
    FaPause,
    FaMicrophone,
    FaBuilding,
    FaClock,
    FaTachometerAlt,
    FaSchool,
    FaUserGraduate,
    FaStarHalfAlt,
    FaStarOfLife,
    FaChevronDown,
    FaTimes,
    FaCheck
} from "react-icons/fa";
import RolePlayAnswers from "./RolePlayAnswers";
import WebkitVADService, { VADConfig, VADCallbacks, SpeechResult } from "../services/WebkitVADService";
import FallbackVADService, { FallbackVADConfig, FallbackVADCallbacks } from "../services/VADFallbackService";

export default function VoiceAgent() {
    // ---------- State ----------
    const [connected, setConnected] = useState(false);
    const [listening, setListening] = useState(false);
    
    // Mobile-specific state
    const [isMobile, setIsMobile] = useState(false);
    const [isProcessingAudio, setIsProcessingAudio] = useState(false);

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
    const [level, setLevel] = useState<"easy" | "medium" | "fast">("medium");
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

    // Audio queue management for streaming
    const audioQueueRef = useRef<AudioBufferSourceNode[]>([]);
    const isPlayingAudioRef = useRef(false);
    const currentAudioIndexRef = useRef(0);
    const audioPlaybackTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const audioQueueLockRef = useRef(false);
    
    // Real-time text highlighting during audio playback
    const [highlightedText, setHighlightedText] = useState("");
    const [currentSpeakingText, setCurrentSpeakingText] = useState("");
    const speakingTextRef = useRef("");

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
    const [selectedVoice, setSelectedVoice] = useState<string>("en_US-libritts-high");
    const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
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
    const [availableOrganizations, setAvailableOrganizations] = useState<Array<{ id: number, name: string, details: string }>>([]);
    const [selectedOrgForCustomer, setSelectedOrgForCustomer] = useState<{ id: number, name: string } | null>(null);
    const [isLoadingOrgs, setIsLoadingOrgs] = useState(false);

    // RAG system state - organization context for LLM
    const [organizationContext, setOrganizationContext] = useState<string>("");

    // Language dropdown ref for click outside detection
    const languageDropdownRef = useRef<HTMLDivElement>(null);
    const voiceDropdownRef = useRef<HTMLDivElement>(null);

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

    // ---------- Mobile Detection ----------
    useEffect(() => {
        const mobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        setIsMobile(mobile);
        console.log('Device type:', mobile ? 'Mobile' : 'Desktop');
    }, []);

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


    // ---------- Voice Selection Handler ----------
    const handleVoiceSelection = (voice: any) => {
        console.log('🎤 VOICE DEBUG: Voice selected:', voice.id, voice.name, voice.gender);
        setSelectedVoice(voice.id);
        setIsVoiceModalOpen(false);
        
        // Force send preferences immediately after voice selection
        setTimeout(() => {
            if (ws.current?.readyState === WebSocket.OPEN) {
                const prefs = {
                    type: "client_prefs",
                    client_id: clientIdRef.current,
                    level,
                    use_local_tts: useLocalTTS,
                    language: selectedLanguage,
                    voice: voice.id,
                    role_play_enabled: rolePlayEnabled,
                    role_play_template: rolePlayTemplate,
                    organization_name: organizationName,
                    organization_details: organizationDetails,
                    role_title: roleTitle,
                    rag_context: userType === 'customer' ? organizationContext : "",
                };
                console.log('🎤 Sending immediate voice change:', prefs);
                ws.current.send(JSON.stringify(prefs));
            }
        }, 100);
    };

    // ---------- Voice Configuration ----------
    const voiceConfig = {
        en: [
            { 
                id: "en_US-libritts-high", 
                name: "Sarah (Female)",
                fullName: "Sarah (Female)",
                gender: "female", 
                quality: "high"
            },
            { 
                id: "en_GB-cori-medium", 
                name: "Cori (Female)",
                fullName: "Cori (Female)",
                gender: "female", 
                quality: "medium"
            },
            { 
                id: "en_US-ryan-high", 
                name: "Ryan (Male)",
                fullName: "Ryan (Male)",
                gender: "male", 
                quality: "high"
            },
            { 
                id: "en_GB-northern_english_male-medium", 
                name: "Northern English Male",
                fullName: "Northern English Male",
                gender: "male", 
                quality: "medium"
            }
        ],
        it: [
            { 
                id: "en_US-libritts-high", 
                name: "Sarah (Female)",
                fullName: "Sarah (Female)",
                gender: "female", 
                quality: "high"
            },
            { 
                id: "en_GB-cori-medium", 
                name: "Cori (Female)",
                fullName: "Cori (Female)",
                gender: "female", 
                quality: "medium"
            },
            { 
                id: "en_US-ryan-high", 
                name: "Ryan (Male)",
                fullName: "Ryan (Male)",
                gender: "male", 
                quality: "high"
            },
            { 
                id: "en_GB-northern_english_male-medium", 
                name: "Northern English Male",
                fullName: "Northern English Male",
                gender: "male", 
                quality: "medium"
            }
        ]
    };


    // Debug: Log voice dropdown state changes
    useEffect(() => {
    }, [isVoiceModalOpen, selectedLanguage]);

    // Debug: Monitor voice selection changes
    useEffect(() => {
    }, [selectedVoice, selectedLanguage]);

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
                easy: "Easy",
                medium: "Medium",
                fast: "Fast",
                easyDesc: "Slow & Simple",
                mediumDesc: "Natural & Clear",
                fastDesc: "Fast & Rich",
                easyDetail: "CEFR A2 • Basic vocab • Simple sentences",
                mediumDetail: "CEFR B1-B2 • Intermediate • Natural flow",
                fastDetail: "CEFR C1 • Rich vocab • Native-like",
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
                easy: "Principiante",
                medium: "Intermedio",
                fast: "Avanzato",
                easyDesc: "Lento & Semplice",
                mediumDesc: "Naturale & Chiaro",
                fastDesc: "Veloce & Ricco",
                easyDetail: "CEFR A2 • Vocabolario base • Frasi semplici",
                mediumDetail: "CEFR B1-B2 • Intermedio • Flusso naturale",
                fastDetail: "CEFR C1 • Vocabolario ricco • Come nativo",
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
            setListening(true);
            setStatus(currentLang.status.listening);
            setShowTranscription(true);
        },
        onSpeechEnd: () => {
            // Don't automatically turn off microphone - keep it active for continuous listening
            setStatus(currentLang.status.connected);
        },
        onSpeechResult: (transcript: string, isFinal: boolean, confidence: number) => {
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
            updateMicLevel(level, source);
        }
    };

    const fallbackVADCallbacks: FallbackVADCallbacks = {
        onSpeechStart: () => {
            setListening(true);
            setStatus(currentLang.status.listening);
            setShowTranscription(true);
        },
        onSpeechEnd: () => {
            // Don't automatically turn off microphone - keep it active for continuous listening
            setStatus(currentLang.status.connected);
        },
        onSpeechResult: (transcript: string, isFinal: boolean, confidence: number) => {
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
                voice: selectedVoice,
                // role play fields (ALWAYS send)
                role_play_enabled: rolePlayEnabled,
                role_play_template: rolePlayTemplate,
                organization_name: currentOrgName,
                organization_details: orgDetails,
                role_title: roleTitle,
                // RAG context for customers
                rag_context: userType === 'customer' ? organizationContext : "",
            };

            // Debug voice selection
            console.log('🎤 Sending voice selection:', {
                voice: selectedVoice,
                language: selectedLanguage,
                level: level
            });
            ws.current.send(JSON.stringify(prefs));
        }
    }, [
        level,
        useLocalTTS,
        selectedLanguage,
        selectedVoice,
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
        // Send preferences to backend when organization context changes
        if (organizationContext && ws.current?.readyState === WebSocket.OPEN) {
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
            // CRITICAL: Immediately pause VAD services during audio playback to prevent feedback
            console.log('🔇 Pausing VAD services during AI speaking to prevent audio loop');
            if (useWebkitVAD && vadService.current) {
                vadService.current.stop();
                console.log('🔇 Webkit VAD paused');
            }
            if (useFallbackVAD && fallbackVADService.current) {
                fallbackVADService.current.stop();
                console.log('🔇 Fallback VAD paused');
            }
        } else {
            // CRITICAL: Restart VAD services after audio playback with longer delay to prevent audio loop
            console.log('🔊 Scheduling VAD restart after AI speaking ends');
            setTimeout(() => {
                if (listening && !aiSpeaking) {
                    console.log('🔊 Restarting VAD services after audio playback');

                    if (useWebkitVAD && vadService.current && vadInitialized) {
                        try {
                            // Ensure WebSocket is still connected for VAD service
                            if (ws.current?.readyState === WebSocket.OPEN) {
                                vadService.current.setWebSocket(ws.current);
                            }
                            vadService.current.start();
                            console.log('🔊 Webkit VAD restarted');
                        } catch (error) {
                            // Try to reinitialize if restart fails
                            console.log('Failed to restart VAD, reinitializing...');
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
                            console.log('🔊 Fallback VAD restarted');
                        } catch (error) {
                            // Try to reinitialize if restart fails
                            console.log('Failed to restart Fallback VAD, reinitializing...');
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
            }, 2000); // Increased delay to 2 seconds to ensure audio has completely stopped
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

    // Click outside handler for language and voice dropdowns
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (languageDropdownRef.current && !languageDropdownRef.current.contains(event.target as Node)) {
                setIsLanguageDropdownOpen(false);
            }
        };

        if (isLanguageDropdownOpen) {
            document.addEventListener('click', handleClickOutside);
        }

        return () => {
            document.removeEventListener('click', handleClickOutside);
        };
    }, [isLanguageDropdownOpen]);

    // Reset voice selection when language changes (only if current voice is not available)
    useEffect(() => {
        const availableVoices = voiceConfig[selectedLanguage];

        if (availableVoices && availableVoices.length > 0) {
            // Check if current voice is available in the new language
            const currentVoiceAvailable = availableVoices.some(voice => voice.id === selectedVoice);

            if (!currentVoiceAvailable) {
                const newVoice = availableVoices[0].id;
                setSelectedVoice(newVoice);
            } else {
            }
        } else {
        }
    }, [selectedLanguage]);

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
                loadOrganizationContext(parseInt(savedSelectedOrgId));
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
            const response = await fetch(`${API_BASE_URL}/api/organizations/by-id/${orgId}`);
            const data = await response.json();

            if (data.success && data.organization) {
                const org = data.organization;

                // Create RAG context for LLM
                const context = `You are representing ${org.name}. ${org.details ? `Organization details: ${org.details}` : 'No additional details provided.'} Always respond as if you are a staff member of ${org.name} and provide helpful, professional assistance.`;

                setOrganizationContext(context);
            } else {
                console.error('Failed to load organization:', data);
            }
        } catch (error) {
            console.error('Error loading organization context:', error);
        }
    };

    // Handle organization selection for customer
    const handleOrgSelection = async (org: { id: number, name: string }) => {
        setSelectedOrgForCustomer(org);
        localStorage.setItem('selectedOrgId', org.id.toString());
        localStorage.setItem('selectedOrgName', org.name);
        setShowOrgSelectionModal(false);

        // Load organization context for RAG
        await loadOrganizationContext(org.id);

        // Send updated preferences to backend immediately
        setTimeout(() => {
            sendPrefs();
        }, 100); // Small delay to ensure state is updated
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
        }
    }, [connected]); // Only depend on connected state

    // Auto-activate VAD when WebSocket is connected and VAD is ready (but don't start listening)
    useEffect(() => {
        if (connected && vadSupported && vadInitialized && !useWebkitVAD && vadService.current) {
            // Auto-activate VAD when everything is ready (but don't start listening)
            setUseWebkitVAD(true);
        }
    }, [connected, vadSupported, vadInitialized]); // Remove useWebkitVAD from dependencies to prevent infinite loop

    const handleLevelChange = (newLevel: "easy" | "medium" | "fast") => {
        setLevel(newLevel);
        setLevelChangeNotification(true);
        setTimeout(() => setLevelChangeNotification(false), 3000);

        // Send combined level and speech speed update to prevent conflicts
        if (ws.current?.readyState === WebSocket.OPEN) {
            const speedToLengthScale = {
                easy: 1.5,    // Slow audio (higher length_scale = slower)
                medium: 1.0,  // Normal audio (default)
                fast: 0.6     // Fast audio (lower length_scale = faster)
            };
            const lengthScale = speedToLengthScale[newLevel];

            // Send both level and speech speed in one message to prevent conflicts
            ws.current.send(JSON.stringify({
                type: "client_prefs",
                client_id: clientIdRef.current,
                level: newLevel,
                speech_speed: newLevel,
                length_scale: lengthScale,
                speed_level: newLevel,
                use_local_tts: useLocalTTS,
                language: selectedLanguage,
                voice: selectedVoice,
                role_play_enabled: rolePlayEnabled,
                role_play_template: rolePlayTemplate,
                organization_name: organizationName,
                organization_details: organizationDetails,
                role_title: roleTitle,
                rag_context: userType === 'customer' ? organizationContext : ""
            }));
        }
    };

    // keep prefs in sync (any of these change)
    useEffect(() => {
        if (connected) {
            sendPrefs();
        }
    }, [
        useLocalTTS,
        selectedLanguage,
        selectedVoice,
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


    // ---------- Helpers: Grammar Correction Parsing ----------
    const parseGrammarCorrection = (text: string) => {
        const startMarker = '🔴 GRAMMAR_CORRECTION_START 🔴';
        const endMarker = '🔴 GRAMMAR_CORRECTION_END 🔴';
        
        const startIndex = text.indexOf(startMarker);
        const endIndex = text.indexOf(endMarker);
        
        if (startIndex === -1 || endIndex === -1) {
            return { hasGrammarCorrection: false, grammarText: '', aiResponse: text };
        }
        
        const grammarText = text.substring(startIndex + startMarker.length, endIndex).trim();
        const aiResponse = text.substring(endIndex + endMarker.length).trim();
        
        // Parse incorrect and correct text
        let incorrectText = '';
        let correctText = '';
        
        const cleanGrammarText = grammarText.replace(/^\s*[-•]\s*/gm, '').trim();
        
        const patterns = [
            /INCORRECT:\s*([^\n]+)\s*\n\s*CORRECT:\s*([^\n]+)/i,
            /❌\s*([^✅]+?)\s*✅\s*(.+)/,
            /Wrong:\s*([^C]+?)\s*Correct:\s*(.+)/i,
            /Error:\s*([^F]+?)\s*Fixed:\s*(.+)/i
        ];
        
        for (const pattern of patterns) {
            const match = cleanGrammarText.match(pattern);
            if (match) {
                incorrectText = match[1].trim();
                correctText = match[2].trim();
                break;
            }
        }
        
        // If no pattern matched, try line-by-line parsing
        if (!incorrectText && !correctText) {
            const lines = cleanGrammarText.split('\n').map(line => line.trim()).filter(line => line);
            
            for (const line of lines) {
                if (line.match(/^(INCORRECT|❌|Wrong|Error):/i)) {
                    incorrectText = line.replace(/^(INCORRECT|❌|Wrong|Error):\s*/i, '').trim();
                } else if (line.match(/^(CORRECT|✅|Correct|Fixed):/i)) {
                    correctText = line.replace(/^(CORRECT|✅|Correct|Fixed):\s*/i, '').trim();
                }
            }
        }
        
        return {
            hasGrammarCorrection: !!(incorrectText && correctText),
            incorrectText,
            correctText,
            grammarText,
            aiResponse
        };
    };

    // ---------- Helpers: Structured Speech with Grammar Correction ----------
    const speakWithGrammarCorrection = (text: string) => {
        const { hasGrammarCorrection, incorrectText, correctText, aiResponse } = parseGrammarCorrection(text);
        
        if (!hasGrammarCorrection) {
            // No grammar correction, just speak the AI response
            speakTextLocal(aiResponse);
            return;
        }
        
        // Create structured speech text
        const speechText = `Grammar correction. You said: ${incorrectText}. The correct way is: ${correctText}. ${aiResponse}`;
        speakTextLocal(speechText);
    };

    // ---------- Helpers: Local TTS ----------
    const speakTextLocal = (text: string) => {
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(text);
            utter.lang = selectedLanguage === "en" ? "en-US" : "it-IT";
            utter.rate = 1.0; // Fixed rate, no difficulty level effect on audio
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
        // Mobile-specific: prevent double audio playback
        if (isMobile && isProcessingAudio) {
            console.log('Mobile: Ignoring duplicate audio request');
            return;
        }
        
        // CRITICAL: Immediately pause VAD services to prevent audio loop
        console.log('🔇 Pausing VAD services before server MP3 playback to prevent loop');
        if (useWebkitVAD && vadService.current) {
            vadService.current.stop();
        }
        if (useFallbackVAD && fallbackVADService.current) {
            fallbackVADService.current.stop();
        }
        
        if (isMobile) {
            setIsProcessingAudio(true);
        }
        
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
            // Audio playback rate removed - now controlled by backend noise_scale
            src.connect(audioCtx.current.destination);
            src.onended = () => {
                setAiSpeaking(false);
                setFinalTranscript(""); // Clear transcript to prevent waiting state
                setIsWaitingForResponse(false); // Clear waiting state when audio ends
                
                // Mobile-specific: reset processing flag
                if (isMobile) {
                    setIsProcessingAudio(false);
                }
            };

            currentSourceRef.current = src;
            setAiSpeaking(true);
            setIsWaitingForResponse(false); // Clear waiting state when audio starts
            src.start(0);
        } catch {
            const el = new Audio(`data:audio/mp3;base64,${base64}`);
            // Fallback audio playback rate removed - now controlled by backend noise_scale
            if (currentAudioRef.current) {
                currentAudioRef.current.pause();
                currentAudioRef.current.src = "";
            }
            currentAudioRef.current = el;
            el.onended = () => {
                setAiSpeaking(false);
                setFinalTranscript(""); // Clear transcript to prevent waiting state
                setIsWaitingForResponse(false); // Clear waiting state when audio ends
                
                // Mobile-specific: reset processing flag
                if (isMobile) {
                    setIsProcessingAudio(false);
                }
            };
            setAiSpeaking(true);
            setIsWaitingForResponse(false); // Clear waiting state when audio starts
            await el.play();
        }
    };

    // ---------- Helpers: Audio Management ----------
    const stopAllAudio = () => {
        console.log("🛑 Stopping all audio playback");
        
        // Stop all audio sources in queue
        audioQueueRef.current.forEach((src, index) => {
            try {
                src.stop();
                src.disconnect();
            } catch (error) {
                console.log(`Audio source ${index} already stopped`);
            }
        });
        
        // Clear queue and reset state
        audioQueueRef.current = [];
        currentAudioIndexRef.current = 0;
        isPlayingAudioRef.current = false;
        audioQueueLockRef.current = false;
        
        // Clear any pending timeouts
        if (audioPlaybackTimeoutRef.current) {
            clearTimeout(audioPlaybackTimeoutRef.current);
            audioPlaybackTimeoutRef.current = null;
        }
        
        // Reset audio state
        setAiSpeaking(false);
        setIsWaitingForResponse(false);
        setHighlightedText("");
        setCurrentSpeakingText("");
    };

    // ---------- Helpers: Real-time Audio Chunk Playback ----------
    const playAudioChunk = async (base64: string, text?: string) => {
        try {
            // CRITICAL: Immediately pause VAD services to prevent audio loop
            console.log('🔇 Pausing VAD services before audio playback to prevent loop');
            if (useWebkitVAD && vadService.current) {
                vadService.current.stop();
            }
            if (useFallbackVAD && fallbackVADService.current) {
                fallbackVADService.current.stop();
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
            src.connect(audioCtx.current.destination);
            
            // Store text for highlighting
            if (text) {
                (src as any).text = text;
            }
            
            // Add to queue instead of playing immediately
            audioQueueRef.current.push(src);
            console.log(`🎵 Audio chunk added to queue (${audioQueueRef.current.length} in queue)`);
            
            // Set speaking state
            setAiSpeaking(true);
            setIsWaitingForResponse(false);
            
            // Play next audio if not already playing
            if (!isPlayingAudioRef.current) {
                playNextAudioInQueue();
            }
            
        } catch (error) {
            console.error("Error playing audio chunk:", error);
        }
    };

    const playNextAudioInQueue = () => {
        if (audioQueueRef.current.length === 0) {
            console.log("🎵 No more audio in queue");
            isPlayingAudioRef.current = false;
            setAiSpeaking(false);
            setIsWaitingForResponse(false);
            setHighlightedText("");
            setCurrentSpeakingText("");
            return;
        }

        if (isPlayingAudioRef.current) {
            console.log("🎵 Already playing audio, waiting...");
            return;
        }

        const src = audioQueueRef.current.shift(); // Remove first item from queue
        if (!src) return;

        console.log(`🎵 Playing audio chunk (${audioQueueRef.current.length} remaining in queue)`);
        isPlayingAudioRef.current = true;

        // Highlight the text being spoken
        if ((src as any).text) {
            setCurrentSpeakingText((src as any).text);
            setHighlightedText((src as any).text);
            speakingTextRef.current = (src as any).text;
        }

        src.onended = () => {
            console.log("🎵 Audio chunk finished");
            isPlayingAudioRef.current = false;
            
            // Clear highlighting for this chunk
            setHighlightedText("");
            
            // Play next audio in queue after a short delay
            setTimeout(() => {
                playNextAudioInQueue();
            }, 50); // Small delay to prevent overlap
        };

        src.start(0);
    };


    // ---------- Cleanup Effect ----------
    useEffect(() => {
        return () => {
            // Cleanup audio on component unmount
            stopAllAudio();
        };
    }, []);

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

                    // initial prefs (NOW including level + stable client_id + speech speed)
                    try {
                        const speedToLengthScale = {
                            easy: 2.5,    // Slow audio 
                            medium: 1.0,  // Normal audio (default)
                            fast: 0.30     // Fast audio 
                        };
                        const lengthScale = speedToLengthScale[level];

                        ws.current?.send(JSON.stringify({
                            type: "client_prefs",
                            client_id: clientIdRef.current,
                            level,
                            use_local_tts: useLocalTTS,
                            language: selectedLanguage,
                            speech_speed: level,
                            length_scale: lengthScale
                        }));

                        // Also send initial speech speed setting
                        ws.current?.send(JSON.stringify({
                            type: "set_speech_speed",
                            length_scale: lengthScale,
                            speed_level: level
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
                        switch (data.type) {
                            case "ai_text_chunk":
                                console.log("🤖 AI Text chunk received:", data.text);
                                // Clear previous text and start fresh for new response
                                if (data.is_first_chunk) {
                                    setAiText(data.text || "");
                                } else {
                                    // Append text chunk for real-time display
                                    setAiText(prev => prev + (data.text || ""));
                                }
                                break;

                            case "ai_text":
                                console.log("🤖 AI Response received:", data.text);
                                setAiText(data.text || "");
                                setIsProcessing(false);
                                // Don't clear waiting state here - keep "AI Thinking" until audio starts
                                if (useLocalTTS && data.text) speakWithGrammarCorrection(data.text);
                                break;

                            case "ai_audio_start":
                                console.log("🔊 AI Audio streaming started - clearing previous audio");
                                // Stop all current audio and clear state
                                stopAllAudio();
                                break;

                            case "ai_audio_chunk":
                                console.log("🔊 AI Audio chunk received:", data.audio_base64 ? "Yes" : "No");
                                setIsProcessing(false);
                                // Play audio chunk immediately for real-time experience
                                if (!useLocalTTS && data.audio_base64) {
                                    await playAudioChunk(data.audio_base64, data.text);
                                }
                                break;

                            case "ai_audio":
                                console.log("🔊 AI Audio received:", data.audio_base64 ? "Yes" : "No");
                                setIsProcessing(false);
                                // Don't clear waiting state here - let playServerMp3 handle it when audio actually starts
                                if (!useLocalTTS && data.audio_base64) {
                                    // Mobile-specific: prevent duplicate audio processing
                                    if (isMobile && isProcessingAudio) {
                                        console.log('Mobile: Ignoring duplicate ai_audio request');
                                        break;
                                    }
                                    await playServerMp3(data.audio_base64);
                                }
                                break;

                            case "ai_audio_complete":
                                console.log("🔊 AI Audio streaming completed");
                                // Reset speaking state when all audio is complete
                                setAiSpeaking(false);
                                setIsWaitingForResponse(false);
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
                                // Update level from backend confirmation
                                setLevel(data.level as "easy" | "medium" | "fast");
                                break;
                            case "role_play_updated":
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
            if (useLocalTTS) speakWithGrammarCorrection(msg);
        }, 700);
    };

    const siriMode = aiSpeaking;

    // ---------------- UI ----------------
    return (
        <>
            <div className="min-h-screen text-zinc-100 bg-black">
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
                                                className={`w-full px-4 py-3 rounded-lg bg-white/[0.05] border text-white placeholder-zinc-500 focus:outline-none focus:bg-white/[0.08] transition-all duration-300 ${orgNameError
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
                                                        onClick={() => handleOrgSelection({ id: org.id, name: org.name })}
                                                        className={`w-full group relative p-4 rounded-xl transition-all duration-300 text-left ${isSelected
                                                            ? "bg-emerald-500/20 border border-emerald-400/50 shadow-lg"
                                                            : "bg-white/[0.05] border border-white/10 hover:border-emerald-400/50 hover:bg-emerald-500/10"
                                                            }`}
                                                    >
                                                        <div className="flex items-center gap-4">
                                                            <div className={`p-2 rounded-lg border transition-colors duration-300 ${isSelected
                                                                ? "bg-emerald-500/30 border-emerald-400/50"
                                                                : "bg-emerald-500/20 border-emerald-500/30 group-hover:bg-emerald-500/30"
                                                                }`}>
                                                                <FaBuilding className="h-5 w-5 text-emerald-400" />
                                                            </div>
                                                            <div className="flex-1">
                                                                <h3 className={`text-lg font-semibold ${isSelected ? "text-emerald-300" : "text-white"
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

                </div>

                {/* Mobile-Optimized Layout Container */}
                <div className="flex items-center justify-center p-2 sm:p-4 md:p-6 lg:p-8">
                    <div className="w-full max-w-7xl rounded-2xl sm:rounded-3xl shadow-2xl">
                        <div className="max-w-6xl mx-auto px-2 sm:px-4 md:px-6 py-3 sm:py-6 md:py-8 relative">
                            {/* Enhanced Professional Header */}
                            <div className="bg-gradient-to-r from-white/[0.08] to-white/[0.02] backdrop-blur-xl rounded-xl border border-white/10 p-5 sm:p-6 mb-4 sm:mb-6 relative overflow-visible shadow-lg">
                                {/* Main Header Row */}
                                <div className="flex items-center justify-between relative overflow-visible gap-6 mb-4">
                                    {/* Enhanced Logo & Title */}
                                    <div className="flex items-center gap-5">
                                        <div className="relative">
                                            <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg border border-white/20">
                                                <Bot className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
                                            </div>
                                            {/* Beta Badge */}
                                            <div className="absolute -top-2 -right-2 bg-gradient-to-r from-orange-400 to-red-500 text-white text-xs font-bold px-2 py-1 rounded-full border border-white/20 shadow-md">
                                                BETA
                                            </div>
                                            {connected && (
                                                <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full border-2 border-white shadow-md animate-pulse" />
                                            )}
                                        </div>
                                        <div className="flex flex-col">
                                            <h1 className="text-lg sm:text-xl font-bold text-white bg-gradient-to-r from-white to-zinc-300 bg-clip-text text-transparent">
                                                SHCI
                                            </h1>
                                            <p className="text-xs text-zinc-400 font-medium">
                                                Voice Agent
                                            </p>
                                        </div>
                                    </div>

                                    {/* Enhanced Language Dropdown */}
                                    <div className="relative" ref={languageDropdownRef}>
                                        <button
                                            onClick={() => setIsLanguageDropdownOpen(!isLanguageDropdownOpen)}
                                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.08] border border-white/20 hover:bg-white/[0.12] transition-all duration-300 shadow-md hover:shadow-lg"
                                        >
                                            <div className="text-lg">
                                                {selectedLanguage === "en" ? languages.en.flag : languages.it.flag}
                                            </div>
                                            <span className="text-sm font-semibold text-white">
                                                {selectedLanguage === "en" ? languages.en.name : languages.it.name}
                                            </span>
                                            <FaChevronDown className={`h-3 w-3 text-zinc-300 transition-transform duration-300 ${isLanguageDropdownOpen ? 'rotate-180' : ''
                                                }`} />
                                        </button>

                                        {/* Enhanced Dropdown Menu */}
                                        {isLanguageDropdownOpen && (
                                            <div className="absolute top-full right-0 mt-2 w-52 bg-gradient-to-br from-white/[0.12] to-white/[0.06] backdrop-blur-xl rounded-xl border border-white/30 shadow-2xl z-50 overflow-hidden">
                                                <div className="py-2">
                                                    {/* English Option */}
                                                    <button
                                                        onClick={() => {
                                                            setSelectedLanguage("en");
                                                            setIsLanguageDropdownOpen(false);
                                                        }}
                                                        className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-all duration-300 rounded-lg mx-2 ${selectedLanguage === "en"
                                                            ? "bg-gradient-to-r from-indigo-500/30 to-purple-500/20 text-indigo-200 border border-indigo-400/30"
                                                            : "text-zinc-300 hover:bg-white/[0.08] hover:text-white hover:border-white/20"
                                                            }`}
                                                    >
                                                        <div className="text-xl">
                                                            {languages.en.flag}
                                                        </div>
                                                        <div className="flex flex-col">
                                                            <span className="text-sm font-bold">
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
                                                        className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-all duration-300 rounded-lg mx-2 ${selectedLanguage === "it"
                                                            ? "bg-gradient-to-r from-indigo-500/30 to-purple-500/20 text-indigo-200 border border-indigo-400/30"
                                                            : "text-zinc-300 hover:bg-white/[0.08] hover:text-white hover:border-white/20"
                                                            }`}
                                                    >
                                                        <div className="text-xl">
                                                            {languages.it.flag}
                                                        </div>
                                                        <div className="flex flex-col">
                                                            <span className="text-sm font-bold">
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

                                {/* Minimal Controls Section */}
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 sm:gap-3">

                                    {/* Speech Speed Control */}
                                    <div className="bg-white/[0.02] backdrop-blur-sm rounded-lg border border-white/8 p-4">
                                        <div className="flex items-center gap-3 mb-3">
                                            <div className="p-2 rounded-lg bg-indigo-500/10">
                                                <svg className="h-4 w-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                </svg>
                                            </div>
                                            <div>
                                                <h3 className="text-sm font-semibold text-white">
                                                    Speech Speed
                                                </h3>
                                                <p className="text-xs text-zinc-400">
                                                    Adjust AI response playback speed
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex gap-2">
                                            {(["easy", "medium", "fast"] as const).map((lvl, index) => {
                                                const icons = [FaClock, FaPlay, FaTachometerAlt];
                                                const IconComponent = icons[index];
                                                const speeds = ["Slow", "Normal", "Fast"];
                                                const labels = ["Easy", "Medium", "Fast"];

                                                return (
                                                    <button
                                                        key={lvl}
                                                        onClick={() => handleLevelChange(lvl)}
                                                        className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200 flex-1 ${level === lvl
                                                                ? "bg-emerald-500 text-white shadow-md"
                                                                : "bg-white/[0.05] text-zinc-400 hover:text-zinc-300 hover:bg-white/[0.08]"
                                                            }`}
                                                    >
                                                        <IconComponent className="h-3 w-3" />
                                                        <div className="flex flex-col items-start">
                                                            <span className="text-xs font-medium">
                                                                {labels[index]}
                                                            </span>
                                                            <span className="text-xs opacity-75">
                                                                {speeds[index]}
                                                            </span>
                                                        </div>
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* Minimal Role Play Section */}
                                    <div className="bg-white/[0.02] backdrop-blur-sm rounded-lg border border-white/8 p-4">
                                        <div className="flex items-center gap-3 mb-3">
                                            <div className="p-2 rounded-lg bg-emerald-500/10">
                                                <FaUserTie className="h-4 w-4 text-emerald-400" />
                                            </div>
                                            <div>
                                                <h3 className="text-sm font-semibold text-white">
                                                    Role Play Mode
                                                </h3>
                                                <p className="text-xs text-zinc-400">
                                                    AI acts as staff from your selected organization
                                                </p>
                                            </div>
                                        </div>

                                        {/* Show selected organization if available */}
                                        {(rolePlayEnabled && organizationName) || (userType === 'customer' && selectedOrgForCustomer) || (userType === 'org_owner' && orgName) ? (
                                            <div className="px-3 py-2 rounded-lg bg-emerald-500/10 border border-emerald-400/20 mb-3">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2">
                                                        <FaBuilding className="h-3 w-3 text-emerald-400" />
                                                        <span className="text-xs font-medium text-emerald-300">
                                                            {rolePlayEnabled && organizationName
                                                                ? organizationName
                                                                : userType === 'customer' && selectedOrgForCustomer
                                                                    ? selectedOrgForCustomer.name
                                                                    : userType === 'org_owner' && orgName
                                                                        ? orgName
                                                                        : "Organization Selected"
                                                            }
                                                        </span>
                                                    </div>
                                                    <button
                                                        onClick={() => {
                                                            // Clear role play and organization data
                                                            setRolePlayEnabled(false);
                                                            setOrganizationName("");
                                                            setOrganizationDetails("");
                                                            setRoleTitle("");
                                                            setSelectedOrgForCustomer(null);

                                                            // Send WebSocket message to clear role play
                                                            if (ws.current?.readyState === WebSocket.OPEN) {
                                                                ws.current.send(JSON.stringify({
                                                                    type: "clear_roleplay"
                                                                }));
                                                            }
                                                        }}
                                                        className="p-1 rounded-full hover:bg-red-500/20 transition-colors duration-200 group"
                                                        title="Remove Organization"
                                                    >
                                                        <svg className="h-3 w-3 text-red-400 group-hover:text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                        </svg>
                                                    </button>
                                                </div>
                                            </div>
                                        ) : null}

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
                                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.05] text-zinc-400 hover:text-zinc-300 hover:bg-white/[0.08] transition-all duration-200 w-full"
                                        >
                                            <FaCog className="h-3 w-3" />
                                            <span className="text-xs font-medium">
                                                {rolePlayEnabled
                                                    ? "Configure Role Play"
                                                    : userType === 'customer'
                                                        ? "Select Organization"
                                                        : userType === 'org_owner'
                                                            ? "Configure Organization"
                                                            : "Configure Role Play"
                                                }
                                            </span>
                                        </button>
                                    </div>
                                </div>
                            </div>



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
                                                        className={`p-4 rounded-xl border transition-all duration-300 text-center ${rolePlayTemplate === key
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

                            {/* Minimal Voice Control Center */}
                            <div className="bg-gradient-to-br from-white/[0.02] to-white/[0.01] backdrop-blur-xl rounded-xl border border-white/10 p-3 sm:p-4 md:p-6 mb-4 sm:mb-6 overflow-hidden">
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

                                <div className="relative flex flex-col items-center">
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
                                    <div className="flex justify-center">
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
                                            className={` px-4 py-2 rounded-full font-medium text-xs transition-colors flex items-center justify-center gap-1 cursor-pointer ${listening
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

                                    {/* Voice Selection Dropdown - Moved below Start button */}
                                    <div className="flex justify-center mt-4">
                                        <div className="relative" ref={voiceDropdownRef}>
                                            <button
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    e.stopPropagation();
                                                    console.log('Voice modal clicked, opening modal');
                                                    setIsVoiceModalOpen(true);
                                                }}
                                                onMouseDown={(e) => e.stopPropagation()}
                                                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[0.03] border border-white/10 hover:bg-white/[0.05] transition-colors"
                                            >
                                                <FaMicrophone className="h-4 w-4 text-purple-400" />
                                                <span className="text-sm font-medium text-white">
                                                    {voiceConfig[selectedLanguage]?.find(v => v.id === selectedVoice)?.fullName || "Select Voice"}
                                                </span>
                                                <FaChevronDown className="h-3 w-3 text-zinc-400" />
                                            </button>

                                        </div>
                                    </div>

                                </div>
                            </div>


                            {/* Minimal Panels */}
                            <div className="grid lg:grid-cols-2 gap-3 sm:gap-4">
                                {/* Minimal Voice Panel */}
                                <div className="group relative rounded-lg border border-white/5 bg-white/[0.01] backdrop-blur-xl overflow-hidden transition-colors hover:border-white/10">
                                    <div className="relative px-3 py-3 border-b border-white/5">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                {/* Soft Icon */}
                                                <div className="relative">
                                                    <div className="h-6 w-6 rounded-md bg-white/[0.03] flex items-center justify-center border border-white/5 transition-colors">
                                                        <User className="h-3 w-3 text-zinc-400" />
                                                    </div>
                                                </div>

                                                <div>
                                                    <h3 className="text-sm font-medium text-zinc-200">
                                                        {currentLang.labels.yourVoice}
                                                    </h3>
                                                    <p className="text-xs text-zinc-500">
                                                        {currentLang.labels.yourVoiceDesc}
                                                    </p>
                                                </div>
                                            </div>

                                            {/* Minimal Status Indicators */}
                                            <div className="flex items-center gap-1">
                                                {(useWebkitVAD || useFallbackVAD) && (
                                                    <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-white/[0.02] border border-white/5">
                                                        <div className="w-1 h-1 bg-emerald-400 rounded-full" />
                                                        <span className="text-xs text-emerald-300">STT</span>
                                                    </div>
                                                )}
                                                {listening && (
                                                    <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-white/[0.02] border border-white/5">
                                                        <div className="w-1 h-1 bg-blue-400 rounded-full" />
                                                        <span className="text-xs text-blue-300">Live</span>
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
                                             <div className="space-y-4">
                                                 {/* Grammar Correction Block - Minimal design */}
                                                 {aiText.includes('GRAMMAR_CORRECTION_START') && (
                                                     <div className="bg-gray-800/50 border border-gray-600/30 rounded-lg p-3 mb-3">
                                                         <div className="flex items-center gap-2 mb-3">
                                                             <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                                                             <h4 className="text-xs font-medium text-gray-300">Grammar Check</h4>
                                                         </div>

                                                         {(() => {
                                                             const startMarker = 'GRAMMAR_CORRECTION_START';
                                                             const endMarker = 'GRAMMAR_CORRECTION_END';
                                                             const startIndex = aiText.indexOf(startMarker);
                                                             const endIndex = aiText.indexOf(endMarker);

                                                             if (startIndex !== -1 && endIndex !== -1) {
                                                                 const grammarText = aiText.substring(startIndex + startMarker.length, endIndex).trim();

                                                                 // More robust parsing - handle different formats
                                                                 let incorrectText = '';
                                                                 let correctText = '';

                                                                 // Clean the grammar text first
                                                                 const cleanGrammarText = grammarText.replace(/^\s*[-•]\s*/gm, '').trim();

                                                                 // Try multiple parsing patterns
                                                                 const patterns = [
                                                                     // Pattern 1: "INCORRECT: text CORRECT: text"
                                                                     /INCORRECT:\s*([^C]+?)\s*CORRECT:\s*(.+)/i,
                                                                     // Pattern 2: "INCORRECT: text\nCORRECT: text"
                                                                     /INCORRECT:\s*([^\n]+)\s*\n\s*CORRECT:\s*([^\n]+)/i,
                                                                     // Pattern 3: "❌ text ✅ text"
                                                                     /❌\s*([^✅]+?)\s*✅\s*(.+)/,
                                                                     // Pattern 4: "Wrong: text Correct: text"
                                                                     /Wrong:\s*([^C]+?)\s*Correct:\s*(.+)/i,
                                                                     // Pattern 5: "Error: text Fixed: text"
                                                                     /Error:\s*([^F]+?)\s*Fixed:\s*(.+)/i
                                                                 ];

                                                                 for (const pattern of patterns) {
                                                                     const match = cleanGrammarText.match(pattern);
                                                                     if (match) {
                                                                         incorrectText = match[1].trim();
                                                                         correctText = match[2].trim();
                                                                         break;
                                                                     }
                                                                 }

                                                                 // If no pattern matched, try line-by-line parsing
                                                                 if (!incorrectText && !correctText) {
                                                                     const lines = cleanGrammarText.split('\n').map(line => line.trim()).filter(line => line);

                                                                     for (const line of lines) {
                                                                         if (line.match(/^(INCORRECT|❌|Wrong|Error):/i)) {
                                                                             incorrectText = line.replace(/^(INCORRECT|❌|Wrong|Error):\s*/i, '').trim();
                                                                         } else if (line.match(/^(CORRECT|✅|Correct|Fixed):/i)) {
                                                                             correctText = line.replace(/^(CORRECT|✅|Correct|Fixed):\s*/i, '').trim();
                                                                         }
                                                                     }
                                                                 }

                                                                 // Final fallback - if we have text but no clear structure
                                                                 if (!incorrectText && !correctText && cleanGrammarText.length > 0) {
                                                                     // Try to split by common separators
                                                                     const separators = ['→', '->', '→', '→', '→'];
                                                                     for (const sep of separators) {
                                                                         if (cleanGrammarText.includes(sep)) {
                                                                             const parts = cleanGrammarText.split(sep);
                                                                             if (parts.length === 2) {
                                                                                 incorrectText = parts[0].trim();
                                                                                 correctText = parts[1].trim();
                                                                                 break;
                                                                             }
                                                                         }
                                                                     }
                                                                 }

                                                                 return (
                                                                     <div className="space-y-2">
                                                                         {incorrectText && correctText && (
                                                                             <div className="space-y-2">
                                                                                 {/* Incorrect Text Block - Minimal */}
                                                                                 <div className="bg-red-500/10 border-l-2 border-red-400 rounded p-2">
                                                                                     <div className="flex items-center gap-2 mb-1">
                                                                                         <div className="w-1.5 h-1.5 bg-red-400 rounded-full"></div>
                                                                                         <span className="text-xs text-red-300">Incorrect:</span>
                                                                                     </div>
                                                                                     <p className="text-sm text-red-200 ml-3">
                                                                                         "{incorrectText}"
                                                                                     </p>
                                                                                 </div>

                                                                                 {/* Correct Text Block - Minimal */}
                                                                                 <div className="bg-green-500/10 border-l-2 border-green-400 rounded p-2">
                                                                                     <div className="flex items-center gap-2 mb-1">
                                                                                         <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>
                                                                                         <span className="text-xs text-green-300">Correct:</span>
                                                                                     </div>
                                                                                     <p className="text-sm text-green-200 ml-3">
                                                                                         "{correctText}"
                                                                                     </p>
                                                                                 </div>
                                                                             </div>
                                                                         )}

                                                                         {correctText && !incorrectText && (
                                                                             <div className="bg-green-500/10 border-l-2 border-green-400 rounded p-2">
                                                                                 <div className="flex items-center gap-2 mb-1">
                                                                                     <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>
                                                                                     <span className="text-xs text-green-300">Grammar Check:</span>
                                                                                 </div>
                                                                                 <p className="text-sm text-green-200 ml-3">
                                                                                     "{correctText}"
                                                                                 </p>
                                                                             </div>
                                                                         )}
                                                                     </div>
                                                                 );
                                                             }
                                                             return null;
                                                         })()}
                                                     </div>
                                                 )}

                                                 {/* AI Response Block - Always show */}
                                                 <div className="bg-green-500/8 border border-green-400/20 rounded-lg p-3">
                                                     <div className="flex items-center gap-2 mb-2">
                                                         <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>
                                                         <h4 className="text-xs font-semibold text-green-300">AI Response</h4>
                                                         <div className="ml-auto text-xs text-green-400/70">AI</div>
                                                     </div>
                                                     <div className="bg-green-500/5 border-l-2 border-green-400 rounded-lg p-3">
                                                         <p className="text-sm leading-relaxed text-green-200 whitespace-pre-wrap">
                                                             {(() => {
                                                                 const displayText = aiText.includes('GRAMMAR_CORRECTION_START')
                                                                     ? aiText.split('GRAMMAR_CORRECTION_END')[1]?.trim() || aiText
                                                                     : aiText;
                                                                 
                                                                 // If there's highlighted text, show it with highlighting
                                                                 if (highlightedText && displayText.includes(highlightedText)) {
                                                                     const parts = displayText.split(highlightedText);
                                                                     return (
                                                                         <>
                                                                             {parts[0]}
                                                                             <span className="bg-yellow-400/30 text-yellow-100 px-1 rounded animate-pulse">
                                                                                 {highlightedText}
                                                                             </span>
                                                                             {parts[1]}
                                                                         </>
                                                                     );
                                                                 }
                                                                 
                                                                 return displayText;
                                                             })()}
                                                         </p>
                                                     </div>
                                                 </div>
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

                            {/* Minimal Mobile-Optimized Footer */}
                            <div className="mt-6 sm:mt-8 text-center px-2 sm:px-4">
                                {/* Compact Status Grid */}
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 mb-3 max-w-4xl mx-auto">
                                    {/* Headphones */}
                                    <div className="flex items-center justify-center gap-1 sm:gap-2 bg-white/[0.02] px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg border border-white/8">
                                        <Headphones className="h-3 w-3 sm:h-4 sm:w-4 text-emerald-400 shrink-0" />
                                        <span className="text-xs font-medium text-zinc-300 truncate">
                                            Optimal
                                        </span>
                                    </div>

                                    {/* Microphone */}
                                    <div className="flex items-center justify-center gap-1 sm:gap-2 bg-white/[0.02] px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg border border-white/8">
                                        <Mic className="h-3 w-3 sm:h-4 sm:w-4 text-blue-400 shrink-0" />
                                        <span className="text-xs font-medium text-zinc-300 truncate">
                                            Natural
                                        </span>
                                    </div>

                                    {/* Real-time */}
                                    <div className="flex items-center justify-center gap-1 sm:gap-2 bg-white/[0.02] px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg border border-white/8">
                                        <Activity className="h-3 w-3 sm:h-4 sm:w-4 text-purple-400 shrink-0" />
                                        <span className="text-xs font-medium text-zinc-300 truncate">
                                            Real-time
                                        </span>
                                    </div>

                                    {/* Difficulty Level */}
                                    <div className="flex items-center justify-center gap-1 sm:gap-2 bg-white/[0.02] px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg border border-white/8">
                                        <Brain className="h-3 w-3 sm:h-4 sm:w-4 text-indigo-400 shrink-0" />
                                        <span className="text-xs font-medium text-zinc-300 truncate">
                                            {currentLang.levels[level]}
                                        </span>
                                    </div>
                                </div>

                                {/* Minimal Brand Text */}
                                <p className="text-xs text-zinc-500 bg-white/3 px-3 py-1.5 rounded-lg border border-white/5 inline-block">
                                    SHCI Voice Assistant
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Professional Voice Selection Modal */}
            {isVoiceModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="bg-gradient-to-br from-white/[0.08] to-white/[0.02] backdrop-blur-xl rounded-2xl border border-white/20 shadow-xl p-5 max-w-md w-full mx-4">
                        {/* Modal Header */}
                        <div className="flex items-center justify-center mb-4">
                            <div className="p-3 rounded-xl bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border border-emerald-500/30">
                                <FaMicrophone className="h-6 w-6 text-emerald-400" />
                            </div>
                        </div>

                        <div className="text-center mb-5">
                            <h2 className="text-xl font-bold text-white mb-2">
                                Select Voice
                            </h2>
                            <p className="text-zinc-400 text-xs">
                                Choose your preferred AI voice
                            </p>
                        </div>

                        {/* Voice Options */}
                        <div className="space-y-3 mb-5">
                            {voiceConfig[selectedLanguage]?.map((voice) => (
                                <button
                                    key={voice.id}
                                    onClick={() => handleVoiceSelection(voice)}
                                    className={`w-full group relative p-3 rounded-xl transition-all duration-300 text-left border-2 ${selectedVoice === voice.id
                                            ? "bg-emerald-500/15 border-emerald-400/50 shadow-md shadow-emerald-500/10"
                                            : "bg-white/[0.05] border-white/10 hover:border-emerald-400/50 hover:bg-emerald-500/10 hover:shadow-md hover:shadow-emerald-500/5"
                                        }`}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`p-2 rounded-lg border transition-all duration-300 ${selectedVoice === voice.id
                                                ? "bg-emerald-500/30 border-emerald-400/50"
                                                : "bg-emerald-500/20 border-emerald-500/30 group-hover:bg-emerald-500/30 group-hover:border-emerald-400/50"
                                            }`}>
                                            <div className="text-lg">
                                                {voice.gender === "female" ? "👩" : "👨"}
                                            </div>
                                        </div>
                                        <div className="flex flex-col flex-1 min-w-0">
                                            <span className="text-sm font-semibold text-white">
                                                {voice.fullName}
                                            </span>
                                            <span className="text-xs text-zinc-400">
                                                {voice.gender} • {voice.quality}
                                            </span>
                                        </div>
                                        {selectedVoice === voice.id && (
                                            <div className="p-1.5 rounded-full bg-emerald-500/20 border border-emerald-400/30">
                                                <svg className="h-4 w-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                </svg>
                                            </div>
                                        )}
                                    </div>
                                </button>
                            )) || (
                                    <div className="text-center py-8">
                                        <div className="p-4 rounded-full bg-zinc-800/50 mx-auto w-fit mb-4">
                                            <FaMicrophone className="h-8 w-8 text-zinc-500" />
                                        </div>
                                        <p className="text-zinc-400">No voices available for {selectedLanguage}</p>
                                    </div>
                                )}
                        </div>

                        {/* Modal Footer */}
                        <div className="pt-4 border-t border-white/10">
                            <button
                                onClick={() => setIsVoiceModalOpen(false)}
                                className="w-full px-5 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl font-semibold transition-all duration-300 shadow-md hover:shadow-lg hover:shadow-emerald-500/20 text-sm"
                            >
                                Done
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  Chip,
  IconButton,
  Stack,
  CircularProgress,
  Tooltip,
  Alert,
  LinearProgress,
} from '@mui/material';
import {
  FlashOn as FlashIcon,
  Close as CloseIcon,
  Search as SearchIcon,
  Shield as ShieldIcon,
  Mic as MicIcon,
  GraphicEq as WaveIcon,
  VolumeUp as VolumeIcon,
  ScreenShare as TabAudioIcon,
  Hearing as HearingIcon,
  RestartAlt as ReconnectIcon,
} from '@mui/icons-material';

import { sidekickApi, type SidekickQueryResponse } from '../../api/endpoints/sidekick';

const QUICK_PRESETS = [
  'Distributed Rate Limiter',
  'LRU Cache',
  'Consistent Hashing',
  'Deadlock Prevention',
  'CAP Theorem',
  'Kafka Event Streaming',
  'Database Sharding',
  'Cache Stampede & Invalidation',
  'TCP vs UDP Handshake',
  'SQL vs NoSQL',
  'Two-Phase Commit vs Saga',
  'Major Production Outage (STAR)',
];

// Conversational filler phrases to strip for ultra-fast Trie/RAG matching
const CONVERSATIONAL_PREFIXES = [
  /^(can you|could you|would you|please)?\s*(walk me through|tell me about|explain|describe|what is|how does|how do you|how would you)\s+/i,
  /^(so|well|okay|now|next|also|tell me|give me|can you share)\s+/i,
  /^(what are the trade-offs of|what is the difference between|compare)\s+/i,
];

function cleanQuestionIntent(raw: string): string {
  let cleaned = raw.trim();
  for (const regex of CONVERSATIONAL_PREFIXES) {
    cleaned = cleaned.replace(regex, '');
  }
  return cleaned.trim() || raw.trim();
}

export const InterviewSidekickHUD: React.FC = () => {
  const [queryInput, setQueryInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [panicHidden, setPanicHidden] = useState(false);
  const [invisibleActive, setInvisibleActive] = useState(true);

  // Audio / Speech State
  const [isListening, setIsListening] = useState(false);
  const [audioSource, setAudioSource] = useState<'mic' | 'tab'>('mic');
  const [heardSpeech, setHeardSpeech] = useState('');
  const [liveTranscriptLog, setLiveTranscriptLog] = useState<string[]>([]);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const [activeResponse, setActiveResponse] = useState<SidekickQueryResponse>({
    source: 'trie_exact_match',
    tier: 1,
    title: 'Distributed Rate Limiter',
    category: 'High-Throughput Infra',
    bullets: [
      'Architecture: API Gateway -> Redis Cluster with Lua scripts running Token Bucket or Sliding Window Log for atomic checks.',
      'Trade-offs: Token Bucket allows bursts with low memory; Sliding Window Counter gives smooth rate at cost of slight approximation.',
      'Scale & Failure: Local in-memory fallback cache if Redis cluster degrades | Return HTTP 429 with Retry-After header.',
    ],
    latency_microseconds: 1.45,
    latency_display: '1.45 µs (In-Memory Trie)',
  });

  const querySeqRef = useRef(0);
  const recognitionRef = useRef<any>(null);
  const isListeningRef = useRef(false);
  const debounceTimerRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const restartTimeoutRef = useRef<any>(null);

  // Global Panic Switch Hotkey: Cmd+Shift+X or Ctrl+Shift+X
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'X' || e.key === 'x')) {
        setPanicHidden((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleExecuteQuery = useCallback(async (q: string) => {
    if (!q || !q.trim() || q.trim().length < 2) return;
    const cleaned = cleanQuestionIntent(q);
    const targetQuery = cleaned.length >= 2 ? cleaned : q.trim();

    const currentSeq = ++querySeqRef.current;
    setLoading(true);
    try {
      const res = await sidekickApi.query(targetQuery);
      if (currentSeq === querySeqRef.current) {
        setActiveResponse(res);
      }
    } catch (err) {
      console.error('Query failed:', err);
    } finally {
      if (currentSeq === querySeqRef.current) {
        setLoading(false);
      }
    }
  }, []);

  // Real-Time Live Typing Debounce (200ms)
  const handleInputChange = (val: string) => {
    setQueryInput(val);
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    if (val.trim().length >= 3) {
      debounceTimerRef.current = setTimeout(() => {
        handleExecuteQuery(val);
      }, 200);
    }
  };

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  // Start Real-Time Audio Level VU Meter & Continuous Backend Chunk Transcriber
  const startAudioMeter = async (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        const audioCtx = new AudioCtx();
        audioContextRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        source.connect(analyser);

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const updateMeter = () => {
          if (!isListeningRef.current) {
            setAudioLevel(0);
            return;
          }
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
          }
          const avg = sum / bufferLength;
          const normalized = Math.min(100, Math.round((avg / 128) * 100));
          setAudioLevel(normalized);
          animationFrameRef.current = requestAnimationFrame(updateMeter);
        };

        updateMeter();
      }

      // Continuous MediaRecorder Streamer (Backend AI Transcriber Backup)
      if (typeof MediaRecorder !== 'undefined') {
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : MediaRecorder.isTypeSupported('audio/mp4')
          ? 'audio/mp4'
          : '';

        if (mimeType) {
          const recorder = new MediaRecorder(stream, { mimeType });
          mediaRecorderRef.current = recorder;
          recorder.ondataavailable = async (e) => {
            if (e.data && e.data.size > 2000 && isListeningRef.current) {
              try {
                const res = await sidekickApi.transcribeAudio(e.data);
                if (res.transcript && res.transcript.trim()) {
                  const text = res.transcript.trim();
                  setHeardSpeech(text);
                  setQueryInput(text);
                  setLiveTranscriptLog((prev) => [text, ...prev.slice(0, 4)]);
                  if (res.query_response) {
                    setActiveResponse(res.query_response);
                  }
                }
              } catch (_) {}
            }
          };
          recorder.start(2500); // 2.5s slices
        }
      }
    } catch (err) {
      console.warn('Audio meter / streaming setup warning:', err);
    }
  };

  // Stop Audio Meter & Audio Streams
  const stopAudioMeter = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (_) {}
      mediaRecorderRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    setAudioLevel(0);
  };

  // Initialize Speech Recognition once
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      setSpeechError('Live voice recognition is not supported in this browser. Please use Chrome, Brave, or Edge.');
      return;
    }

    const rec = new SpeechRec();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'en-US';
    rec.maxAlternatives = 1;

    let silenceTimer: any = null;

    rec.onresult = (event: any) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      const spokenChunk = (finalTranscript || interimTranscript).trim();
      if (spokenChunk && spokenChunk.length >= 2) {
        setHeardSpeech(spokenChunk);
        setQueryInput(spokenChunk);

        if (finalTranscript.trim()) {
          setLiveTranscriptLog((prev) => [finalTranscript.trim(), ...prev.slice(0, 4)]);
        }

        // Fast proactive query trigger (250ms debounce)
        if (silenceTimer) clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => {
          handleExecuteQuery(spokenChunk);
        }, 250);
      }
    };

    rec.onerror = (e: any) => {
      if (e.error === 'no-speech') {
        // Normal silence — do nothing, keep listening
        return;
      }
      console.warn('Speech recognition event:', e.error);
      if (e.error === 'not-allowed') {
        setSpeechError('Microphone permission blocked. Please click the lock/tune icon in the browser address bar and allow microphone.');
        setIsListening(false);
        isListeningRef.current = false;
        stopAudioMeter();
      } else if (e.error === 'network' || e.error === 'aborted') {
        // Auto-reconnect on network hiccup if user wanted continuous listening
        if (isListeningRef.current) {
          if (restartTimeoutRef.current) clearTimeout(restartTimeoutRef.current);
          restartTimeoutRef.current = setTimeout(() => {
            try {
              rec.start();
            } catch (_) {}
          }, 300);
        }
      }
    };

    rec.onend = () => {
      // Auto-restart loop to keep listening continuously during entire interview
      if (isListeningRef.current) {
        if (restartTimeoutRef.current) clearTimeout(restartTimeoutRef.current);
        restartTimeoutRef.current = setTimeout(() => {
          if (isListeningRef.current) {
            try {
              rec.start();
            } catch (_) {}
          }
        }, 200);
      }
    };

    recognitionRef.current = rec;

    return () => {
      if (restartTimeoutRef.current) clearTimeout(restartTimeoutRef.current);
      if (silenceTimer) clearTimeout(silenceTimer);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
      stopAudioMeter();
    };
  }, [handleExecuteQuery]);

  // Toggle Microphone Ear
  const toggleListening = async () => {
    if (!recognitionRef.current) {
      alert('Live speech recognition is not supported in this browser. Please use Chrome, Edge, or Brave.');
      return;
    }

    if (isListening) {
      isListeningRef.current = false;
      setIsListening(false);
      try {
        recognitionRef.current.stop();
      } catch (_) {}
      stopAudioMeter();
      setSpeechError(null);
    } else {
      setSpeechError(null);
      isListeningRef.current = true;
      setIsListening(true);
      setAudioSource('mic');

      try {
        // Request mic stream for live VU level meter
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
        startAudioMeter(stream);
      } catch (err: any) {
        console.warn('Could not acquire mic stream for VU meter:', err);
      }

      try {
        recognitionRef.current.start();
      } catch (err) {
        console.warn('Mic start error (already active or retry):', err);
      }
    }
  };

  // Toggle Meeting Tab / System Audio Ear (Google Meet / Zoom / Teams Tab)
  const toggleMeetingTabAudio = async () => {
    if (!recognitionRef.current) return;

    if (isListening && audioSource === 'tab') {
      isListeningRef.current = false;
      setIsListening(false);
      try {
        recognitionRef.current.stop();
      } catch (_) {}
      stopAudioMeter();
      return;
    }

    try {
      setSpeechError(null);
      // Ask user to select the Meeting Tab (Google Meet / Zoom / Teams) with audio sharing enabled
      const displayStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        } as any,
      });

      const audioTrack = displayStream.getAudioTracks()[0];
      if (!audioTrack) {
        setSpeechError('⚠️ No tab audio was shared! Make sure to check "Share tab audio" when selecting the meeting tab.');
        displayStream.getTracks().forEach((t) => t.stop());
        return;
      }

      mediaStreamRef.current = displayStream;
      isListeningRef.current = true;
      setIsListening(true);
      setAudioSource('tab');
      startAudioMeter(displayStream);

      try {
        recognitionRef.current.start();
      } catch (_) {}

      // Handle user stopping screen share from browser banner
      audioTrack.onended = () => {
        isListeningRef.current = false;
        setIsListening(false);
        stopAudioMeter();
      };
    } catch (err: any) {
      if (err.name !== 'NotAllowedError') {
        console.error('Meeting tab audio capture error:', err);
        setSpeechError(`Tab audio capture error: ${err.message || err}`);
      }
    }
  };

  const handleToggleInvisibility = async () => {
    try {
      const res = await sidekickApi.setWindowInvisible('Job Finder');
      setInvisibleActive(res.is_invisible);
    } catch (err) {
      console.error('Failed to toggle invisibility:', err);
    }
  };

  if (panicHidden) {
    return (
      <Box
        onClick={() => setPanicHidden(false)}
        sx={{
          position: 'fixed',
          top: 10,
          right: 10,
          width: 14,
          height: 14,
          borderRadius: '50%',
          bgcolor: 'rgba(0, 255, 163, 0.3)',
          cursor: 'pointer',
          zIndex: 99999,
          '&:hover': { bgcolor: '#00FFA3' },
        }}
      />
    );
  }

  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: '720px',
        mx: 'auto',
        fontFamily: 'monospace',
        userSelect: 'none',
      }}
    >
      <Box
        sx={{
          bgcolor: 'rgba(6, 9, 14, 0.96)',
          backdropFilter: 'blur(20px)',
          border: '1.5px solid rgba(0, 255, 163, 0.45)',
          borderRadius: '20px',
          p: 2.5,
          boxShadow: '0 0 50px rgba(0, 255, 163, 0.18)',
          color: '#F8FAFC',
        }}
      >
        {/* Header Bar */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ pb: 1.5, mb: 2, borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                bgcolor: isListening ? '#00FFA3' : '#64748B',
                boxShadow: isListening ? '0 0 10px #00FFA3' : 'none',
                transition: 'all 0.3s ease',
              }}
            />
            <Typography variant="subtitle2" sx={{ fontWeight: 900, letterSpacing: '0.05em', color: '#00FFA3', textTransform: 'uppercase' }}>
              Ghost Interview Copilot
            </Typography>
            <Chip
              icon={<ShieldIcon sx={{ fontSize: '14px !important', color: '#00F0FF !important' }} />}
              label={invisibleActive ? 'NSWindowSharing: NONE' : 'Visible'}
              size="small"
              onClick={handleToggleInvisibility}
              sx={{
                bgcolor: 'rgba(0, 240, 255, 0.15)',
                color: '#00F0FF',
                fontWeight: 800,
                fontSize: '0.7rem',
                height: 22,
                cursor: 'pointer',
              }}
            />
          </Stack>

          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="caption" sx={{ color: '#64748B', fontSize: '0.7rem' }}>
              [Cmd+Shift+X] Panic Hide
            </Typography>
            <Tooltip title="Emergency Hide">
              <IconButton size="small" onClick={() => setPanicHidden(true)} sx={{ color: '#94A3B8', p: 0.5 }}>
                <CloseIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
          </Stack>
        </Stack>

        {/* Dual Live Audio Listening Modes: Mic vs Meeting Tab Audio */}
        <Box sx={{ mb: 2, p: 1.5, bgcolor: 'rgba(0, 0, 0, 0.5)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} spacing={1.5}>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
              {/* Mic Mode */}
              <Tooltip title="Listen via Microphone (Candidate + Room Audio)">
                <Chip
                  icon={isListening && audioSource === 'mic' ? <WaveIcon sx={{ color: '#00FFA3 !important', animation: 'pulse 1.5s infinite' }} /> : <MicIcon sx={{ color: '#94A3B8 !important' }} />}
                  label={isListening && audioSource === 'mic' ? '🟢 Mic Ear: ACTIVE' : '🎙️ Mic Ear'}
                  onClick={toggleListening}
                  size="small"
                  sx={{
                    bgcolor: isListening && audioSource === 'mic' ? 'rgba(0, 255, 163, 0.25)' : 'rgba(255, 255, 255, 0.06)',
                    color: isListening && audioSource === 'mic' ? '#00FFA3' : '#CBD5E1',
                    fontWeight: 800,
                    fontSize: '0.75rem',
                    height: 28,
                    cursor: 'pointer',
                    border: isListening && audioSource === 'mic' ? '1px solid #00FFA3' : '1px solid rgba(255, 255, 255, 0.12)',
                    '&:hover': { bgcolor: isListening && audioSource === 'mic' ? 'rgba(0, 255, 163, 0.35)' : 'rgba(255, 255, 255, 0.12)' },
                  }}
                />
              </Tooltip>

              {/* Meeting Tab Audio Mode (Zoom / Google Meet / Teams tab audio) */}
              <Tooltip title="Capture Interviewer Voice from Meeting Tab (Google Meet / Zoom / Teams) - Works even with headphones!">
                <Chip
                  icon={isListening && audioSource === 'tab' ? <HearingIcon sx={{ color: '#00F0FF !important', animation: 'pulse 1.5s infinite' }} /> : <TabAudioIcon sx={{ color: '#94A3B8 !important' }} />}
                  label={isListening && audioSource === 'tab' ? '🔵 Meeting Tab Ear: ACTIVE' : '🔊 Meeting Tab Ear'}
                  onClick={toggleMeetingTabAudio}
                  size="small"
                  sx={{
                    bgcolor: isListening && audioSource === 'tab' ? 'rgba(0, 240, 255, 0.25)' : 'rgba(255, 255, 255, 0.06)',
                    color: isListening && audioSource === 'tab' ? '#00F0FF' : '#CBD5E1',
                    fontWeight: 800,
                    fontSize: '0.75rem',
                    height: 28,
                    cursor: 'pointer',
                    border: isListening && audioSource === 'tab' ? '1px solid #00F0FF' : '1px solid rgba(255, 255, 255, 0.12)',
                    '&:hover': { bgcolor: isListening && audioSource === 'tab' ? 'rgba(0, 240, 255, 0.35)' : 'rgba(255, 255, 255, 0.12)' },
                  }}
                />
              </Tooltip>

              {isListening && (
                <IconButton
                  size="small"
                  onClick={() => {
                    if (recognitionRef.current) {
                      try {
                        recognitionRef.current.stop();
                        setTimeout(() => recognitionRef.current.start(), 100);
                      } catch (_) {}
                    }
                  }}
                  sx={{ color: '#94A3B8', p: 0.5 }}
                  title="Force Reconnect Voice Ear"
                >
                  <ReconnectIcon sx={{ fontSize: 16 }} />
                </IconButton>
              )}
            </Stack>

            {/* Real-time Audio Level VU Meter */}
            {isListening && (
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="caption" sx={{ color: audioLevel > 15 ? '#00FFA3' : '#64748B', fontSize: '0.68rem', fontWeight: 700 }}>
                  VU Signal:
                </Typography>
                <Box sx={{ width: 60 }}>
                  <LinearProgress
                    variant="determinate"
                    value={audioLevel}
                    sx={{
                      height: 6,
                      borderRadius: 3,
                      bgcolor: 'rgba(255, 255, 255, 0.1)',
                      '& .MuiLinearProgress-bar': {
                        bgcolor: audioLevel > 60 ? '#FF3366' : audioLevel > 20 ? '#00FFA3' : '#00F0FF',
                      },
                    }}
                  />
                </Box>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.68rem', minWidth: 26 }}>
                  {audioLevel}%
                </Typography>
              </Stack>
            )}
          </Stack>

          {/* Live Heard Transcript Banner */}
          {heardSpeech && isListening && (
            <Box sx={{ mt: 1.2, pt: 1, borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <Stack direction="row" spacing={1} alignItems="center">
                <VolumeIcon sx={{ fontSize: 14, color: '#FFE600' }} />
                <Typography variant="caption" sx={{ color: '#FFE600', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  Live Hearing: "{heardSpeech}"
                </Typography>
              </Stack>
            </Box>
          )}
        </Box>

        {speechError && (
          <Alert severity="warning" sx={{ mb: 1.5, py: 0.5, bgcolor: 'rgba(255, 179, 0, 0.15)', color: '#FFB300', fontSize: '0.75rem' }}>
            {speechError}
          </Alert>
        )}

        {/* Live Conversation Rolling History Log */}
        {liveTranscriptLog.length > 0 && (
          <Box sx={{ mb: 2, display: 'flex', gap: 0.8, overflowX: 'auto', pb: 0.5 }}>
            <Typography variant="caption" sx={{ color: '#64748B', alignSelf: 'center', fontSize: '0.68rem', fontWeight: 700, mr: 0.5 }}>
              Recent Heard:
            </Typography>
            {liveTranscriptLog.map((phrase, pIdx) => (
              <Chip
                key={pIdx}
                label={phrase.length > 35 ? `${phrase.slice(0, 35)}...` : phrase}
                size="small"
                clickable
                onClick={() => {
                  setQueryInput(phrase);
                  handleExecuteQuery(phrase);
                }}
                sx={{
                  bgcolor: 'rgba(0, 240, 255, 0.1)',
                  color: '#00F0FF',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  height: 22,
                  border: '1px solid rgba(0, 240, 255, 0.25)',
                  '&:hover': { bgcolor: 'rgba(0, 240, 255, 0.25)' },
                }}
              />
            ))}
          </Box>
        )}

        {/* Live Input Query Bar with Auto-Debounce */}
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Type question or keyword (e.g. 'LRU Cache', 'Consistent Hashing', 'Deadlock')..."
            value={queryInput}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleExecuteQuery(queryInput);
            }}
            sx={{
              bgcolor: 'rgba(0,0,0,0.6)',
              borderRadius: '10px',
              '& .MuiOutlinedInput-root': {
                color: '#F8FAFC',
                fontSize: '0.85rem',
                fontFamily: 'monospace',
                '& fieldset': { borderColor: 'rgba(0, 240, 255, 0.3)' },
                '&:hover fieldset': { borderColor: '#00FFA3' },
                '&.Mui-focused fieldset': { borderColor: '#00FFA3' },
              },
            }}
          />
          <IconButton
            onClick={() => handleExecuteQuery(queryInput)}
            disabled={loading}
            sx={{ bgcolor: 'rgba(0, 255, 163, 0.2)', color: '#00FFA3', borderRadius: '10px', p: 1 }}
          >
            {loading ? <CircularProgress size={18} color="inherit" /> : <SearchIcon />}
          </IconButton>
        </Stack>

        {/* Question Title & Latency Badge */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 900, color: '#00F0FF', letterSpacing: '0.02em' }}>
            🎯 {activeResponse.title}
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              label={activeResponse.category}
              size="small"
              sx={{ bgcolor: 'rgba(255, 255, 255, 0.08)', color: '#94A3B8', height: 20, fontSize: '0.65rem' }}
            />
            <Chip
              icon={<FlashIcon sx={{ fontSize: '13px !important', color: '#FFE600 !important' }} />}
              label={activeResponse.latency_display}
              size="small"
              sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 800, height: 20, fontSize: '0.65rem' }}
            />
          </Stack>
        </Stack>

        {/* 3-Bullet Teleprompter Display */}
        <Stack spacing={1.5} sx={{ mb: 2 }}>
          {activeResponse.bullets.map((bullet, idx) => (
            <Box
              key={idx}
              sx={{
                p: 1.8,
                bgcolor: '#0A0F1A',
                borderRadius: '12px',
                border: '1px solid rgba(0, 255, 163, 0.2)',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1.5,
                transition: 'all 0.2s ease',
                '&:hover': {
                  borderColor: 'rgba(0, 255, 163, 0.5)',
                  bgcolor: '#0D1424',
                },
              }}
            >
              <Typography sx={{ color: '#FFE600', fontWeight: 900, fontSize: '0.9rem', lineHeight: 1.2 }}>
                ▶
              </Typography>
              <Typography variant="body2" sx={{ color: '#F1F5F9', fontSize: '0.85rem', lineHeight: 1.6, fontWeight: 500 }}>
                {bullet}
              </Typography>
            </Box>
          ))}
        </Stack>

        {/* Quick Question Presets */}
        <Box sx={{ pt: 1, borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
          <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mb: 1, fontWeight: 700 }}>
            ⚡ 1-Click Instant Recall Battlecards:
          </Typography>
          <Stack direction="row" spacing={0.8} flexWrap="wrap" useFlexGap>
            {QUICK_PRESETS.map((preset) => (
              <Chip
                key={preset}
                label={preset}
                size="small"
                clickable
                onClick={() => {
                  setQueryInput(preset);
                  handleExecuteQuery(preset);
                }}
                sx={{
                  bgcolor: 'rgba(255, 255, 255, 0.05)',
                  color: '#94A3B8',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  '&:hover': { bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', borderColor: '#00FFA3' },
                }}
              />
            ))}
          </Stack>
        </Box>
      </Box>
    </Box>
  );
};

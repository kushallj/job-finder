import React, { useState, useEffect, useRef } from 'react';
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
} from '@mui/material';
import {
  FlashOn as FlashIcon,
  Close as CloseIcon,
  Search as SearchIcon,
  Shield as ShieldIcon,
  MicOff as MicOffIcon,
  GraphicEq as WaveIcon,
  VolumeUp as VolumeIcon,
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

export const InterviewSidekickHUD: React.FC = () => {
  const [queryInput, setQueryInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [panicHidden, setPanicHidden] = useState(false);
  const [invisibleActive, setInvisibleActive] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [heardSpeech, setHeardSpeech] = useState('');
  const [speechError, setSpeechError] = useState<string | null>(null);

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
  const debounceTimerRef = useRef<any>(null);

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

  const handleExecuteQuery = async (q: string) => {
    if (!q.trim()) return;
    const currentSeq = ++querySeqRef.current;
    setLoading(true);
    try {
      const res = await sidekickApi.query(q);
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
  };

  // Real-Time Live Typing Debounce (300ms)
  const handleInputChange = (val: string) => {
    setQueryInput(val);
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    if (val.trim().length >= 3) {
      debounceTimerRef.current = setTimeout(() => {
        handleExecuteQuery(val);
      }, 300);
    }
  };

  // Initialize Continuous Web Speech Recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRec) {
        setSpeechError('Microphone Speech-to-Text is not supported in this browser. Use Chrome, Edge, or Brave.');
        return;
      }

      const rec = new SpeechRec();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'en-US';

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

        const currentText = (finalTranscript || interimTranscript).trim();
        if (currentText) {
          setHeardSpeech(currentText);
          setQueryInput(currentText);

          // Clear previous silence timer
          if (silenceTimer) clearTimeout(silenceTimer);

          // Auto-trigger query 900ms after speaker pauses
          silenceTimer = setTimeout(() => {
            handleExecuteQuery(currentText);
          }, 900);
        }
      };

      rec.onerror = (e: any) => {
        if (e.error !== 'no-speech') {
          console.warn('Speech recognition warning:', e.error);
          setSpeechError(e.error === 'not-allowed' ? 'Microphone permission blocked. Click allow in browser address bar.' : e.error);
        }
      };

      rec.onend = () => {
        // Auto-restart if listening mode is still toggled ON
        if (recognitionRef.current && isListening) {
          try {
            rec.start();
          } catch (_) {}
        }
      };

      recognitionRef.current = rec;
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
    };
  }, [isListening]);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Live speech recognition is not supported in this browser. Please use Chrome, Edge, or Brave.');
      return;
    }

    if (isListening) {
      try {
        recognitionRef.current.stop();
      } catch (_) {}
      setIsListening(false);
      setSpeechError(null);
    } else {
      setSpeechError(null);
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.error('Mic start error:', err);
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
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#00FFA3', boxShadow: '0 0 10px #00FFA3' }} />
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

        {/* Live Audio Listening Bar & Toggle */}
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
          <Tooltip title={isListening ? 'Click to Mute Auto-Listening' : 'Click to Enable Continuous Voice Listening'}>
            <Chip
              icon={isListening ? <WaveIcon sx={{ color: '#00FFA3 !important', animation: 'pulse 1.5s infinite' }} /> : <MicOffIcon sx={{ color: '#94A3B8 !important' }} />}
              label={isListening ? '🟢 Live Ear ACTIVE: Auto-Transcribing...' : '🎙️ Start Auto-Listen to Interviewer'}
              onClick={toggleListening}
              size="small"
              sx={{
                bgcolor: isListening ? 'rgba(0, 255, 163, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                color: isListening ? '#00FFA3' : '#CBD5E1',
                fontWeight: 800,
                fontSize: '0.75rem',
                height: 28,
                cursor: 'pointer',
                border: isListening ? '1px solid #00FFA3' : '1px solid rgba(255, 255, 255, 0.15)',
                '&:hover': { bgcolor: isListening ? 'rgba(0, 255, 163, 0.3)' : 'rgba(255, 255, 255, 0.15)' },
              }}
            />
          </Tooltip>

          {heardSpeech && isListening && (
            <Chip
              icon={<VolumeIcon sx={{ fontSize: '13px !important', color: '#FFE600 !important' }} />}
              label={`Heard: "${heardSpeech.slice(-40)}"`}
              size="small"
              sx={{
                bgcolor: 'rgba(255, 230, 0, 0.12)',
                color: '#FFE600',
                fontSize: '0.7rem',
                fontWeight: 700,
                height: 24,
                maxWidth: '280px',
              }}
            />
          )}
        </Stack>

        {speechError && (
          <Alert severity="warning" sx={{ mb: 1.5, py: 0, bgcolor: 'rgba(255, 179, 0, 0.15)', color: '#FFB300', fontSize: '0.75rem' }}>
            {speechError}
          </Alert>
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

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Chip,
  IconButton,
  Stack,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  FlashOn as FlashIcon,
  Close as CloseIcon,
  Search as SearchIcon,
  Shield as ShieldIcon,
} from '@mui/icons-material';

import { sidekickApi, type SidekickQueryResponse } from '../../api/endpoints/sidekick';

export const InterviewSidekickHUD: React.FC = () => {
  const [queryInput, setQueryInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [panicHidden, setPanicHidden] = useState(false);
  const [invisibleActive, setInvisibleActive] = useState(true);
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
    setLoading(true);
    try {
      const res = await sidekickApi.query(q);
      setActiveResponse(res);
    } catch (err) {
      console.error('Query failed:', err);
    } finally {
      setLoading(false);
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
        maxWidth: '680px',
        mx: 'auto',
        fontFamily: 'monospace',
        userSelect: 'none',
      }}
    >
      <Box
        sx={{
          bgcolor: 'rgba(6, 9, 14, 0.94)',
          backdropFilter: 'blur(16px)',
          border: '1.5px solid rgba(0, 255, 163, 0.4)',
          borderRadius: '18px',
          p: 2.5,
          boxShadow: '0 0 40px rgba(0, 255, 163, 0.15)',
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

        {/* Live Audio / Input Query Bar */}
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Type or listen for question (e.g. 'LRU Cache', 'Consistent Hashing')..."
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleExecuteQuery(queryInput);
            }}
            sx={{
              bgcolor: 'rgba(0,0,0,0.5)',
              borderRadius: '10px',
              '& .MuiOutlinedInput-root': {
                color: '#F8FAFC',
                fontSize: '0.85rem',
                fontFamily: 'monospace',
                '& fieldset': { borderColor: 'rgba(0, 240, 255, 0.25)' },
                '&:hover fieldset': { borderColor: '#00FFA3' },
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
          <Typography variant="body2" sx={{ fontWeight: 800, color: '#00F0FF' }}>
            🎯 {activeResponse.title}
          </Typography>
          <Chip
            icon={<FlashIcon sx={{ fontSize: '13px !important', color: '#FFE600 !important' }} />}
            label={activeResponse.latency_display}
            size="small"
            sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 800, height: 20, fontSize: '0.65rem' }}
          />
        </Stack>

        {/* 3-Bullet Teleprompter Display */}
        <Stack spacing={1.5} sx={{ mb: 2 }}>
          {activeResponse.bullets.map((bullet, idx) => (
            <Box
              key={idx}
              sx={{
                p: 1.5,
                bgcolor: '#0D131F',
                borderRadius: '10px',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1.5,
              }}
            >
              <Typography sx={{ color: '#FFE600', fontWeight: 900, fontSize: '0.85rem', lineHeight: 1.2 }}>
                ▶
              </Typography>
              <Typography variant="body2" sx={{ color: '#E2E8F0', fontSize: '0.82rem', lineHeight: 1.5 }}>
                {bullet}
              </Typography>
            </Box>
          ))}
        </Stack>

        {/* Quick Question Presets */}
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {['LRU Cache', 'Distributed Rate Limiter', 'Top K Frequent', 'Consistent Hashing', 'Course Schedule'].map((preset) => (
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
                fontSize: '0.7rem',
                fontWeight: 700,
                border: '1px solid rgba(255, 255, 255, 0.1)',
                '&:hover': { bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', borderColor: '#00FFA3' },
              }}
            />
          ))}
        </Stack>
      </Box>
    </Box>
  );
};

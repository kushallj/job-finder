import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Stack,
  Chip,
  Button,
  TextField,
  Paper,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  Psychology as BrainIcon,
  CheckCircle as CheckIcon,
  ContentCopy as CopyIcon,
  PersonSearch as SearchIcon,
  ChatBubbleOutline as OpenerIcon,
} from '@mui/icons-material';

import { interviewerProfilerApi, type InterviewerDossier } from '../../api/endpoints/sprint1_api';

export const InterviewerProfilerCard: React.FC = () => {
  const [name, setName] = useState('Ankit Sharma');
  const [company, setCompany] = useState('CRED');
  const [role, setRole] = useState('Director of Engineering');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [dossier, setDossier] = useState<InterviewerDossier | null>({
    status: 'success',
    interviewer: {
      name: 'Ankit Sharma',
      company: 'CRED',
      role: 'Director of Engineering',
    },
    cognitive_archetype: 'Deep Technical Architect',
    architectural_biases: [
      'Favors strict data consistency (ACID, 2PC, Saga patterns) over eventual consistency where money is involved.',
      'Values raw query optimization, connection pooling, and idempotency keys on payment webhooks.',
      'Deep appreciation for fault tolerance: Circuit breakers, Redis distributed locking, dead-letter queues.',
    ],
    green_lights_to_highlight: [
      'Explicitly mention idempotency mechanisms and deduplication windows when designing APIs.',
      'Discuss database row-level locking vs optimistic concurrency control.',
      'Highlight past experience dealing with high-concurrency payment spikes or webhook retries.',
    ],
    red_lines_to_avoid: [
      'Do NOT suggest eventual consistency for balance deduction or ledger mutations.',
      'Do NOT overlook integer overflow in currency handling (always use integer cents/paise or Decimal).',
      'Avoid hand-waving cache invalidation—explain cache-aside with TTL and stampede protection.',
    ],
    personalized_conversation_opener:
      "Hi Ankit, I've been closely following CRED's engineering work around high-throughput transaction reliability. I recently benchmarked distributed idempotency patterns in FastAPI and would love to discuss how your team balances latency and strict ledger consistency.",
    recommended_questions_to_ask_them: [
      "What is the single biggest architectural bottleneck your team at CRED is tackling this quarter?",
      "How does your engineering team balance shipping velocity against technical debt refactoring?",
      "What distinguishes a good engineer from a truly exceptional engineer on your team?",
    ],
  });

  const handleProfile = async () => {
    if (!name.trim() || !company.trim()) return;
    setLoading(true);
    try {
      const res = await interviewerProfilerApi.profile({ name, company, role });
      setDossier(res);
    } catch (err) {
      console.error('Failed to profile interviewer:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyOpener = () => {
    if (!dossier) return;
    navigator.clipboard.writeText(dossier.personalized_conversation_opener);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <Card sx={{ bgcolor: '#0D131F', border: '1.5px solid rgba(0, 255, 163, 0.3)', borderRadius: '18px' }}>
      <CardContent sx={{ p: 3 }}>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2.5 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Box sx={{ width: 36, height: 36, borderRadius: '10px', bgcolor: 'rgba(0, 255, 163, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #00FFA3' }}>
              <BrainIcon sx={{ color: '#00FFA3', fontSize: 22 }} />
            </Box>
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                Interviewer Cognitive Profiler & Bias Radar
              </Typography>
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                Reverse-engineers architectural beliefs, green lights, red lines & bespoke openers
              </Typography>
            </Box>
          </Stack>
          <Chip label="OSINT Profiler Active" size="small" sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800 }} />
        </Stack>

        {/* Input Form */}
        <Grid container spacing={1.5} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              fullWidth
              size="small"
              label="Interviewer Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              sx={{ bgcolor: '#06090E' }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              fullWidth
              size="small"
              label="Target Company"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              sx={{ bgcolor: '#06090E' }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              fullWidth
              size="small"
              label="Role (e.g. VP / Staff Eng)"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              sx={{ bgcolor: '#06090E' }}
            />
          </Grid>
        </Grid>

        <Button
          fullWidth
          variant="contained"
          startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <SearchIcon />}
          onClick={handleProfile}
          disabled={loading}
          sx={{
            bgcolor: '#00FFA3',
            color: '#06090E',
            fontWeight: 900,
            textTransform: 'none',
            mb: 3,
            py: 1,
            '&:hover': { bgcolor: '#00F0FF' },
          }}
        >
          {loading ? 'Synthesizing Cognitive Dossier...' : 'Generate Interviewer Dossier'}
        </Button>

        {/* Dossier Output */}
        {dossier && (
          <Stack spacing={2.5}>
            {/* Conversation Opener Banner */}
            <Paper sx={{ p: 2.5, bgcolor: '#06090E', border: '1px solid rgba(0, 240, 255, 0.3)', borderRadius: '12px' }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <OpenerIcon sx={{ color: '#00F0FF', fontSize: 20 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#00F0FF' }}>
                    Personalized Conversation Hook
                  </Typography>
                </Stack>
                <Tooltip title="Copy Opener">
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={copied ? <CheckIcon /> : <CopyIcon />}
                    onClick={handleCopyOpener}
                    sx={{ color: '#00FFA3', borderColor: '#00FFA3', fontSize: '0.7rem', height: 24, textTransform: 'none', fontWeight: 800 }}
                  >
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                </Tooltip>
              </Stack>
              <Typography variant="body2" sx={{ color: '#E2E8F0', fontStyle: 'italic', lineHeight: 1.5 }}>
                "{dossier.personalized_conversation_opener}"
              </Typography>
            </Paper>

            {/* Architectural Biases */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#FFE600', mb: 1 }}>
                🧠 Core Architectural Biases & Mental Models
              </Typography>
              <Stack spacing={1}>
                {dossier.architectural_biases.map((b, i) => (
                  <Paper key={i} sx={{ p: 1.5, bgcolor: '#06090E', border: '1px solid rgba(255, 230, 0, 0.15)', borderRadius: '8px' }}>
                    <Typography variant="body2" sx={{ color: '#CBD5E1', fontSize: '0.82rem' }}>
                      • {b}
                    </Typography>
                  </Paper>
                ))}
              </Stack>
            </Box>

            {/* Green Lights vs Red Lines */}
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#00FFA3', mb: 1 }}>
                  🟢 Green Lights (Topics to Highlight)
                </Typography>
                <Stack spacing={1}>
                  {dossier.green_lights_to_highlight.map((g, i) => (
                    <Paper key={i} sx={{ p: 1.5, bgcolor: '#06090E', border: '1px solid rgba(0, 255, 163, 0.2)', borderRadius: '8px' }}>
                      <Typography variant="body2" sx={{ color: '#E2E8F0', fontSize: '0.82rem' }}>
                        ✓ {g}
                      </Typography>
                    </Paper>
                  ))}
                </Stack>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#FF0055', mb: 1 }}>
                  🔴 Red Lines (Pet Peeves to Avoid)
                </Typography>
                <Stack spacing={1}>
                  {dossier.red_lines_to_avoid.map((r, i) => (
                    <Paper key={i} sx={{ p: 1.5, bgcolor: '#06090E', border: '1px solid rgba(255, 0, 85, 0.2)', borderRadius: '8px' }}>
                      <Typography variant="body2" sx={{ color: '#E2E8F0', fontSize: '0.82rem' }}>
                        ✕ {r}
                      </Typography>
                    </Paper>
                  ))}
                </Stack>
              </Grid>
            </Grid>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
};

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  LinearProgress,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Slider,
  CircularProgress,
  Alert,
  Tooltip,
  IconButton,
  Divider,
} from '@mui/material';
import {
  RocketLaunch as RocketIcon,
  CheckCircle as CheckCircleIcon,
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon,
  Bolt as BoltIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
  CloudDone as CloudDoneIcon,
  Layers as LayersIcon,
} from '@mui/icons-material';

import {
  nextraiseApi,
  type NextRaiseStatusResponse,
  type NextRaiseBatchApplyResponse,
} from '../../api/endpoints/nextraise';

const ATS_PLATFORMS = [
  { name: 'Workday', code: 'workday', color: '#00F0FF' },
  { name: 'Greenhouse', code: 'greenhouse', color: '#00FFA3' },
  { name: 'Lever', code: 'lever', color: '#FFE600' },
  { name: 'Ashby', code: 'ashby', color: '#A855F7' },
  { name: 'BambooHR', code: 'bamboohr', color: '#38BDF8' },
  { name: 'SmartRecruiters', code: 'smartrecruiters', color: '#F43F5E' },
  { name: 'Taleo', code: 'taleo', color: '#FB923C' },
  { name: 'iCIMS', code: 'icims', color: '#4ADE80' },
  { name: 'SuccessFactors', code: 'successfactors', color: '#818CF8' },
  { name: 'Custom ATS Portals', code: 'custom_ats', color: '#E2E8F0' },
];

export const NextRaiseStudio: React.FC = () => {
  const [statusData, setStatusData] = useState<NextRaiseStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [batchLoading, setBatchLoading] = useState<boolean>(false);
  const [targetCount, setTargetCount] = useState<number>(250);
  const [minScore, setMinScore] = useState<number>(50);
  const [lastBatchResult, setLastBatchResult] = useState<NextRaiseBatchApplyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await nextraiseApi.getStatus();
      setStatusData(data);
    } catch (err: any) {
      console.error('Failed to load NextRaise telemetry:', err);
      setError(err?.response?.data?.detail || 'Failed to connect to NextRaise backend agent.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleLaunchBatch = async () => {
    try {
      setBatchLoading(true);
      setError(null);
      setLastBatchResult(null);
      const res = await nextraiseApi.batchApply(targetCount, minScore);
      setLastBatchResult(res);
      await fetchStatus();
    } catch (err: any) {
      console.error('Batch apply failed:', err);
      setError(err?.response?.data?.detail || 'Failed to execute NextRaise batch application dispatch.');
    } finally {
      setBatchLoading(false);
    }
  };

  const quota = statusData?.quota || {
    daily_used: 0,
    daily_limit: 300,
    daily_remaining: 300,
    daily_progress_percent: 0,
    total_submitted: 0,
    total_failed: 0,
    active_tier: 'nextraise_pro_unlimited',
    last_reset_date: 'Today',
  };

  const account = statusData?.account || {
    account_email: 'canaby007@gmail.com',
    oauth_connected: true,
    has_token: true,
    mode: 'instant_auto',
    daily_target: 300,
    min_fit_score: 60,
    auto_batch_enabled: true,
    batch_concurrency: 5,
    enabled_ats: ['workday', 'greenhouse', 'lever', 'ashby'],
    api_url: 'https://api.nextraise.com/v1',
    updated_at: null,
  };

  const submissions = statusData?.recent_submissions || [];

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto', p: { xs: 1.5, md: 3 } }}>
      {/* Header Banner */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: '14px',
              background: 'linear-gradient(135deg, #7C3AED 0%, #00F0FF 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 25px rgba(124, 58, 237, 0.45)',
            }}
          >
            <RocketIcon sx={{ fontSize: 28, color: '#FFFFFF' }} />
          </Box>
          <Box>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Typography variant="h5" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #A855F7 0%, #00F0FF 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.02em' }}>
                NextRaise Auto-Apply Command Center
              </Typography>
              <Chip
                label="200–300 Daily Suite"
                size="small"
                sx={{
                  bgcolor: 'rgba(168, 85, 247, 0.2)',
                  color: '#A855F7',
                  border: '1px solid #A855F7',
                  fontWeight: 900,
                  fontSize: '0.7rem',
                }}
              />
            </Stack>
            <Typography variant="body2" sx={{ color: '#94A3B8', mt: 0.25 }}>
              Autonomous high-throughput application dispatch wired to OAuth profile (<strong>{account.account_email}</strong>)
            </Typography>
          </Box>
        </Stack>

        <Stack direction="row" spacing={1.5}>
          <Button
            startIcon={<RefreshIcon />}
            variant="outlined"
            onClick={fetchStatus}
            disabled={loading || batchLoading}
            sx={{
              borderColor: 'rgba(0, 240, 255, 0.3)',
              color: '#00F0FF',
              fontWeight: 700,
              textTransform: 'none',
              borderRadius: '10px',
              '&:hover': { borderColor: '#00F0FF', bgcolor: 'rgba(0, 240, 255, 0.08)' },
            }}
          >
            Refresh Telemetry
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: '12px', bgcolor: 'rgba(239, 68, 68, 0.1)', color: '#F87171', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
          {error}
        </Alert>
      )}

      {lastBatchResult && (
        <Alert
          severity={lastBatchResult.status === 'completed' ? 'success' : 'info'}
          sx={{
            mb: 3,
            borderRadius: '12px',
            bgcolor: lastBatchResult.status === 'completed' ? 'rgba(0, 255, 163, 0.1)' : 'rgba(0, 240, 255, 0.1)',
            color: lastBatchResult.status === 'completed' ? '#00FFA3' : '#00F0FF',
            border: `1px solid ${lastBatchResult.status === 'completed' ? 'rgba(0, 255, 163, 0.3)' : 'rgba(0, 240, 255, 0.3)'}`,
          }}
        >
          {lastBatchResult.status === 'completed' ? (
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              🎉 Dispatched {lastBatchResult.successful_submissions} jobs via NextRaise ({lastBatchResult.daily_progress} daily quota completed)!
            </Typography>
          ) : (
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {lastBatchResult.message}
            </Typography>
          )}
        </Alert>
      )}

      {/* KPI & Quota Gauges */}
      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        {/* Daily Quota Card */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card
            sx={{
              height: '100%',
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(168, 85, 247, 0.3)',
              borderRadius: '18px',
              boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <Box sx={{ position: 'absolute', top: 0, right: 0, width: '100px', height: '100px', background: 'radial-gradient(circle, rgba(168,85,247,0.15) 0%, transparent 70%)' }} />
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <SpeedIcon sx={{ color: '#A855F7', fontSize: 20 }} />
                  <Typography variant="caption" sx={{ fontWeight: 900, color: '#A855F7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Daily Quota Target
                  </Typography>
                </Stack>
                <Chip
                  label="200–300/DAY"
                  size="small"
                  sx={{ height: 20, fontSize: '0.65rem', fontWeight: 900, bgcolor: 'rgba(168, 85, 247, 0.2)', color: '#C084FC' }}
                />
              </Stack>

              <Typography variant="h3" sx={{ fontWeight: 900, color: '#F8FAFC', mb: 0.5 }}>
                {quota.daily_used} <span style={{ fontSize: '1.2rem', color: '#94A3B8', fontWeight: 600 }}>/ {quota.daily_limit}</span>
              </Typography>

              <LinearProgress
                variant="determinate"
                value={Math.min(100, quota.daily_progress_percent)}
                sx={{
                  height: 10,
                  borderRadius: 5,
                  bgcolor: 'rgba(255, 255, 255, 0.08)',
                  mb: 1.5,
                  '& .MuiLinearProgress-bar': {
                    background: 'linear-gradient(90deg, #7C3AED 0%, #00F0FF 100%)',
                    borderRadius: 5,
                  },
                }}
              />

              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 600 }}>
                  Remaining Today: <strong style={{ color: '#00FFA3' }}>{quota.daily_remaining}</strong>
                </Typography>
                <Typography variant="caption" sx={{ color: '#A855F7', fontWeight: 800 }}>
                  {quota.daily_progress_percent}% Reached
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* OAuth Account Card */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card
            sx={{
              height: '100%',
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(0, 240, 255, 0.3)',
              borderRadius: '18px',
              boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5)',
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <CloudDoneIcon sx={{ color: '#00F0FF', fontSize: 20 }} />
                  <Typography variant="caption" sx={{ fontWeight: 900, color: '#00F0FF', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    OAuth Subscription Account
                  </Typography>
                </Stack>
                <Chip
                  label="PRO UNLIMITED"
                  size="small"
                  sx={{ height: 20, fontSize: '0.65rem', fontWeight: 900, bgcolor: 'rgba(0, 255, 163, 0.2)', color: '#00FFA3' }}
                />
              </Stack>

              <Typography variant="h6" sx={{ fontWeight: 800, color: '#F8FAFC', mb: 0.5 }}>
                {account.account_email}
              </Typography>

              <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 2 }}>
                OAuth Session: <strong style={{ color: '#00FFA3' }}>Active &amp; Authenticated</strong>
              </Typography>

              <Stack direction="row" spacing={1.5} alignItems="center">
                <Box sx={{ px: 1.5, py: 0.5, borderRadius: '8px', bgcolor: 'rgba(0, 240, 255, 0.1)', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
                  <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', fontSize: '0.65rem' }}>TOTAL SUBMITTED</Typography>
                  <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#00F0FF' }}>{quota.total_submitted}</Typography>
                </Box>
                <Box sx={{ px: 1.5, py: 0.5, borderRadius: '8px', bgcolor: 'rgba(0, 255, 163, 0.1)', border: '1px solid rgba(0, 255, 163, 0.2)' }}>
                  <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', fontSize: '0.65rem' }}>SUCCESS RATE</Typography>
                  <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                    {quota.total_submitted > 0 ? Math.round((quota.total_submitted / (quota.total_submitted + quota.total_failed)) * 100) : 100}%
                  </Typography>
                </Box>
                <Box sx={{ px: 1.5, py: 0.5, borderRadius: '8px', bgcolor: 'rgba(255, 230, 0, 0.1)', border: '1px solid rgba(255, 230, 0, 0.2)' }}>
                  <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', fontSize: '0.65rem' }}>MODE</Typography>
                  <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#FFE600' }}>Instant Auto</Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* ATS Security & Cryptographic Verifier */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card
            sx={{
              height: '100%',
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(0, 255, 163, 0.3)',
              borderRadius: '18px',
              boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5)',
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <SecurityIcon sx={{ color: '#00FFA3', fontSize: 20 }} />
                  <Typography variant="caption" sx={{ fontWeight: 900, color: '#00FFA3', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Cryptographic Receipts
                  </Typography>
                </Stack>
                <Chip
                  label="SHA-256 PROOF"
                  size="small"
                  sx={{ height: 20, fontSize: '0.65rem', fontWeight: 900, bgcolor: 'rgba(0, 255, 163, 0.2)', color: '#00FFA3' }}
                />
              </Stack>

              <Typography variant="body2" sx={{ color: '#CBD5E1', mb: 1.5, fontSize: '0.82rem', lineHeight: 1.4 }}>
                Every dispatched job produces a tamper-evident cryptographic receipt ID (<code>NR-ATS-HASH</code>) and verifiable proof payload.
              </Typography>

              <Box sx={{ p: 1.25, borderRadius: '10px', bgcolor: '#080C12', border: '1px dashed rgba(0, 255, 163, 0.4)' }}>
                <Typography variant="caption" sx={{ color: '#00FFA3', fontFamily: 'monospace', fontWeight: 700, display: 'block' }}>
                  https://app.nextraise.ai/proof/NR-WORKDAY-9A2F...
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* High-Volume Batch Dispatcher Console */}
      <Card
        sx={{
          mb: 3.5,
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(168, 85, 247, 0.4)',
          borderRadius: '20px',
          boxShadow: '0 10px 40px rgba(124, 58, 237, 0.25)',
          background: 'linear-gradient(180deg, rgba(13, 19, 31, 1) 0%, rgba(20, 15, 38, 0.95) 100%)',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
            <BoltIcon sx={{ color: '#FFE600', fontSize: 26 }} />
            <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
              High-Volume Batch Auto-Apply Dispatcher (200–300 Target)
            </Typography>
          </Stack>

          <Grid container spacing={3} alignItems="center">
            <Grid size={{ xs: 12, md: 4 }}>
              <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700, display: 'block', mb: 1 }}>
                TARGET APPLICATIONS COUNT: <strong style={{ color: '#00F0FF' }}>{targetCount} Jobs</strong>
              </Typography>
              <Slider
                value={targetCount}
                onChange={(_, v) => setTargetCount(v as number)}
                min={50}
                max={300}
                step={25}
                marks={[
                  { value: 50, label: '50' },
                  { value: 150, label: '150' },
                  { value: 200, label: '200' },
                  { value: 250, label: '250' },
                  { value: 300, label: '300' },
                ]}
                sx={{
                  color: '#A855F7',
                  '& .MuiSlider-markLabel': { color: '#64748B', fontSize: '0.75rem', fontWeight: 700 },
                }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 4 }}>
              <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700, display: 'block', mb: 1 }}>
                MIN FIT SCORE THRESHOLD: <strong style={{ color: '#00FFA3' }}>{minScore}%</strong>
              </Typography>
              <Slider
                value={minScore}
                onChange={(_, v) => setMinScore(v as number)}
                min={30}
                max={90}
                step={5}
                marks={[
                  { value: 30, label: '30%' },
                  { value: 50, label: '50%' },
                  { value: 70, label: '70%' },
                  { value: 90, label: '90%' },
                ]}
                sx={{
                  color: '#00FFA3',
                  '& .MuiSlider-markLabel': { color: '#64748B', fontSize: '0.75rem', fontWeight: 700 },
                }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 4 }}>
              <Button
                variant="contained"
                fullWidth
                size="large"
                disabled={batchLoading}
                onClick={handleLaunchBatch}
                startIcon={batchLoading ? <CircularProgress size={20} color="inherit" /> : <RocketIcon sx={{ fontSize: 24 }} />}
                sx={{
                  py: 1.8,
                  background: 'linear-gradient(135deg, #7C3AED 0%, #A855F7 50%, #00F0FF 100%)',
                  color: '#FFFFFF',
                  fontWeight: 900,
                  fontSize: '1rem',
                  textTransform: 'none',
                  borderRadius: '14px',
                  boxShadow: '0 0 25px rgba(168, 85, 247, 0.5)',
                  transition: 'all 0.25s ease',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #6D28D9 0%, #9333EA 50%, #00D8E6 100%)',
                    boxShadow: '0 0 35px rgba(0, 240, 255, 0.7)',
                    transform: 'translateY(-2px)',
                  },
                }}
              >
                {batchLoading ? 'Dispatching Batch Applications...' : `🚀 Apply to ${targetCount} Jobs Now`}
              </Button>
            </Grid>
          </Grid>

          {/* ATS Coverage Chips */}
          <Divider sx={{ my: 2.5, borderColor: 'rgba(255, 255, 255, 0.08)' }} />
          <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', mb: 1 }}>
            Supported Multi-ATS Portals &amp; Engines:
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {ATS_PLATFORMS.map((ats) => (
              <Chip
                key={ats.code}
                label={ats.name}
                size="small"
                sx={{
                  bgcolor: 'rgba(255, 255, 255, 0.05)',
                  color: ats.color,
                  border: `1px solid ${ats.color}40`,
                  fontWeight: 700,
                  fontSize: '0.72rem',
                }}
              />
            ))}
          </Stack>
        </CardContent>
      </Card>

      {/* Submissions & Proof Ledger */}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <LayersIcon sx={{ color: '#00F0FF', fontSize: 22 }} />
          <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
            NextRaise Verified Submissions &amp; Proof Receipts
          </Typography>
        </Stack>
        <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 600 }}>
          Showing latest {submissions.length} records
        </Typography>
      </Box>

      <TableContainer
        component={Paper}
        sx={{
          borderRadius: '18px',
          border: '1.5px solid rgba(0, 240, 255, 0.2)',
          bgcolor: '#0D131F',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)',
        }}
      >
        <Table size="small">
          <TableHead sx={{ bgcolor: '#080C12' }}>
            <TableRow>
              <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Role &amp; Company</TableCell>
              <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>ATS Portal</TableCell>
              <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Candidate Email</TableCell>
              <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Receipt ID</TableCell>
              <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Status</TableCell>
              <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Dispatched At</TableCell>
              <TableCell align="right" sx={{ fontWeight: 900, color: '#00F0FF' }}>Proof</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {submissions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} sx={{ textAlign: 'center', py: 4, color: '#64748B' }}>
                  No applications dispatched yet. Launch a batch or click 🚀 NextRaise on any job card.
                </TableCell>
              </TableRow>
            ) : (
              submissions.map((sub) => (
                <TableRow key={sub.id} hover sx={{ '&:hover': { bgcolor: 'rgba(0, 240, 255, 0.05)' } }}>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 800, color: '#F8FAFC' }}>
                      {sub.job_title || 'Software Engineer'}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#FFE600', fontWeight: 700 }}>
                      {sub.company_name || 'Target Company'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={sub.ats_type.toUpperCase()}
                      size="small"
                      sx={{
                        fontSize: '0.68rem',
                        fontWeight: 800,
                        bgcolor: 'rgba(168, 85, 247, 0.15)',
                        color: '#A855F7',
                        border: '1px solid rgba(168, 85, 247, 0.3)',
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontFamily: 'monospace' }}>
                      {sub.account_email}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ color: '#00FFA3', fontFamily: 'monospace', fontWeight: 700 }}>
                      {sub.receipt_id || 'NR-WORKDAY-PENDING'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={sub.status.toUpperCase()}
                      size="small"
                      icon={<CheckCircleIcon sx={{ fontSize: '14px !important', color: '#00FFA3 !important' }} />}
                      sx={{
                        fontSize: '0.68rem',
                        fontWeight: 900,
                        bgcolor: 'rgba(0, 255, 163, 0.15)',
                        color: '#00FFA3',
                        border: '1px solid rgba(0, 255, 163, 0.4)',
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                      {sub.submitted_at ? new Date(sub.submitted_at).toLocaleTimeString() : 'Just now'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    {sub.proof_url && (
                      <Tooltip title="View verifiable cryptographic proof payload">
                        <IconButton
                          size="small"
                          href={sub.proof_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          sx={{
                            color: '#00F0FF',
                            border: '1px solid rgba(0, 240, 255, 0.3)',
                            borderRadius: '8px',
                            '&:hover': { bgcolor: 'rgba(0, 240, 255, 0.1)' },
                          }}
                        >
                          <OpenInNewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default NextRaiseStudio;

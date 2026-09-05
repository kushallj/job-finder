import React, { useState, useEffect } from 'react';
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
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Architecture as WhiteboardIcon,
  ContentCopy as CopyIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  Memory as MemoryIcon,
  Shield as ShieldIcon,
  CheckCircle as CheckIcon,
  AutoAwesome as AutoIcon,
} from '@mui/icons-material';
import {
  sprint6Api,
  type SystemDesignArchetype,
  type WhiteboardResponse,
} from '../../api/endpoints/sprint6_api';

export const SystemDesignWhiteboardCard: React.FC = () => {
  const [archetypes, setArchetypes] = useState<SystemDesignArchetype[]>([]);
  const [selectedArchetypeId, setSelectedArchetypeId] = useState('realtime_trading_engine');
  const [dau, setDau] = useState<number>(10000000);
  const [actionsPerDay, setActionsPerDay] = useState<number>(20);
  const [payloadBytes, setPayloadBytes] = useState<number>(1024);

  const [loading, setLoading] = useState(false);
  const [whiteboardData, setWhiteboardData] = useState<WhiteboardResponse | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMsg, setSnackbarMsg] = useState('');

  useEffect(() => {
    sprint6Api.getSystemDesignArchetypes().then((res) => {
      if (res && res.archetypes) {
        setArchetypes(res.archetypes);
        if (res.archetypes.length > 0) {
          handleEstimateAndDiagram(res.archetypes[0].archetype_id, 10000000, 20, 1024);
        }
      }
    }).catch(console.error);
  }, []);

  const handleEstimateAndDiagram = async (
    archId = selectedArchetypeId,
    uDau = dau,
    uActions = actionsPerDay,
    uPayload = payloadBytes
  ) => {
    setLoading(true);
    try {
      const res = await sprint6Api.estimateAndDiagram({
        archetype_id: archId,
        daily_active_users: uDau,
        avg_actions_per_user_day: uActions,
        payload_size_bytes: uPayload,
      });
      setWhiteboardData(res);
    } catch (err) {
      console.error('Failed to generate system design whiteboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectArchetype = (a: SystemDesignArchetype) => {
    setSelectedArchetypeId(a.archetype_id);
    setDau(a.default_dau);
    setPayloadBytes(a.avg_payload_bytes);
    handleEstimateAndDiagram(a.archetype_id, a.default_dau, actionsPerDay, a.avg_payload_bytes);
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setSnackbarMsg(`Copied ${label} to clipboard!`);
    setSnackbarOpen(true);
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header Banner */}
      <Card
        sx={{
          mb: 3,
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 240, 255, 0.3)',
          borderRadius: '16px',
          boxShadow: '0 0 30px rgba(0, 240, 255, 0.12)',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            justifyContent="space-between"
            alignItems={{ xs: 'flex-start', md: 'center' }}
            spacing={2}
          >
            <Box>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Box
                  sx={{
                    width: 42,
                    height: 42,
                    borderRadius: '10px',
                    bgcolor: 'rgba(0, 240, 255, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #00F0FF',
                  }}
                >
                  <WhiteboardIcon sx={{ color: '#00F0FF', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    📐 AI System Design Whiteboard Co-Pilot (Agent 24)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Real-time Back-of-the-Envelope Capacity Estimator, Mermaid architecture synthesizer, and defensive failure-mode matrix.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip
                label="Instant Capacity Math"
                sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 900, fontSize: '0.78rem' }}
              />
              <Chip
                label="Mermaid + Failure Matrix"
                sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, fontSize: '0.75rem' }}
              />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* System Design Archetype Switcher */}
      <Stack direction="row" spacing={1} sx={{ mb: 3, overflowX: 'auto', pb: 0.5 }}>
        {archetypes.map((a) => (
          <Chip
            key={a.archetype_id}
            label={a.title}
            clickable
            onClick={() => handleSelectArchetype(a)}
            sx={{
              fontWeight: 800,
              fontSize: '0.78rem',
              py: 2.2,
              px: 1,
              bgcolor: selectedArchetypeId === a.archetype_id ? 'rgba(0, 240, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              color: selectedArchetypeId === a.archetype_id ? '#00F0FF' : '#94A3B8',
              border: `1.5px solid ${selectedArchetypeId === a.archetype_id ? '#00F0FF' : 'rgba(255, 255, 255, 0.1)'}`,
            }}
          />
        ))}
      </Stack>

      {/* Two Column Simulator */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Left: Input Parameters */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper
            sx={{
              p: 3,
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '16px',
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00F0FF', mb: 2 }}>
              ⚙️ System Scale Parameters
            </Typography>

            <Stack spacing={2}>
              <TextField
                size="small"
                type="number"
                label="Daily Active Users (DAU)"
                value={dau}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setDau(val);
                  handleEstimateAndDiagram(selectedArchetypeId, val, actionsPerDay, payloadBytes);
                }}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                type="number"
                label="Avg Requests / User / Day"
                value={actionsPerDay}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setActionsPerDay(val);
                  handleEstimateAndDiagram(selectedArchetypeId, dau, val, payloadBytes);
                }}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                type="number"
                label="Average Payload Size (Bytes)"
                value={payloadBytes}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setPayloadBytes(val);
                  handleEstimateAndDiagram(selectedArchetypeId, dau, actionsPerDay, val);
                }}
                sx={{ bgcolor: '#06090E' }}
              />

              <Button
                variant="contained"
                disabled={loading}
                onClick={() => handleEstimateAndDiagram(selectedArchetypeId, dau, actionsPerDay, payloadBytes)}
                startIcon={loading ? <CircularProgress size={18} sx={{ color: '#06090E' }} /> : <AutoIcon />}
                sx={{
                  bgcolor: '#00F0FF',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  py: 1.2,
                  '&:hover': { bgcolor: '#00C8D6' },
                }}
              >
                {loading ? 'Re-Estimating Capacity...' : 'Synthesize Architecture Blueprint'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* Right: Back-of-the-Envelope Capacity Cards */}
        <Grid size={{ xs: 12, md: 8 }}>
          {whiteboardData && (
            <Stack spacing={2.5}>
              <Grid container spacing={1.5}>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(0, 240, 255, 0.2)', textAlign: 'center' }}>
                    <Stack direction="row" justifyContent="center" alignItems="center" spacing={0.5} sx={{ mb: 0.5 }}>
                      <SpeedIcon sx={{ color: '#00F0FF', fontSize: 16 }} />
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>PEAK QPS</Typography>
                    </Stack>
                    <Typography variant="h6" sx={{ color: '#00F0FF', fontWeight: 900, fontFamily: 'monospace' }}>
                      {whiteboardData.capacity_estimates.peak_qps.toLocaleString()}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>req / sec</Typography>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(0, 255, 163, 0.2)', textAlign: 'center' }}>
                    <Stack direction="row" justifyContent="center" alignItems="center" spacing={0.5} sx={{ mb: 0.5 }}>
                      <StorageIcon sx={{ color: '#00FFA3', fontSize: 16 }} />
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>ANNUAL STORAGE</Typography>
                    </Stack>
                    <Typography variant="h6" sx={{ color: '#00FFA3', fontWeight: 900, fontFamily: 'monospace' }}>
                      {whiteboardData.capacity_estimates.annual_storage_tb} TB
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>~{whiteboardData.capacity_estimates.daily_storage_gb} GB/day</Typography>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255, 230, 0, 0.2)', textAlign: 'center' }}>
                    <Stack direction="row" justifyContent="center" alignItems="center" spacing={0.5} sx={{ mb: 0.5 }}>
                      <MemoryIcon sx={{ color: '#FFE600', fontSize: 16 }} />
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>RAM CACHE (80/20)</Typography>
                    </Stack>
                    <Typography variant="h6" sx={{ color: '#FFE600', fontWeight: 900, fontFamily: 'monospace' }}>
                      {whiteboardData.capacity_estimates.ram_cache_required_gb} GB
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>Redis Shards</Typography>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.1)', textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, display: 'block', mb: 0.5 }}>EGRESS BANDWIDTH</Typography>
                    <Typography variant="h6" sx={{ color: '#F8FAFC', fontWeight: 900, fontFamily: 'monospace' }}>
                      {whiteboardData.capacity_estimates.network_egress_mbps} Mbps
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>P99: {whiteboardData.p99_sla_target}</Typography>
                  </Paper>
                </Grid>
              </Grid>

              {/* Whiteboard Verbal Talking Points */}
              <Paper sx={{ p: 2, bgcolor: '#0D131F', borderRadius: '12px', border: '1px solid rgba(0, 255, 163, 0.2)' }}>
                <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 800, display: 'block', mb: 1 }}>
                  🎙️ SYSTEM DESIGN VERBAL DEFENSE TALKING POINTS:
                </Typography>
                <Stack spacing={0.5}>
                  {whiteboardData.whiteboard_talking_points.map((pt, i) => (
                    <Typography key={i} variant="caption" sx={{ color: '#CBD5E1', display: 'block' }}>
                      • {pt}
                    </Typography>
                  ))}
                </Stack>
              </Paper>
            </Stack>
          )}
        </Grid>
      </Grid>

      {/* Mermaid Architecture & Defensive Failure Mode Matrix */}
      {whiteboardData && (
        <Grid container spacing={3}>
          {/* Left: Mermaid Diagram */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', borderRadius: '16px', height: '100%' }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                  🏗️ Production Architecture Blueprint
                </Typography>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<CopyIcon />}
                  onClick={() => copyToClipboard(whiteboardData.mermaid_diagram, 'Mermaid Diagram')}
                  sx={{ color: '#00F0FF', borderColor: 'rgba(0, 240, 255, 0.4)', textTransform: 'none', fontWeight: 800 }}
                >
                  Copy Mermaid
                </Button>
              </Stack>

              <Paper
                sx={{
                  p: 2,
                  bgcolor: '#06090E',
                  borderRadius: '10px',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  maxHeight: '340px',
                  overflowY: 'auto',
                }}
              >
                <Typography component="pre" sx={{ color: '#FFE600', fontFamily: 'monospace', fontSize: '0.74rem', whiteSpace: 'pre-wrap', lineHeight: 1.4 }}>
                  {whiteboardData.mermaid_diagram}
                </Typography>
              </Paper>
            </Paper>
          </Grid>

          {/* Right: Defensive Failure Mode Matrix */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 255, 163, 0.25)', borderRadius: '16px', height: '100%' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00FFA3', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <ShieldIcon sx={{ color: '#00FFA3' }} /> Defensive Failure Modes & Edge-Case Matrix
              </Typography>

              <Stack spacing={1.5} sx={{ maxHeight: '340px', overflowY: 'auto' }}>
                {whiteboardData.failure_matrix.map((fm) => (
                  <Paper key={fm.failure_mode} sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <Typography variant="body2" sx={{ color: '#FFE600', fontWeight: 800, mb: 0.5 }}>
                      ⚠️ {fm.failure_mode}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 0.5 }}>
                      <strong>Risk:</strong> {fm.risk}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#00FFA3', display: 'block' }}>
                      <strong>Mitigation:</strong> {fm.defensive_mitigation}
                    </Typography>
                  </Paper>
                ))}
              </Stack>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Snackbar notification */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbarOpen(false)}
          severity="success"
          icon={<CheckIcon fontSize="inherit" />}
          sx={{ bgcolor: '#00FFA3', color: '#06090E', fontWeight: 800 }}
        >
          {snackbarMsg}
        </Alert>
      </Snackbar>
    </Box>
  );
};

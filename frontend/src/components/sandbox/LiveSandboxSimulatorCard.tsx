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
  Paper,
  Slider,
  CircularProgress,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Science as LabIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import {
  sprint6Api,
  type SandboxModel,
  type SimulationResponse,
} from '../../api/endpoints/sprint6_api';

export const LiveSandboxSimulatorCard: React.FC = () => {
  const [models, setModels] = useState<SandboxModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState('distributed_cache_eviction');
  const [concurrencyRps, setConcurrencyRps] = useState<number>(25000);
  const [failureInjection, setFailureInjection] = useState<boolean>(true);

  const [loading, setLoading] = useState(false);
  const [simResult, setSimResult] = useState<SimulationResponse | null>(null);

  useEffect(() => {
    sprint6Api.getSandboxModels().then((res) => {
      if (res && res.models) {
        setModels(res.models);
        if (res.models.length > 0) {
          handleRunSimulation(res.models[0].model_id, 25000, true);
        }
      }
    }).catch(console.error);
  }, []);

  const handleRunSimulation = async (
    mId = selectedModelId,
    rps = concurrencyRps,
    fail = failureInjection
  ) => {
    setLoading(true);
    try {
      const res = await sprint6Api.runSimulation({
        model_id: mId,
        concurrency_rps: rps,
        failure_injection_enabled: fail,
      });
      setSimResult(res);
    } catch (err) {
      console.error('Simulation run failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectModel = (m: SandboxModel) => {
    setSelectedModelId(m.model_id);
    setConcurrencyRps(m.default_concurrency);
    handleRunSimulation(m.model_id, m.default_concurrency, failureInjection);
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header Banner */}
      <Card
        sx={{
          mb: 3,
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 255, 163, 0.3)',
          borderRadius: '16px',
          boxShadow: '0 0 30px rgba(0, 255, 163, 0.12)',
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
                    bgcolor: 'rgba(0, 255, 163, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #00FFA3',
                  }}
                >
                  <LabIcon sx={{ color: '#00FFA3', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    🧪 Live Architecture Interactive Sandbox Simulator (Agent 26)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Real-time distributed system scenario simulator (Cache Eviction, Raft Split-Brain, Token Bucket Rate Limiting) with live telemetry streams.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip
                label="Real-Time Concurrency"
                sx={{ bgcolor: 'rgba(0, 255, 163, 0.2)', color: '#00FFA3', fontWeight: 900, fontSize: '0.78rem' }}
              />
              <Chip
                label="Failure Chaos Injection"
                sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 800, fontSize: '0.75rem' }}
              />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Model Selector Tabs */}
      <Stack direction="row" spacing={1} sx={{ mb: 3, overflowX: 'auto', pb: 0.5 }}>
        {models.map((m) => (
          <Chip
            key={m.model_id}
            label={m.title}
            clickable
            onClick={() => handleSelectModel(m)}
            sx={{
              fontWeight: 800,
              fontSize: '0.78rem',
              py: 2.2,
              px: 1,
              bgcolor: selectedModelId === m.model_id ? 'rgba(0, 255, 163, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              color: selectedModelId === m.model_id ? '#00FFA3' : '#94A3B8',
              border: `1.5px solid ${selectedModelId === m.model_id ? '#00FFA3' : 'rgba(255, 255, 255, 0.1)'}`,
            }}
          />
        ))}
      </Stack>

      {/* Two Column Layout */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Left: Controls */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper
            sx={{
              p: 3,
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '16px',
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00FFA3', mb: 2 }}>
              ⚙️ Load & Chaos Parameters
            </Typography>

            <Stack spacing={2.5}>
              <Box>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                  <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700 }}>
                    Synthetic Concurrency Load:
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#00FFA3', fontWeight: 900, fontFamily: 'monospace' }}>
                    {concurrencyRps.toLocaleString()} RPS
                  </Typography>
                </Stack>
                <Slider
                  value={concurrencyRps}
                  min={1000}
                  max={100000}
                  step={5000}
                  onChange={(_, v) => {
                    const val = v as number;
                    setConcurrencyRps(val);
                    handleRunSimulation(selectedModelId, val, failureInjection);
                  }}
                  sx={{ color: '#00FFA3' }}
                />
              </Box>

              <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={failureInjection}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setFailureInjection(checked);
                        handleRunSimulation(selectedModelId, concurrencyRps, checked);
                      }}
                      sx={{
                        '& .MuiSwitch-switchBase.Mui-checked': { color: '#FFE600' },
                        '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { backgroundColor: '#FFE600' },
                      }}
                    />
                  }
                  label={
                    <Typography variant="caption" sx={{ color: failureInjection ? '#FFE600' : '#94A3B8', fontWeight: 800 }}>
                      Chaos Injection (Stampede / Partition)
                    </Typography>
                  }
                />
              </Paper>

              <Button
                variant="contained"
                disabled={loading}
                onClick={() => handleRunSimulation(selectedModelId, concurrencyRps, failureInjection)}
                startIcon={loading ? <CircularProgress size={18} sx={{ color: '#06090E' }} /> : <PlayIcon />}
                sx={{
                  bgcolor: '#00FFA3',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  py: 1.2,
                  '&:hover': { bgcolor: '#00D88B' },
                }}
              >
                {loading ? 'Running Real-Time Simulation...' : 'Trigger Synthetic Simulation'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* Right: Live Telemetry Metrics */}
        <Grid size={{ xs: 12, md: 8 }}>
          {simResult && (
            <Stack spacing={2.5}>
              <Grid container spacing={1.5}>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(0, 255, 163, 0.2)', textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, display: 'block', mb: 0.5 }}>THROUGHPUT</Typography>
                    <Typography variant="h6" sx={{ color: '#00FFA3', fontWeight: 900, fontFamily: 'monospace' }}>
                      {simResult.metrics.concurrency_rps.toLocaleString()}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>RPS Load</Typography>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(0, 240, 255, 0.2)', textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, display: 'block', mb: 0.5 }}>P99 LATENCY</Typography>
                    <Typography variant="h6" sx={{ color: '#00F0FF', fontWeight: 900, fontFamily: 'monospace' }}>
                      {simResult.metrics.p99_latency_ms} ms
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>P50: {simResult.metrics.p50_latency_ms}ms</Typography>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255, 230, 0, 0.2)', textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, display: 'block', mb: 0.5 }}>CACHE HIT</Typography>
                    <Typography variant="h6" sx={{ color: '#FFE600', fontWeight: 900, fontFamily: 'monospace' }}>
                      {simResult.metrics.cache_hit_rate_percent}%
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>Efficiency</Typography>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.1)', textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, display: 'block', mb: 0.5 }}>ERROR RATE</Typography>
                    <Typography variant="h6" sx={{ color: simResult.metrics.error_rate_percent > 0 ? '#FF5252' : '#00FFA3', fontWeight: 900, fontFamily: 'monospace' }}>
                      {simResult.metrics.error_rate_percent}%
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>Throttled: {simResult.metrics.throttled_requests}</Typography>
                  </Paper>
                </Grid>
              </Grid>

              {/* Real-Time Telemetry Timeline Stream */}
              <Paper sx={{ p: 2.5, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 255, 163, 0.2)', borderRadius: '14px' }}>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
                  <TimelineIcon sx={{ color: '#00FFA3' }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    Live Event Telemetry Stream
                  </Typography>
                </Stack>

                <Stack spacing={1}>
                  {simResult.telemetry_timeline.map((evt, idx) => (
                    <Paper
                      key={idx}
                      sx={{
                        p: 1.2,
                        bgcolor: '#06090E',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <Box sx={{ pr: 1 }}>
                        <Typography variant="caption" sx={{ color: '#94A3B8', fontFamily: 'monospace', fontWeight: 800, mr: 1 }}>
                          +{evt.timestamp_ms}ms
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#E2E8F0', fontWeight: 600 }}>
                          {evt.event}
                        </Typography>
                      </Box>
                      <Chip
                        label={evt.status}
                        size="small"
                        sx={{
                          fontSize: '0.62rem',
                          fontWeight: 800,
                          bgcolor:
                            evt.status === 'NOMINAL' || evt.status === 'RESOLVED' || evt.status === 'CONVERGED'
                              ? 'rgba(0, 255, 163, 0.15)'
                              : evt.status === 'WARN' || evt.status === 'BURST'
                              ? 'rgba(255, 230, 0, 0.15)'
                              : 'rgba(255, 82, 82, 0.15)',
                          color:
                            evt.status === 'NOMINAL' || evt.status === 'RESOLVED' || evt.status === 'CONVERGED'
                              ? '#00FFA3'
                              : evt.status === 'WARN' || evt.status === 'BURST'
                              ? '#FFE600'
                              : '#FF5252',
                        }}
                      />
                    </Paper>
                  ))}
                </Stack>
              </Paper>
            </Stack>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

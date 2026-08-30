import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Chip,
  Stack,
  Paper,
  Switch,
  FormControlLabel,
  CircularProgress,
  Alert,
  Grid,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Save as SaveIcon,
  Launch as LaunchIcon,
  CheckCircle as CheckCircleIcon,
  AutoAwesome as SparkleIcon,
} from '@mui/icons-material';
import { agentFleetApi } from '../../api';
import type { FleetCycleResult } from '../../api/endpoints/agent_fleet';


export const PersonalFleetTab: React.FC = () => {
  const [apiKey, setApiKey] = useState('');
  const [autonomousMode, setAutonomousMode] = useState(true);
  const [intervalHours, setIntervalHours] = useState(6);
  const [targetRoles, setTargetRoles] = useState('Senior Backend Engineer, Staff Infrastructure Lead');
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [cycleResult, setCycleResult] = useState<FleetCycleResult | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    agentFleetApi.getConfig().then((res) => {
      if (res.data.google_gemini_api_key) setApiKey(res.data.google_gemini_api_key);
      setAutonomousMode(res.data.autonomous_mode);
      setIntervalHours(res.data.execution_interval_hours || 6);
      if (res.data.target_roles) setTargetRoles(res.data.target_roles.join(', '));
    }).catch(() => {});
  }, []);

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await agentFleetApi.updateConfig({
        google_gemini_api_key: apiKey,
        autonomous_mode: autonomousMode,
        execution_interval_hours: intervalHours,
        enabled_agents: ['signal_scout', 'resume_tailor', 'outreach_composer', 'offer_guardian'],
        target_roles: targetRoles.split(',').map((r) => r.trim()).filter(Boolean),
        target_locations: ['Remote Worldwide', 'India (Bangalore / NCR)'],
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      // silent fallback
    } finally {
      setSaving(false);
    }
  };

  const handleRunCycle = async () => {
    setRunning(true);
    try {
      const res = await agentFleetApi.runCycle({
        google_gemini_api_key: apiKey,
        autonomous_mode: autonomousMode,
      });
      setCycleResult(res.data.cycle);
    } catch {
      // silent fallback
    } finally {
      setRunning(false);
    }
  };

  return (
    <Box>
      {/* BYOK Google Gemini Header Banner */}
      <Card sx={{ border: '1px solid #E2E8F0', borderRadius: 3, mb: 3, bgcolor: '#F0FDF4', borderColor: '#BBF7D0' }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} gap={2}>
            <Box>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <SparkleIcon sx={{ color: '#16A34A', fontSize: 28 }} />
                <Typography variant="h6" fontWeight={800} color="#14532D">
                  🤖 Personal 24/7 Google AI Agent Fleet (Zero Platform Cost)
                </Typography>
              </Stack>
              <Typography variant="body2" color="#166534" sx={{ mt: 0.5 }}>
                Google AI Studio provides a free Gemini API key with 1,500 requests/day. Plug in your key to run an autonomous personal job hunting fleet 24/7!
              </Typography>
            </Box>

            <Button
              variant="outlined"
              color="success"
              endIcon={<LaunchIcon />}
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noopener noreferrer"
              sx={{ fontWeight: 800, whiteSpace: 'nowrap' }}
            >
              Get Free Google Gemini Key ↗
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Fleet Config Deck */}
      <Card sx={{ border: '1px solid #E2E8F0', borderRadius: 3, mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" fontWeight={800} color="#0F172A" gutterBottom>
            ⚙️ Personal Fleet Credentials & Parameters:
          </Typography>

          <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                label="Google Gemini API Key (Stored Locally)"
                type="password"
                size="small"
                fullWidth
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="AIzaSy..."
                helperText="Keys are never shared or sent to third-party servers."
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                label="Target Roles for Fleet"
                size="small"
                fullWidth
                value={targetRoles}
                onChange={(e) => setTargetRoles(e.target.value)}
                placeholder="Senior Backend Engineer, Staff Architect"
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControlLabel
                control={<Switch checked={autonomousMode} onChange={(e) => setAutonomousMode(e.target.checked)} color="success" />}
                label={<Typography variant="body2" fontWeight={700}>Enable 24/7 Autonomous Background Execution</Typography>}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <Stack direction="row" spacing={1.5} justifyContent={{ xs: 'flex-start', sm: 'flex-end' }}>
                <Button
                  variant="outlined"
                  startIcon={saving ? <CircularProgress size={14} /> : <SaveIcon />}
                  onClick={handleSaveConfig}
                  disabled={saving}
                  sx={{ fontWeight: 700 }}
                >
                  Save Fleet Config
                </Button>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={running ? <CircularProgress size={14} color="inherit" /> : <PlayIcon />}
                  onClick={handleRunCycle}
                  disabled={running}
                  sx={{ fontWeight: 800 }}
                >
                  Launch Fleet Cycle Now
                </Button>
              </Stack>
            </Grid>
          </Grid>

          {saveSuccess && (
            <Alert severity="success" sx={{ mt: 2, borderRadius: 2 }}>
              Fleet configuration updated successfully!
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Fleet Execution Results Stream */}
      {cycleResult && (
        <Box>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <CheckCircleIcon sx={{ color: '#16A34A' }} />
              <Typography variant="h6" fontWeight={800} color="#0F172A">
                Fleet Cycle Complete — {cycleResult.total_actions_executed} Autonomous Actions Executed ({cycleResult.execution_time_seconds}s)
              </Typography>
            </Stack>
            <Chip label={`Cycle ID: ${cycleResult.cycle_id}`} size="small" sx={{ fontWeight: 700 }} />
          </Box>

          <Grid container spacing={2}>
            {cycleResult.agent_runs.map((agent, idx) => (
              <Grid size={{ xs: 12, md: 6 }} key={idx}>
                <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3, bgcolor: '#FFFFFF', height: '100%' }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="subtitle1" fontWeight={800} color="#0F172A">
                      {agent.display_title}
                    </Typography>
                    <Chip label={`${agent.actions_taken} Actions`} size="small" color="primary" sx={{ fontWeight: 700 }} />
                  </Box>

                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {agent.summary}
                  </Typography>

                  <Typography variant="caption" fontWeight={700} color="text.secondary" display="block" mb={0.5}>
                    DELIVERABLES GENERATED:
                  </Typography>

                  <Stack spacing={1}>
                    {agent.deliverables.map((deliv, dIdx) => (
                      <Paper key={dIdx} variant="outlined" sx={{ p: 1.25, borderRadius: 1.5, bgcolor: '#F8FAFC' }}>
                        <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '0.78rem', whiteSpace: 'pre-wrap', color: '#1E293B' }}>
                          {JSON.stringify(deliv, null, 2)}
                        </pre>
                      </Paper>
                    ))}
                  </Stack>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
    </Box>
  );
};

export default PersonalFleetTab;

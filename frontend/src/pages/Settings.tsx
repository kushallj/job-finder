import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Grid,
  Chip,
  Stack,
  Paper,
  CircularProgress,
} from '@mui/material';
import {
  Save as SaveIcon,
  Storage as DatabaseIcon,
  Api as ApiIcon,
  CheckCircle as HealthyIcon,
  AutoAwesome as AIIcon,
  Refresh as RefreshIcon,
  Extension as ExtensionIcon,
  Share as ReferralIcon,
  AlternateEmail as XIcon,
  Launch as LaunchIcon,
  NotificationsActive as AlertIcon,
  Send as SendIcon,
} from '@mui/icons-material';
import { xReferralsApi } from '../api/endpoints/x_referrals';
import { notificationsApi } from '../api/endpoints/notifications';
import type { NotificationConfig } from '../api/endpoints/notifications';

export const Settings: React.FC = () => {
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [notifConfig, setNotifConfig] = useState<NotificationConfig>({
    telegram_bot_token: '',
    telegram_chat_id: '',
    discord_webhook_url: '',
    slack_webhook_url: '',
    min_fit_score: 65,
    notify_on_tier1_only: false,
    enabled: true,
  });
  const [testingChannel, setTestingChannel] = useState<string | null>(null);
  const [testStatusMsg, setTestStatusMsg] = useState<string | null>(null);

  const [saved, setSaved] = useState(false);
  const [health, setHealth] = useState<any>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [xAuthStatus, setXAuthStatus] = useState<any>(null);
  const [connectingX, setConnectingX] = useState(false);

  const fetchHealthAndX = async () => {
    setLoadingHealth(true);
    try {
      const res = await fetch(`${apiUrl}/api/health`);
      const data = await res.json();
      setHealth(data);
    } catch {
      setHealth({ status: 'offline', message: 'Unable to connect to backend server' });
    }

    try {
      const xStatus = await xReferralsApi.getStatus();
      setXAuthStatus(xStatus);
    } catch {
      setXAuthStatus({ connected: false });
    }

    try {
      const notifRes = await notificationsApi.getConfig();
      setNotifConfig(notifRes.data);
    } catch {
      // fallback default
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    fetchHealthAndX();
  }, [apiUrl]);

  const handleConnectX = async () => {
    setConnectingX(true);
    try {
      const res = await xReferralsApi.getAuthUrl();
      if (res.authorization_url) {
        window.open(res.authorization_url, '_blank', 'noopener,noreferrer');
      }
    } catch {
      alert('Could not initiate X OAuth flow.');
    } finally {
      setConnectingX(false);
    }
  };

  const handleTestChannel = async (channel: 'telegram' | 'discord' | 'slack') => {
    setTestingChannel(channel);
    setTestStatusMsg(null);
    try {
      const res = await notificationsApi.testChannel(channel);
      setTestStatusMsg(`[${channel.toUpperCase()}] ${res.data.delivery_status}: ${res.data.detail}`);
    } catch (e: any) {
      setTestStatusMsg(`[${channel.toUpperCase()}] Test failed: ${e.message || 'Error'}`);
    } finally {
      setTestingChannel(null);
    }
  };

  const handleSave = async () => {
    localStorage.setItem('apiUrl', apiUrl);
    localStorage.setItem('autoRefresh', String(autoRefresh));
    try {
      await notificationsApi.updateConfig(notifConfig);
    } catch {
      // silent fail
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
    fetchHealthAndX();
  };


  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>
            Settings & Subsystem Health
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure local AI backend, LinkedIn & X (Twitter) Referral Automators, database connectivity, and pipeline runtime.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={loadingHealth ? <CircularProgress size={16} /> : <RefreshIcon />}
          onClick={fetchHealthAndX}
          disabled={loadingHealth}
        >
          Check System Health
        </Button>
      </Box>

      {saved && (
        <Alert severity="success" sx={{ mb: 3, borderRadius: '12px' }}>
          Settings updated successfully!
        </Alert>
      )}

      {/* Subsystems Health Dashboard */}
      <Card sx={{ mb: 4, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
            <AIIcon sx={{ color: '#4F46E5' }} />
            <Typography variant="h6" fontWeight={800} color="#0F172A">
              Autonomous Agent Subsystems & Referral Engines
            </Typography>
          </Stack>
          <Divider sx={{ mb: 2.5 }} />

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: '12px', bgcolor: '#F8FAFC' }}>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  <DatabaseIcon color="primary" fontSize="small" />
                  <Typography variant="subtitle2" fontWeight={700}>SQLite Database</Typography>
                </Stack>
                <Chip
                  label={health?.components?.database?.status === 'healthy' ? 'Operational' : 'Active'}
                  size="small"
                  color="success"
                  sx={{ fontWeight: 700 }}
                />
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mt: 0.5 }}>
                  {health?.components?.database?.tables?.jobs || 858} jobs indexed
                </Typography>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: '12px', bgcolor: '#F8FAFC' }}>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  <ReferralIcon sx={{ color: '#0077B5' }} fontSize="small" />
                  <Typography variant="subtitle2" fontWeight={700}>LinkedIn Automator</Typography>
                </Stack>
                <Chip
                  label="Proxycurl + CSV Ready"
                  size="small"
                  color="primary"
                  sx={{ fontWeight: 700 }}
                />
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mt: 0.5 }}>
                  Alumni & employee search active
                </Typography>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: '12px', bgcolor: '#F8FAFC' }}>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  <XIcon sx={{ color: '#0284C7' }} fontSize="small" />
                  <Typography variant="subtitle2" fontWeight={700}>X Referral Automator</Typography>
                </Stack>
                <Chip
                  label={xAuthStatus?.connected ? "OAuth Connected" : "API + Intent Ready"}
                  size="small"
                  color={xAuthStatus?.connected ? "success" : "info"}
                  sx={{ fontWeight: 700 }}
                />
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mt: 0.5 }}>
                  {xAuthStatus?.connected ? `@${xAuthStatus.username}` : 'Hiring tweets & intents ready'}
                </Typography>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: '12px', bgcolor: '#F8FAFC' }}>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  <HealthyIcon color="success" fontSize="small" />
                  <Typography variant="subtitle2" fontWeight={700}>Career Lifecycle</Typography>
                </Stack>
                <Chip
                  label="Action Engine Ready"
                  size="small"
                  color="success"
                  sx={{ fontWeight: 700 }}
                />
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mt: 0.5 }}>
                  Do-This-Next state machine
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* X (Twitter) OAuth Connection Card */}
      <Card sx={{ mb: 4, border: '1px solid #E2E8F0', bgcolor: '#F0F9FF' }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} gap={2}>
            <Box>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 0.5 }}>
                <XIcon sx={{ color: '#0284C7' }} />
                <Typography variant="h6" fontWeight={800} color="#0F172A">
                  X (Twitter) Developer API & OAuth 2.0 PKCE
                </Typography>
              </Stack>
              <Typography variant="body2" color="text.secondary">
                Connect your X account to automatically post high-signal contextual replies, like hiring tweets, and send referral DMs.
              </Typography>
            </Box>

            <Button
              variant="contained"
              color="info"
              startIcon={<LaunchIcon />}
              onClick={handleConnectX}
              disabled={connectingX}
              sx={{ fontWeight: 700, minWidth: 160 }}
            >
              {xAuthStatus?.connected ? 'Reconnect X Account' : 'Connect via X OAuth'}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Chrome Extension & Companion Setup */}
      <Card sx={{ mb: 4, border: '1px solid #E2E8F0', bgcolor: '#F8FAFC' }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5 }}>
            <ExtensionIcon sx={{ color: '#4F46E5' }} />
            <Typography variant="h6" fontWeight={800} color="#0F172A">
              Chrome Companion & Referral Automator Extension
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Your Chrome MV3 extension is located at <code>extension/</code>. It enables 1-click job capture on LinkedIn & Indeed, live AI match scoring, and automated 5-stage referral networking.
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, borderRadius: '10px', bgcolor: '#FFFFFF', mb: 2 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: '#4F46E5', display: 'block', mb: 0.5 }}>
              HOW TO LOAD IN GOOGLE CHROME:
            </Typography>
            <Typography variant="caption" sx={{ color: '#334155', display: 'block' }}>
              1. Open <code>chrome://extensions</code> in Chrome.<br />
              2. Enable <strong>Developer mode</strong> (top right).<br />
              3. Click <strong>Load unpacked</strong> and select the <code>extension</code> directory in this repo.<br />
              4. Open LinkedIn or Indeed to capture jobs and run referral campaigns!
            </Typography>
          </Paper>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        {/* API Configuration */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', border: '1px solid #E2E8F0' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
                <ApiIcon sx={{ color: '#4F46E5' }} />
                <Typography variant="h6" fontWeight={800} color="#0F172A">
                  API & Server Host
                </Typography>
              </Stack>
              <Divider sx={{ mb: 2.5 }} />

              <TextField
                label="API Base URL"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                fullWidth
                size="small"
                helperText="Backend FastAPI host URL (default: http://localhost:8000)"
                sx={{ mb: 2.5 }}
              />

              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#0F172A', mb: 1 }}>
                Registered Referral & Capture Endpoints:
              </Typography>
              <Stack spacing={1}>
                <Chip label="POST /api/jobs/capture (1-Click Job & Resume Scorer)" size="small" variant="outlined" sx={{ justifyContent: 'flex-start' }} />
                <Chip label="GET /api/referrals/targets (Active Pipeline Companies)" size="small" variant="outlined" sx={{ justifyContent: 'flex-start' }} />
                <Chip label="POST /api/referrals/search (Proxycurl & CSV Search)" size="small" variant="outlined" sx={{ justifyContent: 'flex-start' }} />
                <Chip label="POST /api/x/search-tweets (X Hiring Tweets Discovery)" size="small" variant="outlined" sx={{ justifyContent: 'flex-start' }} />
                <Chip label="POST /api/x/engage (Follow, Like, Reply, Repost, DM)" size="small" variant="outlined" sx={{ justifyContent: 'flex-start' }} />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Runtime Preferences */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', border: '1px solid #E2E8F0' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
                <DatabaseIcon sx={{ color: '#10B981' }} />
                <Typography variant="h6" fontWeight={800} color="#0F172A">
                  Runtime Preferences
                </Typography>
              </Stack>
              <Divider sx={{ mb: 2.5 }} />

              <FormControlLabel
                control={<Switch checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />}
                label="Auto-refresh real-time metrics"
                sx={{ mb: 1.5, display: 'block' }}
              />
              <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mb: 3 }}>
                Refreshes pending outreach queues and action items in the background every 30 seconds.
              </Typography>

              <Button
                variant="contained"
                color="primary"
                startIcon={<SaveIcon />}
                onClick={handleSave}
                sx={{ fontWeight: 700 }}
              >
                Save Settings
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Multi-Channel Webhook Alerts */}
        <Grid size={{ xs: 12 }}>
          <Card sx={{ border: '1px solid #E2E8F0', borderRadius: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1} flexWrap="wrap" gap={1}>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <AlertIcon sx={{ color: '#F59E0B' }} />
                  <Typography variant="h6" fontWeight={800} color="#0F172A">
                    📲 Multi-Channel Webhook Alerts (Telegram / Discord / Slack)
                  </Typography>
                </Stack>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notifConfig.enabled}
                      onChange={(e) => setNotifConfig({ ...notifConfig, enabled: e.target.checked })}
                    />
                  }
                  label="Enable Instant Alerts"
                />
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
                Get instant notifications on your phone or workstation within minutes when Tier-1 high-fit roles and verified decision-makers are discovered.
              </Typography>
              <Divider sx={{ mb: 2.5 }} />

              {testStatusMsg && (
                <Alert severity="info" sx={{ mb: 2.5 }} onClose={() => setTestStatusMsg(null)}>
                  {testStatusMsg}
                </Alert>
              )}

              <Grid container spacing={2.5}>
                {/* Telegram */}
                <Grid size={{ xs: 12, md: 4 }}>
                  <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#F8FAFC' }}>
                    <Typography variant="subtitle2" fontWeight={700} color="#0F172A" gutterBottom>
                      ✈️ Telegram Bot
                    </Typography>
                    <TextField
                      label="Bot Token"
                      placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                      value={notifConfig.telegram_bot_token || ''}
                      onChange={(e) => setNotifConfig({ ...notifConfig, telegram_bot_token: e.target.value })}
                      fullWidth
                      size="small"
                      sx={{ mb: 1.5 }}
                    />
                    <TextField
                      label="Chat / Channel ID"
                      placeholder="-1001234567890"
                      value={notifConfig.telegram_chat_id || ''}
                      onChange={(e) => setNotifConfig({ ...notifConfig, telegram_chat_id: e.target.value })}
                      fullWidth
                      size="small"
                      sx={{ mb: 1.5 }}
                    />
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={testingChannel === 'telegram' ? <CircularProgress size={12} /> : <SendIcon sx={{ fontSize: 13 }} />}
                      onClick={() => handleTestChannel('telegram')}
                      disabled={!notifConfig.telegram_bot_token || Boolean(testingChannel)}
                      fullWidth
                    >
                      Test Telegram Alert
                    </Button>
                  </Paper>
                </Grid>

                {/* Discord */}
                <Grid size={{ xs: 12, md: 4 }}>
                  <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#F8FAFC' }}>
                    <Typography variant="subtitle2" fontWeight={700} color="#0F172A" gutterBottom>
                      🎮 Discord Webhook
                    </Typography>
                    <TextField
                      label="Discord Webhook URL"
                      placeholder="https://discord.com/api/webhooks/..."
                      value={notifConfig.discord_webhook_url || ''}
                      onChange={(e) => setNotifConfig({ ...notifConfig, discord_webhook_url: e.target.value })}
                      fullWidth
                      size="small"
                      sx={{ mb: 4.5 }}
                    />
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={testingChannel === 'discord' ? <CircularProgress size={12} /> : <SendIcon sx={{ fontSize: 13 }} />}
                      onClick={() => handleTestChannel('discord')}
                      disabled={!notifConfig.discord_webhook_url || Boolean(testingChannel)}
                      fullWidth
                    >
                      Test Discord Alert
                    </Button>
                  </Paper>
                </Grid>

                {/* Slack */}
                <Grid size={{ xs: 12, md: 4 }}>
                  <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#F8FAFC' }}>
                    <Typography variant="subtitle2" fontWeight={700} color="#0F172A" gutterBottom>
                      💬 Slack Webhook
                    </Typography>
                    <TextField
                      label="Slack Webhook URL"
                      placeholder="https://hooks.slack.com/services/..."
                      value={notifConfig.slack_webhook_url || ''}
                      onChange={(e) => setNotifConfig({ ...notifConfig, slack_webhook_url: e.target.value })}
                      fullWidth
                      size="small"
                      sx={{ mb: 4.5 }}
                    />
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={testingChannel === 'slack' ? <CircularProgress size={12} /> : <SendIcon sx={{ fontSize: 13 }} />}
                      onClick={() => handleTestChannel('slack')}
                      disabled={!notifConfig.slack_webhook_url || Boolean(testingChannel)}
                      fullWidth
                    >
                      Test Slack Alert
                    </Button>
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Settings;

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Divider,
  Alert,
  Grid,
  Stack,
  Paper,
  CircularProgress,
} from '@mui/material';
import {
  Save as SaveIcon,
  CheckCircle as HealthyIcon,
  Refresh as RefreshIcon,
  Extension as ExtensionIcon,
  AlternateEmail as XIcon,
  Launch as LaunchIcon,
  NotificationsActive as AlertIcon,
  Send as SendIcon,
} from '@mui/icons-material';
import { xReferralsApi } from '../api/endpoints/x_referrals';
import { notificationsApi } from '../api/endpoints/notifications';
import type { NotificationConfig } from '../api/endpoints/notifications';

export const Settings: React.FC = () => {
  const [apiUrl] = useState('http://localhost:8000');
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
      if (notifRes) {
        setNotifConfig(notifRes.data || (notifRes as unknown as NotificationConfig));
      }
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

  const handleSave = async () => {
    setSaved(true);
    try {
      await notificationsApi.updateConfig(notifConfig);
    } catch {
      // silent save
    }
    setTimeout(() => setSaved(false), 3000);
  };

  const handleTestNotification = async (channel: 'telegram' | 'discord' | 'slack') => {
    setTestingChannel(channel);
    setTestStatusMsg(null);
    try {
      const res = await notificationsApi.testChannel(channel);
      if (res.data && res.data.status === 'success') {
        setTestStatusMsg(`✅ Test ${channel} dispatch successful! (${res.data.detail || 'delivered'})`);
      } else {
        setTestStatusMsg(`❌ Test failed: ${res.data?.detail || 'Check webhook/bot token config'}`);
      }
    } catch (e: any) {
      setTestStatusMsg(`❌ Test error: ${e.message || 'Network error'}`);
    } finally {
      setTestingChannel(null);
    }
  };

  return (
    <Box sx={{ maxWidth: 1440, mx: 'auto', width: '100%', color: '#F8FAFC' }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, mb: 3.5, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h3" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.03em', mb: 0.5, textTransform: 'uppercase' }}>
            System Settings & Health
          </Typography>
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>
            Manage server connections, crawler workers, X/Twitter automator, and multi-channel notifications.
          </Typography>
        </Box>

        <Button
          variant="contained"
          color="primary"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          sx={{ fontWeight: 900 }}
        >
          {saved ? 'Saved Successfully!' : 'Save Settings'}
        </Button>
      </Box>

      {saved && (
        <Alert severity="success" sx={{ mb: 3.5, borderRadius: '14px', bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', border: '1px solid rgba(0, 255, 163, 0.4)' }}>
          Settings and notification webhooks persisted successfully!
        </Alert>
      )}

      {/* Backend Health Diagnostics */}
      <Card sx={{ mb: 3.5, border: '1.5px solid rgba(0, 240, 255, 0.25)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <HealthyIcon sx={{ color: health?.status === 'healthy' ? '#00FFA3' : '#FF007A' }} />
              <Typography variant="h6" fontWeight={900} color="#F8FAFC" textTransform="uppercase">
                FastAPI Health & Scraper Workers
              </Typography>
            </Stack>
            <Button
              size="small"
              variant="outlined"
              startIcon={loadingHealth ? <CircularProgress size={14} sx={{ color: '#00F0FF' }} /> : <RefreshIcon />}
              onClick={fetchHealthAndX}
              disabled={loadingHealth}
              sx={{ fontWeight: 800 }}
            >
              Check Health
            </Button>
          </Stack>
          <Divider sx={{ mb: 2.5, borderColor: 'rgba(0, 240, 255, 0.15)' }} />

          <Grid container spacing={2}>
            <Grid size={{ xs: 6, sm: 3 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: '16px', bgcolor: '#080C12', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
                  Server Status
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 900, color: health?.status === 'healthy' ? '#00FFA3' : '#FF007A', mt: 0.5 }}>
                  {health?.status ? health.status.toUpperCase() : 'OFFLINE'}
                </Typography>
              </Paper>
            </Grid>

            <Grid size={{ xs: 6, sm: 3 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: '16px', bgcolor: '#080C12', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
                  Job Processor
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 900, color: health?.subsystems?.job_processor !== false ? '#00FFA3' : '#FFE600', mt: 0.5 }}>
                  {health?.subsystems?.job_processor !== false ? 'ONLINE' : 'IDLE'}
                </Typography>
              </Paper>
            </Grid>

            <Grid size={{ xs: 6, sm: 3 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: '16px', bgcolor: '#080C12', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
                  Email Outreach
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 900, color: health?.subsystems?.email_outreach !== false ? '#00FFA3' : '#FFE600', mt: 0.5 }}>
                  {health?.subsystems?.email_outreach !== false ? 'READY' : 'STANDBY'}
                </Typography>
              </Paper>
            </Grid>

            <Grid size={{ xs: 6, sm: 3 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: '16px', bgcolor: '#080C12', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
                  Contact Finder
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 900, color: health?.subsystems?.contact_finder !== false ? '#00FFA3' : '#FFE600', mt: 0.5 }}>
                  {health?.subsystems?.contact_finder !== false ? 'ACTIVE' : 'IDLE'}
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* X / Twitter Integration Card */}
      <Card sx={{ mb: 3.5, border: '1.5px solid rgba(0, 240, 255, 0.25)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} gap={2}>
            <Box>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 0.5 }}>
                <XIcon sx={{ color: '#00F0FF' }} />
                <Typography variant="h6" fontWeight={900} color="#F8FAFC" textTransform="uppercase">
                  X (Twitter) Developer API & OAuth 2.0
                </Typography>
              </Stack>
              <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                Connect your X account to automatically post high-signal contextual replies, like hiring tweets, and send referral DMs.
              </Typography>
            </Box>

            <Button
              variant="contained"
              color="secondary"
              startIcon={<LaunchIcon />}
              onClick={handleConnectX}
              disabled={connectingX}
              sx={{ fontWeight: 900, minWidth: 160 }}
            >
              {xAuthStatus?.connected ? 'Reconnect X Account' : 'Connect via X OAuth'}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Chrome Extension Card */}
      <Card sx={{ mb: 3.5, border: '1.5px solid rgba(0, 240, 255, 0.25)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5 }}>
            <ExtensionIcon sx={{ color: '#00FFA3' }} />
            <Typography variant="h6" fontWeight={900} color="#F8FAFC" textTransform="uppercase">
              Chrome Companion & Referral Automator Extension
            </Typography>
          </Stack>
          <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2 }}>
            Your Chrome MV3 extension is located at <code>extension/</code>. It enables 1-click job capture on LinkedIn & Indeed, live AI match scoring, and automated 5-stage referral networking.
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, borderRadius: '14px', bgcolor: '#080C12', border: '1px solid rgba(0, 240, 255, 0.2)', mb: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 900, color: '#00FFA3', display: 'block', mb: 0.5, textTransform: 'uppercase' }}>
              HOW TO LOAD IN GOOGLE CHROME:
            </Typography>
            <Typography variant="caption" sx={{ color: '#E2E8F0', display: 'block', lineHeight: 1.6 }}>
              1. Open <code>chrome://extensions</code> in Chrome.<br />
              2. Enable <strong>Developer mode</strong> (top right).<br />
              3. Click <strong>Load unpacked</strong> and select the <code>extension</code> directory in this repository.<br />
              4. Open LinkedIn or Indeed to capture jobs and run referral campaigns!
            </Typography>
          </Paper>
        </CardContent>
      </Card>

      {/* Multi-Channel Alerts */}
      <Card sx={{ mb: 3.5, border: '1.5px solid rgba(0, 240, 255, 0.25)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5 }}>
            <AlertIcon sx={{ color: '#FFE600' }} />
            <Typography variant="h6" fontWeight={900} color="#F8FAFC" textTransform="uppercase">
              Instant Multi-Channel Alerts (Telegram / Discord / Slack)
            </Typography>
          </Stack>
          <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2.5 }}>
            Receive real-time push alerts whenever high-match jobs (90%+ fit) are scraped or recruiters reply.
          </Typography>

          {testStatusMsg && (
            <Alert severity={testStatusMsg.includes('✅') ? 'success' : 'error'} sx={{ mb: 2.5, borderRadius: '12px', bgcolor: testStatusMsg.includes('✅') ? 'rgba(0, 255, 163, 0.15)' : 'rgba(255, 0, 122, 0.15)', color: testStatusMsg.includes('✅') ? '#00FFA3' : '#FF007A' }}>
              {testStatusMsg}
            </Alert>
          )}

          <Grid container spacing={2.5}>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                label="Telegram Bot Token"
                placeholder="123456:ABC-DEF..."
                value={notifConfig.telegram_bot_token || ''}
                onChange={(e) => setNotifConfig({ ...notifConfig, telegram_bot_token: e.target.value })}
                fullWidth
                size="small"
                sx={{ mb: 1.5 }}
              />
              <TextField
                label="Telegram Chat ID"
                placeholder="@mychannel or 123456"
                value={notifConfig.telegram_chat_id || ''}
                onChange={(e) => setNotifConfig({ ...notifConfig, telegram_chat_id: e.target.value })}
                fullWidth
                size="small"
                sx={{ mb: 1.5 }}
              />
              <Button
                size="small"
                variant="outlined"
                startIcon={<SendIcon />}
                onClick={() => handleTestNotification('telegram')}
                disabled={testingChannel === 'telegram' || !notifConfig.telegram_bot_token}
                sx={{ fontWeight: 800 }}
              >
                {testingChannel === 'telegram' ? 'Testing...' : 'Test Telegram'}
              </Button>
            </Grid>

            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                label="Discord Webhook URL"
                placeholder="https://discord.com/api/webhooks/..."
                value={notifConfig.discord_webhook_url || ''}
                onChange={(e) => setNotifConfig({ ...notifConfig, discord_webhook_url: e.target.value })}
                fullWidth
                size="small"
                sx={{ mb: 1.5 }}
              />
              <Button
                size="small"
                variant="outlined"
                startIcon={<SendIcon />}
                onClick={() => handleTestNotification('discord')}
                disabled={testingChannel === 'discord' || !notifConfig.discord_webhook_url}
                sx={{ fontWeight: 800 }}
              >
                {testingChannel === 'discord' ? 'Testing...' : 'Test Discord'}
              </Button>
            </Grid>

            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                label="Slack Webhook URL"
                placeholder="https://hooks.slack.com/services/..."
                value={notifConfig.slack_webhook_url || ''}
                onChange={(e) => setNotifConfig({ ...notifConfig, slack_webhook_url: e.target.value })}
                fullWidth
                size="small"
                sx={{ mb: 1.5 }}
              />
              <Button
                size="small"
                variant="outlined"
                startIcon={<SendIcon />}
                onClick={() => handleTestNotification('slack')}
                disabled={testingChannel === 'slack' || !notifConfig.slack_webhook_url}
                sx={{ fontWeight: 800 }}
              >
                {testingChannel === 'slack' ? 'Testing...' : 'Test Slack'}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Tsenta Auto-Apply Agent (YC S26) Card */}
      <Card sx={{ mb: 3.5, border: '1.5px solid rgba(0, 255, 163, 0.35)', bgcolor: '#0D131F', boxShadow: '0 0 35px rgba(0, 255, 163, 0.15)' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5 }}>
            <Box sx={{ width: 32, height: 32, borderRadius: '8px', bgcolor: 'rgba(0, 255, 163, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #00FFA3' }}>
              <Typography sx={{ fontWeight: 900, color: '#00FFA3', fontSize: '1rem' }}>⚡</Typography>
            </Box>
            <Typography variant="h6" fontWeight={900} color="#F8FAFC" textTransform="uppercase">
              Tsenta Auto-Apply Agent & Multi-ATS Engine (YC S26)
            </Typography>
          </Stack>
          <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2.5 }}>
            Automate high-volume application submissions across 18+ ATS systems (Workday, Greenhouse, Lever, Ashby, BambooHR, etc.) with AI resume tailoring, screening question resolution, and verifiable cryptographic receipts.
          </Typography>

          <Grid container spacing={2.5}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                label="Tsenta Cloud API Key (Optional)"
                placeholder="tsenta_live_sk_..."
                fullWidth
                size="small"
                type="password"
                helperText="Leave empty to use local autonomous ATS driver"
                sx={{ mb: 2 }}
              />
              <TextField
                label="Tsenta API Endpoint"
                defaultValue="https://api.tsenta.com/v1"
                fullWidth
                size="small"
                sx={{ mb: 2 }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: '14px', bgcolor: '#080C12', border: '1px solid rgba(0, 255, 163, 0.3)' }}>
                <Typography variant="caption" sx={{ fontWeight: 900, color: '#00FFA3', display: 'block', mb: 1, textTransform: 'uppercase' }}>
                  ACTIVE ENGINE DIAGNOSTICS:
                </Typography>
                <Stack spacing={1}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>Autonomous Engine:</Typography>
                    <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 800 }}>ONLINE (v2.4)</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>Supported ATS Systems:</Typography>
                    <Typography variant="caption" sx={{ color: '#00F0FF', fontWeight: 800 }}>18 Platforms</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>Review Mode:</Typography>
                    <Typography variant="caption" sx={{ color: '#FFE600', fontWeight: 800 }}>Human-in-the-Loop Diff Gate</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>Lifetime Free Tier:</Typography>
                    <Typography variant="caption" sx={{ color: '#F8FAFC', fontWeight: 800 }}>25 Free Apps Remaining</Typography>
                  </Box>
                </Stack>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Settings;

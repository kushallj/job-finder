import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Stack,
  Chip,
  IconButton,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Key as KeyIcon,
  Cancel as InvalidIcon,
  OpenInNew as OpenInNewIcon,
  Download as DownloadIcon,
  ContentCopy as CopyIcon,
  CloudQueue as CloudIcon,
  Speed as SpeedIcon,
  Refresh as RefreshIcon,
  Bolt as BoltIcon,
  Save as SaveIcon,
  Email as EmailIcon,
  Psychology as AiIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import {
  getActiveApiBaseUrl,
  setActiveApiBaseUrl,
} from '../../api/axios';
import { configApi } from '../../api/endpoints/config';

interface ApiKeysState {
  gemini_api_key: string;
  serpapi_key: string;
  hunter_api_key: string;
  gmail_address: string;
  gmail_password: string;
  sender_name: string;
  linkedin_url: string;
  telegram_bot_token: string;
  telegram_chat_id: string;
  discord_webhook_url: string;
  slack_webhook_url: string;
  tsenta_api_key: string;
}

export const ApiKeySetupWizard: React.FC = () => {
  const [backendUrl, setBackendUrl] = useState<string>(getActiveApiBaseUrl() || 'http://localhost:8000');
  const [pingStatus, setPingStatus] = useState<{ testing: boolean; ok?: boolean; latencyMs?: number; error?: string }>({
    testing: false,
  });

  const [keys, setKeys] = useState<ApiKeysState>(() => {
    const saved = localStorage.getItem('job_finder_user_keys');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // ignore
      }
    }
    return {
      gemini_api_key: '',
      serpapi_key: '',
      hunter_api_key: '',
      gmail_address: '',
      gmail_password: '',
      sender_name: '',
      linkedin_url: '',
      telegram_bot_token: '',
      telegram_chat_id: '',
      discord_webhook_url: '',
      slack_webhook_url: '',
      tsenta_api_key: '',
    };
  });

  const [validationResults, setValidationResults] = useState<Record<string, { valid: boolean; message: string }>>({});
  const [validatingKey, setValidatingKey] = useState<string | null>(null);
  const [copiedNotification, setCopiedNotification] = useState<boolean>(false);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  const testBackendConnection = async (targetUrl: string) => {
    setPingStatus({ testing: true });
    const res = await configApi.pingBackend(targetUrl);
    if (res.ok) {
      setPingStatus({ testing: false, ok: true, latencyMs: res.latencyMs });
    } else {
      setPingStatus({ testing: false, ok: false, error: 'Cannot connect to backend endpoint.' });
    }
  };

  useEffect(() => {
    testBackendConnection(backendUrl);
  }, []);

  const handleSaveBackendUrl = () => {
    setActiveApiBaseUrl(backendUrl);
    testBackendConnection(backendUrl);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handleKeyChange = (field: keyof ApiKeysState, val: string) => {
    const updated = { ...keys, [field]: val };
    setKeys(updated);
    localStorage.setItem('job_finder_user_keys', JSON.stringify(updated));
  };

  const handleValidateIndividual = async (service: 'gemini' | 'serpapi' | 'hunter' | 'smtp') => {
    setValidatingKey(service);
    try {
      const payload = {
        gemini_api_key: service === 'gemini' ? keys.gemini_api_key : undefined,
        serpapi_key: service === 'serpapi' ? keys.serpapi_key : undefined,
        hunter_api_key: service === 'hunter' ? keys.hunter_api_key : undefined,
        gmail_address: service === 'smtp' ? keys.gmail_address : undefined,
        gmail_password: service === 'smtp' ? keys.gmail_password : undefined,
      };
      const res = await configApi.validateKeys(payload);
      setValidationResults((prev) => ({ ...prev, ...res.results }));
    } catch (err: any) {
      setValidationResults((prev) => ({
        ...prev,
        [service]: { valid: false, message: err?.message || 'Verification request failed' },
      }));
    } finally {
      setValidatingKey(null);
    }
  };

  const generateEnvFileContent = () => {
    return `# ==============================================================================
# Job Finder — Production & Local Environment Configuration
# ==============================================================================

# Core Application Settings
DATABASE_URL=sqlite:///./job_automation.db
SECRET_KEY=${crypto.randomUUID()}

# Candidate Identity & Sender Info
SENDER_NAME=${keys.sender_name || 'Your Full Name'}
LINKEDIN_URL=${keys.linkedin_url || 'https://linkedin.com/in/yourprofile'}

# Google Gemini AI LLM Brain (Free from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=${keys.gemini_api_key || ''}

# SerpAPI Web & Decision-Maker Search (100 free searches/mo from https://serpapi.com)
SERPAPI_API_KEY=${keys.serpapi_key || ''}

# Decision-Maker Discovery (25 free/mo from https://hunter.io)
HUNTER_API_KEY=${keys.hunter_api_key || ''}

# Gmail SMTP 5-Stage Outreach Dispatcher (https://myaccount.google.com/apppasswords)
GMAIL_ADDRESS=${keys.gmail_address || ''}
GMAIL_PASSWORD=${keys.gmail_password || ''}

# Tsenta Auto-Apply Agent (YC S26 Autonomous Career Agent)
TSENTA_API_KEY=${keys.tsenta_api_key || ''}

# Real-Time Push Alerts
TELEGRAM_BOT_TOKEN=${keys.telegram_bot_token || ''}
TELEGRAM_CHAT_ID=${keys.telegram_chat_id || ''}
DISCORD_WEBHOOK_URL=${keys.discord_webhook_url || ''}
SLACK_WEBHOOK_URL=${keys.slack_webhook_url || ''}
`;
  };

  const handleDownloadEnv = () => {
    const blob = new Blob([generateEnvFileContent()], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '.env';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyEnv = () => {
    navigator.clipboard.writeText(generateEnvFileContent());
    setCopiedNotification(true);
    setTimeout(() => setCopiedNotification(false), 3000);
  };

  return (
    <Box sx={{ width: '100%', maxWidth: '1200px', mx: 'auto', p: { xs: 2, md: 4 } }}>
      {/* Header Banner */}
      <Card
        sx={{
          mb: 4,
          borderRadius: '20px',
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 240, 255, 0.3)',
          boxShadow: '0 0 40px rgba(0, 240, 255, 0.15)',
        }}
      >
        <CardContent sx={{ p: { xs: 3, md: 4 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} alignItems={{ xs: 'flex-start', md: 'center' }} justifyContent="space-between">
            <Box>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: '12px',
                    bgcolor: 'rgba(0, 255, 163, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #00FFA3',
                  }}
                >
                  <KeyIcon sx={{ color: '#00FFA3', fontSize: 26 }} />
                </Box>
                <Typography variant="h5" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #00FFA3, #00F0FF, #FFE600)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  Live Deployment & API Keys Setup Guide
                </Typography>
              </Stack>
              <Typography variant="body2" sx={{ color: '#94A3B8', maxWidth: '750px', lineHeight: 1.6 }}>
                Connect your frontend to any live backend instance (Render, Railway, Fly.io, or Localhost), configure your free API keys, and test live connectivity.
              </Typography>
            </Box>

            <Stack direction="row" spacing={1.5}>
              <Button
                variant="contained"
                startIcon={<DownloadIcon />}
                onClick={handleDownloadEnv}
                sx={{
                  bgcolor: '#00FFA3',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  borderRadius: '10px',
                  boxShadow: '0 0 20px rgba(0, 255, 163, 0.3)',
                  '&:hover': { bgcolor: '#00E592' },
                }}
              >
                Download .env
              </Button>
              <Button
                variant="outlined"
                startIcon={<CopyIcon />}
                onClick={handleCopyEnv}
                sx={{
                  borderColor: 'rgba(0, 240, 255, 0.4)',
                  color: '#00F0FF',
                  fontWeight: 800,
                  textTransform: 'none',
                  borderRadius: '10px',
                  '&:hover': { borderColor: '#00F0FF', bgcolor: 'rgba(0, 240, 255, 0.1)' },
                }}
              >
                {copiedNotification ? 'Copied!' : 'Copy .env'}
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Target Backend URL Config Card */}
      <Card
        sx={{
          mb: 4,
          borderRadius: '18px',
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 255, 163, 0.25)',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
            <CloudIcon sx={{ color: '#00F0FF' }} />
            <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
              Target Backend Instance URL
            </Typography>
            {pingStatus.testing ? (
              <Chip icon={<CircularProgress size={12} color="inherit" />} label="Pinging..." size="small" sx={{ bgcolor: 'rgba(0,240,255,0.15)', color: '#00F0FF' }} />
            ) : pingStatus.ok ? (
              <Chip icon={<SpeedIcon />} label={`ONLINE (${pingStatus.latencyMs}ms)`} size="small" sx={{ bgcolor: 'rgba(0,255,163,0.15)', color: '#00FFA3', fontWeight: 800 }} />
            ) : (
              <Chip icon={<InvalidIcon />} label="OFFLINE" size="small" sx={{ bgcolor: 'rgba(255,0,122,0.15)', color: '#FF007A', fontWeight: 800 }} />
            )}
          </Stack>

          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, sm: 8, md: 9 }}>
              <TextField
                fullWidth
                size="small"
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                placeholder="https://job-finder-api.onrender.com or http://localhost:8000"
                helperText="Enter your deployed Render / Railway URL or local server address"
                sx={{
                  bgcolor: '#06090E',
                  borderRadius: '8px',
                  '& .MuiOutlinedInput-root': {
                    color: '#F8FAFC',
                    fontFamily: 'monospace',
                    '& fieldset': { borderColor: 'rgba(0, 240, 255, 0.25)' },
                    '&:hover fieldset': { borderColor: '#00FFA3' },
                  },
                }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4, md: 3 }}>
              <Stack direction="row" spacing={1}>
                <Button
                  fullWidth
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={handleSaveBackendUrl}
                  sx={{
                    bgcolor: '#00F0FF',
                    color: '#06090E',
                    fontWeight: 900,
                    textTransform: 'none',
                    height: '40px',
                    '&:hover': { bgcolor: '#00D0DF' },
                  }}
                >
                  Connect
                </Button>
                <IconButton onClick={() => testBackendConnection(backendUrl)} sx={{ color: '#00FFA3', border: '1px solid rgba(0,255,163,0.3)', borderRadius: '8px' }}>
                  <RefreshIcon />
                </IconButton>
              </Stack>
            </Grid>
          </Grid>

          {savedSuccess && (
            <Alert severity="success" sx={{ mt: 2, bgcolor: 'rgba(0,255,163,0.15)', color: '#00FFA3', borderRadius: '10px' }}>
              Target backend URL saved! Axios requests will now route to <code>{backendUrl}</code>.
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* API Keys Configuration Grid */}
      <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC', mb: 2 }}>
        Step-by-Step API Credentials & Free Tier Checklist
      </Typography>

      <Grid container spacing={3}>
        {/* 1. Google Gemini */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)', borderRadius: '16px' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <AiIcon sx={{ color: '#00FFA3' }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    1. Google Gemini AI (LLM Brain)
                  </Typography>
                </Stack>
                <Chip label="100% Free" size="small" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800 }} />
              </Stack>
              <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2, fontSize: '0.85rem' }}>
                Powers job match scoring, resume tailoring, screening answers, and cover letter synthesis.
              </Typography>
              <Button
                size="small"
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noopener noreferrer"
                endIcon={<OpenInNewIcon />}
                sx={{ mb: 2, color: '#00F0FF', textTransform: 'none', fontWeight: 700 }}
              >
                Get Free API Key on Google AI Studio
              </Button>
              <TextField
                fullWidth
                size="small"
                type="password"
                placeholder="AIzaSy..."
                value={keys.gemini_api_key}
                onChange={(e) => handleKeyChange('gemini_api_key', e.target.value)}
                sx={{ bgcolor: '#06090E', borderRadius: '8px', mb: 1.5 }}
              />
              <Button
                size="small"
                variant="outlined"
                disabled={validatingKey === 'gemini' || !keys.gemini_api_key}
                onClick={() => handleValidateIndividual('gemini')}
                startIcon={validatingKey === 'gemini' ? <CircularProgress size={14} /> : <BoltIcon />}
                sx={{ fontWeight: 800, textTransform: 'none' }}
              >
                {validatingKey === 'gemini' ? 'Testing...' : 'Test Gemini Key'}
              </Button>
              {validationResults.gemini && (
                <Alert severity={validationResults.gemini.valid ? 'success' : 'error'} sx={{ mt: 1.5, py: 0.5, fontSize: '0.8rem' }}>
                  {validationResults.gemini.message}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 2. SerpAPI */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)', borderRadius: '16px' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <SearchIcon sx={{ color: '#00F0FF' }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    2. SerpAPI (Web & Referral Crawlers)
                  </Typography>
                </Stack>
                <Chip label="100 Free/Mo" size="small" sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800 }} />
              </Stack>
              <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2, fontSize: '0.85rem' }}>
                Used for Google Jobs, LinkedIn referral discovery, and hiring manager search across S&P 500.
              </Typography>
              <Button
                size="small"
                href="https://serpapi.com"
                target="_blank"
                rel="noopener noreferrer"
                endIcon={<OpenInNewIcon />}
                sx={{ mb: 2, color: '#00F0FF', textTransform: 'none', fontWeight: 700 }}
              >
                Get Free API Key on SerpAPI.com
              </Button>
              <TextField
                fullWidth
                size="small"
                type="password"
                placeholder="c2017d7e..."
                value={keys.serpapi_key}
                onChange={(e) => handleKeyChange('serpapi_key', e.target.value)}
                sx={{ bgcolor: '#06090E', borderRadius: '8px', mb: 1.5 }}
              />
              <Button
                size="small"
                variant="outlined"
                disabled={validatingKey === 'serpapi' || !keys.serpapi_key}
                onClick={() => handleValidateIndividual('serpapi')}
                startIcon={validatingKey === 'serpapi' ? <CircularProgress size={14} /> : <BoltIcon />}
                sx={{ fontWeight: 800, textTransform: 'none' }}
              >
                {validatingKey === 'serpapi' ? 'Testing...' : 'Test SerpAPI Key'}
              </Button>
              {validationResults.serpapi && (
                <Alert severity={validationResults.serpapi.valid ? 'success' : 'error'} sx={{ mt: 1.5, py: 0.5, fontSize: '0.8rem' }}>
                  {validationResults.serpapi.message}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 3. Gmail App Password */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)', borderRadius: '16px' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <EmailIcon sx={{ color: '#FFE600' }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    3. Gmail SMTP (Outreach Dispatcher)
                  </Typography>
                </Stack>
                <Chip label="500 Emails/Day" size="small" sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 800 }} />
              </Stack>
              <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2, fontSize: '0.85rem' }}>
                Dispatches cold emails & referral inquiries via your Gmail account with 2FA App Password.
              </Typography>
              <Button
                size="small"
                href="https://myaccount.google.com/apppasswords"
                target="_blank"
                rel="noopener noreferrer"
                endIcon={<OpenInNewIcon />}
                sx={{ mb: 2, color: '#FFE600', textTransform: 'none', fontWeight: 700 }}
              >
                Generate 16-Char Google App Password
              </Button>
              <TextField
                fullWidth
                size="small"
                placeholder="your.email@gmail.com"
                value={keys.gmail_address}
                onChange={(e) => handleKeyChange('gmail_address', e.target.value)}
                sx={{ bgcolor: '#06090E', borderRadius: '8px', mb: 1.5 }}
              />
              <TextField
                fullWidth
                size="small"
                type="password"
                placeholder="16-character app password"
                value={keys.gmail_password}
                onChange={(e) => handleKeyChange('gmail_password', e.target.value)}
                sx={{ bgcolor: '#06090E', borderRadius: '8px', mb: 1.5 }}
              />
              <Button
                size="small"
                variant="outlined"
                disabled={validatingKey === 'smtp' || !keys.gmail_address || !keys.gmail_password}
                onClick={() => handleValidateIndividual('smtp')}
                startIcon={validatingKey === 'smtp' ? <CircularProgress size={14} /> : <BoltIcon />}
                sx={{ fontWeight: 800, textTransform: 'none', color: '#FFE600', borderColor: '#FFE600' }}
              >
                {validatingKey === 'smtp' ? 'Verifying SMTP...' : 'Test Gmail Connection'}
              </Button>
              {validationResults.smtp && (
                <Alert severity={validationResults.smtp.valid ? 'success' : 'error'} sx={{ mt: 1.5, py: 0.5, fontSize: '0.8rem' }}>
                  {validationResults.smtp.message}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 4. Hunter.io / Decision Maker */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)', borderRadius: '16px' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <KeyIcon sx={{ color: '#FF007A' }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    4. Hunter.io (Corporate Email Discovery)
                  </Typography>
                </Stack>
                <Chip label="25 Free/Mo" size="small" sx={{ bgcolor: 'rgba(255, 0, 122, 0.15)', color: '#FF007A', fontWeight: 800 }} />
              </Stack>
              <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2, fontSize: '0.85rem' }}>
                Verifies decision-maker email addresses and domain MX delivery patterns.
              </Typography>
              <Button
                size="small"
                href="https://hunter.io"
                target="_blank"
                rel="noopener noreferrer"
                endIcon={<OpenInNewIcon />}
                sx={{ mb: 2, color: '#FF007A', textTransform: 'none', fontWeight: 700 }}
              >
                Get Free API Key on Hunter.io
              </Button>
              <TextField
                fullWidth
                size="small"
                type="password"
                placeholder="hunter_api_key..."
                value={keys.hunter_api_key}
                onChange={(e) => handleKeyChange('hunter_api_key', e.target.value)}
                sx={{ bgcolor: '#06090E', borderRadius: '8px', mb: 1.5 }}
              />
              <Button
                size="small"
                variant="outlined"
                disabled={validatingKey === 'hunter' || !keys.hunter_api_key}
                onClick={() => handleValidateIndividual('hunter')}
                startIcon={validatingKey === 'hunter' ? <CircularProgress size={14} /> : <BoltIcon />}
                sx={{ fontWeight: 800, textTransform: 'none', color: '#FF007A', borderColor: '#FF007A' }}
              >
                {validatingKey === 'hunter' ? 'Testing...' : 'Test Hunter.io Key'}
              </Button>
              {validationResults.hunter && (
                <Alert severity={validationResults.hunter.valid ? 'success' : 'error'} sx={{ mt: 1.5, py: 0.5, fontSize: '0.8rem' }}>
                  {validationResults.hunter.message}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

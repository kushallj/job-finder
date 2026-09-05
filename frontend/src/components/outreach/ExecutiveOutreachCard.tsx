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
  Send as SendIcon,
  ContentCopy as CopyIcon,
  Business as ExecIcon,
  CheckCircle as CheckIcon,
  Email as EmailIcon,
} from '@mui/icons-material';
import {
  sprint6Api,
  type ExecutivePainPoint,
  type ExecutiveCampaignResponse,
} from '../../api/endpoints/sprint6_api';

export const ExecutiveOutreachCard: React.FC = () => {
  const [painPoints, setPainPoints] = useState<ExecutivePainPoint[]>([]);
  const [selectedPainId, setSelectedPainId] = useState('p99_latency_bottleneck');
  const [candidateName, setCandidateName] = useState('Ujjwal');
  const [targetCompany, setTargetCompany] = useState('Databricks');
  const [execName, setExecName] = useState('David (VP of Engineering)');
  const [execTitle, setExecTitle] = useState('VP of Core Infrastructure Engineering');
  const [powUrl, setPowUrl] = useState('https://github.com/ujjwal-sovereign/distributed-idempotency-engine');

  const [loading, setLoading] = useState(false);
  const [campaign, setCampaign] = useState<ExecutiveCampaignResponse | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMsg, setSnackbarMsg] = useState('');

  useEffect(() => {
    sprint6Api.getExecutivePainPoints().then((res) => {
      if (res && res.pain_points) {
        setPainPoints(res.pain_points);
        if (res.pain_points.length > 0) {
          handleGenerateCampaign(res.pain_points[0].pain_id);
        }
      }
    }).catch(console.error);
  }, []);

  const handleGenerateCampaign = async (painId = selectedPainId) => {
    if (!targetCompany.trim()) return;
    setLoading(true);
    try {
      const res = await sprint6Api.generateExecutiveCampaign({
        candidate_name: candidateName,
        target_company: targetCompany,
        executive_name: execName,
        executive_title: execTitle,
        pain_point_id: painId,
        custom_proof_of_work_url: powUrl,
      });
      setCampaign(res);
    } catch (err) {
      console.error('Failed to generate executive campaign:', err);
    } finally {
      setLoading(false);
    }
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
          border: '1.5px solid rgba(255, 230, 0, 0.3)',
          borderRadius: '16px',
          boxShadow: '0 0 30px rgba(255, 230, 0, 0.12)',
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
                    bgcolor: 'rgba(255, 230, 0, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #FFE600',
                  }}
                >
                  <ExecIcon sx={{ color: '#FFE600', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    🎯 Autonomous Executive Outbound Pitch Engine (Agent 25)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Bypass junior recruiters to pitch Engineering Directors, VPs of Engineering, and CTOs directly with high-conviction Trojan Horse drip campaigns.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip
                label="Direct VP / CTO Bypass"
                sx={{ bgcolor: 'rgba(255, 230, 0, 0.2)', color: '#FFE600', fontWeight: 900, fontSize: '0.78rem' }}
              />
              <Chip
                label="3-Stage Trojan Drip"
                sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800, fontSize: '0.75rem' }}
              />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Main Two Column Pitch Builder */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Left: Campaign Parameters */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper
            sx={{
              p: 3,
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '16px',
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#FFE600', mb: 2 }}>
              ⚙️ Executive Target Parameters
            </Typography>

            <Stack spacing={2}>
              <TextField
                size="small"
                label="Candidate Name"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                label="Target Company"
                value={targetCompany}
                onChange={(e) => setTargetCompany(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                label="Executive Name"
                value={execName}
                onChange={(e) => setExecName(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                label="Executive Title"
                value={execTitle}
                onChange={(e) => setExecTitle(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Box>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700, display: 'block', mb: 1 }}>
                  ARCHITECTURAL PAIN POINT TRIGGER:
                </Typography>
                <Stack spacing={1}>
                  {painPoints.map((p) => (
                    <Chip
                      key={p.pain_id}
                      label={p.title}
                      size="small"
                      clickable
                      onClick={() => {
                        setSelectedPainId(p.pain_id);
                        handleGenerateCampaign(p.pain_id);
                      }}
                      sx={{
                        justifyContent: 'flex-start',
                        py: 2,
                        fontWeight: selectedPainId === p.pain_id ? 900 : 600,
                        bgcolor: selectedPainId === p.pain_id ? 'rgba(255, 230, 0, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                        color: selectedPainId === p.pain_id ? '#FFE600' : '#CBD5E1',
                        border: `1px solid ${selectedPainId === p.pain_id ? '#FFE600' : 'rgba(255, 255, 255, 0.08)'}`,
                      }}
                    />
                  ))}
                </Stack>
              </Box>

              <TextField
                size="small"
                label="Proof-of-Work Micro-Repo URL"
                value={powUrl}
                onChange={(e) => setPowUrl(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Button
                variant="contained"
                disabled={loading || !targetCompany.trim()}
                onClick={() => handleGenerateCampaign(selectedPainId)}
                startIcon={loading ? <CircularProgress size={18} sx={{ color: '#06090E' }} /> : <SendIcon />}
                sx={{
                  bgcolor: '#FFE600',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  py: 1.2,
                  '&:hover': { bgcolor: '#E6CF00' },
                }}
              >
                {loading ? 'Synthesizing Drip Campaign...' : 'Generate 3-Stage Executive Drip'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* Right: 3-Stage Drip Campaign Preview */}
        <Grid size={{ xs: 12, md: 7 }}>
          {campaign ? (
            <Stack spacing={2.5}>
              {campaign.campaign_stages.map((st) => (
                <Paper
                  key={st.stage_number}
                  sx={{
                    p: 2.5,
                    bgcolor: '#0D131F',
                    border: `1.5px solid ${st.stage_number === 1 ? 'rgba(0, 240, 255, 0.3)' : st.stage_number === 2 ? 'rgba(0, 255, 163, 0.3)' : 'rgba(255, 230, 0, 0.3)'}`,
                    borderRadius: '14px',
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <EmailIcon sx={{ color: st.stage_number === 1 ? '#00F0FF' : st.stage_number === 2 ? '#00FFA3' : '#FFE600', fontSize: 18 }} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                        Stage {st.stage_number}: {st.timing}
                      </Typography>
                    </Stack>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<CopyIcon />}
                      onClick={() => copyToClipboard(`Subject: ${st.subject}

${st.body}`, `Stage ${st.stage_number} Email`)}
                      sx={{
                        color: st.stage_number === 1 ? '#00F0FF' : st.stage_number === 2 ? '#00FFA3' : '#FFE600',
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                        textTransform: 'none',
                        fontSize: '0.72rem',
                        fontWeight: 800,
                      }}
                    >
                      Copy Stage {st.stage_number}
                    </Button>
                  </Stack>

                  <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 1 }}>
                    <strong>Goal:</strong> {st.strategic_goal}
                  </Typography>

                  <Paper
                    sx={{
                      p: 1.8,
                      bgcolor: '#06090E',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      maxHeight: '160px',
                      overflowY: 'auto',
                    }}
                  >
                    <Typography component="pre" sx={{ color: '#CBD5E1', fontFamily: 'monospace', fontSize: '0.74rem', whiteSpace: 'pre-wrap', lineHeight: 1.4 }}>
                      {`Subject: ${st.subject}

${st.body}`}
                    </Typography>
                  </Paper>
                </Paper>
              ))}
            </Stack>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress size={30} sx={{ color: '#FFE600' }} />
            </Box>
          )}
        </Grid>
      </Grid>

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

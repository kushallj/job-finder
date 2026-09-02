import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Switch,
  FormControlLabel,
  Divider,
  Grid,
  Stack,
  Chip,
  Paper,
} from '@mui/material';
import {
  Send as SendIcon,
  Schedule as ScheduleIcon,
  CheckCircle as SuccessIcon,
  MarkEmailRead as RepliedIcon,
  ShieldOutlined as SafeIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useOutreach } from '../hooks/useOutreach';
import { useJobs } from '../hooks/useJobs';
import { useStats } from '../hooks/useStats';
import { useLocation } from 'react-router-dom';
import { formatRelativeTime } from '../utils/formatters';

const OUTREACH_TEMPLATES = [
  {
    id: 'em-direct',
    label: 'Engineering Manager — High Fit Intro',
    text: "Hi {name},\n\nI noticed you're leading engineering for {role} at {company}. I have deep experience in {skills} and recently built high-throughput distributed systems that cut processing latency by 40%.\n\nI'd love to learn more about your team's upcoming roadmap. Would you be open to a brief 10-minute chat this week?\n\nBest regards,\nCandidate",
  },
  {
    id: 'founder-pitch',
    label: 'Founder / Executive Direct Pitch',
    text: "Hi {name},\n\nI've been following {company}'s growth and love your product direction. Given my background scaling cloud architecture, I believe I can immediately help accelerate your Q4 goals.\n\nAre you free for a quick coffee or Zoom intro?\n\nCheers,\nCandidate",
  },
  {
    id: 'follow-up',
    label: 'Value-Add Follow-up (Day 3)',
    text: "Hi {name},\n\nFollowing up on my previous note regarding the {role} opportunity. I put together a quick 1-pager outlining how I would approach the core architecture challenge.\n\nHappy to share if you'd find it helpful!\n\nBest,\nCandidate",
  },
];

export const Outreach: React.FC = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactName, setContactName] = useState('');
  const [templateId, setTemplateId] = useState('em-direct');
  const [messageBody, setMessageBody] = useState(OUTREACH_TEMPLATES[0].text);

  const location = useLocation();
  const { sendOutreach, isSendingOutreach, outreachResult } = useOutreach();
  const { pendingOutreach } = useJobs();
  const { stats: outreachStats, recentOutreach, isLoadingStats, refetchStats } = useStats();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const emailParam = params.get('email');
    const nameParam = params.get('name');
    const jobIdParam = params.get('jobId');

    if (emailParam || jobIdParam) {
      if (emailParam) setContactEmail(emailParam);
      if (nameParam) setContactName(nameParam);
      if (jobIdParam) setSelectedJobId(Number(jobIdParam));
      setDialogOpen(true);
    }
  }, [location.search]);

  const handleOpenDialog = () => {
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
  };

  const handleTemplateChange = (tplId: string) => {
    setTemplateId(tplId);
    const tpl = OUTREACH_TEMPLATES.find((t) => t.id === tplId);
    if (tpl) {
      setMessageBody(tpl.text);
    }
  };

  const handleSend = () => {
    if (!selectedJobId || !contactEmail) return;

    sendOutreach({
      job_id: Number(selectedJobId),
      contact_email: contactEmail,
      contact_name: contactName || 'Hiring Team',
      send_immediately: !dryRun,
    });
  };

  const jobs = pendingOutreach?.jobs || [];

  return (
    <Box sx={{ maxWidth: 1440, mx: 'auto', width: '100%', color: '#F8FAFC' }}>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, mb: 3.5, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h3" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.03em', mb: 0.5, textTransform: 'uppercase' }}>
            Autonomous Outreach Engine
          </Typography>
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>
            Personalized, rate-limited email campaigns dispatched to engineering leaders & recruiters.
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5}>
          <Button
            variant="outlined"
            onClick={() => refetchStats()}
            disabled={isLoadingStats}
            startIcon={<RefreshIcon />}
            sx={{ borderRadius: '12px', fontWeight: 800 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            color="primary"
            startIcon={<SendIcon />}
            onClick={handleOpenDialog}
            sx={{ fontWeight: 900 }}
          >
            Compose Outreach
          </Button>
        </Stack>
      </Box>

      {/* Metrics Row */}
      <Grid container spacing={2.5} sx={{ mb: 3.5 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '20px', border: '1.5px solid rgba(0, 240, 255, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.25, borderRadius: '14px', bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', border: '1px solid rgba(0, 240, 255, 0.4)', boxShadow: '0 0 15px rgba(0, 240, 255, 0.25)' }}>
                <SendIcon />
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
                  Emails Sent
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 900, color: '#F8FAFC', mt: 0.25 }}>
                  {isLoadingStats ? '-' : outreachStats?.emails_sent || 0}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '20px', border: '1.5px solid rgba(0, 255, 163, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.25, borderRadius: '14px', bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', border: '1px solid rgba(0, 255, 163, 0.4)', boxShadow: '0 0 15px rgba(0, 255, 163, 0.25)' }}>
                <RepliedIcon />
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
                  Replies Received
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 900, color: '#F8FAFC', mt: 0.25 }}>
                  {isLoadingStats ? '-' : (outreachStats as any)?.replies_count || 0}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '20px', border: '1.5px solid rgba(255, 230, 0, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.25, borderRadius: '14px', bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', border: '1px solid rgba(255, 230, 0, 0.4)', boxShadow: '0 0 15px rgba(255, 230, 0, 0.25)' }}>
                <ScheduleIcon />
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
                  Follow-ups Dispatched
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 900, color: '#F8FAFC', mt: 0.25 }}>
                  {isLoadingStats ? '-' : outreachStats?.follow_ups_sent || 0}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '20px', border: '1.5px solid rgba(121, 40, 202, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.25, borderRadius: '14px', bgcolor: 'rgba(121, 40, 202, 0.15)', color: '#A855F7', border: '1px solid rgba(121, 40, 202, 0.4)', boxShadow: '0 0 15px rgba(121, 40, 202, 0.25)' }}>
                <SuccessIcon />
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
                  Success Rate
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 900, color: '#F8FAFC', mt: 0.25 }}>
                  {isLoadingStats ? '-' : `${outreachStats?.success_rate || 0}%`}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>
      </Grid>

      {/* Safety Mode Banner */}
      <Card sx={{ mb: 3.5, border: '1.5px solid rgba(0, 255, 163, 0.3)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
        <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Box sx={{ p: 1.2, borderRadius: '12px', bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', border: '1px solid rgba(0, 255, 163, 0.4)' }}>
              <SafeIcon />
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2" fontWeight={900} color="#00FFA3" textTransform="uppercase">
                Anti-Spam & Max 2 Outreach/Company Protection Active
              </Typography>
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                Smart throttling ensures you never exceed email provider limits. Dry-run mode allows full previewing before live transmission.
              </Typography>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* Recent Outreach History Feed */}
      <Card sx={{ border: '1.5px solid rgba(0, 240, 255, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Typography variant="h6" fontWeight={900} color="#F8FAFC" sx={{ mb: 2 }} textTransform="uppercase">
            Campaign Transmission Log
          </Typography>
          <Divider sx={{ mb: 2, borderColor: 'rgba(0, 240, 255, 0.15)' }} />

          {isLoadingStats ? (
            <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress sx={{ color: '#00FFA3' }} />
            </Box>
          ) : recentOutreach && recentOutreach.length > 0 ? (
            <Stack spacing={1.5}>
              {recentOutreach.map((item) => (
                <Paper
                  key={item.id}
                  variant="outlined"
                  sx={{
                    p: 2,
                    borderRadius: '16px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    bgcolor: '#080C12',
                    border: '1px solid rgba(0, 240, 255, 0.2)',
                    transition: 'all 0.2s ease',
                    '&:hover': { borderColor: '#00F0FF', boxShadow: '0 0 15px rgba(0, 240, 255, 0.2)' },
                  }}
                >
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Box sx={{ p: 1, borderRadius: '10px', bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF' }}>
                      <SendIcon fontSize="small" />
                    </Box>
                    <Box>
                      <Typography variant="subtitle2" fontWeight={800} color="#F8FAFC">
                        {item.contact_email}
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                        Transmission ID: #{item.id} · {formatRelativeTime(item.sent_at)}
                      </Typography>
                    </Box>
                  </Stack>

                  <Chip
                    label={item.status}
                    size="small"
                    color={item.status === 'sent' ? 'success' : item.status === 'replied' ? 'primary' : 'default'}
                    sx={{ fontWeight: 800, textTransform: 'capitalize' }}
                  />
                </Paper>
              ))}
            </Stack>
          ) : (
            <Box sx={{ py: 6, textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                No active outreach logs recorded yet.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Compose Outreach Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth PaperProps={{ sx: { bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.3)', borderRadius: '24px' } }}>
        <DialogTitle sx={{ fontWeight: 900, color: '#F8FAFC', textTransform: 'uppercase' }}>
          Compose AI-Targeted Outreach
        </DialogTitle>
        <DialogContent dividers sx={{ borderColor: 'rgba(0, 240, 255, 0.15)' }}>
          {outreachResult && (
            <Alert
              severity={outreachResult.status === 'success' ? 'success' : 'error'}
              sx={{ mb: 3, borderRadius: '12px', bgcolor: outreachResult.status === 'success' ? 'rgba(0, 255, 163, 0.15)' : 'rgba(255, 0, 122, 0.15)', color: outreachResult.status === 'success' ? '#00FFA3' : '#FF007A' }}
            >
              {outreachResult.message || (outreachResult.status === 'success' ? 'Outreach dispatched successfully!' : 'Transmission failed')}
            </Alert>
          )}

          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: '#94A3B8' }}>Associated Target Job</InputLabel>
              <Select
                value={selectedJobId}
                label="Associated Target Job"
                onChange={(e) => setSelectedJobId(e.target.value as number)}
              >
                {jobs.map((job) => (
                  <MenuItem key={job.id} value={job.id}>
                    {job.title} — {job.company || 'Unknown'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Contact Name"
                  placeholder="e.g. Sarah Connor"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  fullWidth
                  size="small"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Contact Email"
                  placeholder="e.g. sarah@company.com"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  fullWidth
                  size="small"
                />
              </Grid>
            </Grid>

            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: '#94A3B8' }}>Message Template</InputLabel>
              <Select
                value={templateId}
                label="Message Template"
                onChange={(e) => handleTemplateChange(e.target.value)}
              >
                {OUTREACH_TEMPLATES.map((tpl) => (
                  <MenuItem key={tpl.id} value={tpl.id}>
                    {tpl.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Email Body Content"
              multiline
              rows={6}
              value={messageBody}
              onChange={(e) => setMessageBody(e.target.value)}
              fullWidth
            />

            <FormControlLabel
              control={
                <Switch
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                  color="warning"
                />
              }
              label={
                <Typography variant="body2" sx={{ color: '#FFE600', fontWeight: 800 }}>
                  Dry-Run Mode (Simulation only — will not actually send SMTP email)
                </Typography>
              }
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5, borderColor: 'rgba(0, 240, 255, 0.15)' }}>
          <Button onClick={handleCloseDialog} sx={{ color: '#94A3B8', fontWeight: 800 }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={handleSend}
            disabled={isSendingOutreach || !selectedJobId || !contactEmail}
            startIcon={isSendingOutreach ? <CircularProgress size={16} /> : <SendIcon />}
            sx={{ fontWeight: 900 }}
          >
            {isSendingOutreach ? 'Transmitting...' : dryRun ? 'Simulate Send' : 'Send Campaign Email'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Outreach;

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
  alpha,
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

  const handleSendOutreach = () => {
    if (selectedJobId && contactEmail && contactName) {
      sendOutreach({
        job_id: Number(selectedJobId),
        contact_email: contactEmail,
        contact_name: contactName,
        send_immediately: !dryRun,
      });
    }
  };

  const jobs = pendingOutreach?.jobs || [];

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>
            Outreach & Campaign Engine
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Multi-stage autonomous email outreach, automated follow-up scheduler, and reply detector.
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<SendIcon />}
            onClick={handleOpenDialog}
            sx={{ fontWeight: 700 }}
          >
            Compose Outreach
          </Button>
          <Button
            variant="outlined"
            onClick={() => refetchStats()}
            disabled={isLoadingStats}
            startIcon={<RefreshIcon />}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* KPI Stats Grid */}
      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.25, borderRadius: '10px', bgcolor: alpha('#4F46E5', 0.1), color: '#4F46E5' }}>
                <SendIcon />
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
                  Total Sent
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 800, color: '#0F172A', mt: 0.25 }}>
                  {isLoadingStats ? '-' : outreachStats?.emails_sent || 0}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.25, borderRadius: '10px', bgcolor: alpha('#10B981', 0.1), color: '#10B981' }}>
                <RepliedIcon />
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
                  Replies Received
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 800, color: '#0F172A', mt: 0.25 }}>
                  {isLoadingStats ? '-' : Math.round(((outreachStats?.success_rate || 0) * (outreachStats?.emails_sent || 0)) / 100)}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.25, borderRadius: '10px', bgcolor: alpha('#F59E0B', 0.1), color: '#F59E0B' }}>
                <ScheduleIcon />
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
                  Auto Follow-ups
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 800, color: '#0F172A', mt: 0.25 }}>
                  {isLoadingStats ? '-' : outreachStats?.follow_ups_sent || 0}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.25, borderRadius: '10px', bgcolor: alpha('#7C3AED', 0.1), color: '#7C3AED' }}>
                <SuccessIcon />
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
                  Success Rate
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 800, color: '#0F172A', mt: 0.25 }}>
                  {isLoadingStats ? '-' : `${outreachStats?.success_rate || 0}%`}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>
      </Grid>

      {/* Safety Mode Banner */}
      <Card sx={{ mb: 4, border: '1px solid #E2E8F0', bgcolor: '#F8FAFC' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Box sx={{ p: 1, borderRadius: '8px', bgcolor: alpha('#10B981', 0.1), color: '#10B981' }}>
              <SafeIcon />
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2" fontWeight={800} color="#0F172A">
                Anti-Spam & Rate Limiting Active
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Smart throttling ensures you never exceed email provider limits. Dry-run mode allows full previewing before live transmission.
              </Typography>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* Recent Outreach History Feed */}
      <Card sx={{ border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Typography variant="h6" fontWeight={800} color="#0F172A" sx={{ mb: 2 }}>
            Campaign Transmission Log
          </Typography>
          <Divider sx={{ mb: 2 }} />

          {isLoadingStats ? (
            <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : recentOutreach && recentOutreach.length > 0 ? (
            <Stack spacing={1.5}>
              {recentOutreach.map((item) => (
                <Paper
                  key={item.id}
                  variant="outlined"
                  sx={{
                    p: 2,
                    borderRadius: '12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    bgcolor: '#FFFFFF',
                  }}
                >
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Box sx={{ p: 1, borderRadius: '8px', bgcolor: alpha('#4F46E5', 0.1), color: '#4F46E5' }}>
                      <SendIcon fontSize="small" />
                    </Box>
                    <Box>
                      <Typography variant="subtitle2" fontWeight={700} color="#0F172A">
                        {item.contact_email}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Transmission ID: #{item.id} · {formatRelativeTime(item.sent_at)}
                      </Typography>
                    </Box>
                  </Stack>

                  <Chip
                    label={item.status}
                    size="small"
                    color={item.status === 'sent' ? 'success' : item.status === 'replied' ? 'primary' : 'default'}
                    sx={{ fontWeight: 700, textTransform: 'capitalize' }}
                  />
                </Paper>
              ))}
            </Stack>
          ) : (
            <Box sx={{ py: 6, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                No active outreach logs recorded yet.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Compose Outreach Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 800, color: '#0F172A' }}>
          Compose AI-Targeted Outreach
        </DialogTitle>
        <DialogContent dividers>
          {outreachResult && (
            <Alert
              severity={outreachResult.status === 'success' ? 'success' : 'error'}
              sx={{ mb: 3 }}
            >
              {outreachResult.message || (outreachResult.status === 'success' ? 'Outreach dispatched successfully!' : 'Transmission failed')}
            </Alert>
          )}

          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Associated Target Job</InputLabel>
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
              <InputLabel>Message Strategy Template</InputLabel>
              <Select
                value={templateId}
                label="Message Strategy Template"
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
              label="Email Body Preview"
              multiline
              rows={7}
              value={messageBody}
              onChange={(e) => setMessageBody(e.target.value)}
              fullWidth
            />

            <FormControlLabel
              control={<Switch checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />}
              label="Dry-Run Mode (Test without sending real email)"
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={handleCloseDialog} color="inherit">
            Cancel
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={handleSendOutreach}
            disabled={isSendingOutreach || !selectedJobId || !contactEmail || !contactName}
            startIcon={isSendingOutreach ? <CircularProgress size={16} /> : <SendIcon />}
            sx={{ fontWeight: 700 }}
          >
            {isSendingOutreach ? 'Transmitting...' : dryRun ? 'Execute Dry-Run' : 'Send Outreach Email'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Outreach;

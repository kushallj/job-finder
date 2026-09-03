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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  LinearProgress,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Email as EmailIcon,
  QuestionAnswer as ReplyIcon,
  Event as InterviewIcon,
  EmojiEvents as OfferIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import { profileApi, type FunnelMetricsData } from '../../api/endpoints/profile';

export const FunnelConversionTracker: React.FC = () => {
  const [metrics, setMetrics] = useState<FunnelMetricsData | null>(null);
  const [openLogModal, setOpenLogModal] = useState(false);
  const [logForm, setLogForm] = useState({
    event_type: 'reply_received',
    company: '',
    role_title: '',
    contact_name: '',
    notes: '',
  });

  const fetchMetrics = () => {
    profileApi.getFunnelMetrics()
      .then((data) => setMetrics(data))
      .catch(() => {});
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const handleLogEvent = async () => {
    if (!logForm.company.trim()) return;
    try {
      await profileApi.logFunnelEvent(logForm);
      setOpenLogModal(false);
      setLogForm({ event_type: 'reply_received', company: '', role_title: '', contact_name: '', notes: '' });
      fetchMetrics();
    } catch (err) {
      console.error('Failed to log event:', err);
    }
  };

  const totalSent = metrics?.total_sent || 1;
  const replies = metrics?.replies || 0;
  const interviews = metrics?.interviews || 0;
  const offers = metrics?.offers || 0;

  const replyRate = metrics?.reply_rate_pct || 0;
  const interviewRate = metrics?.interview_rate_pct || 0;

  return (
    <Card
      sx={{
        mb: 3.5,
        borderRadius: '20px',
        bgcolor: '#0D131F',
        border: '1.5px solid rgba(0, 240, 255, 0.25)',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)',
      }}
    >
      <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2.5 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Box
              sx={{
                width: 36,
                height: 36,
                borderRadius: '10px',
                bgcolor: 'rgba(0, 255, 163, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid #00FFA3',
              }}
            >
              <TrendingUpIcon sx={{ color: '#00FFA3' }} />
            </Box>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                Account-Based Outreach Conversion Funnel
              </Typography>
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                Outcome tracking vs industry baseline (Mass blast: 2–6% vs Our ABM target: 15–30%)
              </Typography>
            </Box>
          </Stack>

          <Button
            size="small"
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => setOpenLogModal(true)}
            sx={{
              borderColor: '#00FFA3',
              color: '#00FFA3',
              fontWeight: 800,
              textTransform: 'none',
              borderRadius: '8px',
              '&:hover': { bgcolor: 'rgba(0, 255, 163, 0.1)', borderColor: '#00F0FF' },
            }}
          >
            Log Reply / Interview
          </Button>
        </Stack>

        {/* Funnel Metrics Grid */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 6, sm: 3 }}>
            <Box sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                <EmailIcon sx={{ color: '#00F0FF', fontSize: 18 }} />
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700 }}>
                  OUTREACH SENT
                </Typography>
              </Stack>
              <Typography variant="h4" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                {totalSent}
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748B' }}>
                5-Stage Verified
              </Typography>
            </Box>
          </Grid>

          <Grid size={{ xs: 6, sm: 3 }}>
            <Box sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(0, 255, 163, 0.25)' }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                <ReplyIcon sx={{ color: '#00FFA3', fontSize: 18 }} />
                <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 800 }}>
                  REPLIES RECEIVED
                </Typography>
              </Stack>
              <Typography variant="h4" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                {replies}
              </Typography>
              <Chip label={`${replyRate}% Reply Rate`} size="small" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, height: 20, fontSize: '0.7rem' }} />
            </Box>
          </Grid>

          <Grid size={{ xs: 6, sm: 3 }}>
            <Box sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255, 230, 0, 0.25)' }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                <InterviewIcon sx={{ color: '#FFE600', fontSize: 18 }} />
                <Typography variant="caption" sx={{ color: '#FFE600', fontWeight: 800 }}>
                  INTERVIEWS
                </Typography>
              </Stack>
              <Typography variant="h4" sx={{ fontWeight: 900, color: '#FFE600' }}>
                {interviews}
              </Typography>
              <Chip label={`${interviewRate}% Conv.`} size="small" sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 800, height: 20, fontSize: '0.7rem' }} />
            </Box>
          </Grid>

          <Grid size={{ xs: 6, sm: 3 }}>
            <Box sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255, 0, 122, 0.25)' }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                <OfferIcon sx={{ color: '#FF007A', fontSize: 18 }} />
                <Typography variant="caption" sx={{ color: '#FF007A', fontWeight: 800 }}>
                  OFFERS / CLOSES
                </Typography>
              </Stack>
              <Typography variant="h4" sx={{ fontWeight: 900, color: '#FF007A' }}>
                {offers}
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748B' }}>
                Final Stage
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {/* Progress Bar Visualizer */}
        <Box sx={{ bgcolor: '#06090E', p: 2, borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700 }}>
              Funnel Efficiency (Reply Target: 15%+)
            </Typography>
            <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 900 }}>
              {replyRate}% Actual
            </Typography>
          </Stack>
          <LinearProgress
            variant="determinate"
            value={Math.min(replyRate * 3.3, 100)}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: 'rgba(255,255,255,0.1)',
              '& .MuiLinearProgress-bar': {
                background: 'linear-gradient(90deg, #00FFA3, #00F0FF, #FFE600)',
              },
            }}
          />
        </Box>

        {/* Modal for logging replies/interviews */}
        <Dialog open={openLogModal} onClose={() => setOpenLogModal(false)} PaperProps={{ sx: { bgcolor: '#0D131F', border: '1px solid #00FFA3', borderRadius: '16px', color: '#FFF' } }}>
          <DialogTitle sx={{ fontWeight: 900, color: '#00FFA3' }}>Log Outreach Outcome Event</DialogTitle>
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: '#94A3B8' }}>Event Type</InputLabel>
              <Select
                value={logForm.event_type}
                label="Event Type"
                onChange={(e) => setLogForm({ ...logForm, event_type: e.target.value })}
                sx={{ bgcolor: '#06090E', color: '#FFF' }}
              >
                <MenuItem value="reply_received">💬 Recruiter / Hiring Manager Replied</MenuItem>
                <MenuItem value="interview_scheduled">📅 Interview Scheduled</MenuItem>
                <MenuItem value="offer_received">🎉 Offer Received</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Company Name"
              placeholder="e.g. Palantir"
              size="small"
              value={logForm.company}
              onChange={(e) => setLogForm({ ...logForm, company: e.target.value })}
              sx={{ bgcolor: '#06090E' }}
            />
            <TextField
              label="Role Title (Optional)"
              placeholder="e.g. Senior Backend Engineer"
              size="small"
              value={logForm.role_title}
              onChange={(e) => setLogForm({ ...logForm, role_title: e.target.value })}
              sx={{ bgcolor: '#06090E' }}
            />
            <TextField
              label="Contact / Recruiter Name (Optional)"
              size="small"
              value={logForm.contact_name}
              onChange={(e) => setLogForm({ ...logForm, contact_name: e.target.value })}
              sx={{ bgcolor: '#06090E' }}
            />
          </DialogContent>
          <DialogActions sx={{ p: 2.5, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            <Button onClick={() => setOpenLogModal(false)} sx={{ color: '#94A3B8', textTransform: 'none' }}>
              Cancel
            </Button>
            <Button variant="contained" onClick={handleLogEvent} sx={{ bgcolor: '#00FFA3', color: '#06090E', fontWeight: 900, textTransform: 'none' }}>
              Save Outcome Event
            </Button>
          </DialogActions>
        </Dialog>
      </CardContent>
    </Card>
  );
};

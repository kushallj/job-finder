import React, { useState } from 'react';
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
} from '@mui/material';
import {
  Send as SendIcon,
  Schedule as ScheduleIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import { useOutreach } from '../hooks/useOutreach';
import { useJobs } from '../hooks/useJobs';
import { useStats } from '../hooks/useStats';

export const Outreach: React.FC = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactName, setContactName] = useState('');
  
  const { sendOutreach, isSendingOutreach, outreachResult } = useOutreach();
  const { pendingOutreach } = useJobs();
  const { stats: outreachStats, isLoadingStats } = useStats();

  const handleOpenDialog = () => {
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedJobId('');
    setContactEmail('');
    setContactName('');
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
    <Box>
      {/* Header Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Outreach
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Send personalized outreach emails to hiring managers
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Box sx={{ display: 'flex', gap: 3, mb: 4, flexWrap: 'wrap' }}>
        <Card sx={{ flex: 1, minWidth: 200 }}>
          <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'primary.light' }}>
              <SendIcon color="primary" />
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">Total Outreach</Typography>
              <Typography variant="h5" fontWeight={600}>
                {isLoadingStats ? '-' : outreachStats?.total_outreach_attempts || 0}
              </Typography>
            </Box>
          </CardContent>
        </Card>
        
        <Card sx={{ flex: 1, minWidth: 200 }}>
          <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'success.light' }}>
              <SuccessIcon color="success" />
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">Emails Sent</Typography>
              <Typography variant="h5" fontWeight={600}>
                {isLoadingStats ? '-' : outreachStats?.emails_sent || 0}
              </Typography>
            </Box>
          </CardContent>
        </Card>

        <Card sx={{ flex: 1, minWidth: 200 }}>
          <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'warning.light' }}>
              <ScheduleIcon color="warning" />
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">Follow-ups</Typography>
              <Typography variant="h5" fontWeight={600}>
                {isLoadingStats ? '-' : outreachStats?.follow_ups_sent || 0}
              </Typography>
            </Box>
          </CardContent>
        </Card>

        <Card sx={{ flex: 1, minWidth: 200 }}>
          <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'success.light' }}>
              <SuccessIcon color="success" />
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">Success Rate</Typography>
              <Typography variant="h5" fontWeight={600}>
                {isLoadingStats ? '-' : `${outreachStats?.success_rate || 0}%`}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Action Section */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Send Outreach Email
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Select a job and contact to send a personalized outreach email
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Select Job</InputLabel>
              <Select
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value as number | '')}
                label="Select Job"
              >
                <MenuItem value=""><em>Choose a job...</em></MenuItem>
                {jobs.map((job) => (
                  <MenuItem key={job.id} value={job.id}>
                    {job.title} at {job.company}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <Button
              variant="contained"
              startIcon={isSendingOutreach ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
              onClick={handleOpenDialog}
              disabled={!selectedJobId}
            >
              {isSendingOutreach ? 'Sending...' : 'Compose & Send'}
            </Button>
          </Box>

          {outreachResult && (
            <Alert 
              severity={outreachResult.email_sent ? 'success' : 'error'} 
              sx={{ mt: 2 }}
            >
              {outreachResult.email_sent 
                ? `Email sent successfully! (ID: ${outreachResult.outreach_id})`
                : 'Failed to send email. Please check your configuration.'
              }
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Template Info */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Available Templates
          </Typography>
          <Divider sx={{ my: 2 }} />
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
              <Typography variant="subtitle2" fontWeight={600}>HR Outreach</Typography>
              <Typography variant="body2" color="text.secondary">
                General outreach template for HR managers and recruiters
              </Typography>
            </Box>
            
            <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
              <Typography variant="subtitle2" fontWeight={600}>Engineering Manager</Typography>
              <Typography variant="body2" color="text.secondary">
                Technical outreach template for engineering managers and tech leads
              </Typography>
            </Box>
            
            <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
              <Typography variant="subtitle2" fontWeight={600}>Follow-up</Typography>
              <Typography variant="body2" color="text.secondary">
                Follow-up template for pending applications
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Compose Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Compose Outreach Email</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              label="Contact Name"
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              fullWidth
              required
            />
            <TextField
              label="Contact Email"
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              fullWidth
              required
            />
            <FormControlLabel
              control={
                <Switch
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                />
              }
              label="Dry Run (Don't actually send)"
            />
            <Typography variant="caption" color="text.secondary">
              {dryRun 
                ? 'Preview the email without actually sending it'
                : 'This will send a real email to the contact'
              }
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button 
            onClick={handleSendOutreach} 
            variant="contained"
            disabled={!contactName || !contactEmail || isSendingOutreach}
          >
            {isSendingOutreach ? <CircularProgress size={20} /> : dryRun ? 'Preview' : 'Send'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Outreach;


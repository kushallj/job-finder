import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  LinearProgress,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  AutoAwesome as AIIcon,
  Business as CompanyIcon,
  Email as EmailIcon,
  Launch as LaunchIcon,
  People as PeopleIcon,
  Description as ResumeIcon,
  Send as SendIcon,
  TrackChanges as TrackIcon,
  CheckCircle as CheckIcon,
  Verified as ProofIcon,
} from '@mui/icons-material';
import { opportunitiesApi } from '../api/endpoints/opportunities';
import { lifecycleApi } from '../api/endpoints/lifecycle';
import type { OpportunityBrief as OpportunityBriefData } from '../api/types';

const lifecycleStages = ['saved', 'ready', 'applied', 'interview', 'offer', 'negotiation', 'accepted'];
const stageLabel: Record<string, string> = {
  saved: 'Saved',
  ready: 'Application ready',
  applied: 'Applied',
  interview: 'Interview',
  offer: 'Offer',
  negotiation: 'Negotiation',
  accepted: 'Accepted',
  rejected: 'Closed',
};

const OpportunityBrief: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const id = Number(jobId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const briefQuery = useQuery({
    queryKey: ['opportunity-brief', id],
    queryFn: () => opportunitiesApi.brief(id),
    enabled: Number.isFinite(id),
    staleTime: 15000,
  });

  const [working, setWorking] = React.useState(false);
  const [proofOpen, setProofOpen] = React.useState(false);
  const [proof, setProof] = React.useState({ confirmation_number: '', proof_note: '', proof_url: '' });
  const [toast, setToast] = React.useState('');
  const [confirmAccept, setConfirmAccept] = React.useState(false);
  const [advanceStage, setAdvanceStage] = React.useState<string | null>(null);

  const brief = briefQuery.data as OpportunityBriefData | undefined;

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['opportunity-brief', id] });
    await queryClient.invalidateQueries({ queryKey: ['action-queue'] });
    await queryClient.invalidateQueries({ queryKey: ['applications'] });
    await queryClient.invalidateQueries({ queryKey: ['jobs'] });
  };

  const handlePrimary = async () => {
    if (!brief) return;
    if (brief.next_action.key === 'accept_offer') {
      setConfirmAccept(true);
      return;
    }
    setWorking(true);
    try {
      const result = await opportunitiesApi.doNext(id);
      await refresh();
      if (result.action === 'apply' && result.open_url) {
        window.open(result.open_url, '_blank', 'noopener,noreferrer');
      } else if (result.open_url) {
        navigate(result.open_url);
      }
      setToast(result.message || 'Action executed successfully.');
    } catch {
      setToast('Could not complete this action automatically.');
    } finally {
      setWorking(false);
    }
  };

  const advance = async (status: string) => {
    if (!brief?.application_id) return;
    setWorking(true);
    try {
      await lifecycleApi.transition(brief.application_id, status as any);
      setAdvanceStage(null);
      await refresh();
      setToast(`Opportunity moved to ${stageLabel[status] || status}.`);
    } finally {
      setWorking(false);
    }
  };

  const acceptOffer = async () => {
    if (!brief?.application_id) return;
    setWorking(true);
    try {
      await lifecycleApi.transition(brief.application_id, 'accepted');
      setConfirmAccept(false);
      await refresh();
      setToast('Offer accepted. Opportunity closed as a win.');
    } finally {
      setWorking(false);
    }
  };

  const logProof = async () => {
    if (!brief?.application_id) return;
    setWorking(true);
    try {
      await opportunitiesApi.logProof(brief.application_id, proof);
      setProofOpen(false);
      setProof({ confirmation_number: '', proof_note: '', proof_url: '' });
      await refresh();
      setToast('Application proof recorded and marked as applied.');
    } finally {
      setWorking(false);
    }
  };

  if (briefQuery.isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (briefQuery.isError || !brief) {
    return <Alert severity="error">Could not load this opportunity.</Alert>;
  }

  const score = Math.round(brief.fit_score);
  const action = brief.next_action.key;
  const openListing = () => brief.job.url && window.open(brief.job.url, '_blank', 'noopener,noreferrer');

  return (
    <Box sx={{ pb: 6 }}>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/jobs')} sx={{ mb: 2 }}>
        Back to opportunities
      </Button>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: { xs: 2.5, md: 4 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={3}>
            <Box>
              <Chip icon={<AIIcon />} label="Opportunity Brief" color="secondary" size="small" sx={{ mb: 1.5 }} />
              <Typography variant="h4" fontWeight={800}>{brief.job.title}</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
                <Chip icon={<CompanyIcon />} label={brief.job.company || 'Unknown company'} size="small" variant="outlined" />
                <Chip label={brief.job.location || 'Remote'} size="small" variant="outlined" />
                <Chip label={brief.job.source || 'Other'} size="small" variant="outlined" />
                {brief.application_status && (
                  <Chip label={stageLabel[brief.application_status] || brief.application_status} size="small" color="primary" />
                )}
              </Stack>
            </Box>
            <Stack direction={{ xs: 'column', sm: 'row', md: 'column' }} spacing={1.25} sx={{ minWidth: { md: 250 } }}>
              <Button
                variant="contained"
                size="large"
                startIcon={action === 'outreach' || action === 'followup' ? <SendIcon /> : <TrackIcon />}
                onClick={handlePrimary}
                disabled={working}
                fullWidth
              >
                {working ? 'Processing…' : brief.next_action.label}
              </Button>
              {brief.application_status === 'ready' && (
                <Button variant="outlined" color="success" startIcon={<ProofIcon />} onClick={() => setProofOpen(true)} fullWidth>
                  Log proof
                </Button>
              )}
              {brief.job.url && (
                <Button variant="outlined" startIcon={<LaunchIcon />} onClick={openListing} fullWidth>
                  Open listing
                </Button>
              )}
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ py: 2 }}>
          <Typography variant="caption" color="text.secondary" fontWeight={700}>
            CAREER LIFECYCLE
          </Typography>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
            {lifecycleStages.map((stage, index) => {
              const current = brief.application_status || 'saved';
              const currentIndex = lifecycleStages.indexOf(current);
              const active = index <= currentIndex && current !== 'rejected';
              return (
                <Chip
                  key={stage}
                  label={stageLabel[stage]}
                  size="small"
                  color={active ? 'primary' : 'default'}
                  variant={active ? 'filled' : 'outlined'}
                />
              );
            })}
          </Stack>
          {brief.application_id && ['applied', 'interview', 'offer', 'negotiation'].includes(brief.application_status || '') && (
            <Stack direction="row" alignItems="center" justifyContent="space-between" gap={2} sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Update the stage when the real-world milestone happens.
              </Typography>
              {brief.application_status === 'applied' && (
                <Button size="small" variant="outlined" onClick={() => setAdvanceStage('interview')}>
                  Mark interview
                </Button>
              )}
              {brief.application_status === 'interview' && (
                <Button size="small" variant="outlined" onClick={() => setAdvanceStage('offer')}>
                  Mark offer
                </Button>
              )}
              {brief.application_status === 'offer' && (
                <Button size="small" variant="outlined" onClick={() => setAdvanceStage('negotiation')}>
                  Start negotiation
                </Button>
              )}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Fit assessment</Typography>
              <Stack direction="row" alignItems="center" spacing={2} sx={{ my: 2 }}>
                <Typography variant="h2" fontWeight={800}>{score}</Typography>
                <Box>
                  <Typography fontWeight={700}>{brief.fit_label}</Typography>
                  <Typography variant="body2" color="text.secondary">Indexed resume + job data</Typography>
                </Box>
              </Stack>
              <LinearProgress variant="determinate" value={score} sx={{ height: 9, borderRadius: 5, mb: 2 }} />
              <List dense disablePadding>
                {brief.fit_reasons.map((reason) => (
                  <ListItem key={reason} disableGutters>
                    <ListItemText primary={reason} />
                  </ListItem>
                ))}
              </List>
              {brief.resume.missing_keywords.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2">Resume gaps</Typography>
                  <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                    {brief.resume.missing_keywords.map((k) => (
                      <Chip key={k} label={k} size="small" variant="outlined" />
                    ))}
                  </Stack>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={1}>
                <CompanyIcon color="primary" />
                <Typography variant="h6" fontWeight={700}>Company signals</Typography>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Signals from your indexed data — not external claims.
              </Typography>
              <Grid container spacing={1.5}>
                {brief.company_signals.map((signal) => (
                  <Grid key={signal.label} size={{ xs: 12, sm: 6 }}>
                    <Card variant="outlined">
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <Stack direction="row" justifyContent="space-between" gap={1}>
                          <Box>
                            <Typography variant="subtitle2">{signal.label}</Typography>
                            <Typography fontWeight={700}>{signal.value}</Typography>
                          </Box>
                          <Chip
                            label={signal.strength}
                            size="small"
                            color={signal.strength === 'strong' ? 'success' : signal.strength === 'weak' ? 'warning' : 'default'}
                          />
                        </Stack>
                        <Typography variant="caption" color="text.secondary">{signal.detail}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                <PeopleIcon color="primary" />
                <Typography variant="h6" fontWeight={700}>People who can open the door</Typography>
              </Stack>
              {brief.people.length === 0 ? (
                <Alert severity="info">No contacts are indexed for this company yet. Use Contact Intelligence next.</Alert>
              ) : (
                <List disablePadding>
                  {brief.people.map((person) => (
                    <ListItem key={person.id} sx={{ px: 0 }}>
                      <ListItemAvatar>
                        <Avatar>{person.name.split(' ').map((x) => x[0]).slice(0, 2).join('')}</Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={person.name}
                        secondary={
                          <>
                            {person.title || person.relationship_hint}
                            {person.email ? ` • ${person.email}` : ''}
                          </>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              )}
              {brief.people.length > 0 && (
                <Button startIcon={<PeopleIcon />} onClick={() => navigate(`/contacts?company=${encodeURIComponent(brief.job.company || '')}`)}>
                  View company contacts
                </Button>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={1}>
                <ResumeIcon color="primary" />
                <Typography variant="h6" fontWeight={700}>Resume strategy</Typography>
              </Stack>
              <Divider sx={{ my: 1.5 }} />
              <Typography variant="subtitle2">Master resume</Typography>
              <Typography variant="body2" color="text.secondary">
                {brief.resume.master_resume_label || 'No routed resume found'}
              </Typography>
              <Typography variant="subtitle2" sx={{ mt: 1.5 }}>Tailored version</Typography>
              <Typography variant="body2" color={brief.resume.has_tailored_resume ? 'text.primary' : 'text.secondary'}>
                {brief.resume.has_tailored_resume ? brief.resume.tailored_resume_label : 'Not generated for this opportunity yet'}
              </Typography>
              {brief.resume.cover_letter_preview && (
                <Box sx={{ mt: 1.5, p: 1.5, borderRadius: 1, bgcolor: 'background.default' }}>
                  <Typography variant="caption" color="text.secondary">Cover letter preview</Typography>
                  <Typography variant="body2">{brief.resume.cover_letter_preview}</Typography>
                </Box>
              )}
              <Button sx={{ mt: 2 }} variant="outlined" onClick={() => navigate('/settings')}>
                {brief.resume.has_tailored_resume ? 'Review resume setup' : 'Prepare resume'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}>
                <Box>
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <EmailIcon color="primary" />
                    <Typography variant="h6" fontWeight={700}>Outreach strategy</Typography>
                  </Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {brief.outreach.recommended_message}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1}>
                  <Chip label={`${brief.outreach.total} threads`} />
                  <Chip
                    label={`${brief.outreach.replied} replies`}
                    color={brief.outreach.replied ? 'success' : 'default'}
                  />
                </Stack>
              </Stack>
              <Grid container spacing={1.5} sx={{ mt: 1 }}>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Typography variant="caption" color="text.secondary">Sent</Typography>
                  <Typography variant="h6">{brief.outreach.sent}</Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Typography variant="caption" color="text.secondary">Pending</Typography>
                  <Typography variant="h6">{brief.outreach.pending}</Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Typography variant="caption" color="text.secondary">Latest</Typography>
                  <Typography variant="h6">{brief.outreach.latest_status || 'None'}</Typography>
                </Grid>
              </Grid>
              <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
                <Button variant="contained" startIcon={<SendIcon />} onClick={() => navigate(`/outreach?jobId=${id}`)}>
                  {brief.outreach.total ? 'Open outreach' : 'Start outreach'}
                </Button>
                <Button variant="outlined" onClick={() => navigate('/tracker')}>
                  Open tracker
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Alert
            icon={<CheckIcon />}
            severity={brief.next_action.priority === 'high' ? 'warning' : 'info'}
            sx={{ alignItems: 'flex-start' }}
          >
            <Typography fontWeight={800}>{brief.next_action.label}</Typography>
            {brief.next_action.reason}
          </Alert>
        </Grid>
      </Grid>

      <Dialog open={Boolean(advanceStage)} onClose={() => !working && setAdvanceStage(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Update opportunity stage?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            This records a real-world milestone in your tracker. It does not send an email or contact the employer.
          </Typography>
          {advanceStage && (
            <Typography fontWeight={700} sx={{ mt: 2 }}>
              Move to {stageLabel[advanceStage] || advanceStage}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAdvanceStage(null)} disabled={working}>Cancel</Button>
          <Button variant="contained" onClick={() => advanceStage && void advance(advanceStage)} disabled={working}>
            Confirm stage
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={confirmAccept} onClose={() => !working && setConfirmAccept(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Accept this offer?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            This will mark the opportunity as accepted and close it as a win. Only continue after you have made the real-world decision.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmAccept(false)} disabled={working}>Cancel</Button>
          <Button variant="contained" onClick={() => void acceptOffer()} disabled={working}>
            {working ? 'Saving…' : 'Confirm acceptance'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={proofOpen} onClose={() => !working && setProofOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Record application proof</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Record confirmation details or a proof URL after submitting on the employer site.
          </Typography>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Confirmation number"
              fullWidth
              value={proof.confirmation_number}
              onChange={(e) => setProof({ ...proof, confirmation_number: e.target.value })}
            />
            <TextField
              label="Submission proof URL"
              fullWidth
              value={proof.proof_url}
              onChange={(e) => setProof({ ...proof, proof_url: e.target.value })}
            />
            <TextField
              label="Notes"
              fullWidth
              multiline
              rows={3}
              value={proof.proof_note}
              onChange={(e) => setProof({ ...proof, proof_note: e.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setProofOpen(false)} disabled={working}>Cancel</Button>
          <Button variant="contained" onClick={() => void logProof()} disabled={working}>
            Save proof
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(toast)}
        autoHideDuration={4000}
        onClose={() => setToast('')}
        message={toast}
      />
    </Box>
  );
};

export default OpportunityBrief;

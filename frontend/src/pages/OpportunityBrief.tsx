import React, { useState } from 'react';
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
  ListItemIcon,
  ListItemText,
  Snackbar,
  Stack,
  TextField,
  Typography,
  Paper,
  alpha,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  AutoAwesome as AIIcon,
  Business as CompanyIcon,
  Launch as LaunchIcon,
  People as PeopleIcon,
  Description as ResumeIcon,
  Send as SendIcon,
  TrackChanges as TrackIcon,
  CheckCircle as CheckIcon,
  Verified as ProofIcon,
  LocationOn as LocationIcon,
  ContentCopy as CopyIcon,
  Check as CopiedIcon,
  Search as SearchIcon,
  PersonAdd as PersonAddIcon,
  Share as ReferralIcon,
} from '@mui/icons-material';
import { opportunitiesApi } from '../api/endpoints/opportunities';
import { lifecycleApi } from '../api/endpoints/lifecycle';
import { referralsApi } from '../api/endpoints/referrals';
import type { OpportunityBrief as OpportunityBriefData, ReferralProfile } from '../api/types';

const lifecycleStages = ['saved', 'ready', 'applied', 'interview', 'offer', 'negotiation', 'accepted'];
const stageLabel: Record<string, string> = {
  saved: 'Saved',
  ready: 'Application Ready',
  applied: 'Applied',
  interview: 'Interviewing',
  offer: 'Offer Received',
  negotiation: 'Negotiation',
  accepted: 'Accepted (Win)',
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

  const [working, setWorking] = useState(false);
  const [proofOpen, setProofOpen] = useState(false);
  const [proof, setProof] = useState({ confirmation_number: '', proof_note: '', proof_url: '' });
  const [toast, setToast] = useState('');
  const [confirmAccept, setConfirmAccept] = useState(false);
  const [advanceStage, setAdvanceStage] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Referral search state
  const [referralDialogOpen, setReferralDialogOpen] = useState(false);
  const [referralLoading, setReferralLoading] = useState(false);
  const [referralProfiles, setReferralProfiles] = useState<ReferralProfile[]>([]);
  const [selectedReferral, setSelectedReferral] = useState<ReferralProfile | null>(null);
  const [generatedNote, setGeneratedNote] = useState<any>(null);
  const [generatingNote, setGeneratingNote] = useState(false);

  const brief = briefQuery.data as OpportunityBriefData | undefined;

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['opportunity-brief', id] });
    await queryClient.invalidateQueries({ queryKey: ['action-queue'] });
    await queryClient.invalidateQueries({ queryKey: ['applications'] });
    await queryClient.invalidateQueries({ queryKey: ['jobs'] });
    await queryClient.invalidateQueries({ queryKey: ['contacts'] });
  };

  const copyKeyword = (k: string) => {
    navigator.clipboard.writeText(k);
    setCopiedKey(k);
    setTimeout(() => setCopiedKey(null), 2000);
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
      setToast('Offer accepted. Opportunity recorded as a career win! 🎉');
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

  const handleOpenReferralSearch = async () => {
    if (!brief?.job.company) return;
    setReferralDialogOpen(true);
    setReferralLoading(true);
    try {
      const res = await referralsApi.search(brief.job.company, 8);
      setReferralProfiles(res.profiles || []);
    } catch {
      setToast('Could not fetch LinkedIn referrals for this company.');
    } finally {
      setReferralLoading(false);
    }
  };

  const handleGenerateReferralNote = async (profile: ReferralProfile) => {
    if (!brief) return;
    setSelectedReferral(profile);
    setGeneratingNote(true);
    try {
      const res = await referralsApi.generateNote({
        full_name: profile.full_name,
        company: profile.company || brief.job.company || '',
        title: profile.title,
        headline: profile.headline,
        job_title: brief.job.title,
        job_link: brief.job.url || '',
        max_length: 200,
      });
      setGeneratedNote(res);
    } catch {
      setToast('Failed to generate referral note.');
    } finally {
      setGeneratingNote(false);
    }
  };

  const handleSyncReferralToCRM = async (profile: ReferralProfile) => {
    try {
      await referralsApi.sync([profile]);
      await refresh();
      setToast(`Saved ${profile.full_name} to Contacts CRM!`);
    } catch {
      setToast('Failed to sync contact to CRM.');
    }
  };

  if (briefQuery.isLoading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', py: 12, gap: 2 }}>
        <CircularProgress />
        <Typography variant="body2" color="text.secondary">Synthesizing executive opportunity brief...</Typography>
      </Box>
    );
  }

  if (briefQuery.isError || !brief) {
    return (
      <Alert severity="error" sx={{ my: 4 }}>
        Could not load brief for opportunity #{id}.
      </Alert>
    );
  }

  const score = Math.round(brief.fit_score);
  const action = brief.next_action.key;
  const openListing = () => brief.job.url && window.open(brief.job.url, '_blank', 'noopener,noreferrer');

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto', pb: 8 }}>
      {/* Back Button */}
      <Button
        startIcon={<ArrowBackIcon fontSize="small" />}
        onClick={() => navigate('/jobs')}
        sx={{ mb: 2.5, color: '#64748B', fontWeight: 600 }}
      >
        Back to Opportunities
      </Button>

      {/* Hero Header Card */}
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0', boxShadow: '0 4px 20px -4px rgba(0,0,0,0.05)' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} gap={3}>
            <Box sx={{ flex: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <Chip
                  icon={<AIIcon sx={{ fontSize: '14px !important', color: '#4F46E5 !important' }} />}
                  label="Executive Decision Brief"
                  size="small"
                  sx={{ bgcolor: alpha('#4F46E5', 0.1), color: '#4F46E5', fontWeight: 700 }}
                />
                {brief.application_status && (
                  <Chip
                    label={stageLabel[brief.application_status] || brief.application_status}
                    size="small"
                    color="primary"
                    sx={{ fontWeight: 700 }}
                  />
                )}
              </Stack>

              <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em', mb: 1 }}>
                {brief.job.title}
              </Typography>

              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Chip
                  icon={<CompanyIcon fontSize="small" />}
                  label={brief.job.company || 'Unknown Company'}
                  size="small"
                  sx={{ bgcolor: '#F1F5F9', fontWeight: 600 }}
                />
                <Chip
                  icon={<LocationIcon fontSize="small" />}
                  label={brief.job.location || 'Remote'}
                  size="small"
                  variant="outlined"
                />
                <Chip
                  label={brief.job.source || 'Scraped Role'}
                  size="small"
                  variant="outlined"
                  sx={{ color: '#64748B' }}
                />
              </Stack>
            </Box>

            {/* Quick Action Button Deck */}
            <Stack direction={{ xs: 'column', sm: 'row', md: 'column' }} spacing={1.5} sx={{ minWidth: { md: 240 }, width: { xs: '100%', md: 'auto' } }}>
              <Button
                variant="contained"
                size="large"
                color="primary"
                startIcon={action === 'outreach' || action === 'followup' ? <SendIcon /> : <TrackIcon />}
                onClick={handlePrimary}
                disabled={working}
                fullWidth
                sx={{ fontWeight: 700 }}
              >
                {working ? 'Processing…' : brief.next_action.label}
              </Button>

              <Button
                variant="outlined"
                color="secondary"
                startIcon={<ReferralIcon />}
                onClick={handleOpenReferralSearch}
                fullWidth
                sx={{ fontWeight: 700 }}
              >
                Find LinkedIn Referrals
              </Button>

              {brief.application_status === 'ready' && (
                <Button
                  variant="outlined"
                  color="success"
                  startIcon={<ProofIcon />}
                  onClick={() => setProofOpen(true)}
                  fullWidth
                  sx={{ fontWeight: 700 }}
                >
                  Log Submission Proof
                </Button>
              )}

              {brief.job.url && (
                <Button
                  variant="outlined"
                  startIcon={<LaunchIcon />}
                  onClick={openListing}
                  fullWidth
                >
                  Open Original Listing
                </Button>
              )}
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Career Lifecycle Progression Stepper */}
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} gap={1.5} sx={{ mb: 1.5 }}>
            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Career Lifecycle Stage Progression
            </Typography>
            {brief.application_id && ['applied', 'interview', 'offer', 'negotiation'].includes(brief.application_status || '') && (
              <Stack direction="row" spacing={1}>
                {brief.application_status === 'applied' && (
                  <Button size="small" variant="outlined" color="warning" onClick={() => setAdvanceStage('interview')}>
                    Mark Interview Scheduled
                  </Button>
                )}
                {brief.application_status === 'interview' && (
                  <Button size="small" variant="outlined" color="success" onClick={() => setAdvanceStage('offer')}>
                    Mark Offer Received
                  </Button>
                )}
                {brief.application_status === 'offer' && (
                  <Button size="small" variant="outlined" color="secondary" onClick={() => setAdvanceStage('negotiation')}>
                    Enter Negotiation
                  </Button>
                )}
              </Stack>
            )}
          </Stack>

          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            {lifecycleStages.map((stage, index) => {
              const current = brief.application_status || 'saved';
              const currentIndex = lifecycleStages.indexOf(current);
              const isPastOrCurrent = index <= currentIndex && current !== 'rejected';
              const isCurrent = stage === current;

              return (
                <Chip
                  key={stage}
                  label={stageLabel[stage]}
                  size="small"
                  color={isCurrent ? 'primary' : isPastOrCurrent ? 'success' : 'default'}
                  variant={isPastOrCurrent ? 'filled' : 'outlined'}
                  sx={{ fontWeight: 700 }}
                />
              );
            })}
          </Stack>
        </CardContent>
      </Card>

      {/* 4-Quadrant Intelligence Deck */}
      <Grid container spacing={3}>
        {/* Fit & Gap Assessment */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ height: '100%', border: '1px solid #E2E8F0' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
                AI Match Assessment
              </Typography>

              <Stack direction="row" alignItems="center" spacing={2} sx={{ my: 2 }}>
                <Box
                  sx={{
                    width: 64,
                    height: 64,
                    borderRadius: '16px',
                    bgcolor: score >= 80 ? alpha('#10B981', 0.1) : alpha('#4F46E5', 0.1),
                    color: score >= 80 ? '#059669' : '#4F46E5',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 800,
                    fontSize: '1.5rem',
                  }}
                >
                  {score}%
                </Box>
                <Box>
                  <Typography variant="subtitle1" fontWeight={800} color="#0F172A">
                    {brief.fit_label}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Resume vs Job description match
                  </Typography>
                </Box>
              </Stack>

              <LinearProgress
                variant="determinate"
                value={score}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  mb: 2,
                  bgcolor: '#E2E8F0',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: score >= 80 ? '#10B981' : '#4F46E5',
                  },
                }}
              />

              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#0F172A', mb: 1 }}>
                Match Strengths:
              </Typography>
              <List dense disablePadding>
                {brief.fit_reasons.map((reason) => (
                  <ListItem key={reason} disableGutters sx={{ py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 24, color: '#10B981' }}>
                      <CheckIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText
                      primary={reason}
                      primaryTypographyProps={{ fontSize: '0.825rem', color: '#334155' }}
                    />
                  </ListItem>
                ))}
              </List>

              {brief.resume.missing_keywords.length > 0 && (
                <Box sx={{ mt: 3, pt: 2, borderTop: '1px solid #F1F5F9' }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>
                    Missing Keywords (Click to copy)
                  </Typography>
                  <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                    {brief.resume.missing_keywords.map((k) => (
                      <Chip
                        key={k}
                        label={k}
                        size="small"
                        icon={copiedKey === k ? <CopiedIcon fontSize="small" /> : <CopyIcon fontSize="small" />}
                        onClick={() => copyKeyword(k)}
                        sx={{
                          cursor: 'pointer',
                          bgcolor: copiedKey === k ? alpha('#10B981', 0.1) : '#F1F5F9',
                          color: copiedKey === k ? '#059669' : '#334155',
                          fontWeight: 600,
                        }}
                      />
                    ))}
                  </Stack>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Company Signals & Metadata */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Card sx={{ height: '100%', border: '1px solid #E2E8F0' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
                <CompanyIcon sx={{ color: '#4F46E5' }} />
                <Typography variant="h6" fontWeight={800} color="#0F172A">
                  Company Hiring Signals & Intelligence
                </Typography>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
                Corroborated signals extracted from your indexed history and provider sync.
              </Typography>

              <Grid container spacing={2}>
                {brief.company_signals.map((signal) => (
                  <Grid key={signal.label} size={{ xs: 12, sm: 6 }}>
                    <Paper variant="outlined" sx={{ p: 2, borderRadius: '12px', bgcolor: '#F8FAFC' }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
                        <Box>
                          <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>
                            {signal.label}
                          </Typography>
                          <Typography variant="subtitle1" fontWeight={800} color="#0F172A">
                            {signal.value}
                          </Typography>
                        </Box>
                        <Chip
                          label={signal.strength}
                          size="small"
                          color={signal.strength === 'strong' ? 'success' : signal.strength === 'weak' ? 'warning' : 'default'}
                          sx={{ textTransform: 'capitalize', fontWeight: 700, fontSize: '0.7rem' }}
                        />
                      </Stack>
                      <Typography variant="caption" sx={{ color: '#64748B', mt: 0.5, display: 'block' }}>
                        {signal.detail}
                      </Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Decision-Makers & Door Openers */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', border: '1px solid #E2E8F0' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Stack direction="row" alignItems="center" spacing={1.5}>
                  <PeopleIcon sx={{ color: '#10B981' }} />
                  <Typography variant="h6" fontWeight={800} color="#0F172A">
                    Hiring Decision-Makers
                  </Typography>
                </Stack>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<SearchIcon fontSize="small" />}
                  onClick={handleOpenReferralSearch}
                  sx={{ fontWeight: 700 }}
                >
                  Find Referrals
                </Button>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Identified contacts and LinkedIn referrals who can open doors for this role.
              </Typography>

              {brief.people.length === 0 ? (
                <Alert severity="info" sx={{ borderRadius: '10px' }}>
                  No contacts indexed yet for {brief.job.company || 'this company'}. Click "Find Referrals" to search alumni and employees.
                </Alert>
              ) : (
                <Stack spacing={1.5}>
                  {brief.people.map((person) => (
                    <Paper key={person.id} variant="outlined" sx={{ p: 1.5, borderRadius: '12px', bgcolor: '#F8FAFC' }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Stack direction="row" spacing={1.5} alignItems="center">
                          <Avatar sx={{ bgcolor: alpha('#10B981', 0.1), color: '#059669', fontWeight: 700 }}>
                            {person.name.split(' ').map((n) => n[0]).slice(0, 2).join('')}
                          </Avatar>
                          <Box>
                            <Typography variant="subtitle2" fontWeight={700} color="#0F172A">
                              {person.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {person.title || person.relationship_hint}
                              {person.email ? ` • ${person.email}` : ''}
                            </Typography>
                          </Box>
                        </Stack>
                        <Stack direction="row" spacing={1}>
                          {person.email && (
                            <Button
                              size="small"
                              variant="contained"
                              startIcon={<SendIcon fontSize="small" />}
                              onClick={() => navigate(`/outreach?email=${encodeURIComponent(person.email || '')}&name=${encodeURIComponent(person.name)}&jobId=${id}`)}
                              sx={{ fontWeight: 700 }}
                            >
                              Outreach
                            </Button>
                          )}
                        </Stack>
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Resume & Strategy Deck */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', border: '1px solid #E2E8F0' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
                <ResumeIcon sx={{ color: '#7C3AED' }} />
                <Typography variant="h6" fontWeight={800} color="#0F172A">
                  Resume & Outreach Strategy
                </Typography>
              </Stack>
              <Divider sx={{ my: 1.5 }} />

              <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
                Routed Master Resume:
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 700, color: '#0F172A', mb: 1.5 }}>
                {brief.resume.master_resume_label || 'data/resume.pdf'}
              </Typography>

              <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
                Recommended Cold Outreach Hook:
              </Typography>
              <Paper variant="outlined" sx={{ p: 1.5, borderRadius: '10px', bgcolor: '#F8FAFC', mt: 0.5 }}>
                <Typography variant="body2" sx={{ color: '#334155', fontStyle: 'italic' }}>
                  "{brief.outreach.recommended_message || 'Highlight your experience scaling distributed backend systems and mention recent production milestones.'}"
                </Typography>
              </Paper>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* LinkedIn Referral Search & Generator Dialog */}
      <Dialog open={referralDialogOpen} onClose={() => setReferralDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 800, color: '#0F172A' }}>
          LinkedIn Employee Referrals — {brief.job.company}
        </DialogTitle>
        <DialogContent dividers>
          {referralLoading ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 6, gap: 2 }}>
              <CircularProgress />
              <Typography variant="body2" color="text.secondary">Searching LinkedIn network & alumni database...</Typography>
            </Box>
          ) : referralProfiles.length === 0 ? (
            <Alert severity="info">No employee profiles found in the local cache/API for this company.</Alert>
          ) : (
            <Stack spacing={2}>
              {referralProfiles.map((p, idx) => (
                <Paper key={idx} variant="outlined" sx={{ p: 2, borderRadius: '12px', bgcolor: '#FFFFFF' }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1.5}>
                    <Stack direction="row" spacing={1.5} alignItems="center">
                      <Avatar sx={{ bgcolor: alpha('#4F46E5', 0.1), color: '#4F46E5', fontWeight: 700 }}>
                        {p.full_name.split(' ').map((n) => n[0]).slice(0, 2).join('')}
                      </Avatar>
                      <Box>
                        <Typography variant="subtitle2" fontWeight={800} color="#0F172A">
                          {p.full_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {p.title || p.headline || 'Engineer'} · {p.company}
                        </Typography>
                      </Box>
                    </Stack>

                    <Stack direction="row" spacing={1}>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<PersonAddIcon fontSize="small" />}
                        onClick={() => handleSyncReferralToCRM(p)}
                      >
                        Save to CRM
                      </Button>
                      <Button
                        size="small"
                        variant="contained"
                        startIcon={<AIIcon fontSize="small" />}
                        onClick={() => handleGenerateReferralNote(p)}
                        disabled={generatingNote}
                        sx={{ fontWeight: 700 }}
                      >
                        {generatingNote && selectedReferral?.full_name === p.full_name ? 'Generating…' : 'Generate Note'}
                      </Button>
                    </Stack>
                  </Stack>
                </Paper>
              ))}
            </Stack>
          )}

          {generatedNote && selectedReferral && (
            <Box sx={{ mt: 3, p: 2.5, borderRadius: '12px', bgcolor: '#F8FAFC', border: '1px solid #E2E8F0' }}>
              <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
                AI Referral Note for {selectedReferral.full_name} ({generatedNote.char_count} / 200 chars)
              </Typography>
              <TextField
                multiline
                rows={3}
                fullWidth
                value={generatedNote.connection_note}
                sx={{ mb: 2, bgcolor: '#FFFFFF' }}
              />
              <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<CopyIcon fontSize="small" />}
                  onClick={() => {
                    navigator.clipboard.writeText(generatedNote.connection_note);
                    setToast('Connection note copied to clipboard!');
                  }}
                  sx={{ fontWeight: 700 }}
                >
                  Copy Note
                </Button>
              </Stack>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setReferralDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Stage Transition Confirmation Dialog */}
      <Dialog open={Boolean(advanceStage)} onClose={() => !working && setAdvanceStage(null)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 800, color: '#0F172A' }}>Update Opportunity Stage?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            This records a real-world career milestone in your CRM tracker.
          </Typography>
          {advanceStage && (
            <Typography variant="h6" fontWeight={800} color="#4F46E5" sx={{ mt: 2 }}>
              Move to: {stageLabel[advanceStage] || advanceStage}
            </Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setAdvanceStage(null)} disabled={working}>Cancel</Button>
          <Button variant="contained" color="primary" onClick={() => advanceStage && void advance(advanceStage)} disabled={working} sx={{ fontWeight: 700 }}>
            Confirm Stage Advance
          </Button>
        </DialogActions>
      </Dialog>

      {/* Accept Offer Modal */}
      <Dialog open={confirmAccept} onClose={() => !working && setConfirmAccept(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 800, color: '#0F172A' }}>Accept Offer & Close as Win? 🎉</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            This records this position as accepted and successfully completes your campaign for this role.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setConfirmAccept(false)} disabled={working}>Cancel</Button>
          <Button variant="contained" color="success" onClick={() => void acceptOffer()} disabled={working} sx={{ fontWeight: 700 }}>
            {working ? 'Saving…' : 'Confirm Win'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Proof Submission Modal */}
      <Dialog open={proofOpen} onClose={() => !working && setProofOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 800, color: '#0F172A' }}>Record Application Submission Proof</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Save confirmation details after submitting your application on the employer website.
          </Typography>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Confirmation ID / Number"
              fullWidth
              size="small"
              value={proof.confirmation_number}
              onChange={(e) => setProof({ ...proof, confirmation_number: e.target.value })}
            />
            <TextField
              label="Submission Proof URL (Screenshot / Email link)"
              fullWidth
              size="small"
              value={proof.proof_url}
              onChange={(e) => setProof({ ...proof, proof_url: e.target.value })}
            />
            <TextField
              label="Notes & Next Steps"
              fullWidth
              multiline
              rows={3}
              value={proof.proof_note}
              onChange={(e) => setProof({ ...proof, proof_note: e.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setProofOpen(false)} disabled={working}>Cancel</Button>
          <Button variant="contained" color="primary" onClick={() => void logProof()} disabled={working} sx={{ fontWeight: 700 }}>
            Save & Advance to Applied
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

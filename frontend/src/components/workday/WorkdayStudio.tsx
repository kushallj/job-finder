import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  LinearProgress,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Slider,
  CircularProgress,
  Alert,
  Tooltip,
  IconButton,
  Divider,
  Tabs,
  Tab,
  TextField,
  FormControlLabel,
  Switch,
} from '@mui/material';
import {
  RocketLaunch as RocketIcon,
  CheckCircle as CheckCircleIcon,
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon,
  Bolt as BoltIcon,
  Speed as SpeedIcon,
  Layers as LayersIcon,
  Person as PersonIcon,
  Business as BusinessIcon,
  AssignmentTurnedIn as SubmittedIcon,
  Edit as EditIcon,
  Psychology as BrainIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Search as SearchIcon,
} from '@mui/icons-material';

import {
  workdayApi,
  type WorkdayStatusResponse,
  type WorkdayCandidateProfileData,
  type WorkdayBatchApplyResponse,
  type AnswerItem,
} from '../../api/endpoints/workday';

export const WorkdayStudio: React.FC = () => {
  const [activeTab, setActiveTab] = useState<number>(0);
  const [statusData, setStatusData] = useState<WorkdayStatusResponse | null>(null);
  const [profileData, setProfileData] = useState<WorkdayCandidateProfileData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [batchLoading, setBatchLoading] = useState<boolean>(false);
  const [savingProfile, setSavingProfile] = useState<boolean>(false);
  const [batchTarget, setBatchTarget] = useState<number>(25);
  const [minFitScore, setMinFitScore] = useState<number>(60);
  const [batchResult, setBatchResult] = useState<WorkdayBatchApplyResponse | null>(null);
  const [profileSuccessMsg, setProfileSuccessMsg] = useState<string | null>(null);

  const [answers, setAnswers] = useState<AnswerItem[]>([]);
  const [answersLoading, setAnswersLoading] = useState<boolean>(false);
  const [answersQuery, setAnswersQuery] = useState<string>('');
  const [newQuestion, setNewQuestion] = useState<string>('');
  const [newAnswer, setNewAnswer] = useState<string>('');
  const [newCategory, setNewCategory] = useState<string>('');
  const [showAddAnswer, setShowAddAnswer] = useState<boolean>(false);
  const [savingAnswer, setSavingAnswer] = useState<boolean>(false);
  const [answerSuccessMsg, setAnswerSuccessMsg] = useState<string | null>(null);

  const fetchTelemetry = async () => {
    try {
      setLoading(true);
      const res = await workdayApi.getStatus();
      setStatusData(res);
      setProfileData(res.profile);
    } catch (e) {
      console.error('Failed to load Workday status:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnswers = async (queryText?: string) => {
    try {
      setAnswersLoading(true);
      const res = await workdayApi.getAnswers({ query: queryText !== undefined ? queryText : answersQuery || undefined });
      setAnswers(res.answers || []);
    } catch (e) {
      console.error('Failed to load Answer Bank answers:', e);
    } finally {
      setAnswersLoading(false);
    }
  };

  const handleSaveNewAnswer = async () => {
    if (!newQuestion.trim() || !newAnswer.trim()) return;
    try {
      setSavingAnswer(true);
      await workdayApi.saveAnswer({
        question: newQuestion.trim(),
        answer: newAnswer.trim(),
        category: newCategory.trim() || undefined,
        source: 'user_provided',
      });
      setAnswerSuccessMsg('Answer saved into Cognitive Answer Bank!');
      setNewQuestion('');
      setNewAnswer('');
      setNewCategory('');
      setShowAddAnswer(false);
      await fetchAnswers();
      setTimeout(() => setAnswerSuccessMsg(null), 3000);
    } catch (e) {
      console.error('Failed to save answer:', e);
    } finally {
      setSavingAnswer(false);
    }
  };

  const handleDeleteAnswer = async (id: number) => {
    try {
      await workdayApi.deleteAnswer(id);
      setAnswers((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      console.error('Failed to delete answer:', e);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    fetchAnswers();
  }, []);


  const handleBatchApply = async () => {
    try {
      setBatchLoading(true);
      setBatchResult(null);
      const res = await workdayApi.batchApply(batchTarget, minFitScore);
      setBatchResult(res);
      await fetchTelemetry();
    } catch (e: any) {
      console.error('Batch apply failed:', e);
      setBatchResult({
        status: 'quota_reached',
        account_email: statusData?.profile.account_email || 'canaby007@gmail.com',
        message: e?.response?.data?.detail || e.message || 'Batch apply failed',
      });
    } finally {
      setBatchLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    if (!profileData) return;
    try {
      setSavingProfile(true);
      setProfileSuccessMsg(null);
      const res = await workdayApi.updateProfile(profileData);
      setProfileData(res.profile);
      setProfileSuccessMsg('Candidate Workday profile & form autofill preferences updated!');
      setTimeout(() => setProfileSuccessMsg(null), 4000);
    } catch (e) {
      console.error('Failed to update profile:', e);
    } finally {
      setSavingProfile(false);
    }
  };

  if (loading && !statusData) {
    return (
      <Box sx={{ p: 4, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
        <CircularProgress sx={{ color: '#FFE600', mb: 2 }} />
        <Typography variant="body1" sx={{ color: '#94A3B8' }}>
          Connecting to Workday Autopilot Engine & Candidate Vault...
        </Typography>
      </Box>
    );
  }

  const config = statusData?.config;
  const profile = profileData || statusData?.profile;
  const submissions = statusData?.recent_submissions || [];
  const accounts = statusData?.accounts || [];

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1400, margin: '0 auto' }}>
      {/* ── Header ── */}
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} spacing={2} sx={{ mb: 4 }}>
        <Box>
          <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 0.5 }}>
            <Box sx={{ width: 36, height: 36, borderRadius: '8px', background: 'linear-gradient(135deg, #FFE600 0%, #F59E0B 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <LayersIcon sx={{ color: '#0F172A', fontSize: 22 }} />
            </Box>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#F8FAFC', letterSpacing: '-0.02em' }}>
              Workday Autopilot Studio
            </Typography>
            <Chip
              label="AUTONOMOUS PROFILE & ATS TAILOR"
              size="small"
              sx={{
                background: 'rgba(255, 230, 0, 0.15)',
                color: '#FFE600',
                fontWeight: 700,
                fontSize: '0.7rem',
                border: '1px solid rgba(255, 230, 0, 0.3)',
              }}
            />
          </Stack>
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>
            Multi-Tenant Account Provisioning • Dynamic Keyword Tailoring • Multi-Step Workday Application Automation
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchTelemetry}
            sx={{
              borderColor: 'rgba(255, 255, 255, 0.15)',
              color: '#F8FAFC',
              '&:hover': { borderColor: '#FFE600', background: 'rgba(255, 230, 0, 0.05)' },
            }}
          >
            Refresh
          </Button>
        </Stack>
      </Stack>

      {/* ── Top Metrics Overview ── */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 3, backdropFilter: 'blur(12px)' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700, textTransform: 'uppercase' }}>
                  Candidate Account
                </Typography>
                <PersonIcon sx={{ color: '#FFE600', fontSize: 20 }} />
              </Stack>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#F8FAFC', mb: 0.5, wordBreak: 'break-all' }}>
                {profile?.account_email}
              </Typography>
              <Typography variant="caption" sx={{ color: '#4ADE80', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <CheckCircleIcon sx={{ fontSize: 13 }} /> Master Profile Active ({profile?.first_name} {profile?.last_name})
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 3, backdropFilter: 'blur(12px)' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700, textTransform: 'uppercase' }}>
                  Daily Submissions Target
                </Typography>
                <SpeedIcon sx={{ color: '#38BDF8', fontSize: 20 }} />
              </Stack>
              <Typography variant="h4" sx={{ fontWeight: 800, color: '#F8FAFC', mb: 0.5 }}>
                {config?.daily_used} <span style={{ fontSize: '1rem', color: '#64748B', fontWeight: 500 }}>/ {config?.daily_limit}</span>
              </Typography>
              <LinearProgress
                variant="determinate"
                value={config?.daily_percent || 0}
                sx={{
                  height: 6,
                  borderRadius: 3,
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  '& .MuiLinearProgress-bar': { background: 'linear-gradient(90deg, #38BDF8 0%, #FFE600 100%)' },
                  mb: 0.5,
                }}
              />
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                {config?.daily_remaining} remaining today ({config?.daily_percent}%)
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 3, backdropFilter: 'blur(12px)' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700, textTransform: 'uppercase' }}>
                  Tenant Accounts Vault
                </Typography>
                <BusinessIcon sx={{ color: '#A855F7', fontSize: 20 }} />
              </Stack>
              <Typography variant="h4" sx={{ fontWeight: 800, color: '#F8FAFC', mb: 0.5 }}>
                {accounts.length}
              </Typography>
              <Typography variant="caption" sx={{ color: '#A855F7' }}>
                Provisioned Employer Portals
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 3, backdropFilter: 'blur(12px)' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700, textTransform: 'uppercase' }}>
                  Total Lifetime Submissions
                </Typography>
                <SubmittedIcon sx={{ color: '#00FFA3', fontSize: 20 }} />
              </Stack>
              <Typography variant="h4" sx={{ fontWeight: 800, color: '#00FFA3', mb: 0.5 }}>
                {config?.total_submitted}
              </Typography>
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                100% Verifiable Proof Receipts
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* ── Navigation Tabs ── */}
      <Tabs
        value={activeTab}
        onChange={(_, val) => setActiveTab(val)}
        sx={{
          mb: 3,
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          '& .MuiTab-root': { color: '#94A3B8', fontWeight: 600, textTransform: 'none', fontSize: '0.95rem' },
          '& .Mui-selected': { color: '#FFE600' },
          '& .MuiTabs-indicator': { backgroundColor: '#FFE600' },
        }}
      >
        <Tab icon={<RocketIcon sx={{ fontSize: 18, mr: 1 }} />} iconPosition="start" label="Autopilot Dispatch & Submissions" />
        <Tab icon={<PersonIcon sx={{ fontSize: 18, mr: 1 }} />} iconPosition="start" label="Candidate Profile & EEO Settings" />
        <Tab icon={<BusinessIcon sx={{ fontSize: 18, mr: 1 }} />} iconPosition="start" label={`Tenant Accounts Vault (${accounts.length})`} />
        <Tab icon={<BrainIcon sx={{ fontSize: 18, mr: 1 }} />} iconPosition="start" label={`Cognitive Answer Bank (${answers.length})`} />
      </Tabs>

      {/* ── TAB 0: Autopilot Dispatch & Submissions ── */}
      {activeTab === 0 && (
        <Stack spacing={4}>
          {/* Batch Launcher Card */}
          <Card sx={{ background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)', border: '1px solid rgba(255, 230, 0, 0.25)', borderRadius: 3, p: 3 }}>
            <Grid container spacing={3} alignItems="center">
              <Grid size={{ xs: 12, md: 7 }}>
                <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
                  <BoltIcon sx={{ color: '#FFE600' }} />
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#F8FAFC' }}>
                    Launch Autonomous Workday Batch Apply
                  </Typography>
                </Stack>
                <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2 }}>
                  Executes the 5-step Workday candidate journey for eligible jobs: auto-provisions tenant accounts, customizes keywords, builds ReportLab PDF resumes, resolves screening Q&A via AnswerBank, and submits with cryptographic proof.
                </Typography>

                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 600 }}>
                      Target Jobs Count: {batchTarget}
                    </Typography>
                    <Slider
                      value={batchTarget}
                      onChange={(_, v) => setBatchTarget(v as number)}
                      min={5}
                      max={100}
                      step={5}
                      marks
                      valueLabelDisplay="auto"
                      sx={{ color: '#FFE600' }}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 600 }}>
                      Minimum ATS Fit Score: {minFitScore}%
                    </Typography>
                    <Slider
                      value={minFitScore}
                      onChange={(_, v) => setMinFitScore(v as number)}
                      min={50}
                      max={90}
                      step={5}
                      marks
                      valueLabelDisplay="auto"
                      sx={{ color: '#38BDF8' }}
                    />
                  </Grid>
                </Grid>
              </Grid>

              <Grid size={{ xs: 12, md: 5 }} sx={{ display: 'flex', flexDirection: 'column', alignItems: { xs: 'stretch', md: 'flex-end' }, justifyContent: 'center' }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleBatchApply}
                  disabled={batchLoading}
                  startIcon={batchLoading ? <CircularProgress size={20} color="inherit" /> : <RocketIcon />}
                  sx={{
                    background: 'linear-gradient(135deg, #FFE600 0%, #D97706 100%)',
                    color: '#0F172A',
                    fontWeight: 800,
                    fontSize: '1rem',
                    px: 4,
                    py: 1.8,
                    borderRadius: 2.5,
                    boxShadow: '0 8px 24px rgba(255, 230, 0, 0.25)',
                    '&:hover': { background: 'linear-gradient(135deg, #FFF04D 0%, #F59E0B 100%)' },
                  }}
                >
                  {batchLoading ? 'Executing Workday Autopilot...' : `🚀 Apply to ${batchTarget} Workday Jobs`}
                </Button>
              </Grid>
            </Grid>

            {batchResult && (
              <Box sx={{ mt: 3 }}>
                <Alert
                  severity={batchResult.status === 'completed' ? 'success' : 'info'}
                  sx={{ background: 'rgba(15, 23, 42, 0.9)', color: '#F8FAFC', border: '1px solid rgba(255, 255, 255, 0.1)' }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {batchResult.message || `Dispatched ${batchResult.successful_submissions} applications! Quota: ${batchResult.daily_progress}`}
                  </Typography>
                  {batchResult.recent_receipts && (
                    <Typography variant="caption" sx={{ color: '#94A3B8', mt: 0.5, display: 'block' }}>
                      Recent Receipts: {batchResult.recent_receipts.join(', ')}
                    </Typography>
                  )}
                </Alert>
              </Box>
            )}
          </Card>

          {/* Submissions Audit Table */}
          <Card sx={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, color: '#F8FAFC' }}>
                  Workday Submissions Audit Trail ({submissions.length})
                </Typography>
                <Chip label="Verifiable Cryptographic Proof" size="small" sx={{ background: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 600 }} />
              </Stack>

              {submissions.length === 0 ? (
                <Typography variant="body2" sx={{ color: '#64748B', py: 4, textAlign: 'center' }}>
                  No Workday submissions yet. Launch a batch or click 🚀 Apply on any Workday opportunity!
                </Typography>
              ) : (
                <TableContainer component={Paper} sx={{ background: 'transparent', boxShadow: 'none' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ '& th': { borderColor: 'rgba(255, 255, 255, 0.08)', color: '#94A3B8', fontWeight: 700 } }}>
                        <TableCell>Company & Role</TableCell>
                        <TableCell>Workday Tenant</TableCell>
                        <TableCell>ATS Match</TableCell>
                        <TableCell>Screening Q&A</TableCell>
                        <TableCell>Receipt ID & Proof</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {submissions.map((s) => (
                        <TableRow key={s.id} sx={{ '& td': { borderColor: 'rgba(255, 255, 255, 0.05)', color: '#F8FAFC' } }}>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontWeight: 700 }}>
                              {s.company_name}
                            </Typography>
                            <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                              {s.job_title}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#38BDF8' }}>
                              {s.tenant_domain}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={`${s.match_score.toFixed(1)}%`}
                              size="small"
                              sx={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38BDF8', fontWeight: 700, fontSize: '0.75rem' }}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                              {s.answers_count} answered
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#FFE600', fontWeight: 700 }}>
                              {s.receipt_id}
                            </Typography>
                            {s.proof_url && (
                              <Tooltip title="View Verified Submission Proof">
                                <IconButton size="small" href={s.proof_url} target="_blank" sx={{ color: '#94A3B8', ml: 0.5, p: 0.2 }}>
                                  <OpenInNewIcon sx={{ fontSize: 14 }} />
                                </IconButton>
                              </Tooltip>
                            )}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={s.status.toUpperCase()}
                              size="small"
                              sx={{
                                background: s.status === 'submitted' ? 'rgba(0, 255, 163, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                                color: s.status === 'submitted' ? '#00FFA3' : '#EF4444',
                                fontWeight: 700,
                                fontSize: '0.7rem',
                              }}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Stack>
      )}

      {/* ── TAB 1: Candidate Profile & EEO Settings ── */}
      {activeTab === 1 && profile && (
        <Card sx={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 3, p: 3 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#F8FAFC' }}>
                Master Candidate Profile & Form Autofill Rules
              </Typography>
              <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                Configured data used to automatically populate Workday's My Information, My Experience, Screening Q&A, and Voluntary Disclosures.
              </Typography>
            </Box>
            <Button
              variant="contained"
              onClick={handleSaveProfile}
              disabled={savingProfile}
              startIcon={savingProfile ? <CircularProgress size={16} color="inherit" /> : <EditIcon />}
              sx={{
                background: 'linear-gradient(135deg, #FFE600 0%, #D97706 100%)',
                color: '#0F172A',
                fontWeight: 700,
              }}
            >
              {savingProfile ? 'Saving...' : 'Save Profile Changes'}
            </Button>
          </Stack>

          {profileSuccessMsg && (
            <Alert severity="success" sx={{ mb: 3, background: 'rgba(0, 255, 163, 0.1)', color: '#00FFA3' }}>
              {profileSuccessMsg}
            </Alert>
          )}

          <Grid container spacing={3}>
            {/* Personal Details */}
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                fullWidth
                label="First Name"
                value={profile.first_name || ''}
                onChange={(e) => setProfileData({ ...profile, first_name: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                fullWidth
                label="Last Name"
                value={profile.last_name || ''}
                onChange={(e) => setProfileData({ ...profile, last_name: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                fullWidth
                label="Phone Number"
                value={profile.phone || ''}
                onChange={(e) => setProfileData({ ...profile, phone: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>

            {/* Address */}
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                fullWidth
                label="City"
                value={profile.city || ''}
                onChange={(e) => setProfileData({ ...profile, city: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                fullWidth
                label="State / Province"
                value={profile.state_province || ''}
                onChange={(e) => setProfileData({ ...profile, state_province: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                fullWidth
                label="Country"
                value={profile.country || ''}
                onChange={(e) => setProfileData({ ...profile, country: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>

            {/* Links */}
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="LinkedIn Profile URL"
                value={profile.linkedin_url || ''}
                onChange={(e) => setProfileData({ ...profile, linkedin_url: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="GitHub / Portfolio URL"
                value={profile.github_url || ''}
                onChange={(e) => setProfileData({ ...profile, github_url: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>

            {/* Professional Headline */}
            <Grid size={{ xs: 12 }}>
              <TextField
                fullWidth
                label="Master Headline / Title"
                value={profile.headline || ''}
                onChange={(e) => setProfileData({ ...profile, headline: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>

            {/* Work Authorization & Legal */}
            <Grid size={{ xs: 12 }}>
              <Divider sx={{ my: 1, borderColor: 'rgba(255, 255, 255, 0.08)' }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#FFE600', mb: 1.5 }}>
                Workday Screening & Work Authorization
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={profile.legally_authorized}
                    onChange={(e) => setProfileData({ ...profile, legally_authorized: e.target.checked })}
                    sx={{ '& .Mui-checked': { color: '#FFE600' } }}
                  />
                }
                label="Legally authorized to work in target country"
                sx={{ color: '#F8FAFC' }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={profile.requires_sponsorship}
                    onChange={(e) => setProfileData({ ...profile, requires_sponsorship: e.target.checked })}
                    sx={{ '& .Mui-checked': { color: '#FFE600' } }}
                  />
                }
                label="Requires current or future visa sponsorship"
                sx={{ color: '#F8FAFC' }}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                fullWidth
                type="number"
                label="Notice Period (Days)"
                value={profile.notice_period_days || 30}
                onChange={(e) => setProfileData({ ...profile, notice_period_days: parseInt(e.target.value, 10) || 0 })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                fullWidth
                type="number"
                label="Target Salary Min (USD)"
                value={profile.target_salary_min || 120000}
                onChange={(e) => setProfileData({ ...profile, target_salary_min: parseFloat(e.target.value) || 0 })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                fullWidth
                type="number"
                label="Target Salary Max (USD)"
                value={profile.target_salary_max || 180000}
                onChange={(e) => setProfileData({ ...profile, target_salary_max: parseFloat(e.target.value) || 0 })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>

            {/* Voluntary EEO Disclosures */}
            <Grid size={{ xs: 12 }}>
              <Divider sx={{ my: 1, borderColor: 'rgba(255, 255, 255, 0.08)' }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#FFE600', mb: 1.5 }}>
                Voluntary EEO & Diversity Disclosures
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Gender"
                value={profile.gender || 'Male'}
                onChange={(e) => setProfileData({ ...profile, gender: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Race / Ethnicity"
                value={profile.race_ethnicity || 'Asian'}
                onChange={(e) => setProfileData({ ...profile, race_ethnicity: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Veteran Status"
                value={profile.veteran_status || 'I am not a protected veteran'}
                onChange={(e) => setProfileData({ ...profile, veteran_status: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Disability Status"
                value={profile.disability_status || 'No, I do not have a disability'}
                onChange={(e) => setProfileData({ ...profile, disability_status: e.target.value })}
                variant="outlined"
                size="small"
                sx={{ '& input': { color: '#F8FAFC' } }}
              />
            </Grid>
          </Grid>
        </Card>
      )}

      {/* ── TAB 2: Tenant Accounts Vault ── */}
      {activeTab === 2 && (
        <Card sx={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 3, p: 3 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#F8FAFC' }}>
                Provisioned Workday Employer Accounts Vault ({accounts.length})
              </Typography>
              <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                Securely cached candidate accounts per employer Workday portal allowing instant repeat applications.
              </Typography>
            </Box>
            <Chip label="Autonomous Provisioning Active" size="small" sx={{ background: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 700 }} />
          </Stack>

          {accounts.length === 0 ? (
            <Typography variant="body2" sx={{ color: '#64748B', py: 4, textAlign: 'center' }}>
              No employer accounts provisioned yet. As you apply to Workday jobs, accounts are created automatically!
            </Typography>
          ) : (
            <TableContainer component={Paper} sx={{ background: 'transparent', boxShadow: 'none' }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ '& th': { borderColor: 'rgba(255, 255, 255, 0.08)', color: '#94A3B8', fontWeight: 700 } }}>
                    <TableCell>Company</TableCell>
                    <TableCell>Workday Domain</TableCell>
                    <TableCell>Career Site</TableCell>
                    <TableCell>Account Email</TableCell>
                    <TableCell>Session Status</TableCell>
                    <TableCell>Last Activity</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {accounts.map((a) => (
                    <TableRow key={a.id} sx={{ '& td': { borderColor: 'rgba(255, 255, 255, 0.05)', color: '#F8FAFC' } }}>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {a.company_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#38BDF8' }}>
                          {a.tenant_domain}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={a.career_site_name} size="small" sx={{ background: 'rgba(255, 255, 255, 0.1)', color: '#F8FAFC', fontSize: '0.7rem' }} />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                          {a.account_email}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={a.status.toUpperCase()}
                          size="small"
                          sx={{ background: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 700, fontSize: '0.7rem' }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" sx={{ color: '#64748B' }}>
                          {a.last_login_at ? new Date(a.last_login_at).toLocaleDateString() : 'Just now'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Card>
      )}

      {/* ── TAB 3: Cognitive Answer Bank & Learning ── */}
      {activeTab === 3 && (
        <Card sx={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 3, p: 3 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2} sx={{ mb: 3 }}>
            <Box>
              <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 0.5 }}>
                <BrainIcon sx={{ color: '#C084FC', fontSize: 24 }} />
                <Typography variant="h6" sx={{ fontWeight: 700, color: '#F8FAFC' }}>
                  Cognitive Answer Bank &amp; Bi-Directional Memory
                </Typography>
              </Stack>
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                Every applicant question answered or human-corrected is indexed here for instantaneous, 100% accurate reuse across all ATS forms.
              </Typography>
            </Box>

            <Stack direction="row" spacing={1.5}>
              <Button
                variant="outlined"
                size="small"
                startIcon={<RefreshIcon />}
                onClick={() => fetchAnswers()}
                sx={{ borderColor: 'rgba(255, 255, 255, 0.15)', color: '#F8FAFC' }}
              >
                Refresh
              </Button>
              <Button
                variant="contained"
                size="small"
                startIcon={<AddIcon />}
                onClick={() => setShowAddAnswer(!showAddAnswer)}
                sx={{ background: 'linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%)', fontWeight: 700 }}
              >
                {showAddAnswer ? 'Cancel' : 'Add Answer'}
              </Button>
            </Stack>
          </Stack>

          {answerSuccessMsg && (
            <Alert severity="success" sx={{ mb: 3, background: 'rgba(0, 255, 163, 0.1)', color: '#00FFA3', border: '1px solid #00FFA3' }}>
              {answerSuccessMsg}
            </Alert>
          )}

          {/* Add Answer Form */}
          {showAddAnswer && (
            <Card sx={{ background: 'rgba(30, 41, 59, 0.7)', border: '1px solid #8B5CF6', borderRadius: 2.5, p: 2.5, mb: 3 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#C084FC', mb: 2 }}>
                Teach New Screening Question &amp; Preferred Answer
              </Typography>
              <Stack spacing={2}>
                <TextField
                  fullWidth
                  size="small"
                  label="Screening Question"
                  placeholder="e.g. How many years of experience do you have with distributed event streams?"
                  value={newQuestion}
                  onChange={(e) => setNewQuestion(e.target.value)}
                  sx={{ '& .MuiOutlinedInput-root': { color: '#fff', background: 'rgba(15, 23, 42, 0.6)' } }}
                />
                <TextField
                  fullWidth
                  multiline
                  rows={2}
                  size="small"
                  label="Verified Canonical Answer"
                  placeholder="e.g. I have 8+ years designing high-throughput Kafka streaming pipelines and distributed microservices."
                  value={newAnswer}
                  onChange={(e) => setNewAnswer(e.target.value)}
                  sx={{ '& .MuiOutlinedInput-root': { color: '#fff', background: 'rgba(15, 23, 42, 0.6)' } }}
                />
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center" justifyContent="space-between">
                  <TextField
                    size="small"
                    label="Category (optional)"
                    placeholder="e.g. experience_years, distributed_systems, visa"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    sx={{ width: { xs: '100%', sm: 300 }, '& .MuiOutlinedInput-root': { color: '#fff', background: 'rgba(15, 23, 42, 0.6)' } }}
                  />
                  <Button
                    variant="contained"
                    disabled={savingAnswer || !newQuestion.trim() || !newAnswer.trim()}
                    onClick={handleSaveNewAnswer}
                    sx={{ background: 'linear-gradient(135deg, #10B981, #059669)', fontWeight: 700, px: 3 }}
                  >
                    {savingAnswer ? 'Saving…' : 'Save into Memory'}
                  </Button>
                </Stack>
              </Stack>
            </Card>
          )}

          {/* Search Filter */}
          <Stack direction="row" spacing={1.5} sx={{ mb: 2.5 }}>
            <TextField
              size="small"
              fullWidth
              placeholder="Search learned questions or answers by keyword…"
              value={answersQuery}
              onChange={(e) => setAnswersQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') fetchAnswers(answersQuery); }}
              slotProps={{
                input: {
                  startAdornment: <SearchIcon sx={{ color: '#64748B', mr: 1, fontSize: 20 }} />,
                }
              }}
              sx={{ '& .MuiOutlinedInput-root': { color: '#fff', background: 'rgba(15, 23, 42, 0.6)' } }}
            />
            <Button
              variant="contained"
              onClick={() => fetchAnswers(answersQuery)}
              sx={{ background: '#334155', color: '#F8FAFC', fontWeight: 600, px: 2.5 }}
            >
              Search
            </Button>
          </Stack>

          {/* Answers Table */}
          {answersLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
              <CircularProgress size={32} sx={{ color: '#8B5CF6' }} />
            </Box>
          ) : answers.length === 0 ? (
            <Typography variant="body2" sx={{ color: '#64748B', py: 5, textAlign: 'center' }}>
              No answers found in Answer Bank. As you autofill forms or edit answers in the Chrome extension, learned answers will appear here!
            </Typography>
          ) : (
            <TableContainer component={Paper} sx={{ background: 'transparent', boxShadow: 'none' }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ '& th': { borderColor: 'rgba(255, 255, 255, 0.08)', color: '#94A3B8', fontWeight: 700 } }}>
                    <TableCell sx={{ width: '38%' }}>Question</TableCell>
                    <TableCell sx={{ width: '38%' }}>Learned Answer</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Source</TableCell>
                    <TableCell>Uses</TableCell>
                    <TableCell align="right">Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {answers.map((ans) => (
                    <TableRow key={ans.id} sx={{ '& td': { borderColor: 'rgba(255, 255, 255, 0.05)', color: '#F8FAFC' } }}>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600, color: '#F1F5F9' }}>
                          {ans.question_text}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ color: '#38BDF8', fontWeight: 500 }}>
                          {ans.answer_text}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={ans.category || 'general'}
                          size="small"
                          sx={{ background: 'rgba(255, 255, 255, 0.08)', color: '#94A3B8', fontSize: '0.72rem' }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={ans.source.replace('_', ' ')}
                          size="small"
                          sx={{
                            background: ans.source === 'user_edited' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(16, 185, 129, 0.15)',
                            color: ans.source === 'user_edited' ? '#C084FC' : '#34D399',
                            fontWeight: 700,
                            fontSize: '0.68rem',
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700 }}>
                          {ans.times_used}x
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteAnswer(ans.id)}
                          sx={{ color: '#EF4444', opacity: 0.8, '&:hover': { opacity: 1, background: 'rgba(239, 68, 68, 0.15)' } }}
                          title="Delete from Answer Bank"
                        >
                          <DeleteIcon sx={{ fontSize: 18 }} />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Card>
      )}
    </Box>
  );
};


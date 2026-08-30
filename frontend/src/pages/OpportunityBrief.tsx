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
  Tab,
  Tabs,
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
  Favorite as FavoriteIcon,
  Repeat as RepostIcon,
  ChatBubbleOutline as ReplyIcon,
  AlternateEmail as XIcon,
  Email as EmailIcon,
  FindInPage as DorkIcon,
  MarkEmailRead as VerifiedMailIcon,
  Security as SecurityIcon,
  PictureAsPdf as PdfIcon,
  Article as ArticleIcon,
  Print as PrintIcon,
} from '@mui/icons-material';
import { opportunitiesApi } from '../api/endpoints/opportunities';
import { lifecycleApi } from '../api/endpoints/lifecycle';
import { referralsApi } from '../api/endpoints/referrals';
import { xReferralsApi } from '../api/endpoints/x_referrals';
import { emailIntelligenceApi } from '../api/endpoints/email_intelligence';
import { attentionApi } from '../api/endpoints/attention';
import { resumeGeneratorApi } from '../api/endpoints/resume_generator';
import type { ResumeDocumentResponse } from '../api/endpoints/resume_generator';
import { AttentionHeatmap } from '../components/attention/AttentionHeatmap';
import { GhostBadge } from '../components/ghost_hunter/GhostBadge';
import { SpamHeatmapSandbox } from '../components/deliverability/SpamHeatmapSandbox';
import { CommunityIntelPanel } from '../components/community_intel/CommunityIntelPanel';
import type { DiscoveredContactItem, SearchDorkItem, EmailPermutationItem } from '../api/endpoints/email_intelligence';

import type { OpportunityBrief as OpportunityBriefData, ReferralProfile, XProfile, XTweet } from '../api/types';


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

  const attentionQuery = useQuery({
    queryKey: ['attention-match', id],
    queryFn: () =>
      attentionApi.match(
        briefQuery.data?.job?.description ||
          `${briefQuery.data?.job?.title || 'Software Engineer'} at ${briefQuery.data?.job?.company || 'Company'}`
      ),
    enabled: !!briefQuery.data,
    staleTime: 60000,
  });

  const [working, setWorking] = useState(false);
  const [proofOpen, setProofOpen] = useState(false);
  const [proof, setProof] = useState({ confirmation_number: '', proof_note: '', proof_url: '' });
  const [toast, setToast] = useState('');
  const [confirmAccept, setConfirmAccept] = useState(false);
  const [advanceStage, setAdvanceStage] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // LinkedIn Referral state
  const [referralDialogOpen, setReferralDialogOpen] = useState(false);
  const [referralLoading, setReferralLoading] = useState(false);
  const [referralProfiles, setReferralProfiles] = useState<ReferralProfile[]>([]);
  const [selectedReferral, setSelectedReferral] = useState<ReferralProfile | null>(null);
  const [generatedNote, setGeneratedNote] = useState<any>(null);
  const [generatingNote, setGeneratingNote] = useState(false);

  // X (Twitter) Referral & Tweets state
  const [xDialogOpen, setXDialogOpen] = useState(false);
  const [xTab, setXTab] = useState(0);
  const [xLoading, setXLoading] = useState(false);
  const [xProfiles, setXProfiles] = useState<XProfile[]>([]);
  const [xTweets, setXTweets] = useState<XTweet[]>([]);
  const [xGeneratedMessage, setXGeneratedMessage] = useState<any>(null);
  const [selectedXProfile, setSelectedXProfile] = useState<XProfile | null>(null);

  // Email Intelligence & Google Boolean Dorking state
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [emailTab, setEmailTab] = useState(0);
  const [emailLoading, setEmailLoading] = useState(false);
  const [discoveredContacts, setDiscoveredContacts] = useState<DiscoveredContactItem[]>([]);
  const [emailDorks, setEmailDorks] = useState<SearchDorkItem[]>([]);
  const [emailPermutations, setEmailPermutations] = useState<EmailPermutationItem[]>([]);
  const [domainInfo, setDomainInfo] = useState<{ domain: string; has_mx: boolean; mail_provider: string }>({
    domain: '',
    has_mx: true,
    mail_provider: '',
  });
  const [customPermName, setCustomPermName] = useState('');

  // 1-Click ATS Resume & Cover Letter Generator state
  const [resumeModalOpen, setResumeModalOpen] = useState(false);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [activeDocType, setActiveDocType] = useState<'ats_resume' | 'cover_letter'>('ats_resume');
  const [resumeDoc, setResumeDoc] = useState<ResumeDocumentResponse | null>(null);

  const brief = briefQuery.data as OpportunityBriefData | undefined;

  const handleOpenResumeModal = async (docType: 'ats_resume' | 'cover_letter' = 'ats_resume') => {
    if (!brief) return;
    setActiveDocType(docType);
    setResumeModalOpen(true);
    setResumeLoading(true);
    try {
      if (docType === 'ats_resume') {
        const res = await resumeGeneratorApi.generateAtsResume({
          role_title: brief.job.title || 'Software Engineer',
          company: brief.job.company || 'Target Company',
          job_description: brief.job.description || undefined,
        });
        setResumeDoc(res.data);
      } else {
        const res = await resumeGeneratorApi.generateCoverLetter({
          role_title: brief.job.title || 'Software Engineer',
          company: brief.job.company || 'Target Company',
          job_description: brief.job.description || undefined,
        });
        setResumeDoc(res.data);
      }
    } catch {
      setToast('Failed to generate document.');
    } finally {
      setResumeLoading(false);
    }
  };

  const handlePrintResume = () => {
    if (!resumeDoc) return;
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(resumeDoc.html_content);
      printWindow.document.close();
      printWindow.focus();
      setTimeout(() => {
        printWindow.print();
      }, 300);
    }
  };


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

  // LinkedIn handlers
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

  // X (Twitter) Handlers
  const handleOpenXSearch = async () => {
    if (!brief?.job.company) return;
    setXDialogOpen(true);
    setXLoading(true);
    try {
      const [profilesRes, tweetsRes] = await Promise.all([
        xReferralsApi.search(brief.job.company, brief.job.title, 8),
        xReferralsApi.searchTweets(brief.job.company, brief.job.title, 6),
      ]);
      setXProfiles(profilesRes.profiles || []);
      setXTweets(tweetsRes.tweets || []);
    } catch {
      setToast('Could not fetch X referrals/tweets for this company.');
    } finally {
      setXLoading(false);
    }
  };

  const handleGenerateXMessage = async (profile: XProfile, actionType: 'reply' | 'dm' | 'quote', tweet?: XTweet) => {
    if (!brief) return;
    setSelectedXProfile(profile);
    try {
      const res = await xReferralsApi.generateMessage({
        action_type: actionType,
        username: profile.username,
        company: profile.company || brief.job.company || '',
        name: profile.name,
        title: profile.title || undefined,
        role_title: brief.job.title,
        job_link: brief.job.url || undefined,
        tweet_id: tweet?.tweet_id,
        tweet_text: tweet?.text,
        max_length: actionType === 'dm' ? 1000 : 280,
      });
      setXGeneratedMessage(res);
    } catch {
      setToast('Failed to generate X message.');
    }
  };

  const handleExecuteXAction = async (profile: XProfile, actionType: 'follow' | 'like' | 'repost' | 'reply' | 'dm', tweetId?: string, messageText?: string) => {
    try {
      const res = await xReferralsApi.engage({
        action_type: actionType,
        target_username: profile.username,
        company: profile.company || brief?.job.company || 'Company',
        tweet_id: tweetId,
        message_text: messageText,
        job_id: id,
      });
      if (res.intent_url) {
        window.open(res.intent_url, '_blank', 'noopener,noreferrer');
      }
      await refresh();
      setToast(`Executed ${actionType} on @${profile.username} (Logged to CRM) ✓`);
    } catch {
      setToast(`Failed to execute ${actionType}.`);
    }
  };

  const handleSyncXProfileToCRM = async (profile: XProfile) => {
    try {
      await xReferralsApi.sync([profile]);
      await refresh();
      setToast(`Saved @${profile.username} to Contacts CRM!`);
    } catch {
      setToast('Failed to sync X contact.');
    }
  };

  // Email Intelligence Handlers
  const handleOpenEmailIntelligence = async () => {
    if (!brief?.job.company) return;
    setEmailDialogOpen(true);
    setEmailLoading(true);
    try {
      const [discoveryRes, dorksRes] = await Promise.all([
        emailIntelligenceApi.discover(brief.job.company, brief.job.title, brief.job.company_website || undefined),
        emailIntelligenceApi.getDorks(brief.job.company, undefined, undefined, brief.job.title),
      ]);
      setDiscoveredContacts(discoveryRes.contacts || []);
      setDomainInfo({
        domain: discoveryRes.domain,
        has_mx: discoveryRes.has_mx,
        mail_provider: discoveryRes.mail_provider,
      });
      setEmailDorks(dorksRes.dorks || []);
      if (discoveryRes.contacts.length > 0) {
        const topName = discoveryRes.contacts[0].name;
        const permsRes = await emailIntelligenceApi.getPermutations(topName, discoveryRes.domain);
        setEmailPermutations(permsRes.permutations || []);
      }
    } catch {
      setToast('Email Intelligence discovery encountered an issue.');
    } finally {
      setEmailLoading(false);
    }
  };

  const handleGenerateCustomPermutations = async () => {
    if (!customPermName.trim() || !domainInfo.domain) return;
    try {
      const res = await emailIntelligenceApi.getPermutations(customPermName.trim(), domainInfo.domain);
      setEmailPermutations(res.permutations || []);
      setToast(`Generated 12 permutations for ${customPermName}!`);
    } catch {
      setToast('Could not generate permutations.');
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
                <GhostBadge jobId={id} />
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

              <Stack direction="row" spacing={1}>
                <Button
                  variant="outlined"
                  color="warning"
                  startIcon={<EmailIcon />}
                  onClick={handleOpenEmailIntelligence}
                  fullWidth
                  sx={{ fontWeight: 700 }}
                >
                  Emails & Dorks
                </Button>
                <Button
                  variant="outlined"
                  color="secondary"
                  startIcon={<ReferralIcon />}
                  onClick={handleOpenReferralSearch}
                  fullWidth
                  sx={{ fontWeight: 700 }}
                >
                  LinkedIn
                </Button>
                <Button
                  variant="outlined"
                  color="info"
                  startIcon={<XIcon />}
                  onClick={handleOpenXSearch}
                  fullWidth
                  sx={{ fontWeight: 700 }}
                >
                  X
                </Button>
              </Stack>

              <Button
                variant="outlined"
                color="secondary"
                startIcon={<PdfIcon />}
                onClick={() => handleOpenResumeModal('ats_resume')}
                fullWidth
                sx={{ fontWeight: 700 }}
              >
                Export Tailored ATS Resume
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

      {/* Transformer Q,K,V Attention Analysis Heatmap */}
      <AttentionHeatmap data={attentionQuery.data} loading={attentionQuery.isLoading} />

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
                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    variant="outlined"
                    color="warning"
                    startIcon={<EmailIcon fontSize="small" />}
                    onClick={handleOpenEmailIntelligence}
                    sx={{ fontWeight: 700 }}
                  >
                    Email Dorks
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<SearchIcon fontSize="small" />}
                    onClick={handleOpenReferralSearch}
                    sx={{ fontWeight: 700 }}
                  >
                    LinkedIn
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    color="info"
                    startIcon={<XIcon fontSize="small" />}
                    onClick={handleOpenXSearch}
                    sx={{ fontWeight: 700 }}
                  >
                    X
                  </Button>
                </Stack>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Identified contacts, recruiters, and tech leaders who can open doors for this role.
              </Typography>

              {brief.people.length === 0 ? (
                <Alert severity="info" sx={{ borderRadius: '10px' }}>
                  No contacts indexed yet for {brief.job.company || 'this company'}. Click "Email Dorks", "LinkedIn", or "X" to search hiring leads.
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
              <Paper variant="outlined" sx={{ p: 1.5, borderRadius: '10px', bgcolor: '#F8FAFC', mt: 0.5, mb: 2 }}>
                <Typography variant="body2" sx={{ color: '#334155', fontStyle: 'italic' }}>
                  "{brief.outreach.recommended_message || 'Highlight your experience scaling distributed backend systems and mention recent production milestones.'}"
                </Typography>
              </Paper>

              <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase', display: 'block', mb: 1 }}>
                ATS Document Engine & Deliverability Sandbox:
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                <Button
                  size="small"
                  variant="contained"
                  color="primary"
                  startIcon={<PdfIcon fontSize="small" />}
                  onClick={() => handleOpenResumeModal('ats_resume')}
                  sx={{ fontWeight: 700 }}
                >
                  Export Tailored ATS Resume
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  color="secondary"
                  startIcon={<ArticleIcon fontSize="small" />}
                  onClick={() => handleOpenResumeModal('cover_letter')}
                  sx={{ fontWeight: 700 }}
                >
                  Generate Cover Letter
                </Button>
              </Stack>

              {/* Spam Heatmap Sandbox */}
              <SpamHeatmapSandbox
                subject={`Excited about ${brief.job.title || 'engineering'} opportunities at ${brief.job.company}`}
                body={brief.outreach.recommended_message || `Hi Team,\n\nI noticed the ${brief.job.title || 'engineering'} opening at ${brief.job.company} and wanted to reach out. In my previous role, I scaled distributed systems handling 50k RPS with sub-15ms latency.\n\nBest regards,\nCandidate`}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Community Interview Debriefs & Insider Intelligence */}
      <CommunityIntelPanel
        company={brief.job.company || 'Target Company'}
        roleTitle={brief.job.title || 'Software Engineer'}
      />

      {/* Email Intelligence & Google Boolean Dorking Dialog */}

      <Dialog open={emailDialogOpen} onClose={() => setEmailDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 800, color: '#0F172A' }}>
          Email Intelligence & Google Boolean Dorks — {brief.job.company}
        </DialogTitle>
        <DialogContent dividers>
          {/* Domain & MX Header Banner */}
          <Paper variant="outlined" sx={{ p: 2, mb: 2.5, borderRadius: '12px', bgcolor: '#F0FDF4', borderColor: '#BBF7D0' }}>
            <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} gap={1.5}>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <SecurityIcon sx={{ color: '#16A34A' }} />
                <Box>
                  <Typography variant="subtitle2" fontWeight={800} color="#14532D">
                    Corporate Domain: <code>{domainInfo.domain || 'resolving...'}</code>
                  </Typography>
                  <Typography variant="caption" color="#166534">
                    Mail Provider: <strong>{domainInfo.mail_provider || 'Active'}</strong> · MX Verified: {domainInfo.has_mx ? 'Yes ✓' : 'No'}
                  </Typography>
                </Box>
              </Stack>
              <Chip
                label={domainInfo.has_mx ? "Deliverability High" : "Standard"}
                size="small"
                color={domainInfo.has_mx ? "success" : "warning"}
                sx={{ fontWeight: 700 }}
              />
            </Stack>
          </Paper>

          <Tabs value={emailTab} onChange={(_, val) => setEmailTab(val)} sx={{ mb: 2.5 }}>
            <Tab label={`Verified Decision-Makers (${discoveredContacts.length})`} sx={{ fontWeight: 700 }} />
            <Tab label={`Google Boolean Dorks (${emailDorks.length})`} sx={{ fontWeight: 700 }} />
            <Tab label={`12-Pattern Permutations (${emailPermutations.length})`} sx={{ fontWeight: 700 }} />
          </Tabs>

          {emailLoading ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 6, gap: 2 }}>
              <CircularProgress />
              <Typography variant="body2" color="text.secondary">Running multi-provider waterfall & Google Dork analysis...</Typography>
            </Box>
          ) : emailTab === 0 ? (
            // Contacts Tab
            discoveredContacts.length === 0 ? (
              <Alert severity="info">No emails discovered yet. Run Google Dorks or Permutations below.</Alert>
            ) : (
              <Stack spacing={2}>
                {discoveredContacts.map((c, idx) => (
                  <Paper key={idx} variant="outlined" sx={{ p: 2, borderRadius: '12px' }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1.5}>
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <Avatar sx={{ bgcolor: alpha('#16A34A', 0.1), color: '#16A34A', fontWeight: 800 }}>
                          {c.name.split(' ').map((n) => n[0]).slice(0, 2).join('')}
                        </Avatar>
                        <Box>
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Typography variant="subtitle2" fontWeight={800} color="#0F172A">
                              {c.name}
                            </Typography>
                            <Chip
                              label={c.title}
                              size="small"
                              sx={{ fontWeight: 700, fontSize: '0.7rem', bgcolor: '#F1F5F9' }}
                            />
                          </Stack>
                          <Typography variant="body2" fontWeight={600} color="#2563EB" sx={{ my: 0.25 }}>
                            {c.email}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Confidence: {Math.round(c.confidence_score)}% · Source: {c.source} · {c.mail_provider || 'Verified MX'}
                          </Typography>
                        </Box>
                      </Stack>

                      <Stack direction="row" spacing={1}>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<CopyIcon fontSize="small" />}
                          onClick={() => {
                            navigator.clipboard.writeText(c.email);
                            setToast(`Copied ${c.email}!`);
                          }}
                        >
                          Copy
                        </Button>
                        <Button
                          size="small"
                          variant="contained"
                          color="primary"
                          startIcon={<SendIcon fontSize="small" />}
                          onClick={() => navigate(`/outreach?email=${encodeURIComponent(c.email)}&name=${encodeURIComponent(c.name)}&jobId=${id}`)}
                          sx={{ fontWeight: 700 }}
                        >
                          Draft Cold Email
                        </Button>
                      </Stack>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            )
          ) : emailTab === 1 ? (
            // Dorks Tab
            emailDorks.length === 0 ? (
              <Alert severity="info">No dorks generated.</Alert>
            ) : (
              <Stack spacing={2}>
                <Typography variant="caption" color="text.secondary">
                  Targeted Google Boolean search operators designed to uncover unindexed employee emails and personal contact details:
                </Typography>
                {emailDorks.map((d, idx) => (
                  <Paper key={idx} variant="outlined" sx={{ p: 2, borderRadius: '12px', bgcolor: '#F8FAFC' }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1.5}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" fontWeight={800} color="#0F172A">
                          {d.dork_type.replace(/_/g, ' ').toUpperCase()}
                        </Typography>
                        <Paper variant="outlined" sx={{ p: 1.5, my: 1, bgcolor: '#FFFFFF', fontFamily: 'monospace', fontSize: '0.8rem', color: '#0F172A' }}>
                          {d.query}
                        </Paper>
                        <Typography variant="caption" color="text.secondary">
                          {d.description}
                        </Typography>
                      </Box>
                      {d.url && (
                        <Button
                          size="small"
                          variant="contained"
                          color="warning"
                          startIcon={<DorkIcon fontSize="small" />}
                          onClick={() => window.open(d.url ?? undefined, '_blank', 'noopener,noreferrer')}
                          sx={{ fontWeight: 700, whiteSpace: 'nowrap' }}
                        >
                          Google Search
                        </Button>
                      )}
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            )
          ) : (
            // Permutations Tab
            <Box>
              <Stack direction="row" spacing={1} sx={{ mb: 2.5 }}>
                <TextField
                  label="Target Person Name"
                  size="small"
                  fullWidth
                  placeholder="e.g. John Doe"
                  value={customPermName}
                  onChange={(e) => setCustomPermName(e.target.value)}
                />
                <Button
                  variant="contained"
                  onClick={handleGenerateCustomPermutations}
                  sx={{ fontWeight: 700, whiteSpace: 'nowrap' }}
                >
                  Generate 12 Patterns
                </Button>
              </Stack>

              <Stack spacing={1.5}>
                {emailPermutations.map((p, idx) => (
                  <Paper key={idx} variant="outlined" sx={{ p: 1.5, borderRadius: '10px' }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <VerifiedMailIcon sx={{ color: '#2563EB' }} fontSize="small" />
                        <Box>
                          <Typography variant="body2" fontWeight={700} color="#0F172A">
                            {p.email}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Pattern: <code>{p.pattern_name}</code> · Confidence: {Math.round(p.confidence_score)}%
                          </Typography>
                        </Box>
                      </Stack>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<CopyIcon fontSize="small" />}
                        onClick={() => {
                          navigator.clipboard.writeText(p.email);
                          setToast(`Copied ${p.email}!`);
                        }}
                      >
                        Copy
                      </Button>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setEmailDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* LinkedIn Referral Search Dialog */}
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

      {/* X (Twitter) Referral Dialog */}
      <Dialog open={xDialogOpen} onClose={() => setXDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 800, color: '#0F172A' }}>
          X (Twitter) Referrals & Hiring Tweets — {brief.job.company}
        </DialogTitle>
        <DialogContent dividers>
          <Tabs value={xTab} onChange={(_, val) => setXTab(val)} sx={{ mb: 2.5 }}>
            <Tab label={`Tech Leaders & Employees (${xProfiles.length})`} sx={{ fontWeight: 700 }} />
            <Tab label={`Active Hiring Tweets (${xTweets.length})`} sx={{ fontWeight: 700 }} />
          </Tabs>

          {xLoading ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 6, gap: 2 }}>
              <CircularProgress />
              <Typography variant="body2" color="text.secondary">Searching X developer network & hiring posts...</Typography>
            </Box>
          ) : xTab === 0 ? (
            // Profiles Tab
            xProfiles.length === 0 ? (
              <Alert severity="info">No profiles found for {brief.job.company}.</Alert>
            ) : (
              <Stack spacing={2}>
                {xProfiles.map((p, idx) => (
                  <Paper key={idx} variant="outlined" sx={{ p: 2, borderRadius: '12px' }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={1.5}>
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <Avatar sx={{ bgcolor: alpha('#0284C7', 0.1), color: '#0284C7', fontWeight: 800 }}>
                          {p.name.split(' ').map((n) => n[0]).slice(0, 2).join('')}
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle2" fontWeight={800} color="#0F172A">
                            {p.name} <span style={{ color: '#64748B', fontWeight: 500 }}>@{p.username}</span>
                          </Typography>
                          <Typography variant="caption" color="text.secondary" display="block">
                            {p.title || 'Engineer'} · {p.company}
                          </Typography>
                          {p.description && (
                            <Typography variant="caption" sx={{ color: '#475569', mt: 0.5, display: 'block', maxWidth: 500 }}>
                              {p.description}
                            </Typography>
                          )}
                        </Box>
                      </Stack>

                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleSyncXProfileToCRM(p)}
                        >
                          Save CRM
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleExecuteXAction(p, 'follow')}
                        >
                          Follow
                        </Button>
                        <Button
                          size="small"
                          variant="contained"
                          color="info"
                          onClick={() => handleGenerateXMessage(p, 'dm')}
                          sx={{ fontWeight: 700 }}
                        >
                          Draft DM
                        </Button>
                      </Stack>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            )
          ) : (
            // Tweets Tab
            xTweets.length === 0 ? (
              <Alert severity="info">No active hiring tweets found for {brief.job.company}.</Alert>
            ) : (
              <Stack spacing={2}>
                {xTweets.map((t, idx) => (
                  <Paper key={idx} variant="outlined" sx={{ p: 2, borderRadius: '12px', bgcolor: '#F8FAFC' }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1.5}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" fontWeight={800} color="#0F172A">
                          {t.author_name || 'Hiring Lead'} <span style={{ color: '#64748B', fontWeight: 500 }}>@{t.author_username || 'team'}</span>
                        </Typography>
                        <Typography variant="body2" sx={{ color: '#334155', my: 1, whiteSpace: 'pre-wrap' }}>
                          "{t.text}"
                        </Typography>
                      </Box>
                    </Stack>

                    <Divider sx={{ my: 1.5 }} />

                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<FavoriteIcon fontSize="small" />}
                        onClick={() => handleExecuteXAction({ username: t.author_username || 'user', name: t.author_name || 'User', x_user_id: '0', followers_count: 0, verified: false }, 'like', t.tweet_id)}
                      >
                        Like
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<RepostIcon fontSize="small" />}
                        onClick={() => handleExecuteXAction({ username: t.author_username || 'user', name: t.author_name || 'User', x_user_id: '0', followers_count: 0, verified: false }, 'repost', t.tweet_id)}
                      >
                        Repost
                      </Button>
                      <Button
                        size="small"
                        variant="contained"
                        color="info"
                        startIcon={<ReplyIcon fontSize="small" />}
                        onClick={() => handleGenerateXMessage({ username: t.author_username || 'user', name: t.author_name || 'User', x_user_id: '0', followers_count: 0, verified: false }, 'reply', t)}
                        sx={{ fontWeight: 700 }}
                      >
                        AI Reply
                      </Button>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            )
          )}

          {xGeneratedMessage && selectedXProfile && (
            <Box sx={{ mt: 3, p: 2.5, borderRadius: '12px', bgcolor: '#FFFFFF', border: '1px solid #0284C7' }}>
              <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
                AI Generated {xGeneratedMessage.action_type.toUpperCase()} for @{selectedXProfile.username} ({xGeneratedMessage.char_count} / {xGeneratedMessage.action_type === 'dm' ? 1000 : 280} chars)
              </Typography>
              <TextField
                multiline
                rows={3}
                fullWidth
                value={xGeneratedMessage.message}
                sx={{ mb: 2, bgcolor: '#F8FAFC' }}
              />
              <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<CopyIcon fontSize="small" />}
                  onClick={() => {
                    navigator.clipboard.writeText(xGeneratedMessage.message);
                    setToast('Message copied to clipboard!');
                  }}
                  sx={{ fontWeight: 700 }}
                >
                  Copy Message
                </Button>
                {xGeneratedMessage.intent_url && (
                  <Button
                    variant="outlined"
                    size="small"
                    color="info"
                    startIcon={<LaunchIcon fontSize="small" />}
                    onClick={() => window.open(xGeneratedMessage.intent_url, '_blank', 'noopener,noreferrer')}
                    sx={{ fontWeight: 700 }}
                  >
                    Open on X
                  </Button>
                )}
              </Stack>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setXDialogOpen(false)}>Close</Button>
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

      {/* 1-Click ATS Tailored Resume & Cover Letter Preview Modal */}
      <Dialog open={resumeModalOpen} onClose={() => setResumeModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 800, color: '#0F172A', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            {activeDocType === 'ats_resume' ? <PdfIcon sx={{ color: '#4F46E5' }} /> : <ArticleIcon sx={{ color: '#7C3AED' }} />}
            <Typography variant="h6" fontWeight={800}>
              {activeDocType === 'ats_resume' ? 'Tailored ATS-Compliant Resume' : 'Executive Cover Letter'} — {brief?.job.company}
            </Typography>
          </Stack>
          {resumeDoc && (
            <Chip
              label={`ATS Score: ${resumeDoc.ats_match_score}%`}
              size="small"
              color="success"
              sx={{ fontWeight: 700 }}
            />
          )}
        </DialogTitle>
        <DialogContent dividers sx={{ p: 2 }}>
          {resumeLoading ? (
            <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={8}>
              <CircularProgress size={36} sx={{ mb: 2 }} />
              <Typography variant="body2" color="text.secondary">
                Applying Transformer Q,K,V Attention matrix to synthesize document…
              </Typography>
            </Box>
          ) : resumeDoc ? (
            <Box>
              <Stack direction="row" spacing={1} sx={{ mb: 1.5 }} alignItems="center" flexWrap="wrap" useFlexGap>
                <Typography variant="caption" fontWeight={700} color="text.secondary">
                  Attended Keywords:
                </Typography>
                {resumeDoc.suggested_keywords.map((kw, i) => (
                  <Chip key={i} label={kw} size="small" variant="outlined" sx={{ fontWeight: 600, fontSize: '0.75rem' }} />
                ))}
              </Stack>
              <Paper
                variant="outlined"
                sx={{
                  height: 480,
                  bgcolor: '#FFFFFF',
                  borderRadius: 2,
                  overflow: 'hidden',
                  border: '1px solid #CBD5E1',
                }}
              >
                <iframe
                  title="Document Preview"
                  srcDoc={resumeDoc.html_content}
                  style={{ width: '100%', height: '100%', border: 'none' }}
                />
              </Paper>
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant={activeDocType === 'ats_resume' ? 'contained' : 'outlined'}
              onClick={() => handleOpenResumeModal('ats_resume')}
            >
              ATS Resume
            </Button>
            <Button
              size="small"
              variant={activeDocType === 'cover_letter' ? 'contained' : 'outlined'}
              onClick={() => handleOpenResumeModal('cover_letter')}
            >
              Cover Letter
            </Button>
          </Stack>
          <Stack direction="row" spacing={1}>
            <Button onClick={() => setResumeModalOpen(false)}>Close</Button>
            <Button
              variant="contained"
              color="primary"
              startIcon={<PrintIcon />}
              onClick={handlePrintResume}
              disabled={!resumeDoc || resumeLoading}
              sx={{ fontWeight: 700 }}
            >
              Print / Save as PDF
            </Button>
          </Stack>
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

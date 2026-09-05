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
  Handshake as HandshakeIcon,
  AttachMoney as DollarIcon,
  ContentCopy as CopyIcon,
  Email as EmailIcon,
  Send as SendIcon,
  Security as SecurityIcon,
  CheckCircle as CheckIcon,
  WorkOutline as WorkIcon,
} from '@mui/icons-material';
import {
  sprint5Api,
  type HeadhunterBountyListing,
  type PitchPackResponse,
} from '../../api/endpoints/sprint5_api';

export const ReverseHeadhunterCard: React.FC = () => {
  const [listings, setListings] = useState<HeadhunterBountyListing[]>([]);
  const [candidateName, setCandidateName] = useState('Ujjwal');
  const [targetCompany, setTargetCompany] = useState('Stripe');
  const [roleTitle, setRoleTitle] = useState('Staff Distributed Systems Engineer');
  const [referrerName, setReferrerName] = useState('Alex / Senior Peer Referrer');
  const [strengths, setStrengths] = useState('Raft consensus implementation, P99 latency reduction by 64%, Defensive idempotency');
  const [yearsExp, setYearsExp] = useState<number>(6);
  const [githubUrl, setGithubUrl] = useState('https://github.com/ujjwal-sovereign');

  const [loading, setLoading] = useState(false);
  const [pitchPack, setPitchPack] = useState<PitchPackResponse | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMsg, setSnackbarMsg] = useState('');

  useEffect(() => {
    sprint5Api.getHeadhunterListings().then((res) => {
      if (res && res.listings) setListings(res.listings);
    }).catch(console.error);

    // Initial synthesis
    handleGeneratePitchPack('Stripe', 'Staff Distributed Systems Engineer');
  }, []);

  const handleGeneratePitchPack = async (company = targetCompany, role = roleTitle) => {
    if (!company.trim()) return;
    setLoading(true);
    try {
      const strengthList = strengths.split(',').map((s) => s.trim()).filter(Boolean);
      const res = await sprint5Api.generatePitchPack({
        candidate_name: candidateName,
        target_company: company,
        role_title: role,
        referrer_name: referrerName,
        key_strengths: strengthList,
        years_experience: yearsExp,
        github_portfolio: githubUrl,
      });
      setPitchPack(res);
    } catch (err) {
      console.error('Failed to generate pitch pack:', err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setSnackbarMsg(`Copied ${label} to clipboard!`);
    setSnackbarOpen(true);
  };

  const selectBounty = (item: HeadhunterBountyListing) => {
    setTargetCompany(item.company_name);
    setRoleTitle(item.role_title);
    handleGeneratePitchPack(item.company_name, item.role_title);
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
                  <HandshakeIcon sx={{ color: '#FFE600', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    🤝 Reverse Headhunter Bounty Network (Agent 20)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Monetize warm peer introductions ($1,000–$7,500 USD / ₹1L–₹6.5L) with automated referral pitch packs and smart-contract escrow.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip
                label="$1k – $7.5k USD Bounties"
                sx={{ bgcolor: 'rgba(255, 230, 0, 0.2)', color: '#FFE600', fontWeight: 900, fontSize: '0.8rem' }}
              />
              <Chip
                label="Direct Referral Escrow"
                sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, fontSize: '0.75rem' }}
              />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Main Two Column Generator */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Left: Input Controls */}
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
              ⚙️ Candidate & Referral Parameters
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
                label="Target Role Title"
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                label="Referrer / Peer Name"
                value={referrerName}
                onChange={(e) => setReferrerName(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                multiline
                rows={2}
                size="small"
                label="Key Technical Strengths (comma separated)"
                value={strengths}
                onChange={(e) => setStrengths(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Grid container spacing={2}>
                <Grid size={{ xs: 6 }}>
                  <TextField
                    size="small"
                    type="number"
                    label="Years Experience"
                    value={yearsExp}
                    onChange={(e) => setYearsExp(Number(e.target.value))}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField
                    size="small"
                    label="Portfolio / GitHub URL"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
              </Grid>

              <Button
                variant="contained"
                disabled={loading || !targetCompany.trim()}
                onClick={() => handleGeneratePitchPack(targetCompany, roleTitle)}
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
                {loading ? 'Synthesizing Pitch Pack...' : 'Generate Warm Referral Pitch Pack'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* Right: Escrow Financials & Outreach Scripts */}
        <Grid size={{ xs: 12, md: 7 }}>
          {pitchPack ? (
            <Stack spacing={3}>
              {/* Escrow Financials Card */}
              <Paper
                sx={{
                  p: 3,
                  bgcolor: '#0D131F',
                  border: '1.5px solid rgba(255, 230, 0, 0.3)',
                  borderRadius: '16px',
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#FFE600', display: 'flex', alignItems: 'center', gap: 1 }}>
                    <DollarIcon sx={{ color: '#FFE600' }} /> Referral Bounty Escrow Breakdown
                  </Typography>
                  <Chip
                    label={`$${pitchPack.bounty_financials.total_bounty_usd.toLocaleString()} USD (~₹${pitchPack.bounty_financials.total_bounty_inr_lakhs}L)`}
                    sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 900, border: '1px solid #FFE600' }}
                  />
                </Stack>

                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid size={{ xs: 6 }}>
                    <Paper sx={{ p: 1.8, bgcolor: '#06090E', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                        MILESTONE 1 (50% PAYOUT)
                      </Typography>
                      <Typography variant="h6" sx={{ color: '#00FFA3', fontWeight: 900, my: 0.5 }}>
                        ${pitchPack.bounty_financials.milestone_1_payout_usd.toLocaleString()} USD
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#64748B' }}>
                        {pitchPack.bounty_financials.milestone_1_condition}
                      </Typography>
                    </Paper>
                  </Grid>

                  <Grid size={{ xs: 6 }}>
                    <Paper sx={{ p: 1.8, bgcolor: '#06090E', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                        MILESTONE 2 (50% PAYOUT)
                      </Typography>
                      <Typography variant="h6" sx={{ color: '#00F0FF', fontWeight: 900, my: 0.5 }}>
                        ${pitchPack.bounty_financials.milestone_2_payout_usd.toLocaleString()} USD
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#64748B' }}>
                        {pitchPack.bounty_financials.milestone_2_condition}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>

                <Paper sx={{ p: 1.5, bgcolor: 'rgba(0, 255, 163, 0.05)', borderRadius: '8px', border: '1px solid rgba(0, 255, 163, 0.2)' }}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <SecurityIcon sx={{ color: '#00FFA3', fontSize: 18 }} />
                    <Typography variant="caption" sx={{ color: '#CBD5E1', lineHeight: 1.4 }}>
                      <strong>Escrow Security:</strong> {pitchPack.bounty_financials.escrow_guarantee}
                    </Typography>
                  </Stack>
                </Paper>
              </Paper>

              {/* Hiring Manager Referral Note */}
              <Paper
                sx={{
                  p: 3,
                  bgcolor: '#0D131F',
                  border: '1.5px solid rgba(0, 255, 163, 0.25)',
                  borderRadius: '16px',
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00FFA3', display: 'flex', alignItems: 'center', gap: 1 }}>
                    <EmailIcon sx={{ color: '#00FFA3' }} /> Internal Hiring Manager Referral Email
                  </Typography>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<CopyIcon />}
                    onClick={() => copyToClipboard(pitchPack.hiring_manager_referral_email, 'Referral Email')}
                    sx={{ color: '#00FFA3', borderColor: 'rgba(0, 255, 163, 0.4)', textTransform: 'none', fontWeight: 800 }}
                  >
                    Copy Email
                  </Button>
                </Stack>

                <Paper
                  sx={{
                    p: 2,
                    bgcolor: '#06090E',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    maxHeight: '260px',
                    overflowY: 'auto',
                  }}
                >
                  <Typography component="pre" sx={{ color: '#E2E8F0', fontFamily: 'monospace', fontSize: '0.75rem', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                    {pitchPack.hiring_manager_referral_email}
                  </Typography>
                </Paper>
              </Paper>

              {/* LinkedIn / Peer Outreach Script */}
              <Paper
                sx={{
                  p: 3,
                  bgcolor: '#0D131F',
                  border: '1.5px solid rgba(0, 240, 255, 0.25)',
                  borderRadius: '16px',
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00F0FF' }}>
                    💬 Warm LinkedIn / Telegram Outreach Message
                  </Typography>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<CopyIcon />}
                    onClick={() => copyToClipboard(pitchPack.peer_outreach_script, 'Outreach Script')}
                    sx={{ color: '#00F0FF', borderColor: 'rgba(0, 240, 255, 0.4)', textTransform: 'none', fontWeight: 800 }}
                  >
                    Copy Script
                  </Button>
                </Stack>

                <Paper
                  sx={{
                    p: 2,
                    bgcolor: '#06090E',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    maxHeight: '180px',
                    overflowY: 'auto',
                  }}
                >
                  <Typography component="pre" sx={{ color: '#CBD5E1', fontFamily: 'monospace', fontSize: '0.75rem', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                    {pitchPack.peer_outreach_script}
                  </Typography>
                </Paper>
              </Paper>
            </Stack>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress size={30} sx={{ color: '#FFE600' }} />
            </Box>
          )}
        </Grid>
      </Grid>

      {/* Live Bounty Listings Grid */}
      <Card sx={{ bgcolor: '#0D131F', border: '1.5px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC', mb: 2 }}>
            🎯 Verified Referral Bounty Opportunities ($1,000 – $7,500 USD)
          </Typography>

          <Grid container spacing={2}>
            {listings.map((l) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={l.bounty_id}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    bgcolor: '#06090E',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <Box>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 800, color: '#FFE600' }}>
                        {l.company_name}
                      </Typography>
                      <Chip
                        label={`$${l.bounty_amount_usd.toLocaleString()} USD`}
                        size="small"
                        sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontSize: '0.68rem', fontWeight: 800 }}
                      />
                    </Stack>

                    <Typography variant="caption" sx={{ color: '#F8FAFC', fontWeight: 700, display: 'block', mb: 0.5 }}>
                      {l.role_title}
                    </Typography>

                    <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 1 }}>
                      📍 {l.location} | Team: {l.hiring_manager_team}
                    </Typography>

                    <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5} sx={{ mb: 1.5 }}>
                      {l.tech_stack.map((t) => (
                        <Chip
                          key={t}
                          label={t}
                          size="small"
                          sx={{ bgcolor: 'rgba(255,255,255,0.05)', color: '#94A3B8', fontSize: '0.62rem', height: 18 }}
                        />
                      ))}
                    </Stack>
                  </Box>

                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<WorkIcon />}
                    onClick={() => selectBounty(l)}
                    sx={{ color: '#00FFA3', borderColor: 'rgba(0, 255, 163, 0.3)', textTransform: 'none', fontSize: '0.72rem', fontWeight: 800 }}
                  >
                    Select & Synthesize Pitch Pack
                  </Button>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

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

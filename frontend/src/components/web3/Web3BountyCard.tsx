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
  CurrencyBitcoin as Web3Icon,
  ContentCopy as CopyIcon,
  Send as SendIcon,
  CheckCircle as CheckIcon,
  Terminal as CodeIcon,
} from '@mui/icons-material';
import {
  sprint5Api,
  type Web3BountyListing,
  type Web3ProposalResponse,
} from '../../api/endpoints/sprint5_api';

export const Web3BountyCard: React.FC = () => {
  const [bounties, setBounties] = useState<Web3BountyListing[]>([]);
  const [selectedBountyId, setSelectedBountyId] = useState('bounty_solana_blinks_01');
  const [candidateName, setCandidateName] = useState('Ujjwal');
  const [architecture, setArchitecture] = useState(
    'Memory-bounded ring buffer + tokio async actor worker pool with sub-10ms P99 indexing latency.'
  );
  const [timelineDays, setTimelineDays] = useState<number>(10);
  const [githubUrl, setGithubUrl] = useState('https://github.com/ujjwal-sovereign');

  const [loading, setLoading] = useState(false);
  const [proposal, setProposal] = useState<Web3ProposalResponse | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMsg, setSnackbarMsg] = useState('');

  useEffect(() => {
    sprint5Api.getWeb3Bounties().then((res) => {
      if (res && res.bounties) {
        setBounties(res.bounties);
        if (res.bounties.length > 0) {
          handleSynthesizeProposal(res.bounties[0].bounty_id);
        }
      }
    }).catch(console.error);
  }, []);

  const handleSynthesizeProposal = async (bountyId = selectedBountyId) => {
    setLoading(true);
    try {
      const res = await sprint5Api.synthesizeWeb3Proposal({
        bounty_id: bountyId,
        candidate_name: candidateName,
        proposed_architecture: architecture,
        timeline_days: timelineDays,
        github_profile: githubUrl,
      });
      setProposal(res);
    } catch (err) {
      console.error('Failed to synthesize proposal:', err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setSnackbarMsg(`Copied ${label} to clipboard!`);
    setSnackbarOpen(true);
  };

  const selectBounty = (b: Web3BountyListing) => {
    setSelectedBountyId(b.bounty_id);
    handleSynthesizeProposal(b.bounty_id);
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header Card */}
      <Card
        sx={{
          mb: 3,
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 255, 163, 0.3)',
          borderRadius: '16px',
          boxShadow: '0 0 30px rgba(0, 255, 163, 0.12)',
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
                    bgcolor: 'rgba(0, 255, 163, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #00FFA3',
                  }}
                >
                  <Web3Icon sx={{ color: '#00FFA3', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    ⚡ Web3 & Open-Source Bounty Harvester (Agent 22)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Scan ecosystem grants and OSS bounties ($500–$25,000 USD on Solana, Ethereum, Arbitrum), with automated RFC proposals.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip
                label="$500 – $25k Bounties"
                sx={{ bgcolor: 'rgba(0, 255, 163, 0.2)', color: '#00FFA3', fontWeight: 900, fontSize: '0.8rem' }}
              />
              <Chip
                label="Solana • ETH • OSS"
                sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800, fontSize: '0.75rem' }}
              />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Main Two Column Proposal Generator */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Left: Input Parameters */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper
            sx={{
              p: 3,
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '16px',
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00FFA3', mb: 2 }}>
              ⚙️ Proposal Parameters & Architecture
            </Typography>

            <Stack spacing={2}>
              <TextField
                size="small"
                label="Author / Contributor Name"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                multiline
                rows={3}
                size="small"
                label="Technical Architecture & Implementation Approach"
                value={architecture}
                onChange={(e) => setArchitecture(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Grid container spacing={2}>
                <Grid size={{ xs: 6 }}>
                  <TextField
                    size="small"
                    type="number"
                    label="Estimated Delivery Days"
                    value={timelineDays}
                    onChange={(e) => setTimelineDays(Number(e.target.value))}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField
                    size="small"
                    label="GitHub Profile URL"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
              </Grid>

              <Button
                variant="contained"
                disabled={loading}
                onClick={() => handleSynthesizeProposal(selectedBountyId)}
                startIcon={loading ? <CircularProgress size={18} sx={{ color: '#06090E' }} /> : <SendIcon />}
                sx={{
                  bgcolor: '#00FFA3',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  py: 1.2,
                  '&:hover': { bgcolor: '#00D88B' },
                }}
              >
                {loading ? 'Synthesizing RFC Proposal...' : 'Synthesize Formal Bounty RFC'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* Right: Proposal Preview */}
        <Grid size={{ xs: 12, md: 7 }}>
          {proposal ? (
            <Paper
              sx={{
                p: 3,
                bgcolor: '#0D131F',
                border: '1.5px solid rgba(0, 255, 163, 0.3)',
                borderRadius: '16px',
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                  📄 Formal Grant / PR RFC Proposal
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Chip
                    label={`$${proposal.reward_usd.toLocaleString()} (~₹${proposal.reward_inr_lakhs}L)`}
                    sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 900 }}
                  />
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<CopyIcon />}
                    onClick={() => copyToClipboard(proposal.proposal_markdown, 'RFC Proposal')}
                    sx={{ color: '#00FFA3', borderColor: 'rgba(0, 255, 163, 0.4)', textTransform: 'none', fontWeight: 800 }}
                  >
                    Copy Markdown
                  </Button>
                </Stack>
              </Stack>

              <Paper
                sx={{
                  p: 2,
                  bgcolor: '#06090E',
                  borderRadius: '10px',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  maxHeight: '360px',
                  overflowY: 'auto',
                  mb: 2,
                }}
              >
                <Typography component="pre" sx={{ color: '#E2E8F0', fontFamily: 'monospace', fontSize: '0.75rem', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                  {proposal.proposal_markdown}
                </Typography>
              </Paper>

              <Paper sx={{ p: 1.5, bgcolor: 'rgba(0, 240, 255, 0.05)', borderRadius: '8px', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
                <Typography variant="caption" sx={{ color: '#CBD5E1' }}>
                  🚀 <strong>Action:</strong> {proposal.action_summary}
                </Typography>
              </Paper>
            </Paper>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress size={30} sx={{ color: '#00FFA3' }} />
            </Box>
          )}
        </Grid>
      </Grid>

      {/* Curated Bounties Directory Grid */}
      <Card sx={{ bgcolor: '#0D131F', border: '1.5px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC', mb: 2 }}>
            🌐 Live High-Dollar Web3 & Open-Source Bounties ($500 – $12,000 USD)
          </Typography>

          <Grid container spacing={2}>
            {bounties.map((b) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={b.bounty_id}>
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
                      <Chip label={b.ecosystem} size="small" sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontSize: '0.65rem', fontWeight: 800 }} />
                      <Chip
                        label={`$${b.reward_usd.toLocaleString()} ${b.token}`}
                        size="small"
                        sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontSize: '0.68rem', fontWeight: 900 }}
                      />
                    </Stack>

                    <Typography variant="body2" sx={{ fontWeight: 800, color: '#F8FAFC', mb: 0.5 }}>
                      {b.title}
                    </Typography>

                    <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 1 }}>
                      🏛️ {b.organization} | ⏳ {b.deadline_days_left} days left
                    </Typography>

                    <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5} sx={{ mb: 1.5 }}>
                      {b.skills_required.map((s) => (
                        <Chip
                          key={s}
                          label={s}
                          size="small"
                          sx={{ bgcolor: 'rgba(255,255,255,0.05)', color: '#CBD5E1', fontSize: '0.62rem', height: 18 }}
                        />
                      ))}
                    </Stack>
                  </Box>

                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<CodeIcon />}
                    onClick={() => selectBounty(b)}
                    sx={{ color: '#00FFA3', borderColor: 'rgba(0, 255, 163, 0.3)', textTransform: 'none', fontSize: '0.72rem', fontWeight: 800 }}
                  >
                    Select & Synthesize RFC
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

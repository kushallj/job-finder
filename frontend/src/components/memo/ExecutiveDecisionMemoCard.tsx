import React, { useState } from 'react';
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
  Description as MemoIcon,
  ContentCopy as CopyIcon,
  AttachMoney as DollarIcon,
  Email as EmailIcon,
  Send as SendIcon,
  Security as LeverageIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material';
import { sprint4Api, type ExecutiveMemoResponse } from '../../api/endpoints/sprint4_api';

export const ExecutiveDecisionMemoCard: React.FC = () => {
  const [candidateName, setCandidateName] = useState('Ujjwal / Sovereign Engineer');
  const [companyName, setCompanyName] = useState('Acme AI / Stripe');
  const [roleTitle, setRoleTitle] = useState('Senior Staff Distributed Systems Engineer');
  const [interviewStage, setInterviewStage] = useState('Final Hiring Manager & VP Bar-Raiser Debrief');
  const [topics, setTopics] = useState('Raft Consensus, O(1) Cache Eviction, Distributed Lock Sharding, Zero-Downtime Migration');
  const [p99Metric, setP99Metric] = useState('Reduced P99 tail latency by 64% and cut annual cloud compute bill by ,000');
  const [competingOffer, setCompetingOffer] = useState('Competing Tier-1 Offer at ₹75 LPA (,000 USD)');
  const [targetLpa, setTargetLpa] = useState<number>(70);

  const [loading, setLoading] = useState(false);
  const [memoData, setMemoData] = useState<ExecutiveMemoResponse | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMsg, setSnackbarMsg] = useState('');

  const handleSynthesizeMemo = async () => {
    if (!companyName.trim()) return;
    setLoading(true);
    try {
      const topicList = topics.split(',').map((t) => t.trim()).filter(Boolean);
      const res = await sprint4Api.synthesizeExecutiveMemo({
        candidate_name: candidateName,
        company_name: companyName,
        role_title: roleTitle,
        interview_stage: interviewStage,
        key_technical_topics: topicList,
        p99_impact_metric: p99Metric,
        competing_offer_anchor: competingOffer,
        target_compensation_lpa: targetLpa,
      });
      setMemoData(res);
    } catch (err) {
      console.error('Failed to generate memo:', err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setSnackbarMsg(`Copied ${label} to clipboard!`);
    setSnackbarOpen(true);
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header Card */}
      <Card
        sx={{
          mb: 3,
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 240, 255, 0.3)',
          borderRadius: '16px',
          boxShadow: '0 0 30px rgba(0, 240, 255, 0.12)',
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
                    bgcolor: 'rgba(0, 240, 255, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #00F0FF',
                  }}
                >
                  <MemoIcon sx={{ color: '#00F0FF', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    📑 The Executive Decision Memo Closer (Agent 23)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Reverse-engineer the hiring team's ,300 hiring investment and generate a 1-page executive justification memo.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip
                label=",300 Sunk Cost Defense"
                sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 900, fontSize: '0.78rem' }}
              />
              <Chip
                label="Hiring Manager Co-Pilot"
                sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800, fontSize: '0.75rem' }}
              />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Input Parameters & Generator Controls */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper
            sx={{
              p: 3,
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '16px',
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00F0FF', mb: 2 }}>
              ⚙️ Deal Parameters & Candidate Leverage
            </Typography>

            <Stack spacing={2}>
              <TextField
                size="small"
                label="Candidate Full Name"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                label="Target Company / Organization"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                label="Target Role / Designation"
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                label="Interview Stage"
                value={interviewStage}
                onChange={(e) => setInterviewStage(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                label="P99 Production Impact Metric"
                value={p99Metric}
                onChange={(e) => setP99Metric(e.target.value)}
                helperText="Quantifiable metric proving 10x ROI (latency, cloud bills, revenue)"
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                size="small"
                label="Competing Offer Anchor"
                value={competingOffer}
                onChange={(e) => setCompetingOffer(e.target.value)}
                helperText="BATNA leverage anchor to justify urgent executive approval"
                sx={{ bgcolor: '#06090E' }}
              />

              <Grid container spacing={2}>
                <Grid size={{ xs: 6 }}>
                  <TextField
                    size="small"
                    type="number"
                    label="Target CTC (LPA)"
                    value={targetLpa}
                    onChange={(e) => setTargetLpa(Number(e.target.value))}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <Paper
                    sx={{
                      p: 1,
                      bgcolor: '#06090E',
                      borderRadius: '8px',
                      textAlign: 'center',
                      border: '1px solid rgba(255,255,255,0.06)',
                    }}
                  >
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.65rem' }}>
                      USD EQUIVALENT
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#00FFA3', fontWeight: 900 }}>
                      ~$${Math.round((targetLpa * 100000) / 86.5).toLocaleString()}/yr
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>

              <TextField
                multiline
                rows={2}
                size="small"
                label="Key Technical Topics Covered (comma-separated)"
                value={topics}
                onChange={(e) => setTopics(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Button
                variant="contained"
                disabled={loading || !companyName.trim()}
                onClick={handleSynthesizeMemo}
                startIcon={loading ? <CircularProgress size={18} sx={{ color: '#06090E' }} /> : <SendIcon />}
                sx={{
                  bgcolor: '#00F0FF',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  py: 1.2,
                  '&:hover': { bgcolor: '#00C8D6' },
                }}
              >
                {loading ? 'Synthesizing ROI Decision Memo...' : 'Synthesize 1-Page Executive Memo'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* Right: Cost-Per-Hire Breakdown & Sunk Investment Analysis */}
        <Grid size={{ xs: 12, md: 7 }}>
          {memoData ? (
            <Stack spacing={3}>
              {/* Sunk Investment Card */}
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
                    <DollarIcon sx={{ color: '#FFE600' }} /> Sunk Enterprise Cost-Per-Hire Calculator
                  </Typography>
                  <Chip
                    label={`₹${memoData.cost_analysis.total_hiring_investment_inr_lakhs} Lakhs (~$${memoData.cost_analysis.total_usd_equivalent.toLocaleString()} USD)`}
                    sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 900, border: '1px solid #FFE600' }}
                  />
                </Stack>

                <Grid container spacing={1.5} sx={{ mb: 2 }}>
                  <Grid size={{ xs: 6, sm: 3 }}>
                    <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.65rem', display: 'block' }}>
                        AGENCY COMM.
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#F8FAFC', fontWeight: 800, mt: 0.5 }}>
                        {memoData.cost_analysis.breakdown.agency_recruiter_commission}
                      </Typography>
                    </Paper>
                  </Grid>

                  <Grid size={{ xs: 6, sm: 3 }}>
                    <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.65rem', display: 'block' }}>
                        ENG TIME (40+ HRS)
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#F8FAFC', fontWeight: 800, mt: 0.5 }}>
                        {memoData.cost_analysis.breakdown.engineering_team_interview_hours}
                      </Typography>
                    </Paper>
                  </Grid>

                  <Grid size={{ xs: 6, sm: 3 }}>
                    <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.65rem', display: 'block' }}>
                        ATS INFRA
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#F8FAFC', fontWeight: 800, mt: 0.5 }}>
                        {memoData.cost_analysis.breakdown.ats_sourcing_infrastructure}
                      </Typography>
                    </Paper>
                  </Grid>

                  <Grid size={{ xs: 6, sm: 3 }}>
                    <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.65rem', display: 'block' }}>
                        VACANCY COST / MO
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#00FFA3', fontWeight: 800, mt: 0.5 }}>
                        {memoData.cost_analysis.breakdown.cost_of_empty_seat_per_month}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>

                <Paper sx={{ p: 1.5, bgcolor: 'rgba(0, 255, 163, 0.05)', borderRadius: '8px', border: '1px solid rgba(0, 255, 163, 0.2)' }}>
                  <Stack direction="row" spacing={1} alignItems="flex-start">
                    <LeverageIcon sx={{ color: '#00FFA3', fontSize: 18, mt: 0.2 }} />
                    <Typography variant="caption" sx={{ color: '#CBD5E1', lineHeight: 1.5 }}>
                      <strong>Strategic Leverage:</strong> {memoData.strategic_leverage_summary}
                    </Typography>
                  </Stack>
                </Paper>
              </Paper>

              {/* 1-Page Markdown Executive Memo */}
              <Paper
                sx={{
                  p: 3,
                  bgcolor: '#0D131F',
                  border: '1.5px solid rgba(0, 240, 255, 0.25)',
                  borderRadius: '16px',
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    📄 1-Page Executive Justification Memo (Ready for Hiring Manager / VP)
                  </Typography>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<CopyIcon />}
                    onClick={() => copyToClipboard(memoData.executive_memo_markdown, 'Executive Memo')}
                    sx={{
                      color: '#00F0FF',
                      borderColor: 'rgba(0, 240, 255, 0.4)',
                      textTransform: 'none',
                      fontWeight: 800,
                    }}
                  >
                    Copy Markdown
                  </Button>
                </Stack>

                <Paper
                  sx={{
                    p: 2,
                    bgcolor: '#06090E',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    maxHeight: '380px',
                    overflowY: 'auto',
                  }}
                >
                  <Typography
                    component="pre"
                    sx={{
                      color: '#E2E8F0',
                      fontFamily: 'monospace',
                      fontSize: '0.76rem',
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.5,
                    }}
                  >
                    {memoData.executive_memo_markdown}
                  </Typography>
                </Paper>
              </Paper>

              {/* Follow-up Email Template */}
              <Paper
                sx={{
                  p: 3,
                  bgcolor: '#0D131F',
                  border: '1.5px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '16px',
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00FFA3', display: 'flex', alignItems: 'center', gap: 1 }}>
                    <EmailIcon sx={{ color: '#00FFA3' }} /> 2-Hour Post-Debrief Hiring Manager Follow-Up Email
                  </Typography>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<CopyIcon />}
                    onClick={() => copyToClipboard(memoData.followup_email, 'Follow-up Email')}
                    sx={{
                      color: '#00FFA3',
                      borderColor: 'rgba(0, 255, 163, 0.4)',
                      textTransform: 'none',
                      fontWeight: 800,
                    }}
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
                    maxHeight: '220px',
                    overflowY: 'auto',
                  }}
                >
                  <Typography
                    component="pre"
                    sx={{
                      color: '#CBD5E1',
                      fontFamily: 'monospace',
                      fontSize: '0.76rem',
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.5,
                    }}
                  >
                    {memoData.followup_email}
                  </Typography>
                </Paper>
              </Paper>
            </Stack>
          ) : (
            <Paper
              sx={{
                p: 5,
                bgcolor: '#0D131F',
                border: '1.5px dashed rgba(255, 255, 255, 0.15)',
                borderRadius: '16px',
                textAlign: 'center',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <MemoIcon sx={{ fontSize: 48, color: '#64748B', mb: 2 }} />
              <Typography variant="h6" sx={{ color: '#94A3B8', fontWeight: 800, mb: 1 }}>
                Synthesize Hiring Manager Closing Memo
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748B', maxWidth: '400px', mb: 3 }}>
                Fill in the candidate leverage parameters on the left and click "Synthesize 1-Page Executive Memo" to calculate enterprise hiring costs and generate the closure package.
              </Typography>
              <Button
                variant="outlined"
                onClick={handleSynthesizeMemo}
                sx={{
                  color: '#00F0FF',
                  borderColor: 'rgba(0, 240, 255, 0.4)',
                  fontWeight: 800,
                  textTransform: 'none',
                }}
              >
                Generate with Sample Parameters
              </Button>
            </Paper>
          )}
        </Grid>
      </Grid>

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

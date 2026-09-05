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
  Slider,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Sensors as RadarIcon,
  CheckCircle as VerifiedIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  Send as SendIcon,
} from '@mui/icons-material';
import {
  sprint3Api,
  type AntiGhostingEscalationResponse,
  type CompanySlaBenchmark,
} from '../../api/endpoints/sprint3_api';

export const AntiGhostingSlaCard: React.FC = () => {
  const [companyName, setCompanyName] = useState('Pine Labs');
  const [interviewStage, setInterviewStage] = useState('System Design / Round 2');
  const [daysElapsed, setDaysElapsed] = useState<number>(4);
  const [recruiterName, setRecruiterName] = useState('Ananya (Tech Recruiting)');
  const [candidateLeverage, setCandidateLeverage] = useState('Has Competing Timelines');
  const [competingCompany, setCompetingCompany] = useState('Cashfree Payments');

  const [loading, setLoading] = useState(false);
  const [escalationData, setEscalationData] = useState<AntiGhostingEscalationResponse | null>(null);
  const [communityCompanies, setCommunityCompanies] = useState<CompanySlaBenchmark[]>([]);
  const [copiedTier, setCopiedTier] = useState<number | null>(null);

  useEffect(() => {
    sprint3Api.getSlaIndex().then((res) => {
      if (res && res.companies) {
        setCommunityCompanies(res.companies);
      }
    }).catch(console.error);

    // Initial calculation
    handleSynthesize();
  }, []);

  const handleSynthesize = async () => {
    if (!companyName.trim()) return;
    setLoading(true);
    try {
      const res = await sprint3Api.synthesizeEscalation({
        company_name: companyName,
        interview_stage: interviewStage,
        days_elapsed: daysElapsed,
        recruiter_name: recruiterName,
        candidate_leverage: candidateLeverage,
        competing_company: competingCompany,
      });
      setEscalationData(res);
    } catch (err) {
      console.error('Escalation synthesis failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (subject: string, body: string, tier: number) => {
    const fullText = `Subject: ${subject}\n\n${body}`;
    navigator.clipboard.writeText(fullText);
    setCopiedTier(tier);
    setTimeout(() => setCopiedTier(null), 2500);
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
          boxShadow: '0 0 30px rgba(0, 240, 255, 0.1)',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2}>
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
                  <RadarIcon sx={{ color: '#00F0FF', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    📡 Anti-Ghosting SLA & Recruiter Escalation Engine (Agent 18)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Monitors timeline decay, calculates ghosting risk %, and generates calibrated 3-tier leverage escalation emails.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip label="72h SLA Benchmark" sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 800, fontSize: '0.75rem' }} />
              <Chip label="Community Velocity Radar" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, fontSize: '0.75rem' }} />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Control Grid */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Left Column: Input Form */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper sx={{ p: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00F0FF', mb: 2 }}>
              ⏱️ Interview Stage & Timeline Status
            </Typography>

            <Stack spacing={2}>
              <TextField
                fullWidth
                size="small"
                label="Target Company Name"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Stack direction="row" spacing={0.8} flexWrap="wrap">
                {['Pine Labs', 'Cashfree', 'Ather Energy', 'CRED', 'Swiggy', 'Razorpay'].map((comp) => (
                  <Chip
                    key={comp}
                    label={comp}
                    size="small"
                    clickable
                    onClick={() => setCompanyName(comp)}
                    sx={{
                      fontWeight: 800,
                      fontSize: '0.7rem',
                      bgcolor: companyName === comp ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255,255,255,0.05)',
                      color: companyName === comp ? '#00F0FF' : '#94A3B8',
                      border: `1px solid ${companyName === comp ? '#00F0FF' : 'transparent'}`,
                      mb: 0.5,
                    }}
                  />
                ))}
              </Stack>

              <TextField
                fullWidth
                size="small"
                label="Interview Stage Completed"
                value={interviewStage}
                onChange={(e) => setInterviewStage(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Box>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                  <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700 }}>
                    Days Elapsed Since Interview:
                  </Typography>
                  <Typography variant="body2" sx={{ color: daysElapsed > 6 ? '#FF0055' : daysElapsed > 3 ? '#FFE600' : '#00FFA3', fontWeight: 900 }}>
                    {daysElapsed} Days ({daysElapsed * 24} Hours)
                  </Typography>
                </Stack>
                <Slider
                  value={daysElapsed}
                  min={0}
                  max={14}
                  step={1}
                  onChange={(_, val) => setDaysElapsed(val as number)}
                  sx={{
                    color: daysElapsed > 6 ? '#FF0055' : daysElapsed > 3 ? '#FFE600' : '#00FFA3',
                  }}
                />
              </Box>

              <TextField
                fullWidth
                size="small"
                label="Recruiter Name / Contact"
                value={recruiterName}
                onChange={(e) => setRecruiterName(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                fullWidth
                size="small"
                label="Candidate Leverage Context"
                value={candidateLeverage}
                onChange={(e) => setCandidateLeverage(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                fullWidth
                size="small"
                label="Competing Company Name (Leverage Anchor)"
                value={competingCompany}
                onChange={(e) => setCompetingCompany(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Button
                variant="contained"
                disabled={loading || !companyName.trim()}
                onClick={handleSynthesize}
                startIcon={loading ? <CircularProgress size={18} sx={{ color: '#06090E' }} /> : <SendIcon />}
                sx={{
                  bgcolor: '#00F0FF',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  py: 1.2,
                  '&:hover': { bgcolor: '#00D8E6' },
                }}
              >
                {loading ? 'Evaluating SLA...' : 'Synthesize Escalation Drafts'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* Right Column: Ghosting Risk Gauges & 3-Tier Escalation Scripts */}
        <Grid size={{ xs: 12, md: 7 }}>
          {escalationData && (
            <Stack spacing={2.5}>
              {/* SLA Radar Status Strip */}
              <Paper
                sx={{
                  p: 2.5,
                  bgcolor: '#0D131F',
                  border: `1.5px solid ${escalationData.risk_metrics.sla_color}`,
                  borderRadius: '16px',
                }}
              >
                <Grid container spacing={2} alignItems="center">
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                      TIMELINE SLA STATUS
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 900, color: escalationData.risk_metrics.sla_color, mt: 0.5 }}>
                      {escalationData.risk_metrics.sla_status}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#CBD5E1' }}>
                      {escalationData.company_sla_benchmark.company_name} avg turnaround: {escalationData.company_sla_benchmark.avg_feedback_turnaround_hours}h
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }} sx={{ textAlign: { sm: 'right' } }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                      ESTIMATED GHOSTING RISK
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 900, color: escalationData.risk_metrics.sla_color, my: 0.5, fontFamily: 'monospace' }}>
                      {escalationData.risk_metrics.ghosting_risk_percent}%
                    </Typography>
                    <Chip
                      label={escalationData.company_sla_benchmark.tier_rating}
                      size="small"
                      sx={{ bgcolor: 'rgba(255,255,255,0.06)', color: '#CBD5E1', fontSize: '0.65rem' }}
                    />
                  </Grid>
                </Grid>
              </Paper>

              {/* 3 Escalation Tiers */}
              <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#FFE600' }}>
                ✉️ Calibrated 3-Tier Follow-Up Escalation Scripts
              </Typography>

              {escalationData.escalation_tiers.map((tier) => (
                <Paper
                  key={tier.tier_level}
                  sx={{
                    p: 2.5,
                    bgcolor: '#06090E',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '14px',
                    position: 'relative',
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                        {tier.tier_name}
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                        {tier.strategic_intent}
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      startIcon={copiedTier === tier.tier_level ? <CheckIcon /> : <CopyIcon />}
                      onClick={() => handleCopy(tier.subject, tier.body, tier.tier_level)}
                      sx={{
                        bgcolor: copiedTier === tier.tier_level ? '#00FFA3' : 'rgba(255, 255, 255, 0.1)',
                        color: copiedTier === tier.tier_level ? '#06090E' : '#F8FAFC',
                        fontWeight: 800,
                        textTransform: 'none',
                        fontSize: '0.75rem',
                      }}
                    >
                      {copiedTier === tier.tier_level ? 'Copied Email!' : 'Copy Script'}
                    </Button>
                  </Stack>

                  <Typography variant="caption" sx={{ color: '#FFE600', fontWeight: 700, display: 'block', mb: 0.5 }}>
                    Subject: {tier.subject}
                  </Typography>

                  <Typography component="pre" sx={{ color: '#CBD5E1', fontFamily: 'monospace', fontSize: '0.78rem', whiteSpace: 'pre-wrap', lineHeight: 1.45, bgcolor: 'rgba(255,255,255,0.02)', p: 1.5, borderRadius: '8px' }}>
                    {tier.body}
                  </Typography>
                </Paper>
              ))}
            </Stack>
          )}
        </Grid>
      </Grid>

      {/* Community Hiring SLA Benchmark Index */}
      <Card
        sx={{
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '16px',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                📊 Community Tech Employer Hiring Velocity Index
              </Typography>
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                Real-world SLA feedback turnaround times & verified fast-track candidate response ratings.
              </Typography>
            </Box>
            <Chip icon={<VerifiedIcon />} label="Fast-Track Verified: <72h SLA" size="small" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800 }} />
          </Stack>

          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ color: '#94A3B8', fontWeight: 800, borderColor: 'rgba(255,255,255,0.08)' }}>Company Name</TableCell>
                  <TableCell sx={{ color: '#94A3B8', fontWeight: 800, borderColor: 'rgba(255,255,255,0.08)' }}>Avg Turnaround</TableCell>
                  <TableCell sx={{ color: '#94A3B8', fontWeight: 800, borderColor: 'rgba(255,255,255,0.08)' }}>Ghosting Rate</TableCell>
                  <TableCell sx={{ color: '#94A3B8', fontWeight: 800, borderColor: 'rgba(255,255,255,0.08)' }}>Recruiter Responsiveness</TableCell>
                  <TableCell sx={{ color: '#94A3B8', fontWeight: 800, borderColor: 'rgba(255,255,255,0.08)' }}>Badge</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {communityCompanies.map((c) => (
                  <TableRow key={c.company_name} hover sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.03)' } }}>
                    <TableCell sx={{ color: '#F8FAFC', fontWeight: 800, borderColor: 'rgba(255,255,255,0.08)' }}>
                      {c.company_name}
                    </TableCell>
                    <TableCell sx={{ color: '#00FFA3', fontWeight: 700, borderColor: 'rgba(255,255,255,0.08)' }}>
                      ⚡ {c.avg_feedback_turnaround_hours}h
                    </TableCell>
                    <TableCell sx={{ color: c.ghosting_rate_percent > 12 ? '#FF0055' : '#00F0FF', fontWeight: 700, borderColor: 'rgba(255,255,255,0.08)' }}>
                      {c.ghosting_rate_percent}%
                    </TableCell>
                    <TableCell sx={{ color: '#CBD5E1', fontSize: '0.8rem', borderColor: 'rgba(255,255,255,0.08)' }}>
                      {c.recruiter_responsiveness}
                    </TableCell>
                    <TableCell sx={{ borderColor: 'rgba(255,255,255,0.08)' }}>
                      {c.is_verified_fast_track ? (
                        <Chip label="Verified Fast-Track" size="small" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, fontSize: '0.65rem' }} />
                      ) : (
                        <Chip label="Standard SLA" size="small" sx={{ bgcolor: 'rgba(255, 255, 255, 0.06)', color: '#94A3B8', fontSize: '0.65rem' }} />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

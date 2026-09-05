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
} from '@mui/material';
import {
  MonetizationOn as MoneyIcon,
  Psychology as AiIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  OpenInNew as OpenIcon,
  PlayArrow as TestIcon,
} from '@mui/icons-material';
import {
  sprint4Api,
  type FrontierPlatform,
  type FrontierBenchmarkResponse,
  type CodeEvalChallenge,
} from '../../api/endpoints/sprint4_api';

const PRESET_CRITIQUES = [
  {
    title: '🌟 Principal RLHF Critique (100% Score)',
    text: '1. Critical Big-O Bug: get() performs self.order.remove(key) which is an O(N) linear array scan, violating the strict O(1) requirement. 2. Critical Big-O Bug: put() eviction calls self.order.pop(0) which takes O(N) time due to array shifting. 3. Optimal Architecture: Must use a Doubly-Linked List with Node pointers + Hash Map, or Python collections.OrderedDict for true O(1) get/put/evict. 4. Edge Case: Validate capacity <= 0 and handle negative integer input defensively. 5. Concurrency: Add threading.Lock or asyncio mutex to prevent race conditions during concurrent cache evictions.',
  },
  {
    title: '🟡 Intermediate Critique (60% Score)',
    text: 'The code uses a regular list self.order to track keys which makes remove() slow and O(N). We should use an OrderedDict or doubly linked list instead so that lookups and updates are fast.',
  },
];

export const FrontierAiRadarCard: React.FC = () => {
  const [platforms, setPlatforms] = useState<FrontierPlatform[]>([]);
  const [challenge, setChallenge] = useState<CodeEvalChallenge | null>(null);
  const [critiqueText, setCritiqueText] = useState(PRESET_CRITIQUES[0].text);
  const [weeklyHours, setWeeklyHours] = useState<number>(15);
  const [benchmarkResult, setBenchmarkResult] = useState<FrontierBenchmarkResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    sprint4Api.getPlatforms().then((res) => {
      if (res && res.platforms) setPlatforms(res.platforms);
    }).catch(console.error);

    sprint4Api.getSampleChallenge().then((res) => {
      if (res && res.challenge) setChallenge(res.challenge);
    }).catch(console.error);

    // Initial evaluation
    handleRunBenchmark(PRESET_CRITIQUES[0].text, 15);
  }, []);

  const handleRunBenchmark = async (textToEval = critiqueText, hours = weeklyHours) => {
    if (!textToEval.trim()) return;
    setLoading(true);
    try {
      const res = await sprint4Api.evaluateBenchmark({
        critique_text: textToEval,
        weekly_hours_available: hours,
        usd_to_inr_rate: 86.5,
      });
      setBenchmarkResult(res);
    } catch (err) {
      console.error('Benchmark failed:', err);
    } finally {
      setLoading(false);
    }
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
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2}>
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
                  <MoneyIcon sx={{ color: '#00FFA3', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    🌐 Frontier AI & RLHF High-Income Arbitrage Radar (Agent 19)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Access global USD post-training contracts ($40–$120/hr USD) across Outlier, Alignerr, Scale AI, and Mercor.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip label="$40 – $120/hr USD" sx={{ bgcolor: 'rgba(0, 255, 163, 0.2)', color: '#00FFA3', fontWeight: 900, fontSize: '0.8rem' }} />
              <Chip label="Direct USD Payouts" sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800, fontSize: '0.75rem' }} />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Simulator Section */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Left: Code-Eval Test Runner */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px', height: '100%' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00F0FF', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
              <AiIcon sx={{ color: '#00F0FF', fontSize: 20 }} /> Frontier AI Code-Evaluation Challenge
            </Typography>
            <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 2 }}>
              Critique this buggy LLM-generated code to qualify for Tier-1 evaluation projects:
            </Typography>

            {challenge && (
              <Paper sx={{ p: 1.8, bgcolor: '#06090E', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.08)', mb: 2 }}>
                <Typography component="pre" sx={{ color: '#FFE600', fontFamily: 'monospace', fontSize: '0.74rem', whiteSpace: 'pre-wrap', lineHeight: 1.4, maxHeight: '160px', overflowY: 'auto' }}>
                  {challenge.buggy_code}
                </Typography>
              </Paper>
            )}

            <Stack direction="row" spacing={1} sx={{ mb: 1.5 }}>
              {PRESET_CRITIQUES.map((p) => (
                <Chip
                  key={p.title}
                  label={p.title}
                  size="small"
                  clickable
                  onClick={() => {
                    setCritiqueText(p.text);
                    handleRunBenchmark(p.text, weeklyHours);
                  }}
                  sx={{ bgcolor: 'rgba(255,255,255,0.06)', color: '#CBD5E1', fontSize: '0.68rem', fontWeight: 700 }}
                />
              ))}
            </Stack>

            <TextField
              fullWidth
              multiline
              rows={3}
              label="Your Technical Critique & Architecture Proposal"
              value={critiqueText}
              onChange={(e) => setCritiqueText(e.target.value)}
              sx={{ bgcolor: '#06090E', mb: 2 }}
            />

            <Box sx={{ mb: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700 }}>
                  Available Hours per Week:
                </Typography>
                <Typography variant="body2" sx={{ color: '#00FFA3', fontWeight: 900 }}>
                  {weeklyHours} hrs/wk (~{Math.round(weeklyHours * 4.2)} hrs/mo)
                </Typography>
              </Stack>
              <Slider
                value={weeklyHours}
                min={5}
                max={35}
                step={5}
                onChange={(_, v) => {
                  setWeeklyHours(v as number);
                  handleRunBenchmark(critiqueText, v as number);
                }}
                sx={{ color: '#00FFA3' }}
              />
            </Box>

            <Button
              fullWidth
              variant="contained"
              disabled={loading || !critiqueText.trim()}
              onClick={() => handleRunBenchmark(critiqueText, weeklyHours)}
              startIcon={loading ? <CircularProgress size={18} sx={{ color: '#06090E' }} /> : <TestIcon />}
              sx={{
                bgcolor: '#00FFA3',
                color: '#06090E',
                fontWeight: 900,
                textTransform: 'none',
                py: 1,
                '&:hover': { bgcolor: '#00D88B' },
              }}
            >
              {loading ? 'Evaluating RLHF Rubric...' : 'Grade Evaluation & Calculate Cashflow'}
            </Button>
          </Paper>
        </Grid>

        {/* Right: Scorecard & Cashflow Projections */}
        <Grid size={{ xs: 12, md: 6 }}>
          {benchmarkResult && (
            <Paper sx={{ p: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 255, 163, 0.25)', borderRadius: '16px', height: '100%' }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                  📊 Evaluator Assessment & Income Projection
                </Typography>
                <Chip
                  label={`${benchmarkResult.benchmark_score} / 100`}
                  sx={{
                    bgcolor: 'rgba(0, 255, 163, 0.15)',
                    color: benchmarkResult.badge_color,
                    fontWeight: 900,
                    fontSize: '0.85rem',
                    border: `1px solid ${benchmarkResult.badge_color}`,
                  }}
                />
              </Stack>

              <Typography variant="body2" sx={{ color: benchmarkResult.badge_color, fontWeight: 800, mb: 2 }}>
                {benchmarkResult.tier_status}
              </Typography>

              {/* Earnings Cards */}
              <Grid container spacing={1.5} sx={{ mb: 2.5 }}>
                <Grid size={{ xs: 4 }}>
                  <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '10px', textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                      HOURLY RATE
                    </Typography>
                    <Typography variant="h6" sx={{ color: '#00FFA3', fontWeight: 900, my: 0.5, fontFamily: 'monospace' }}>
                      ${benchmarkResult.projected_hourly_rate_usd}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>USD / hour</Typography>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 4 }}>
                  <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '10px', textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                      MONTHLY CASH
                    </Typography>
                    <Typography variant="h6" sx={{ color: '#00F0FF', fontWeight: 900, my: 0.5, fontFamily: 'monospace' }}>
                      ${benchmarkResult.projections.monthly_usd.toLocaleString()}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>~₹{Math.round(benchmarkResult.projections.monthly_inr / 1000)}k/mo</Typography>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 4 }}>
                  <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '10px', textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                      ANNUAL RUNWAY
                    </Typography>
                    <Typography variant="h6" sx={{ color: '#FFE600', fontWeight: 900, my: 0.5, fontFamily: 'monospace' }}>
                      ₹{benchmarkResult.projections.annual_inr_lakhs}L
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>INR / year</Typography>
                  </Paper>
                </Grid>
              </Grid>

              {/* Rubric Checklist */}
              <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, mb: 1, display: 'block' }}>
                RLHF CODE-EVAL RUBRIC BREAKDOWN:
              </Typography>
              <Stack spacing={1}>
                {benchmarkResult.rubric_breakdown.map((r) => (
                  <Stack key={r.criterion} direction="row" spacing={1} alignItems="center">
                    {r.passed ? (
                      <CheckCircleIcon sx={{ color: '#00FFA3', fontSize: 16 }} />
                    ) : (
                      <CancelIcon sx={{ color: '#64748B', fontSize: 16 }} />
                    )}
                    <Typography variant="caption" sx={{ color: r.passed ? '#F8FAFC' : '#64748B', fontWeight: r.passed ? 700 : 400 }}>
                      {r.criterion} ({r.weight} pts)
                    </Typography>
                  </Stack>
                ))}
              </Stack>
            </Paper>
          )}
        </Grid>
      </Grid>

      {/* Curated Platform Directory Grid */}
      <Card sx={{ bgcolor: '#0D131F', border: '1.5px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC', mb: 2 }}>
            🏢 Curated Frontier AI Post-Training & Code Evaluation Platforms
          </Typography>

          <Grid container spacing={2}>
            {platforms.map((p) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={p.id}>
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
                      <Typography variant="body2" sx={{ fontWeight: 800, color: '#00FFA3' }}>
                        {p.name}
                      </Typography>
                      <Chip label={p.hourly_rate_range} size="small" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontSize: '0.65rem', fontWeight: 800 }} />
                    </Stack>
                    <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 1 }}>
                      {p.primary_focus}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#CBD5E1', display: 'block', fontSize: '0.65rem', mb: 1.5 }}>
                      💳 Payout: {p.payout_frequency} | Difficulty: {p.onboarding_difficulty}
                    </Typography>
                  </Box>

                  <Button
                    size="small"
                    variant="outlined"
                    endIcon={<OpenIcon />}
                    href={p.direct_apply_url}
                    target="_blank"
                    sx={{ color: '#00F0FF', borderColor: 'rgba(0, 240, 255, 0.3)', textTransform: 'none', fontSize: '0.72rem', fontWeight: 800 }}
                  >
                    Direct Platform Apply
                  </Button>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

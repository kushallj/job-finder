import React, { useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Divider, IconButton,
  Stack, TextField, Tooltip, Typography, MenuItem, Paper, Grid,
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  RequestQuote as RequestQuoteIcon,
  AccountBalanceWallet as WalletIcon,
  Calculate as CalculateIcon,
} from '@mui/icons-material';

import CompanySelect from './CompanySelect';
import { useNegotiationBenchmark, useNegotiationCounter } from '../../hooks/useAgents';
import { compSimulatorApi } from '../../api';
import type { CompSimulationResponse } from '../../api/endpoints/comp_simulator';

const VESTING_OPTIONS = [
  { value: 'standard_4yr_25', label: 'Standard 4-Year (25% cliff, 25%/yr)' },
  { value: 'amazon_5_15_40_40', label: 'Amazon Style (5% / 15% / 40% / 40%)' },
  { value: 'even_quarterly', label: 'Linear Quarterly (25%/yr)' },
];

const NegotiatorTab: React.FC = () => {
  const [company, setCompany] = useState('');
  const [offer, setOffer] = useState<number | ''>('');
  const benchmarkQuery = useNegotiationBenchmark(company, company.trim().length > 0);
  const counter = useNegotiationCounter();

  // Compensation Simulator State
  const [simBase, setSimBase] = useState<number>(220000);
  const [simSignon, setSimSignon] = useState<number>(30000);
  const [simBonusPct, setSimBonusPct] = useState<number>(15);
  const [simEquity, setSimEquity] = useState<number>(400000);
  const [simVesting, setSimVesting] = useState<string>('standard_4yr_25');
  const [simMultiple, setSimMultiple] = useState<number>(1.0);
  const [simLoading, setSimLoading] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<CompSimulationResponse | null>(null);

  const handleCopy = (text: string) => navigator.clipboard.writeText(text);
  const band = benchmarkQuery.data?.data.band;

  const handleSimulateComp = async () => {
    setSimLoading(true);
    try {
      const res = await compSimulatorApi.simulate({
        company: company || 'Target Company',
        role_title: 'Staff / Senior Engineer',
        base_salary: Number(simBase),
        signon_bonus: Number(simSignon),
        target_bonus_pct: Number(simBonusPct),
        equity_grant_usd: Number(simEquity),
        vesting_schedule: simVesting,
        startup_exit_multiple: Number(simMultiple),
      });
      setSimResult(res.data);
    } catch {
      // silent fallback
    } finally {
      setSimLoading(false);
    }
  };

  return (
    <Box>
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0', borderRadius: 3 }}>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>
            💰 Executive Offer Negotiator & Comp Simulator
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Benchmark salary bands against verified industry compensation data, model 4-year equity vesting trajectories
            (standard vs Amazon backloaded), test startup valuation upside multipliers, and generate data-backed counter-offer scripts.
          </Typography>
          <CompanySelect value={company} onChange={setCompany} />
        </CardContent>
      </Card>

      {/* 4-Year Compensation & Equity Vesting Simulator */}
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0', borderRadius: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
            <WalletIcon sx={{ color: '#4F46E5' }} />
            <Typography variant="h6" sx={{ fontWeight: 800, color: '#0F172A' }}>
              4-Year Total Comp & Equity Vesting Simulator
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
            Model annual cash flow across base salary, sign-on bonuses, performance incentives, and equity vesting schedules.
          </Typography>

          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="Base Salary ($/yr)"
                type="number"
                size="small"
                fullWidth
                value={simBase}
                onChange={(e) => setSimBase(Number(e.target.value))}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="Sign-on Bonus ($)"
                type="number"
                size="small"
                fullWidth
                value={simSignon}
                onChange={(e) => setSimSignon(Number(e.target.value))}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="Target Bonus (%)"
                type="number"
                size="small"
                fullWidth
                value={simBonusPct}
                onChange={(e) => setSimBonusPct(Number(e.target.value))}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="4-Yr Equity Grant ($)"
                type="number"
                size="small"
                fullWidth
                value={simEquity}
                onChange={(e) => setSimEquity(Number(e.target.value))}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 6 }}>
              <TextField
                select
                label="Vesting Schedule"
                size="small"
                fullWidth
                value={simVesting}
                onChange={(e) => setSimVesting(e.target.value)}
              >
                {VESTING_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <TextField
                label="Startup Exit Multiple"
                type="number"
                size="small"
                fullWidth
                value={simMultiple}
                onChange={(e) => setSimMultiple(Number(e.target.value))}
                helperText="e.g. 1.0 = baseline, 3.0 = 3x upside"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Button
                variant="contained"
                startIcon={simLoading ? <CircularProgress size={16} color="inherit" /> : <CalculateIcon />}
                onClick={handleSimulateComp}
                fullWidth
                sx={{ height: 40, fontWeight: 700 }}
              >
                Simulate Package
              </Button>
            </Grid>
          </Grid>

          {/* Simulation Output Dashboard */}
          {simResult && (
            <Box sx={{ mt: 2, p: 2.5, bgcolor: '#F8FAFC', borderRadius: 2, border: '1px solid #E2E8F0' }}>
              <Stack direction="row" spacing={3} flexWrap="wrap" useFlexGap sx={{ mb: 2.5 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">4-Year Total Pre-Tax</Typography>
                  <Typography variant="h5" fontWeight={800} color="#0F172A">
                    ${simResult.four_year_total_pre_tax.toLocaleString()}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Estimated Take-Home (Post-Tax)</Typography>
                  <Typography variant="h5" fontWeight={800} color="#10B981">
                    ${simResult.four_year_total_post_tax.toLocaleString()}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Average Annual Comp</Typography>
                  <Typography variant="h5" fontWeight={800} color="#4F46E5">
                    ${simResult.average_annual_comp.toLocaleString()}/yr
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Target Counter-Ask</Typography>
                  <Typography variant="h5" fontWeight={800} color="#D97706">
                    ${simResult.negotiation_counter_target.toLocaleString()}/yr
                  </Typography>
                </Box>
              </Stack>

              {/* 4-Year Breakdown Cards */}
              <Typography variant="caption" fontWeight={700} color="text.secondary" textTransform="uppercase" display="block" mb={1}>
                Yearly Cash & Equity Trajectory
              </Typography>
              <Grid container spacing={1.5} sx={{ mb: 2 }}>
                {simResult.yearly_breakdowns.map((yr) => (
                  <Grid size={{ xs: 12, sm: 6, md: 3 }} key={yr.year}>
                    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: '#FFFFFF' }}>
                      <Typography variant="subtitle2" fontWeight={800} color="#0F172A">
                        Year {yr.year}
                      </Typography>
                      <Divider sx={{ my: 0.5 }} />
                      <Stack spacing={0.3}>
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="caption" color="text.secondary">Base:</Typography>
                          <Typography variant="caption" fontWeight={600}>${yr.base_salary.toLocaleString()}</Typography>
                        </Box>
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="caption" color="text.secondary">Bonus/Sign-on:</Typography>
                          <Typography variant="caption" fontWeight={600}>${yr.cash_bonus.toLocaleString()}</Typography>
                        </Box>
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="caption" color="text.secondary">Equity Vest:</Typography>
                          <Typography variant="caption" fontWeight={700} color="#4F46E5">${yr.equity_vested.toLocaleString()}</Typography>
                        </Box>
                        <Divider sx={{ my: 0.3 }} />
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="caption" fontWeight={700}>Total Pre-Tax:</Typography>
                          <Typography variant="caption" fontWeight={800} color="#0F172A">${yr.total_pre_tax.toLocaleString()}</Typography>
                        </Box>
                      </Stack>
                    </Paper>
                  </Grid>
                ))}
              </Grid>


              <Alert severity="info" sx={{ fontWeight: 500 }}>
                💡 <b>Strategic Negotiation Advice:</b> {simResult.negotiation_advice}
              </Alert>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Target Company Benchmark */}
      {company.trim() && (
        <Card sx={{ mb: 3, border: '1px solid #E2E8F0', borderRadius: 3 }}>
          <CardContent sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Company Compensation Benchmark</Typography>
            {benchmarkQuery.isLoading ? (
              <CircularProgress size={24} />
            ) : benchmarkQuery.data?.data.suggested_ask_lpa == null ? (
              <Alert severity="warning">
                {benchmarkQuery.data?.warnings?.[0] ??
                  'No comp benchmark on file for this company in config/target_companies.yml.'}
              </Alert>
            ) : (
              <Stack direction="row" spacing={3} flexWrap="wrap">
                <Box>
                  <Typography variant="caption" color="text.secondary">Band (₹ LPA)</Typography>
                  <Typography variant="h6">
                    {band?.min ?? '—'} / {band?.median ?? '—'} / {band?.max ?? '—'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">min / median / max</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Position vs. your target</Typography>
                  <Typography variant="h6">
                    <Chip label={benchmarkQuery.data.data.position.replace('_', ' ')} />
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Suggested anchor ask</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#4F46E5' }}>
                    {benchmarkQuery.data.data.suggested_ask_lpa} LPA
                  </Typography>
                </Box>
              </Stack>
            )}
          </CardContent>
        </Card>
      )}

      {/* Counter-offer script */}
      <Card sx={{ border: '1px solid #E2E8F0', borderRadius: 3 }}>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Data-Backed Counter-Offer Script</Typography>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
            <TextField
              label="Offer received (₹ LPA)"
              size="small"
              type="number"
              value={offer}
              onChange={(e) => setOffer(e.target.value === '' ? '' : Number(e.target.value))}
              sx={{ width: 220 }}
            />
            <Button
              variant="contained"
              startIcon={counter.isPending ? <CircularProgress size={16} color="inherit" /> : <RequestQuoteIcon />}
              onClick={() => offer !== '' && counter.mutate({ company, offerAmountLpa: Number(offer) })}
              disabled={!company.trim() || offer === '' || counter.isPending}
            >
              Get Counter Script
            </Button>
          </Stack>

          {counter.data && (
            <Box>
              <Box sx={{ p: 2, bgcolor: '#F8FAFC', borderRadius: 2, position: 'relative' }}>
                <Tooltip title="Copy Script">
                  <IconButton
                    size="small"
                    sx={{ position: 'absolute', top: 8, right: 8 }}
                    onClick={() => handleCopy(counter.data!.data.script)}
                  >
                    <CopyIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', pr: 4 }}>
                  {counter.data.data.script}
                </Typography>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default NegotiatorTab;

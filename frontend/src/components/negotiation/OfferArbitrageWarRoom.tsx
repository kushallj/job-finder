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
  Paper,
  Tooltip,
} from '@mui/material';
import {
  AccountBalance as BalanceIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  Shield as ShieldIcon,
  Send as SendIcon,
  PlayArrow as PlayIcon,
} from '@mui/icons-material';

import { offerArbitrageApi, type CompensationOfferInput, type ArbitrageSimulationResponse, type CounterScriptResponse } from '../../api/endpoints/sprint1_api';

export const OfferArbitrageWarRoom: React.FC = () => {
  const [offers] = useState<CompensationOfferInput[]>([

    {
      id: 'offer_1',
      company_name: 'CRED',
      role_title: 'Senior Backend Engineer',
      currency: 'LPA (INR)',
      base_salary: 42,
      annual_bonus: 5,
      joining_bonus: 4,
      equity_total_grant: 40,
      equity_type: 'ESOP',
      company_stage: 'Series D / Pre-IPO',
      deadline_date: '2026-09-15',
    },
    {
      id: 'offer_2',
      company_name: 'Walmart Global Tech',
      role_title: 'Senior Software Engineer',
      currency: 'LPA (INR)',
      base_salary: 38,
      annual_bonus: 6,
      joining_bonus: 3,
      equity_total_grant: 48,
      equity_type: 'RSU',
      company_stage: 'Public / BigTech',
      deadline_date: '2026-09-20',
    },
  ]);

  const [simResult, setSimResult] = useState<ArbitrageSimulationResponse | null>({
    status: 'success',
    total_offers_analyzed: 2,
    ranked_offers: [
      {
        id: 'offer_2',
        company_name: 'Walmart Global Tech',
        role_title: 'Senior Software Engineer',
        currency: 'LPA (INR)',
        base_salary: 38,
        annual_bonus: 6,
        joining_bonus: 3,
        equity_annual_nominal: 12,
        equity_annual_risk_adjusted: 11.4,
        equity_risk_multiplier: 95.0,
        year1_nominal_tc: 59,
        year1_risk_adjusted_npv: 58.4,
        four_year_avg_npv: 56.15,
        deadline_date: '2026-09-20',
      },
      {
        id: 'offer_1',
        company_name: 'CRED',
        role_title: 'Senior Backend Engineer',
        currency: 'LPA (INR)',
        base_salary: 42,
        annual_bonus: 5,
        joining_bonus: 4,
        equity_annual_nominal: 10,
        equity_annual_risk_adjusted: 6.0,
        equity_risk_multiplier: 60.0,
        year1_nominal_tc: 61,
        year1_risk_adjusted_npv: 57.0,
        four_year_avg_npv: 54.0,
        deadline_date: '2026-09-15',
      },
    ],
    optimal_target: 'Walmart Global Tech',
    leverage_insights: [
      'You have strong leverage: Walmart Global Tech leads in risk-adjusted NPV by LPA (INR) 1 over CRED due to 95% liquid RSU certainty.',
      'Notice that CRED offers a higher guaranteed cash base (LPA (INR) 42). Use this to ask Walmart to match or exceed CRED on cash base.',
    ],
  });

  const [counterScript, setCounterScript] = useState<CounterScriptResponse | null>(null);
  const [copiedEmail, setCopiedEmail] = useState(false);

  const handleSimulate = async () => {
    try {
      const res = await offerArbitrageApi.simulateArbitrage(offers);
      setSimResult(res);
    } catch (err) {
      console.error('Simulation failed:', err);
    }
  };

  const handleGenerateCounter = async (targetCompany: string, competingCompany: string, currentBase: number) => {
    try {
      const res = await offerArbitrageApi.generateCounterScript({
        target_company: targetCompany,
        competing_company: competingCompany,
        current_base: currentBase,
        target_base: currentBase + 5,
        currency: 'LPA (INR)',
      });
      setCounterScript(res);
    } catch (err) {
      console.error('Failed to generate script:', err);
    }
  };

  const handleCopyEmail = () => {
    if (!counterScript) return;
    navigator.clipboard.writeText(counterScript.email_script);
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2500);
  };

  return (
    <Card sx={{ bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.3)', borderRadius: '18px' }}>
      <CardContent sx={{ p: 3 }}>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2.5 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Box sx={{ width: 36, height: 36, borderRadius: '10px', bgcolor: 'rgba(0, 240, 255, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #00F0FF' }}>
              <BalanceIcon sx={{ color: '#00F0FF', fontSize: 22 }} />
            </Box>
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                Multi-Offer Arbitrage & Negotiation War-Room
              </Typography>
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                Game-theoretic risk-adjusted NPV modeling, leverage gap analysis & counter-offer synthesis
              </Typography>
            </Box>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <Button
              size="small"
              variant="outlined"
              startIcon={<PlayIcon />}
              onClick={handleSimulate}
              sx={{ color: '#00F0FF', borderColor: '#00F0FF', textTransform: 'none', fontWeight: 800, fontSize: '0.75rem' }}
            >
              Re-Calculate NPV
            </Button>
            <Chip label="Game Theory Active" size="small" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800 }} />
          </Stack>
        </Stack>


        {/* Offers Comparison Cards */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {simResult?.ranked_offers.map((offer, idx) => (
            <Grid key={offer.id} size={{ xs: 12, md: 6 }}>
              <Paper sx={{ p: 2.5, bgcolor: '#06090E', borderRadius: '14px', border: `1.5px solid ${idx === 0 ? '#00FFA3' : 'rgba(255, 255, 255, 0.1)'}` }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    {offer.company_name}
                  </Typography>
                  <Chip label={idx === 0 ? '🏆 Highest Risk-Adjusted NPV' : 'Second Choice'} size="small" sx={{ bgcolor: idx === 0 ? 'rgba(0, 255, 163, 0.2)' : 'rgba(255, 255, 255, 0.05)', color: idx === 0 ? '#00FFA3' : '#94A3B8', fontWeight: 800, fontSize: '0.65rem' }} />
                </Stack>

                <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                  <Box>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                      Base Salary
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 900, color: '#FFE600' }}>
                      ₹{offer.base_salary} LPA
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                      Nominal TC (Yr 1)
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 900, color: '#00F0FF' }}>
                      ₹{offer.year1_nominal_tc} LPA
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                      Risk-Adjusted NPV
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                      ₹{offer.year1_risk_adjusted_npv} LPA
                    </Typography>
                  </Box>
                </Stack>

                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<SendIcon />}
                  onClick={() => handleGenerateCounter(offer.company_name, idx === 0 ? 'CRED' : 'Walmart', offer.base_salary)}
                  sx={{ color: '#00FFA3', borderColor: '#00FFA3', textTransform: 'none', fontWeight: 800, fontSize: '0.75rem' }}
                >
                  Generate Counter-Offer Script
                </Button>
              </Paper>
            </Grid>
          ))}
        </Grid>

        {/* Leverage Insights */}
        {simResult && (
          <Paper sx={{ p: 2.5, bgcolor: '#06090E', border: '1px solid rgba(255, 230, 0, 0.25)', borderRadius: '12px', mb: 3 }}>
            <Typography variant="subtitle2" sx={{ color: '#FFE600', fontWeight: 900, mb: 1, textTransform: 'uppercase' }}>
              🎯 Game-Theoretic Leverage Insights
            </Typography>
            <Stack spacing={1}>
              {simResult.leverage_insights.map((insight, i) => (
                <Typography key={i} variant="body2" sx={{ color: '#E2E8F0', fontSize: '0.85rem' }}>
                  • {insight}
                </Typography>
              ))}
            </Stack>
          </Paper>
        )}

        {/* Counter Script Output */}
        {counterScript && (
          <Paper sx={{ p: 2.5, bgcolor: '#06090E', border: '1px solid rgba(0, 255, 163, 0.4)', borderRadius: '12px' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                  Calibrated Counter-Offer Email ({counterScript.target_company})
                </Typography>
                <Chip icon={<ShieldIcon sx={{ fontSize: '13px !important' }} />} label={`Rescission Risk: ${counterScript.rescission_risk_score}`} size="small" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, fontSize: '0.65rem' }} />
              </Stack>
              <Tooltip title="Copy Email">
                <Button
                  size="small"
                  variant="contained"
                  startIcon={copiedEmail ? <CheckIcon /> : <CopyIcon />}
                  onClick={handleCopyEmail}
                  sx={{ bgcolor: '#00FFA3', color: '#06090E', fontWeight: 900, fontSize: '0.75rem', textTransform: 'none' }}
                >
                  {copiedEmail ? 'Copied' : 'Copy Email'}
                </Button>
              </Tooltip>
            </Stack>
            <Typography variant="body2" sx={{ color: '#E2E8F0', whiteSpace: 'pre-line', fontSize: '0.82rem', lineHeight: 1.5, p: 2, bgcolor: '#0D131F', borderRadius: '8px' }}>
              {counterScript.email_script}
            </Typography>
          </Paper>
        )}
      </CardContent>
    </Card>
  );
};

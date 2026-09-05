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
} from '@mui/material';
import {
  Public as WorldIcon,
  Savings as SavingsIcon,
  VerifiedUser as VisaIcon,
  TrendingUp as MultiplierIcon,
} from '@mui/icons-material';
import {
  sprint5Api,
  type GeoMarket,
  type PppCalculationResponse,
} from '../../api/endpoints/sprint5_api';

export const GeoArbitrageCard: React.FC = () => {
  const [markets, setMarkets] = useState<GeoMarket[]>([]);
  const [selectedMarketId, setSelectedMarketId] = useState<string>('japan_tokyo');
  const [grossSalary, setGrossSalary] = useState<number>(16000000); // 16M JPY default
  const [currentInrLpa, setCurrentInrLpa] = useState<number>(35);
  const [loading, setLoading] = useState(false);
  const [pppResult, setPppResult] = useState<PppCalculationResponse | null>(null);

  useEffect(() => {
    sprint5Api.getGeoMarkets().then((res) => {
      if (res && res.markets) {
        setMarkets(res.markets);
        if (res.markets.length > 0) {
          handleCalculate(res.markets[0].market_id, 16000000, 35);
        }
      }
    }).catch(console.error);
  }, []);

  const handleSelectMarket = (m: GeoMarket) => {
    setSelectedMarketId(m.market_id);
    let defaultGross = 100000;
    if (m.currency === 'JPY') defaultGross = 16000000;
    else if (m.currency === 'SGD') defaultGross = 180000;
    else if (m.currency === 'EUR') defaultGross = 110000;
    else if (m.currency === 'GBP') defaultGross = 120000;
    setGrossSalary(defaultGross);
    handleCalculate(m.market_id, defaultGross, currentInrLpa);
  };

  const handleCalculate = async (
    marketId = selectedMarketId,
    salary = grossSalary,
    inrBase = currentInrLpa
  ) => {
    setLoading(true);
    try {
      const res = await sprint5Api.calculatePpp({
        gross_annual_salary: salary,
        market_id: marketId,
        current_inr_ctc_lpa: inrBase,
      });
      setPppResult(res);
    } catch (err) {
      console.error('PPP calculation failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const activeMarket = markets.find((m) => m.market_id === selectedMarketId) || markets[0];

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
                  <WorldIcon sx={{ color: '#00F0FF', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    🌍 Global Geo-Arbitrage & Cross-Border Engine (Agent 21)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Access untapped English-first markets in Japan & Singapore ($80k–$195k USD) and fast-track EU visas with tax-adjusted PPP math.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip
                label="Japan • Singapore • EU • UK"
                sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 900, fontSize: '0.78rem' }}
              />
              <Chip
                label="Fast-Track PR (12-24 Mo)"
                sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, fontSize: '0.75rem' }}
              />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Target Market Selector Tabs */}
      <Stack direction="row" spacing={1} sx={{ mb: 3, overflowX: 'auto', pb: 0.5 }}>
        {markets.map((m) => (
          <Chip
            key={m.market_id}
            label={`${m.city} (${m.currency})`}
            clickable
            onClick={() => handleSelectMarket(m)}
            sx={{
              fontWeight: 800,
              fontSize: '0.82rem',
              py: 2.2,
              px: 1,
              bgcolor: selectedMarketId === m.market_id ? 'rgba(0, 240, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              color: selectedMarketId === m.market_id ? '#00F0FF' : '#94A3B8',
              border: `1.5px solid ${selectedMarketId === m.market_id ? '#00F0FF' : 'rgba(255, 255, 255, 0.1)'}`,
            }}
          />
        ))}
      </Stack>

      {/* Interactive Simulator Grid */}
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
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00F0FF', mb: 2 }}>
              ⚙️ Compensation & Baseline Parameters
            </Typography>

            {activeMarket && (
              <Stack spacing={2.5}>
                <Box>
                  <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700, display: 'block', mb: 0.5 }}>
                    Target Gross Compensation ({activeMarket.currency}):
                  </Typography>
                  <TextField
                    fullWidth
                    size="small"
                    type="number"
                    value={grossSalary}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      setGrossSalary(val);
                      handleCalculate(selectedMarketId, val, currentInrLpa);
                    }}
                    helperText={`Market Benchmark: ${activeMarket.average_gross_salary_range}`}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Box>

                <Box>
                  <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700, display: 'block', mb: 0.5 }}>
                    Current India CTC Baseline (₹ LPA):
                  </Typography>
                  <TextField
                    fullWidth
                    size="small"
                    type="number"
                    value={currentInrLpa}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      setCurrentInrLpa(val);
                      handleCalculate(selectedMarketId, grossSalary, val);
                    }}
                    helperText="Used to compute real savings expansion multiplier vs India living costs"
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Box>

                <Paper sx={{ p: 2, bgcolor: '#06090E', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 0.5 }}>
                    ENGLISH ADOPTION & ECOSYSTEM:
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#00FFA3', fontWeight: 800 }}>
                    {activeMarket.english_adoption_score}% English Tech Environment (No Local Language Mandated)
                  </Typography>
                </Paper>

                <Button
                  variant="contained"
                  disabled={loading}
                  onClick={() => handleCalculate(selectedMarketId, grossSalary, currentInrLpa)}
                  startIcon={loading ? <CircularProgress size={18} sx={{ color: '#06090E' }} /> : <MultiplierIcon />}
                  sx={{
                    bgcolor: '#00F0FF',
                    color: '#06090E',
                    fontWeight: 900,
                    textTransform: 'none',
                    py: 1.2,
                    '&:hover': { bgcolor: '#00C8D6' },
                  }}
                >
                  {loading ? 'Calculating PPP & Tax Arbitrage...' : 'Re-Calculate Net PPP Savings'}
                </Button>
              </Stack>
            )}
          </Paper>
        </Grid>

        {/* Right: Net Take-Home, Tax & Savings Multiplier */}
        <Grid size={{ xs: 12, md: 7 }}>
          {pppResult && (
            <Stack spacing={3}>
              {/* Savings Multiplier Hero Card */}
              <Paper
                sx={{
                  p: 3,
                  bgcolor: '#0D131F',
                  border: '1.5px solid rgba(0, 255, 163, 0.3)',
                  borderRadius: '16px',
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00FFA3', display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SavingsIcon sx={{ color: '#00FFA3' }} /> Net Liquid Savings Arbitrage
                  </Typography>
                  <Chip
                    label={`${pppResult.financials.savings_expansion_multiplier}x Savings Growth`}
                    sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 900, fontSize: '0.85rem', border: '1px solid #00FFA3' }}
                  />
                </Stack>

                <Grid container spacing={1.5} sx={{ mb: 2 }}>
                  <Grid size={{ xs: 4 }}>
                    <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '10px', textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                        NET TAKE-HOME
                      </Typography>
                      <Typography variant="h6" sx={{ color: '#00F0FF', fontWeight: 900, my: 0.5, fontFamily: 'monospace' }}>
                        ₹{pppResult.financials.net_inr_lakhs}L
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#64748B' }}>~${pppResult.financials.net_usd_annual.toLocaleString()}/yr</Typography>
                    </Paper>
                  </Grid>

                  <Grid size={{ xs: 4 }}>
                    <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '10px', textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                        ANNUAL SAVINGS
                      </Typography>
                      <Typography variant="h6" sx={{ color: '#00FFA3', fontWeight: 900, my: 0.5, fontFamily: 'monospace' }}>
                        ₹{pppResult.financials.annual_savings_inr_lakhs}L
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#64748B' }}>INR / year clean</Typography>
                    </Paper>
                  </Grid>

                  <Grid size={{ xs: 4 }}>
                    <Paper sx={{ p: 1.5, bgcolor: '#06090E', borderRadius: '10px', textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800 }}>
                        EFFECTIVE TAX
                      </Typography>
                      <Typography variant="h6" sx={{ color: '#FFE600', fontWeight: 900, my: 0.5, fontFamily: 'monospace' }}>
                        {pppResult.financials.effective_tax_percent}%
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#64748B' }}>Tax Advantage</Typography>
                    </Paper>
                  </Grid>
                </Grid>

                <Paper sx={{ p: 1.5, bgcolor: 'rgba(0, 240, 255, 0.05)', borderRadius: '8px', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
                  <Typography variant="caption" sx={{ color: '#CBD5E1', lineHeight: 1.5, display: 'block' }}>
                    💡 <strong>Takeaway:</strong> {pppResult.takeaway_summary}
                  </Typography>
                </Paper>
              </Paper>

              {/* Visa & Relocation Fast-Track Dossier */}
              <Paper
                sx={{
                  p: 3,
                  bgcolor: '#0D131F',
                  border: '1.5px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '16px',
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC', display: 'flex', alignItems: 'center', gap: 1 }}>
                    <VisaIcon sx={{ color: '#00F0FF' }} /> Fast-Track Visa & Relocation Package
                  </Typography>
                  <Chip
                    label={`PR in ${pppResult.visa_dossier.permanent_residence_timeline}`}
                    sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800 }}
                  />
                </Stack>

                <Stack spacing={1.5}>
                  <Box>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700 }}>
                      VISA SCHEME:
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#F8FAFC', fontWeight: 800 }}>
                      {pppResult.visa_dossier.visa_name}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700 }}>
                      SPONSORED RELOCATION PERKS:
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#00FFA3', fontWeight: 700 }}>
                      {pppResult.visa_dossier.relocation_perks}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 700 }}>
                      TOP HIRING TECH EMPLOYERS:
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" gap={0.5} sx={{ mt: 0.5 }}>
                      {activeMarket.key_employers.map((emp) => (
                        <Chip
                          key={emp}
                          label={emp}
                          size="small"
                          sx={{ bgcolor: 'rgba(255,255,255,0.06)', color: '#CBD5E1', fontWeight: 700 }}
                        />
                      ))}
                    </Stack>
                  </Box>
                </Stack>
              </Paper>
            </Stack>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

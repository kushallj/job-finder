import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Stack,
  Button,
  CircularProgress,
  Paper,
  Divider,
  Grid,
} from '@mui/material';
import {
  Public as GlobalIcon,
  Schedule as TimeIcon,
  Launch as LaunchIcon,
  Business as BusinessIcon,
  TrendingUp as TrendingUpIcon,
  Shield as ShieldIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

import { marketRadarApi } from '../api';
import type { MarketRadarResponse } from '../api/endpoints/market_radar';

export const MarketRadar: React.FC = () => {
  const [radar, setRadar] = useState<MarketRadarResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchRadar = async () => {
    setLoading(true);
    try {
      const res = await marketRadarApi.getOpportunities();
      setRadar(res.data);
    } catch {
      // silent fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRadar();
  }, []);

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: { xs: 1, md: 2 } }}>
      {/* Header Banner */}
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2} mb={3}>
        <Box>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <GlobalIcon sx={{ color: '#0EA5E9', fontSize: 32 }} />
            <Typography variant="h4" fontWeight={800} color="#0F172A" letterSpacing="-0.02em">
              Global Remote Arbitrage & GCC Opportunity Radar
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Discover high-paying USD/EUR remote contracts with purchasing power parity (PPP) multipliers and explore hiring expansions in top Indian GCC tech centers.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={loading ? <CircularProgress size={14} /> : <RefreshIcon />}
          onClick={fetchRadar}
          disabled={loading}
          sx={{ fontWeight: 700 }}
        >
          Refresh Radar
        </Button>
      </Box>

      {/* FX Rates & Tax Arbitrage Highlights */}
      {radar && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Paper variant="outlined" sx={{ p: 2, borderRadius: 2.5, bgcolor: '#F0FDF4', borderColor: '#BBF7D0' }}>
              <Typography variant="caption" fontWeight={700} color="#166534">LIVE USD CONVERSION RATE</Typography>
              <Typography variant="h4" fontWeight={900} color="#15803D" sx={{ mt: 0.5 }}>
                $1.00 = ₹{radar.usd_to_inr_rate}
              </Typography>
              <Typography variant="caption" color="#166534">
                ~3.6x Purchasing Power Parity Multiplier
              </Typography>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, sm: 4 }}>
            <Paper variant="outlined" sx={{ p: 2, borderRadius: 2.5, bgcolor: '#EFF6FF', borderColor: '#BFDBFE' }}>
              <Typography variant="caption" fontWeight={700} color="#1E40AF">LIVE EUR CONVERSION RATE</Typography>
              <Typography variant="h4" fontWeight={900} color="#1D4ED8" sx={{ mt: 0.5 }}>
                €1.00 = ₹{radar.eur_to_inr_rate}
              </Typography>
              <Typography variant="caption" color="#1E40AF">
                ~3.2x European Remote Contract Advantage
              </Typography>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, sm: 4 }}>
            <Paper variant="outlined" sx={{ p: 2, borderRadius: 2.5, bgcolor: '#FAF5FF', borderColor: '#E9D5FF' }}>
              <Typography variant="caption" fontWeight={700} color="#6B21A8">INDIA TAX ARBITRAGE (SEC 44ADA)</Typography>
              <Typography variant="h5" fontWeight={900} color="#7E22CE" sx={{ mt: 0.5 }}>
                50% Flat Deduction
              </Typography>
              <Typography variant="caption" color="#6B21A8">
                Presumptive taxation for global freelance contracts
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Global Remote Roles Section */}
      <Typography variant="h6" fontWeight={800} color="#0F172A" sx={{ mb: 2 }}>
        🌍 High-Yield USD / EUR Remote Opportunities:
      </Typography>

      {loading && !radar ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : radar ? (
        <Stack spacing={2.5} sx={{ mb: 4 }}>
          {radar.remote_global_roles.map((role, idx) => (
            <Card key={idx} sx={{ border: '1px solid #E2E8F0', borderRadius: 3 }}>
              <CardContent sx={{ p: 2.5 }}>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={1.5} mb={1}>
                  <Box>
                    <Typography variant="h6" fontWeight={800} color="#0F172A">
                      {role.title}
                    </Typography>
                    <Typography variant="subtitle2" color="primary.main" fontWeight={700}>
                      {role.company} • <span style={{ color: '#64748B' }}>{role.country}</span>
                    </Typography>
                  </Box>

                  <Box textAlign={{ xs: 'left', sm: 'right' }}>
                    <Typography variant="h6" fontWeight={900} color="#16A34A">
                      {role.base_comp_range}
                    </Typography>
                    <Typography variant="caption" fontWeight={700} color="#15803D" display="block">
                      {role.inr_equivalent_range}
                    </Typography>
                  </Box>
                </Box>

                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ my: 1.5 }}>
                  <Chip icon={<TimeIcon fontSize="small" />} label={role.tz_overlap_hours} size="small" sx={{ fontWeight: 600 }} />
                  <Chip icon={<ShieldIcon fontSize="small" />} label={role.tax_advantage} size="small" color="success" variant="outlined" sx={{ fontWeight: 600 }} />
                  <Chip label={`PPP Multiplier: ${role.ppp_multiplier}x`} size="small" sx={{ bgcolor: '#FEF3C7', color: '#92400E', fontWeight: 700 }} />
                </Stack>

                <Divider sx={{ my: 1.5 }} />

                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                    {role.skills_required.map((s, i) => (
                      <Chip key={i} label={s} size="small" sx={{ height: 22, fontSize: '0.7rem' }} />
                    ))}
                  </Stack>

                  <Button
                    size="small"
                    variant="contained"
                    endIcon={<LaunchIcon fontSize="small" />}
                    href={role.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{ fontWeight: 700 }}
                  >
                    View Remote Role ↗
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Stack>
      ) : null}

      {/* GCC Indian Tech Hubs Section */}
      <Typography variant="h6" fontWeight={800} color="#0F172A" sx={{ mb: 2 }}>
        🏢 Indian GCC (Global Capability Center) Hiring Expansions:
      </Typography>

      {radar && (
        <Grid container spacing={2}>
          {radar.top_gcc_hubs.map((hub, idx) => (
            <Grid size={{ xs: 12, md: 4 }} key={idx}>
              <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3, bgcolor: '#FFFFFF', height: '100%' }}>
                <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                  <BusinessIcon sx={{ color: '#6366F1' }} />
                  <Typography variant="subtitle1" fontWeight={800} color="#0F172A">
                    {hub.hub_city}
                  </Typography>
                </Stack>

                <Stack direction="row" spacing={1} alignItems="center" mb={1.5}>
                  <Chip label={`${hub.active_openings.toLocaleString()} Active Openings`} size="small" color="primary" sx={{ fontWeight: 700 }} />
                  <Chip icon={<TrendingUpIcon fontSize="small" />} label={hub.growth_yoy} size="small" color="success" sx={{ fontWeight: 700 }} />
                </Stack>

                <Typography variant="caption" color="text.secondary" fontWeight={700} display="block">
                  MEDIAN SENIOR CTC BAND:
                </Typography>
                <Typography variant="h6" fontWeight={800} color="#0F172A" gutterBottom>
                  {hub.median_senior_ctc}
                </Typography>

                <Typography variant="caption" color="text.secondary" fontWeight={700} display="block" sx={{ mt: 1 }}>
                  KEY FORTUNE 500 EMPLOYERS:
                </Typography>
                <Typography variant="body2" color="#334155" sx={{ fontSize: '0.85rem' }}>
                  {hub.top_employers.join(', ')}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};

export default MarketRadar;

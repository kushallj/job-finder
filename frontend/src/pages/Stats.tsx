import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  CircularProgress,
  Button,
  Stack,
  Chip,
  Paper,
} from '@mui/material';
import {
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  XAxis,
  YAxis,
  BarChart,
  Bar,
  CartesianGrid,
} from 'recharts';
import {
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useStats } from '../hooks/useStats';
import { formatNumber, formatPercentage } from '../utils/formatters';
import type { RecentOutreach } from '../api/types';

const PIE_COLORS = ['#00FFA3', '#00F0FF', '#FFE600', '#FF007A', '#7928CA'];

export const Stats: React.FC = () => {
  const { stats, recentOutreach, isLoadingStats, refetchStats, statsError, statsSource } = useStats();

  const statusData = React.useMemo(() => {
    if (!recentOutreach || recentOutreach.length === 0) {
      return [
        { name: 'Sent', value: stats?.emails_sent || 1 },
        { name: 'Replied', value: Math.round(((stats?.success_rate || 0) * (stats?.emails_sent || 1)) / 100) },
        { name: 'Pending', value: stats?.total_jobs || 1 },
      ];
    }
    const statusCounts: Record<string, number> = {};
    recentOutreach.forEach((item: RecentOutreach) => {
      const status = item.status || 'unknown';
      statusCounts[status] = (statusCounts[status] || 0) + 1;
    });
    return Object.entries(statusCounts).map(([name, value]) => ({ name, value }));
  }, [recentOutreach, stats]);

  const funnelData = React.useMemo(() => [
    { stage: 'Indexed Jobs', count: stats?.total_jobs || 0, fill: '#00F0FF' },
    { stage: 'Scored & Matched', count: stats?.total_applications || 0, fill: '#00FFA3' },
    { stage: 'Outreach Sent', count: stats?.emails_sent || 0, fill: '#FFE600' },
    { stage: 'Follow-ups', count: stats?.follow_ups_sent || 0, fill: '#7928CA' },
    { stage: 'Replies', count: Math.round(((stats?.success_rate || 0) * (stats?.emails_sent || 0)) / 100), fill: '#FF007A' },
  ], [stats]);

  if (isLoadingStats) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', minHeight: 400, gap: 2 }}>
        <CircularProgress sx={{ color: '#00FFA3' }} />
        <Typography variant="body2" sx={{ color: '#94A3B8' }}>Loading analytics engine...</Typography>
      </Box>
    );
  }

  if (statsError) {
    return (
      <Card sx={{ textAlign: 'center', py: 6, maxWidth: 500, mx: 'auto', mt: 4, bgcolor: '#0D131F', border: '1.5px solid rgba(255, 0, 122, 0.4)' }}>
        <CardContent>
          <Typography variant="h6" color="error" gutterBottom fontWeight={800}>
            Failed to load statistics
          </Typography>
          <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2 }}>
            {statsError instanceof Error ? statsError.message : 'Unknown error occurred'}
          </Typography>
          <Button variant="contained" color="primary" onClick={() => refetchStats()}>
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box sx={{ maxWidth: 1440, mx: 'auto', width: '100%', color: '#F8FAFC' }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, mb: 3.5, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h3" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.03em', mb: 0.5, textTransform: 'uppercase' }}>
            Pipeline & Campaign Analytics
          </Typography>
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>
            End-to-end conversion funnel metrics, response rates, and activity volume.
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5} alignItems="center">
          <Chip
            label={`Source: ${statsSource === 'live' ? '⚡ Real-Time Engine' : 'Database'}`}
            size="small"
            sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800, border: '1px solid rgba(0, 240, 255, 0.4)' }}
          />
          <Button
            variant="outlined"
            onClick={() => refetchStats()}
            startIcon={<RefreshIcon />}
            sx={{ borderRadius: '12px', fontWeight: 800 }}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* Top Level Metric Cards */}
      <Grid container spacing={2.5} sx={{ mb: 3.5 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '20px', border: '1.5px solid rgba(0, 240, 255, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
              Jobs Cataloged
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, color: '#F8FAFC', my: 0.5 }}>
              {formatNumber(stats?.total_jobs)}
            </Typography>
            <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 700 }}>
              S&P 500, Nifty 500 & YC
            </Typography>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '20px', border: '1.5px solid rgba(0, 255, 163, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
              Contacts Extracted
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, color: '#F8FAFC', my: 0.5 }}>
              {formatNumber(stats?.total_contacts)}
            </Typography>
            <Typography variant="caption" sx={{ color: '#00F0FF', fontWeight: 700 }}>
              Verified CTOs & Leads
            </Typography>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '20px', border: '1.5px solid rgba(255, 230, 0, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
              Messages Dispatched
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, color: '#F8FAFC', my: 0.5 }}>
              {formatNumber(stats?.emails_sent)}
            </Typography>
            <Typography variant="caption" sx={{ color: '#FFE600', fontWeight: 700 }}>
              {stats?.follow_ups_sent || 0} automated follow-ups
            </Typography>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '20px', border: '1.5px solid rgba(255, 0, 122, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>
              Conversion Rate
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, color: '#00FFA3', my: 0.5 }}>
              {formatPercentage(stats?.success_rate)}
            </Typography>
            <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 700 }}>
              Ghost-Proof Delivery
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Visual Analytics Grid */}
      <Grid container spacing={3} sx={{ mb: 3.5 }}>
        {/* Funnel Bar Chart */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Card sx={{ height: '100%', border: '1.5px solid rgba(0, 240, 255, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Typography variant="h6" fontWeight={900} color="#F8FAFC" sx={{ mb: 0.5 }} textTransform="uppercase">
                Opportunity Progression Funnel
              </Typography>
              <Typography variant="body2" sx={{ color: '#94A3B8', mb: 3 }}>
                Conversion volume from raw discovery to interview replies.
              </Typography>

              <Box sx={{ width: '100%', height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={funnelData} layout="vertical" margin={{ left: 20, right: 30, top: 10, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(0, 240, 255, 0.1)" />
                    <XAxis type="number" stroke="#94A3B8" />
                    <YAxis dataKey="stage" type="category" stroke="#94A3B8" width={110} tick={{ fontSize: 12, fontWeight: 700 }} />
                    <Tooltip contentStyle={{ borderRadius: 12, border: '1.5px solid rgba(0, 240, 255, 0.3)', backgroundColor: '#080C12', color: '#F8FAFC' }} />
                    <Bar dataKey="count" radius={[0, 8, 8, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Status Distribution Pie */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Card sx={{ height: '100%', border: '1.5px solid rgba(0, 240, 255, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Typography variant="h6" fontWeight={900} color="#F8FAFC" sx={{ mb: 0.5 }} textTransform="uppercase">
                Transmission Distribution
              </Typography>
              <Typography variant="body2" sx={{ color: '#94A3B8', mb: 3 }}>
                Status breakdown across recent outreach activities.
              </Typography>

              <Box sx={{ width: '100%', height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      innerRadius={50}
                      paddingAngle={4}
                    >
                      {statusData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: 12, border: '1.5px solid rgba(0, 240, 255, 0.3)', backgroundColor: '#080C12', color: '#F8FAFC' }} />
                    <Legend wrapperStyle={{ fontSize: '12px', fontWeight: 700 }} />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Stats;

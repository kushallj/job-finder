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
  alpha,
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

const PIE_COLORS = ['#10B981', '#4F46E5', '#F59E0B', '#EF4444', '#8B5CF6'];

export const Stats: React.FC = () => {
  const { stats, recentOutreach, isLoadingStats, refetchStats, statsError, statsSource } = useStats();

  // Prepare data for status pie chart
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

  // Funnel progression data
  const funnelData = React.useMemo(() => [
    { stage: 'Indexed Jobs', count: stats?.total_jobs || 0, fill: '#4F46E5' },
    { stage: 'Scored & Matched', count: stats?.total_applications || 0, fill: '#6366F1' },
    { stage: 'Outreach Sent', count: stats?.emails_sent || 0, fill: '#8B5CF6' },
    { stage: 'Follow-ups', count: stats?.follow_ups_sent || 0, fill: '#F59E0B' },
    { stage: 'Replies', count: Math.round(((stats?.success_rate || 0) * (stats?.emails_sent || 0)) / 100), fill: '#10B981' },
  ], [stats]);

  if (isLoadingStats) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', minHeight: 400, gap: 2 }}>
        <CircularProgress />
        <Typography variant="body2" color="text.secondary">Loading analytics engine...</Typography>
      </Box>
    );
  }

  if (statsError) {
    return (
      <Card sx={{ textAlign: 'center', py: 6, maxWidth: 500, mx: 'auto', mt: 4 }}>
        <CardContent>
          <Typography variant="h6" color="error" gutterBottom fontWeight={700}>
            Failed to load statistics
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {statsError instanceof Error ? statsError.message : 'Unknown error occurred'}
          </Typography>
          <Button variant="contained" onClick={() => refetchStats()}>
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>
            Pipeline & Campaign Analytics
          </Typography>
          <Typography variant="body2" color="text.secondary">
            End-to-end conversion funnel metrics, response rates, and activity volume.
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5} alignItems="center">
          <Chip
            label={`Source: ${statsSource === 'live' ? '⚡ Real-Time Engine' : 'Database'}`}
            size="small"
            sx={{ bgcolor: alpha('#4F46E5', 0.1), color: '#4F46E5', fontWeight: 700 }}
          />
          <Button
            variant="outlined"
            onClick={() => refetchStats()}
            startIcon={<RefreshIcon />}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* Top Level Metric Cards */}
      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
              Jobs Cataloged
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', my: 0.5 }}>
              {formatNumber(stats?.total_jobs)}
            </Typography>
            <Typography variant="caption" sx={{ color: '#10B981', fontWeight: 600 }}>
              Indexed across scrapers
            </Typography>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
              Contacts Extracted
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', my: 0.5 }}>
              {formatNumber(stats?.total_contacts)}
            </Typography>
            <Typography variant="caption" sx={{ color: '#4F46E5', fontWeight: 600 }}>
              Hunter & Apollo verified
            </Typography>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
              Messages Dispatched
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', my: 0.5 }}>
              {formatNumber(stats?.emails_sent)}
            </Typography>
            <Typography variant="caption" sx={{ color: '#F59E0B', fontWeight: 600 }}>
              {stats?.follow_ups_sent || 0} automated follow-ups
            </Typography>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2.5, borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
              Conversion Rate
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#10B981', my: 0.5 }}>
              {formatPercentage(stats?.success_rate)}
            </Typography>
            <Typography variant="caption" sx={{ color: '#10B981', fontWeight: 600 }}>
              Industry benchmark: ~15%
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Visual Analytics Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Funnel Bar Chart */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Card sx={{ height: '100%', border: '1px solid #E2E8F0' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={800} color="#0F172A" sx={{ mb: 0.5 }}>
                Opportunity Progression Funnel
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Conversion volume from raw discovery to interview replies.
              </Typography>

              <Box sx={{ width: '100%', height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={funnelData} layout="vertical" margin={{ left: 20, right: 30, top: 10, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                    <XAxis type="number" stroke="#94A3B8" />
                    <YAxis dataKey="stage" type="category" stroke="#475569" width={110} tick={{ fontSize: 12, fontWeight: 600 }} />
                    <Tooltip contentStyle={{ borderRadius: 10, border: '1px solid #E2E8F0', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }} />
                    <Bar dataKey="count" radius={[0, 8, 8, 0]}>
                      {funnelData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Status Distribution Pie Chart */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Card sx={{ height: '100%', border: '1px solid #E2E8F0' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={800} color="#0F172A" sx={{ mb: 0.5 }}>
                Outreach Status Breakdown
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Distribution of recent campaign communication states.
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
                        <Cell key={`pie-cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: 10, border: '1px solid #E2E8F0' }} />
                    <Legend wrapperStyle={{ fontSize: '12px', fontWeight: 600 }} />
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

import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  CircularProgress,
  Button,
} from '@mui/material';
import {
  LineChart,
  Line,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import {
  Download as DownloadIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useStats } from '../hooks/useStats';
import { formatNumber, formatPercentage } from '../utils/formatters';
import type { RecentOutreach } from '../api/types';

const COLORS = ['#4caf50', '#ff9800', '#f44336', '#9c27b0', '#2196f3'];

export const Stats: React.FC = () => {
  const { stats, recentOutreach, isLoadingStats, refetchStats } = useStats();

  // Prepare data for charts
  const statusData = React.useMemo(() => {
    if (!recentOutreach) return [];
    const statusCounts: Record<string, number> = {};
    recentOutreach.forEach((item: RecentOutreach) => {
      const status = item.status || 'unknown';
      statusCounts[status] = (statusCounts[status] || 0) + 1;
    });
    return Object.entries(statusCounts).map(([name, value]) => ({ name, value }));
  }, [recentOutreach]);

  const outreachTrendData = React.useMemo(() => {
    if (!recentOutreach) return [];
    // Group by date (last 7 days)
    const days: Record<string, { sent: number; replied: number; failed: number }> = {};
    recentOutreach.slice(0, 20).forEach((item: RecentOutreach) => {
      if (!item.sent_at) return;
      const date = new Date(item.sent_at).toLocaleDateString('en-US', { weekday: 'short' });
      if (!days[date]) {
        days[date] = { sent: 0, replied: 0, failed: 0 };
      }
      days[date].sent += 1;
      if (item.status === 'replied') days[date].replied += 1;
      if (item.status === 'failed') days[date].failed += 1;
    });
    return Object.entries(days).map(([date, data]) => ({
      date,
      ...data,
    }));
  }, [recentOutreach]);

  const handleExport = () => {
    console.log('Exporting stats...');
  };

  if (isLoadingStats) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
        <Box>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Statistics
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Track your job search and outreach performance
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => refetchStats()}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleExport}
          >
            Export
          </Button>
        </Box>
      </Box>

      {/* Key Metrics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Total Jobs
              </Typography>
              <Typography variant="h4" fontWeight={700}>
                {formatNumber(stats?.total_jobs || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Total Applications
              </Typography>
              <Typography variant="h4" fontWeight={700}>
                {formatNumber(stats?.total_applications || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Emails Sent
              </Typography>
              <Typography variant="h4" fontWeight={700}>
                {formatNumber(stats?.emails_sent || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Success Rate
              </Typography>
              <Typography variant="h4" fontWeight={700} color="success.main">
                {formatPercentage(stats?.success_rate || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        {/* Outreach Trend */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                Outreach Trend
              </Typography>
              {outreachTrendData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={outreachTrendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <Line type="monotone" dataKey="sent" stroke="#2196f3" name="Sent" strokeWidth={2} />
                    <Line type="monotone" dataKey="replied" stroke="#4caf50" name="Replied" strokeWidth={2} />
                    <Line type="monotone" dataKey="failed" stroke="#f44336" name="Failed" strokeWidth={2} />
                    <Legend />
                    <Tooltip />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography color="text.secondary">No trend data available</Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Status Distribution */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                Status Distribution
              </Typography>
              {statusData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={statusData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {statusData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography color="text.secondary">No status data available</Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Metrics */}
        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                Performance Breakdown
              </Typography>
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Box sx={{ textAlign: 'center', p: 2 }}>
                    <Typography variant="h3" fontWeight={700} color="primary.main">
                      {stats?.total_jobs || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Jobs Found
                    </Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Box sx={{ textAlign: 'center', p: 2 }}>
                    <Typography variant="h3" fontWeight={700} color="success.main">
                      {stats?.emails_sent || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Emails Successfully Sent
                    </Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Box sx={{ textAlign: 'center', p: 2 }}>
                    <Typography variant="h3" fontWeight={700} color="warning.main">
                      {stats?.follow_ups_sent || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Follow-up Emails Sent
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Stats;


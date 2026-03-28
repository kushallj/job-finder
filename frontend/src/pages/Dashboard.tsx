import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Skeleton,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  TextField,
  InputAdornment,
  Slider,

} from '@mui/material';
import {
  Work as JobsIcon,
  People as ContactsIcon,
  Send as OutreachIcon,
  CheckCircle as SuccessIcon,
  TrendingUp as TrendingUpIcon,
  PlayArrow as FetchIcon,
  RocketLaunch as OutreachRunIcon,
  Search as SearchIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useStats } from '../hooks/useStats';
import { useJobs } from '../hooks/useJobs';
import { useNavigate } from 'react-router-dom';
import { formatRelativeTime, formatPercentage, formatNumber } from '../utils/formatters';
import type { RecentOutreach } from '../api/types';

// Stat Card Component
interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  color: 'primary' | 'success' | 'warning' | 'error';
  loading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, loading }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography color="text.secondary" gutterBottom variant="body2">
            {title}
          </Typography>
          {loading ? (
            <Skeleton width={60} height={40} />
          ) : (
            <Typography variant="h4" fontWeight={700}>
              {value}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            p: 1.5,
            borderRadius: 2,
            backgroundColor: `${color}.light`,
            color: `${color}.main`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
);

// Quick Action Button
interface QuickActionProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
  color: 'primary' | 'success' | 'secondary';
  loading?: boolean;
}

const QuickAction: React.FC<QuickActionProps> = ({ title, description, icon, onClick, color, loading }) => (
  <Button
    variant="outlined"
    onClick={onClick}
    disabled={loading}
    sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: 1,
      p: 2,
      borderColor: 'divider',
      '&:hover': {
        borderColor: `${color}.main`,
        backgroundColor: `${color}.light`,
      },
    }}
  >
    <Box sx={{ color: `${color}.main` }}>{icon}</Box>
    <Typography variant="subtitle1" fontWeight={600}>
      {title}
    </Typography>
    <Typography variant="caption" color="text.secondary" textAlign="center">
      {description}
    </Typography>
  </Button>
);

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { stats, recentOutreach, isLoadingStats, refetchStats } = useStats();
  const { pendingOutreach, isPendingOutreachLoading, runQuery, isRunningQuery } = useJobs();

  // Search state for job fetching
  const [searchQuery, setSearchQuery] = useState('python developer');
  const [minScore, setMinScore] = useState(50);

  const handleFetchJobs = () => {
    if (searchQuery.trim()) {
      runQuery({ query: searchQuery.trim(), min_score: minScore });
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleFetchJobs();
    }
  };

  const handleRunOutreach = () => {
    navigate('/outreach');
  };

  const handleViewStats = () => {
    navigate('/stats');
  };

  return (
    <Box>
      {/* Welcome Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Welcome back! 👋
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here's what's happening with your job search and outreach campaign.
        </Typography>
      </Box>

      {/* Stats Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Total Jobs"
            value={formatNumber(stats?.total_jobs)}
            icon={<JobsIcon />}
            color="primary"
            loading={isLoadingStats}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Contacts Found"
            value={formatNumber(stats?.total_contacts)}
            icon={<ContactsIcon />}
            color="success"
            loading={isLoadingStats}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Outreach Sent"
            value={formatNumber(stats?.emails_sent)}
            icon={<OutreachIcon />}
            color="warning"
            loading={isLoadingStats}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Success Rate"
            value={formatPercentage(stats?.success_rate)}
            icon={<SuccessIcon />}
            color="success"
            loading={isLoadingStats}
          />
        </Grid>
      </Grid>

      {/* Search Section */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
            Search Jobs
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField
              placeholder="Enter job title (e.g., Python Developer, React Developer)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              size="small"
              sx={{ flex: 1, minWidth: 250 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
            />
            <Box sx={{ width: 200, px: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Min Score: {minScore}%
              </Typography>
              <Slider
                value={minScore}
                onChange={(_, value) => setMinScore(value as number)}
                min={0}
                max={100}
                step={5}
                valueLabelDisplay="auto"
                color="primary"
              />
            </Box>
            <Button
              variant="contained"
              onClick={handleFetchJobs}
              disabled={isRunningQuery || !searchQuery.trim()}
              startIcon={isRunningQuery ? <Skeleton variant="circular" width={20} height={20} /> : <FetchIcon />}
            >
              {isRunningQuery ? 'Searching...' : 'Fetch Jobs'}
            </Button>
            <Button
              variant="outlined"
              onClick={() => void refetchStats()}
              disabled={isLoadingStats}
              startIcon={<RefreshIcon />}
            >
              Refresh Stats
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
        Quick Actions
      </Typography>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <QuickAction
            title="Run Outreach"
            description="Send personalized outreach emails"
            icon={<OutreachRunIcon />}
            onClick={handleRunOutreach}
            color="success"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <QuickAction
            title="Run Outreach"
            description="Send personalized outreach emails"
            icon={<OutreachRunIcon />}
            onClick={handleRunOutreach}
            color="success"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <QuickAction
            title="View Stats"
            description="See detailed campaign analytics"
            icon={<TrendingUpIcon />}
            onClick={handleViewStats}
            color="secondary"
          />
        </Grid>
      </Grid>

      {/* Recent Activity & Pending Jobs */}
      <Grid container spacing={3}>
        {/* Recent Outreach */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
                Recent Outreach
              </Typography>
              {isLoadingStats ? (
                <Box>
                  <Skeleton height={60} />
                  <Skeleton height={60} />
                  <Skeleton height={60} />
                </Box>
              ) : recentOutreach && recentOutreach.length > 0 ? (
                <List disablePadding>
                  {recentOutreach.map((item: RecentOutreach, index: number) => (
                    <React.Fragment key={item.id}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <OutreachIcon color="primary" fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={item.contact_email}
                          secondary={formatRelativeTime(item.sent_at)}
                          primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
                          secondaryTypographyProps={{ variant: 'caption' }}
                        />
                        <Chip
                          label={item.status}
                          size="small"
                          color={item.status === 'sent' ? 'success' : item.status === 'replied' ? 'primary' : 'default'}
                        />
                      </ListItem>
                      {index < recentOutreach.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                  No outreach yet. Run your first campaign!
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Pending Outreach Jobs */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" fontWeight={600}>
                  Pending Outreach
                </Typography>
                <Chip
                  label={`${pendingOutreach?.total_jobs || 0} jobs`}
                  size="small"
                  color="warning"
                />
              </Box>
              {isPendingOutreachLoading ? (
                <Box>
                  <Skeleton height={60} />
                  <Skeleton height={60} />
                </Box>
              ) : pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? (
                <List disablePadding>
                  {pendingOutreach.jobs.slice(0, 5).map((job, index: number) => (
                    <React.Fragment key={job.id}>
                      <ListItem
                        disablePadding
                        sx={{ py: 1.5, cursor: 'pointer', '&:hover': { backgroundColor: 'action.hover' } }}
                        onClick={() => navigate('/jobs')}
                      >
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <JobsIcon color="action" fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={job.title}
                          secondary={`${job.company} • ${job.location || 'Remote'}`}
                          primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
                          secondaryTypographyProps={{ variant: 'caption' }}
                        />
                      </ListItem>
                      {index < Math.min(pendingOutreach.jobs.length, 5) - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                  No pending jobs. Fetch new jobs to get started!
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;


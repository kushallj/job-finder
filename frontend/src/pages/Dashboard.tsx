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
  Alert,
  Stack,
  Paper,
} from '@mui/material';
import {
  Work as JobsIcon,
  People as ContactsIcon,
  Send as OutreachIcon,
  CheckCircle as SuccessIcon,
  Search as SearchIcon,
  AutoAwesome as AIIcon,
  Language as GlobeIcon,
  Bolt as FlashIcon,
  ArrowForward as ArrowForwardIcon,
  Tune as FilterIcon,
} from '@mui/icons-material';

import { useStats } from '../hooks/useStats';
import { useJobs } from '../hooks/useJobs';
import { useNavigate } from 'react-router-dom';
import { formatRelativeTime, formatPercentage, formatNumber } from '../utils/formatters';
import type { RecentOutreach, ProviderSyncResponse, MarketIntelligenceResponse } from '../api/types';
import ActionQueue from '../components/lifecycle/ActionQueue';
import { providersApi } from '../api/endpoints/providers';

// Stat Card Component
interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: React.ReactNode;
  color: 'primary' | 'success' | 'warning' | 'error' | 'secondary';
  loading?: boolean;
  onClick?: () => void;
}

const colorMap = {
  primary: { main: '#38BDF8', light: 'rgba(56, 189, 248, 0.12)', border: 'rgba(56, 189, 248, 0.3)' },
  success: { main: '#34D399', light: 'rgba(52, 211, 153, 0.12)', border: 'rgba(52, 211, 153, 0.3)' },
  warning: { main: '#FBBF24', light: 'rgba(251, 191, 36, 0.12)', border: 'rgba(251, 191, 36, 0.3)' },
  error: { main: '#F87171', light: 'rgba(248, 113, 113, 0.12)', border: 'rgba(248, 113, 113, 0.3)' },
  secondary: { main: '#818CF8', light: 'rgba(129, 140, 248, 0.12)', border: 'rgba(129, 140, 248, 0.3)' },
};

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, color, loading, onClick }) => {
  const c = colorMap[color] || colorMap.primary;

  return (
    <Card
      sx={{
        height: '100%',
        cursor: onClick ? 'pointer' : 'default',
        bgcolor: '#111827',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        '&:hover': onClick
          ? {
              transform: 'translateY(-2px)',
              boxShadow: `0 10px 25px -5px ${c.light}`,
              borderColor: c.main,
            }
          : {},
      }}
      onClick={onClick}
    >
      <CardContent sx={{ p: 2.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1.5 }}>
          <Box>
            <Typography variant="caption" sx={{ fontWeight: 700, color: '#64748B', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              {title}
            </Typography>
            {loading ? (
              <Skeleton variant="text" width={90} height={42} sx={{ bgcolor: '#1E293B' }} />
            ) : (
              <Typography variant="h4" sx={{ fontWeight: 800, color: '#F8FAFC', my: 0.5, letterSpacing: '-0.025em' }}>
                {value}
              </Typography>
            )}
            {subtitle && (
              <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 500 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              p: 1.25,
              borderRadius: '12px',
              backgroundColor: c.light,
              color: c.main,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: `1px solid ${c.border}`,
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

const QUICK_PRESETS = [
  'Python Developer',
  'S&P 500 US Tech',
  'Nifty 500 India',
  'YC / Accelerators',
  'Full Stack React',
  'AI / ML Engineer',
  'Staff Backend',
];

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { stats, recentOutreach, isLoadingStats, refetchStats } = useStats();
  const { allJobs, allJobsTotal, isAllJobsLoading, pendingOutreach, isPendingOutreachLoading, runQuery, isRunningQuery } = useJobs(1, 10);

  // Search state for job fetching
  const [searchQuery, setSearchQuery] = useState('Python Developer');
  const [minScore, setMinScore] = useState(50);
  const [providerSync, setProviderSync] = useState<ProviderSyncResponse | null>(null);
  const [market, setMarket] = useState<MarketIntelligenceResponse | null>(null);
  const [providerWorking, setProviderWorking] = useState(false);

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

  const handleProviderSync = async () => {
    if (!searchQuery.trim()) return;
    setProviderWorking(true);
    try {
      const result = await providersApi.sync(searchQuery.trim(), undefined, 30, 50);
      setProviderSync(result);
      await refetchStats();
    } finally {
      setProviderWorking(false);
    }
  };

  const handleLoadMarket = async () => {
    try {
      setMarket(await providersApi.market());
    } catch {
      // market fallback
    }
  };

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Hero Welcome Banner (ui.dev Deep Obsidian Gradient) */}
      <Box
        sx={{
          p: { xs: 3, md: 4 },
          mb: 4,
          borderRadius: '20px',
          background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.95) 0%, rgba(30, 41, 59, 0.85) 50%, rgba(15, 23, 42, 0.95) 100%)',
          color: '#F8FAFC',
          position: 'relative',
          overflow: 'hidden',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 20px 50px -10px rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(20px)',
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1, maxWidth: 850 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
            <Chip
              icon={<AIIcon sx={{ fontSize: '16px !important', color: '#38BDF8 !important' }} />}
              label="Autonomous Career Intelligence Active"
              size="small"
              sx={{
                bgcolor: 'rgba(56, 189, 248, 0.12)',
                color: '#38BDF8',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                fontWeight: 700,
                backdropFilter: 'blur(8px)',
              }}
            />
            <Chip
              label="ui.dev Edition"
              size="small"
              sx={{
                bgcolor: 'rgba(129, 140, 248, 0.12)',
                color: '#818CF8',
                border: '1px solid rgba(129, 140, 248, 0.3)',
                fontWeight: 700,
              }}
            />
          </Stack>
          <Typography variant="h3" sx={{ fontWeight: 800, letterSpacing: '-0.03em', mb: 1, color: '#F8FAFC' }}>
            Welcome to your Career Command Center 👋
          </Typography>
          <Typography variant="body1" sx={{ color: '#94A3B8', mb: 3, fontSize: '1rem', maxWidth: 650 }}>
            Discover targeted roles across <strong>2,050+ live opportunities</strong> in S&P 500, Nifty 500, Y Combinator, and FinTech ecosystems with 1-click decision-maker outreach.
          </Typography>
        </Box>
      </Box>

      {/* Quick Search & AI Pipeline Trigger */}
      <Card sx={{ mb: 4, p: 1, bgcolor: '#111827', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2 }}>
            <FilterIcon sx={{ color: '#38BDF8' }} />
            <Typography variant="h6" fontWeight={800} color="#F8FAFC">
              Smart Job Search & Pipeline Ingestion
            </Typography>
          </Stack>

          {/* Quick preset chips */}
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2.5 }}>
            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600, alignSelf: 'center', mr: 0.5 }}>
              Catalogs & presets:
            </Typography>
            {QUICK_PRESETS.map((preset) => {
              const isSelected = searchQuery === preset;
              return (
                <Chip
                  key={preset}
                  label={preset}
                  size="small"
                  onClick={() => setSearchQuery(preset)}
                  sx={{
                    cursor: 'pointer',
                    bgcolor: isSelected ? 'rgba(56, 189, 248, 0.18)' : 'rgba(255, 255, 255, 0.04)',
                    color: isSelected ? '#38BDF8' : '#94A3B8',
                    border: isSelected ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
                    fontWeight: 700,
                    '&:hover': { bgcolor: 'rgba(56, 189, 248, 0.12)', color: '#F8FAFC' },
                  }}
                />
              );
            })}
          </Stack>

          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, md: 5 }}>
              <TextField
                placeholder="Enter role, skills, or target title..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                size="small"
                fullWidth
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: '#64748B' }} />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Box sx={{ px: 1 }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 600, display: 'block', mb: 0.5 }}>
                  Min Match Score: <strong style={{ color: '#38BDF8' }}>{minScore}%</strong>
                </Typography>
                <Slider
                  value={minScore}
                  onChange={(_, value) => setMinScore(value as number)}
                  min={0}
                  max={100}
                  step={5}
                  valueLabelDisplay="auto"
                  size="small"
                  sx={{ color: '#38BDF8' }}
                />
              </Box>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 4 }}>
              <Stack direction="row" spacing={1.5}>
                <Button
                  variant="contained"
                  color="primary"
                  fullWidth
                  onClick={handleFetchJobs}
                  disabled={isRunningQuery || !searchQuery.trim()}
                  startIcon={isRunningQuery ? <Skeleton variant="circular" width={18} height={18} /> : <FlashIcon />}
                  sx={{ py: 1, fontWeight: 700 }}
                >
                  {isRunningQuery ? 'AI Matching...' : 'Fetch & AI Match'}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => void handleProviderSync()}
                  disabled={providerWorking || !searchQuery.trim()}
                  title="Enrich with JobDataAPI & AIDevBoard"
                  sx={{ minWidth: 130, py: 1 }}
                >
                  {providerWorking ? 'Syncing...' : 'Sync Boards'}
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* KPI Stats Grid */}
      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Total Opportunities"
            value={formatNumber(stats?.total_jobs)}
            subtitle="2,050+ across S&P 500, Nifty & YC"
            icon={<JobsIcon />}
            color="primary"
            loading={isLoadingStats}
            onClick={() => navigate('/jobs')}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Decision-Makers"
            value={formatNumber(stats?.total_contacts)}
            subtitle="Verified Founders & CTOs"
            icon={<ContactsIcon />}
            color="success"
            loading={isLoadingStats}
            onClick={() => navigate('/contacts')}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Outreach Sent"
            value={formatNumber(stats?.emails_sent)}
            subtitle={`${stats?.total_applications || 0} active applications`}
            icon={<OutreachIcon />}
            color="warning"
            loading={isLoadingStats}
            onClick={() => navigate('/outreach')}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Delivery & Success"
            value={formatPercentage(stats?.success_rate)}
            subtitle="Strict <= 2/company cap active"
            icon={<SuccessIcon />}
            color="secondary"
            loading={isLoadingStats}
            onClick={() => navigate('/stats')}
          />
        </Grid>
      </Grid>

      {/* "Do This Next" Action Queue */}
      <ActionQueue limit={6} />

      {/* External Intelligence & Market Trends */}
      <Card sx={{ mb: 4, bgcolor: '#111827', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 2 }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1, borderRadius: '10px', bgcolor: 'rgba(56, 189, 248, 0.12)', color: '#38BDF8' }}>
                <GlobeIcon />
              </Box>
              <Box>
                <Typography variant="h6" fontWeight={800} color="#F8FAFC">
                  Market & Multi-Catalog Intelligence
                </Typography>
                <Typography variant="body2" color="#94A3B8">
                  Covers S&P 500 (US), Nifty 500 (NSE), Y Combinator, Global FinTech Fest, and Shark Tank startups.
                </Typography>
              </Box>
            </Stack>
            <Button variant="outlined" size="small" onClick={() => void handleLoadMarket()}>
              Refresh Signals
            </Button>
          </Box>

          {providerSync && (
            <Alert severity="success" sx={{ mb: 2.5, borderRadius: '10px', bgcolor: 'rgba(52, 211, 153, 0.12)', color: '#34D399', border: '1px solid rgba(52, 211, 153, 0.3)' }}>
              Synced <strong>{providerSync.total_fetched}</strong> external roles · {providerSync.total_inserted} newly indexed · {providerSync.total_updated} updated.
            </Alert>
          )}

          {market?.data ? (
            <Grid container spacing={2}>
              {Object.entries(market.data).slice(0, 4).map(([key, value]) => (
                <Grid key={key} size={{ xs: 6, sm: 3 }}>
                  <Paper variant="outlined" sx={{ p: 2, borderRadius: '12px', bgcolor: '#0E131F', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                    <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600, textTransform: 'capitalize' }}>
                      {key.replaceAll('_', ' ')}
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 800, color: '#F8FAFC', mt: 0.5 }}>
                      {String(value)}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          ) : (
            <Box sx={{ p: 2, borderRadius: '10px', bgcolor: '#0E131F', border: '1px solid rgba(255, 255, 255, 0.04)', textAlign: 'center' }}>
              <Typography variant="body2" color="#94A3B8">
                Click <strong>"Refresh Signals"</strong> or <strong>"Sync Boards"</strong> above to pull live market compensation and AI developer demand.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Recent Activity Feed & Pending Outreach */}
      <Grid container spacing={3}>
        {/* Recent Outreach Feed */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', bgcolor: '#111827', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h6" fontWeight={800} color="#F8FAFC">
                  Recent Outreach Activity
                </Typography>
                <Button size="small" onClick={() => navigate('/outreach')} endIcon={<ArrowForwardIcon fontSize="small" />} sx={{ color: '#38BDF8' }}>
                  View all
                </Button>
              </Stack>
              <Divider sx={{ mb: 1, borderColor: 'rgba(255, 255, 255, 0.08)' }} />

              {isLoadingStats ? (
                <Stack spacing={1.5} sx={{ py: 2 }}>
                  <Skeleton height={50} sx={{ bgcolor: '#1E293B' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#1E293B' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#1E293B' }} />
                </Stack>
              ) : recentOutreach && recentOutreach.length > 0 ? (
                <List disablePadding>
                  {recentOutreach.slice(0, 5).map((item: RecentOutreach, index: number) => (
                    <React.Fragment key={item.id}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <ListItemIcon sx={{ minWidth: 38 }}>
                          <Box sx={{ p: 0.75, borderRadius: '8px', bgcolor: 'rgba(56, 189, 248, 0.12)', color: '#38BDF8' }}>
                            <OutreachIcon fontSize="small" />
                          </Box>
                        </ListItemIcon>
                        <ListItemText
                          primary={item.contact_email}
                          secondary={formatRelativeTime(item.sent_at)}
                          primaryTypographyProps={{ variant: 'body2', fontWeight: 600, color: '#F8FAFC' }}
                          secondaryTypographyProps={{ variant: 'caption', color: '#64748B' }}
                        />
                        <Chip
                          label={item.status}
                          size="small"
                          color={item.status === 'sent' ? 'success' : item.status === 'replied' ? 'primary' : 'default'}
                          sx={{ textTransform: 'capitalize' }}
                        />
                      </ListItem>
                      {index < Math.min(recentOutreach.length, 5) - 1 && <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.05)' }} />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ py: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="#94A3B8">
                    No outreach sent yet. Select an opportunity to send your first message!
                  </Typography>
                  <Button variant="outlined" size="small" sx={{ mt: 1.5 }} onClick={() => navigate('/outreach')}>
                    Start Outreach
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Top Opportunities & Ingested Positions Feed */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', bgcolor: '#111827', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" fontWeight={800} color="#F8FAFC">
                  {pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? 'Top Opportunities Ready to Apply' : 'Recently Crawled Positions'}
                </Typography>
                <Chip
                  label={pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? `${pendingOutreach.total_jobs || 0} Ready` : `${allJobsTotal || 0} Ingested`}
                  size="small"
                  sx={{ bgcolor: 'rgba(52, 211, 153, 0.12)', color: '#34D399', fontWeight: 700, border: '1px solid rgba(52, 211, 153, 0.3)' }}
                />
              </Box>
              <Divider sx={{ mb: 1, borderColor: 'rgba(255, 255, 255, 0.08)' }} />

              {isPendingOutreachLoading || isAllJobsLoading ? (
                <Stack spacing={1.5} sx={{ py: 2 }}>
                  <Skeleton height={50} sx={{ bgcolor: '#1E293B' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#1E293B' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#1E293B' }} />
                </Stack>
              ) : (pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? pendingOutreach.jobs : allJobs).length > 0 ? (
                <List disablePadding>
                  {(pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? pendingOutreach.jobs : allJobs).slice(0, 6).map((job, index: number) => (
                    <React.Fragment key={job.id}>
                      <ListItem
                        disablePadding
                        sx={{
                          py: 1.5,
                          cursor: 'pointer',
                          borderRadius: '8px',
                          px: 1,
                          '&:hover': { backgroundColor: 'rgba(56, 189, 248, 0.06)' },
                        }}
                        onClick={() => navigate(`/opportunities/${job.id}`)}
                      >
                        <ListItemIcon sx={{ minWidth: 38 }}>
                          <Box sx={{ p: 0.75, borderRadius: '8px', bgcolor: 'rgba(52, 211, 153, 0.12)', color: '#34D399' }}>
                            <JobsIcon fontSize="small" />
                          </Box>
                        </ListItemIcon>
                        <ListItemText
                          primary={job.title}
                          secondary={`${job.company || 'Unknown'} • ${job.location || 'Remote'}`}
                          primaryTypographyProps={{ variant: 'body2', fontWeight: 700, color: '#F8FAFC' }}
                          secondaryTypographyProps={{ variant: 'caption', color: '#64748B' }}
                        />
                        <Button size="small" variant="text" endIcon={<ArrowForwardIcon fontSize="small" />} sx={{ color: '#38BDF8', fontWeight: 700 }}>
                          Brief
                        </Button>
                      </ListItem>
                      {index < Math.min((pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? pendingOutreach.jobs : allJobs).length, 6) - 1 && (
                        <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.05)' }} />
                      )}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ py: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="#94A3B8">
                    No positions found. The autonomous crawler is scanning company boards in the background...
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;

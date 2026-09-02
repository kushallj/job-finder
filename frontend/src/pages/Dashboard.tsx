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
  LocalFireDepartment as FlameIcon,
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

// Neo-Brutalist Stat Card Component
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
  primary: { main: '#FF3E00', bg: '#FF3E00', text: '#FFFFFF', shadow: '#000000' },
  success: { main: '#00E676', bg: '#00E676', text: '#0A0D0E', shadow: '#000000' },
  warning: { main: '#FFDE59', bg: '#FFDE59', text: '#0A0D0E', shadow: '#000000' },
  error: { main: '#FF007A', bg: '#FF007A', text: '#FFFFFF', shadow: '#000000' },
  secondary: { main: '#8A2BE2', bg: '#8A2BE2', text: '#FFFFFF', shadow: '#000000' },
};

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, color, loading, onClick }) => {
  const c = colorMap[color] || colorMap.primary;

  return (
    <Card
      sx={{
        height: '100%',
        cursor: onClick ? 'pointer' : 'default',
        bgcolor: '#12181B',
        border: '3px solid #2A363F',
        boxShadow: '5px 5px 0px #000000',
        borderRadius: '20px',
        transition: 'all 0.15s ease-in-out',
        '&:hover': onClick
          ? {
              transform: 'translate(-2px, -2px)',
              boxShadow: `7px 7px 0px ${c.main}`,
              borderColor: c.main,
            }
          : {},
      }}
      onClick={onClick}
    >
      <CardContent sx={{ p: 2.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1.5 }}>
          <Box>
            <Typography variant="caption" sx={{ fontWeight: 900, color: '#A0AEC0', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              {title}
            </Typography>
            {loading ? (
              <Skeleton variant="text" width={90} height={42} sx={{ bgcolor: '#181E24' }} />
            ) : (
              <Typography variant="h4" sx={{ fontWeight: 900, color: '#F6F1D7', my: 0.5, letterSpacing: '-0.03em' }}>
                {value}
              </Typography>
            )}
            {subtitle && (
              <Typography variant="caption" sx={{ color: '#A0AEC0', fontWeight: 600 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              p: 1.25,
              borderRadius: '14px',
              backgroundColor: c.bg,
              color: c.text,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '2px solid #000000',
              boxShadow: '3px 3px 0px #000000',
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
  '⚡ S&P 500 US Tech',
  '🇮🇳 Nifty 500 Giants',
  '🚀 YC / Unicorns',
  '🔥 Python Backend',
  '⚡ Full Stack React',
  '🤖 AI / ML Engineer',
  '💀 Ghost-Proof Roles',
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
      {/* Fireship Hero Welcome Banner */}
      <Box
        sx={{
          p: { xs: 3, md: 4 },
          mb: 4,
          borderRadius: '24px',
          bgcolor: '#12181B',
          border: '3.5px solid #000000',
          boxShadow: '8px 8px 0px #FF3E00',
          color: '#F6F1D7',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1, maxWidth: 900 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
            <Chip
              icon={<FlameIcon sx={{ fontSize: '16px !important', color: '#000000 !important' }} />}
              label="100-Second Speedrun Mode"
              size="small"
              sx={{
                bgcolor: '#FFDE59',
                color: '#0A0D0E',
                fontWeight: 900,
                border: '2px solid #000',
              }}
            />
            <Chip
              label="2,050+ Live Roles"
              size="small"
              sx={{
                bgcolor: '#00E676',
                color: '#0A0D0E',
                fontWeight: 900,
                border: '2px solid #000',
              }}
            />
          </Stack>
          <Typography variant="h2" sx={{ fontWeight: 900, letterSpacing: '-0.04em', mb: 1, color: '#F6F1D7', textTransform: 'uppercase' }}>
            Find your next 10x tech job <span style={{ color: '#FF3E00' }}>in 100 seconds</span>. 🔥
          </Typography>
          <Typography variant="body1" sx={{ color: '#A0AEC0', mb: 3, fontSize: '1.05rem', maxWidth: 700, fontWeight: 500 }}>
            No BS cover letters. Direct ATS pipelines across <strong>S&P 500</strong>, <strong>Nifty 500</strong>, and <strong>YC Unicorns</strong> with 1-click decision maker outreach.
          </Typography>
        </Box>
      </Box>

      {/* Quick Search & AI Pipeline Trigger */}
      <Card sx={{ mb: 4, p: 1, bgcolor: '#12181B', border: '3px solid #2A363F', boxShadow: '6px 6px 0px #000000' }}>
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2 }}>
            <FilterIcon sx={{ color: '#FFDE59' }} />
            <Typography variant="h6" fontWeight={900} color="#F6F1D7" textTransform="uppercase">
              Job Speedrun & Pipeline Search
            </Typography>
          </Stack>

          {/* Quick preset chips */}
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2.5 }}>
            <Typography variant="caption" sx={{ color: '#A0AEC0', fontWeight: 900, alignSelf: 'center', mr: 0.5, textTransform: 'uppercase' }}>
              Quick Presets:
            </Typography>
            {QUICK_PRESETS.map((preset) => {
              const isSelected = searchQuery === preset;
              return (
                <Chip
                  key={preset}
                  label={preset}
                  size="small"
                  onClick={() => setSearchQuery(preset.replace(/^[^\w]+/, '').trim())}
                  sx={{
                    cursor: 'pointer',
                    bgcolor: isSelected ? '#FFDE59' : '#181E24',
                    color: isSelected ? '#0A0D0E' : '#F6F1D7',
                    border: '2px solid #000',
                    boxShadow: isSelected ? '3px 3px 0px #FF3E00' : '2px 2px 0px #000',
                    fontWeight: 900,
                    '&:hover': { bgcolor: '#FF3E00', color: '#FFFFFF', transform: 'translateY(-1px)' },
                  }}
                />
              );
            })}
          </Stack>

          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, md: 5 }}>
              <TextField
                placeholder="Enter role, tech stack (Python, React, Go, PyTorch)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                size="small"
                fullWidth
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: '#A0AEC0' }} />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Box sx={{ px: 1 }}>
                <Typography variant="caption" sx={{ color: '#A0AEC0', fontWeight: 900, display: 'block', mb: 0.5, textTransform: 'uppercase' }}>
                  Min Match Score: <strong style={{ color: '#FFDE59' }}>{minScore}%</strong>
                </Typography>
                <Slider
                  value={minScore}
                  onChange={(_, value) => setMinScore(value as number)}
                  min={0}
                  max={100}
                  step={5}
                  valueLabelDisplay="auto"
                  size="small"
                  sx={{ color: '#FF3E00' }}
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
                  sx={{ py: 1.2, fontWeight: 900 }}
                >
                  {isRunningQuery ? 'Speedrunning...' : '⚡ Match Roles'}
                </Button>
                <Button
                  variant="contained"
                  color="secondary"
                  onClick={() => void handleProviderSync()}
                  disabled={providerWorking || !searchQuery.trim()}
                  title="Enrich with external boards"
                  sx={{ minWidth: 130, py: 1.2, fontWeight: 900 }}
                >
                  {providerWorking ? 'Syncing...' : 'Sync ATS'}
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
            subtitle="2,050+ in S&P 500, Nifty & YC"
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
            subtitle="1,043 CTOs & Leads"
            icon={<ContactsIcon />}
            color="success"
            loading={isLoadingStats}
            onClick={() => navigate('/contacts')}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Emails Sent"
            value={formatNumber(stats?.emails_sent)}
            subtitle="Max 2/company cap active"
            icon={<OutreachIcon />}
            color="warning"
            loading={isLoadingStats}
            onClick={() => navigate('/outreach')}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Delivery Rate"
            value={formatPercentage(stats?.success_rate)}
            subtitle="Ghost-Proof Outreach"
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
      <Card sx={{ mb: 4, bgcolor: '#12181B', border: '3px solid #2A363F', boxShadow: '6px 6px 0px #000000' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 2 }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.2, borderRadius: '12px', bgcolor: '#FFDE59', color: '#0A0D0E', border: '2px solid #000', boxShadow: '3px 3px 0px #000' }}>
                <GlobeIcon />
              </Box>
              <Box>
                <Typography variant="h6" fontWeight={900} color="#F6F1D7" textTransform="uppercase">
                  Global Multi-Catalog Intelligence
                </Typography>
                <Typography variant="body2" color="#A0AEC0">
                  Live benchmarks across S&P 500 (US), Nifty 500 (NSE), YC, and FinTech ecosystems.
                </Typography>
              </Box>
            </Stack>
            <Button variant="outlined" size="small" onClick={() => void handleLoadMarket()} sx={{ fontWeight: 900 }}>
              Refresh Signals
            </Button>
          </Box>

          {providerSync && (
            <Alert severity="success" sx={{ mb: 2.5, borderRadius: '14px', bgcolor: '#00E676', color: '#0A0D0E', border: '2px solid #000', fontWeight: 700 }}>
              Synced <strong>{providerSync.total_fetched}</strong> external roles · {providerSync.total_inserted} newly indexed · {providerSync.total_updated} updated.
            </Alert>
          )}

          {market?.data ? (
            <Grid container spacing={2}>
              {Object.entries(market.data).slice(0, 4).map(([key, value]) => (
                <Grid key={key} size={{ xs: 6, sm: 3 }}>
                  <Paper variant="outlined" sx={{ p: 2, borderRadius: '16px', bgcolor: '#0A0D0E', border: '2.5px solid #2A363F', boxShadow: '3px 3px 0px #000' }}>
                    <Typography variant="caption" sx={{ color: '#A0AEC0', fontWeight: 900, textTransform: 'uppercase' }}>
                      {key.replaceAll('_', ' ')}
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 900, color: '#FFDE59', mt: 0.5 }}>
                      {String(value)}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          ) : (
            <Box sx={{ p: 2.5, borderRadius: '14px', bgcolor: '#0A0D0E', border: '2px solid #2A363F', textAlign: 'center' }}>
              <Typography variant="body2" color="#A0AEC0" fontWeight={600}>
                💡 <strong>Fireship Pro Tip:</strong> Click <strong>"Sync ATS"</strong> above to pull live market compensation and AI developer demand.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Recent Activity Feed & Top Positions */}
      <Grid container spacing={3}>
        {/* Recent Outreach Feed */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', bgcolor: '#12181B', border: '3px solid #2A363F', boxShadow: '6px 6px 0px #000000' }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h6" fontWeight={900} color="#F6F1D7" textTransform="uppercase">
                  Recent Outreach Dispatches
                </Typography>
                <Button size="small" onClick={() => navigate('/outreach')} endIcon={<ArrowForwardIcon fontSize="small" />} sx={{ color: '#FFDE59', fontWeight: 900 }}>
                  View all
                </Button>
              </Stack>
              <Divider sx={{ mb: 1, borderColor: '#2A363F' }} />

              {isLoadingStats ? (
                <Stack spacing={1.5} sx={{ py: 2 }}>
                  <Skeleton height={50} sx={{ bgcolor: '#181E24' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#181E24' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#181E24' }} />
                </Stack>
              ) : recentOutreach && recentOutreach.length > 0 ? (
                <List disablePadding>
                  {recentOutreach.slice(0, 5).map((item: RecentOutreach, index: number) => (
                    <React.Fragment key={item.id}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <ListItemIcon sx={{ minWidth: 38 }}>
                          <Box sx={{ p: 0.75, borderRadius: '10px', bgcolor: '#FF3E00', color: '#FFFFFF', border: '1.5px solid #000' }}>
                            <OutreachIcon fontSize="small" />
                          </Box>
                        </ListItemIcon>
                        <ListItemText
                          primary={item.contact_email}
                          secondary={formatRelativeTime(item.sent_at)}
                          primaryTypographyProps={{ variant: 'body2', fontWeight: 700, color: '#F6F1D7' }}
                          secondaryTypographyProps={{ variant: 'caption', color: '#A0AEC0' }}
                        />
                        <Chip
                          label={item.status}
                          size="small"
                          color={item.status === 'sent' ? 'success' : item.status === 'replied' ? 'primary' : 'default'}
                        />
                      </ListItem>
                      {index < Math.min(recentOutreach.length, 5) - 1 && <Divider sx={{ borderColor: '#2A363F' }} />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ py: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="#A0AEC0">
                    No outreach sent yet. Select an opportunity to send your first message!
                  </Typography>
                  <Button variant="contained" color="secondary" size="small" sx={{ mt: 1.5, fontWeight: 900 }} onClick={() => navigate('/outreach')}>
                    Start Outreach
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Top Opportunities Feed */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', bgcolor: '#12181B', border: '3px solid #2A363F', boxShadow: '6px 6px 0px #000000' }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" fontWeight={900} color="#F6F1D7" textTransform="uppercase">
                  {pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? '🔥 Top Speedrun Roles' : 'Recently Crawled Positions'}
                </Typography>
                <Chip
                  label={pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? `${pendingOutreach.total_jobs || 0} Ready` : `${allJobsTotal || 0} Ingested`}
                  size="small"
                  sx={{ bgcolor: '#00E676', color: '#0A0D0E', fontWeight: 900, border: '2px solid #000' }}
                />
              </Box>
              <Divider sx={{ mb: 1, borderColor: '#2A363F' }} />

              {isPendingOutreachLoading || isAllJobsLoading ? (
                <Stack spacing={1.5} sx={{ py: 2 }}>
                  <Skeleton height={50} sx={{ bgcolor: '#181E24' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#181E24' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#181E24' }} />
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
                          borderRadius: '10px',
                          px: 1,
                          '&:hover': { backgroundColor: '#181E24', transform: 'translateX(4px)' },
                          transition: 'all 0.12s ease',
                        }}
                        onClick={() => navigate(`/opportunities/${job.id}`)}
                      >
                        <ListItemIcon sx={{ minWidth: 38 }}>
                          <Box sx={{ p: 0.75, borderRadius: '10px', bgcolor: '#00E676', color: '#0A0D0E', border: '1.5px solid #000' }}>
                            <JobsIcon fontSize="small" />
                          </Box>
                        </ListItemIcon>
                        <ListItemText
                          primary={job.title}
                          secondary={`${job.company || 'Unknown'} • ${job.location || 'Remote'}`}
                          primaryTypographyProps={{ variant: 'body2', fontWeight: 900, color: '#F6F1D7' }}
                          secondaryTypographyProps={{ variant: 'caption', color: '#A0AEC0' }}
                        />
                        <Button size="small" variant="contained" color="secondary" endIcon={<ArrowForwardIcon fontSize="small" />} sx={{ fontWeight: 900, fontSize: '0.75rem', px: 1.5, py: 0.5 }}>
                          Brief
                        </Button>
                      </ListItem>
                      {index < Math.min((pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? pendingOutreach.jobs : allJobs).length, 6) - 1 && (
                        <Divider sx={{ borderColor: '#2A363F' }} />
                      )}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ py: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="#A0AEC0">
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

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
import { FunnelConversionTracker } from '../components/analytics/FunnelConversionTracker';



// Web3 / HFT Stat Card Component
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
  primary: { main: '#00F0FF', light: 'rgba(0, 240, 255, 0.15)', border: 'rgba(0, 240, 255, 0.4)' },
  success: { main: '#00FFA3', light: 'rgba(0, 255, 163, 0.15)', border: 'rgba(0, 255, 163, 0.4)' },
  warning: { main: '#FFE600', light: 'rgba(255, 230, 0, 0.15)', border: 'rgba(255, 230, 0, 0.4)' },
  error: { main: '#FF007A', light: 'rgba(255, 0, 122, 0.15)', border: 'rgba(255, 0, 122, 0.4)' },
  secondary: { main: '#7928CA', light: 'rgba(121, 40, 202, 0.2)', border: 'rgba(121, 40, 202, 0.4)' },
};

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, color, loading, onClick }) => {
  const c = colorMap[color] || colorMap.primary;

  return (
    <Card
      sx={{
        height: '100%',
        cursor: onClick ? 'pointer' : 'default',
        bgcolor: '#0D131F',
        border: '1.5px solid rgba(0, 240, 255, 0.2)',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)',
        borderRadius: '20px',
        transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        '&:hover': onClick
          ? {
              transform: 'translateY(-4px)',
              boxShadow: `0 0 25px ${c.light}, 0 0 50px rgba(0, 240, 255, 0.15)`,
              borderColor: c.main,
            }
          : {},
      }}
      onClick={onClick}
    >
      <CardContent sx={{ p: 2.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1.5 }}>
          <Box>
            <Typography variant="caption" sx={{ fontWeight: 900, color: '#94A3B8', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              {title}
            </Typography>
            {loading ? (
              <Skeleton variant="text" width={90} height={42} sx={{ bgcolor: '#161F30' }} />
            ) : (
              <Typography variant="h3" sx={{ fontWeight: 900, color: '#F8FAFC', my: 0.5, letterSpacing: '-0.03em' }}>
                {value}
              </Typography>
            )}
            {subtitle && (
              <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 600 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              p: 1.25,
              borderRadius: '14px',
              backgroundColor: c.light,
              color: c.main,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: `1px solid ${c.border}`,
              boxShadow: `0 0 15px ${c.light}`,
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
  '⚡ S&P 500 US Alpha',
  '🇮🇳 Nifty 500 Tech',
  '🚀 YC / Unicorns',
  '🔥 HFT & Distributed',
  '⚡ Python & FastAPI',
  '🤖 GenAI & LLMs',
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
    <Box sx={{ maxWidth: 1400, mx: 'auto', color: '#F8FAFC' }}>
      {/* Web3 & HFT Hero Cockpit Banner */}
      <Box
        sx={{
          p: { xs: 3, md: 4.5 },
          mb: 4,
          borderRadius: '24px',
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 240, 255, 0.35)',
          boxShadow: '0 0 35px rgba(0, 240, 255, 0.2), 0 0 70px rgba(0, 255, 163, 0.1)',
          color: '#F8FAFC',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1, maxWidth: 950 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
            <Chip
              icon={<FlameIcon sx={{ fontSize: '16px !important', color: '#00FFA3 !important' }} />}
              label="HFT Alpha Liquidity Active"
              size="small"
              sx={{
                bgcolor: 'rgba(0, 255, 163, 0.15)',
                color: '#00FFA3',
                fontWeight: 900,
                border: '1px solid rgba(0, 255, 163, 0.4)',
                boxShadow: '0 0 10px rgba(0, 255, 163, 0.25)',
              }}
            />
            <Chip
              label="2,050+ Live Pools"
              size="small"
              sx={{
                bgcolor: 'rgba(0, 240, 255, 0.15)',
                color: '#00F0FF',
                fontWeight: 900,
                border: '1px solid rgba(0, 240, 255, 0.4)',
              }}
            />
          </Stack>
          <Typography variant="h2" sx={{ fontWeight: 900, letterSpacing: '-0.035em', mb: 1.5, background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', textTransform: 'uppercase' }}>
            Next-Gen Career Intelligence Cockpit ⚡
          </Typography>
          <Typography variant="body1" sx={{ color: '#94A3B8', mb: 3, fontSize: '1.1rem', maxWidth: 740, fontWeight: 500 }}>
            Sub-millisecond direct ATS scraping across <strong>S&P 500</strong>, <strong>Nifty 500</strong>, and <strong>Top Tier-1 Unicorns</strong> with 1-click autonomous decision maker outreach.
          </Typography>
        </Box>
      </Box>

      {/* Account-Based Outreach Conversion Funnel */}
      <FunnelConversionTracker />

      {/* Quick Search & AI Pipeline Trigger */}

      <Card sx={{ mb: 4, p: 1, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2 }}>
            <FilterIcon sx={{ color: '#00F0FF' }} />
            <Typography variant="h6" fontWeight={900} color="#F8FAFC" textTransform="uppercase">
              Alpha Search & Pipeline Ingestion
            </Typography>
          </Stack>

          {/* Quick preset chips */}
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2.5 }}>
            <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 900, alignSelf: 'center', mr: 0.5, textTransform: 'uppercase' }}>
              Alpha Presets:
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
                    bgcolor: isSelected ? 'rgba(0, 240, 255, 0.25)' : 'rgba(0, 240, 255, 0.05)',
                    color: isSelected ? '#00F0FF' : '#94A3B8',
                    border: isSelected ? '1px solid #00F0FF' : '1px solid rgba(0, 240, 255, 0.2)',
                    boxShadow: isSelected ? '0 0 15px rgba(0, 240, 255, 0.35)' : 'none',
                    fontWeight: 800,
                    '&:hover': { bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', borderColor: '#00F0FF' },
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
                      <SearchIcon sx={{ color: '#00F0FF' }} />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Box sx={{ px: 1 }}>
                <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 900, display: 'block', mb: 0.5, textTransform: 'uppercase' }}>
                  Min Match Score: <strong style={{ color: '#FFE600' }}>{minScore}%</strong>
                </Typography>
                <Slider
                  value={minScore}
                  onChange={(_, value) => setMinScore(value as number)}
                  min={0}
                  max={100}
                  step={5}
                  valueLabelDisplay="auto"
                  size="small"
                  sx={{ color: '#00F0FF' }}
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
                  {isRunningQuery ? 'Sourcing...' : '⚡ Match Roles'}
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
      <Card sx={{ mb: 4, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
        <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 2 }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box sx={{ p: 1.2, borderRadius: '12px', bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', border: '1px solid rgba(0, 240, 255, 0.4)', boxShadow: '0 0 15px rgba(0, 240, 255, 0.3)' }}>
                <GlobeIcon />
              </Box>
              <Box>
                <Typography variant="h6" fontWeight={900} color="#F8FAFC" textTransform="uppercase">
                  Global Multi-Catalog Intelligence
                </Typography>
                <Typography variant="body2" color="#94A3B8">
                  Live benchmarks across S&P 500 (US), Nifty 500 (NSE), YC, and FinTech ecosystems.
                </Typography>
              </Box>
            </Stack>
            <Button variant="outlined" size="small" onClick={() => void handleLoadMarket()} sx={{ fontWeight: 900 }}>
              Refresh Signals
            </Button>
          </Box>

          {providerSync && (
            <Alert severity="success" sx={{ mb: 2.5, borderRadius: '14px', bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', border: '1px solid rgba(0, 255, 163, 0.4)', fontWeight: 800 }}>
              Synced <strong>{providerSync.total_fetched}</strong> external roles · {providerSync.total_inserted} newly indexed · {providerSync.total_updated} updated.
            </Alert>
          )}

          {market?.data ? (
            <Grid container spacing={2}>
              {Object.entries(market.data).slice(0, 4).map(([key, value]) => (
                <Grid key={key} size={{ xs: 6, sm: 3 }}>
                  <Paper variant="outlined" sx={{ p: 2, borderRadius: '16px', bgcolor: '#080C12', border: '1.5px solid rgba(0, 240, 255, 0.2)', boxShadow: '0 0 15px rgba(0, 0, 0, 0.5)' }}>
                    <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 900, textTransform: 'uppercase' }}>
                      {key.replaceAll('_', ' ')}
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 900, color: '#FFE600', mt: 0.5 }}>
                      {String(value)}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          ) : (
            <Box sx={{ p: 2.5, borderRadius: '14px', bgcolor: '#080C12', border: '1px solid rgba(0, 240, 255, 0.15)', textAlign: 'center' }}>
              <Typography variant="body2" color="#94A3B8" fontWeight={600}>
                ⚡ Click <strong>"Sync ATS"</strong> above to pull live market compensation and AI developer demand.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Recent Activity Feed & Top Positions */}
      <Grid container spacing={3}>
        {/* Recent Outreach Feed */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h6" fontWeight={900} color="#F8FAFC" textTransform="uppercase">
                  Recent Outreach Dispatches
                </Typography>
                <Button size="small" onClick={() => navigate('/outreach')} endIcon={<ArrowForwardIcon fontSize="small" />} sx={{ color: '#00F0FF', fontWeight: 900 }}>
                  View all
                </Button>
              </Stack>
              <Divider sx={{ mb: 1, borderColor: 'rgba(0, 240, 255, 0.15)' }} />

              {isLoadingStats ? (
                <Stack spacing={1.5} sx={{ py: 2 }}>
                  <Skeleton height={50} sx={{ bgcolor: '#161F30' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#161F30' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#161F30' }} />
                </Stack>
              ) : recentOutreach && recentOutreach.length > 0 ? (
                <List disablePadding>
                  {recentOutreach.slice(0, 5).map((item: RecentOutreach, index: number) => (
                    <React.Fragment key={item.id}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <ListItemIcon sx={{ minWidth: 38 }}>
                          <Box sx={{ p: 0.75, borderRadius: '10px', bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', border: '1px solid rgba(0, 240, 255, 0.4)' }}>
                            <OutreachIcon fontSize="small" />
                          </Box>
                        </ListItemIcon>
                        <ListItemText
                          primary={item.contact_email}
                          secondary={formatRelativeTime(item.sent_at)}
                          primaryTypographyProps={{ variant: 'body2', fontWeight: 800, color: '#F8FAFC' }}
                          secondaryTypographyProps={{ variant: 'caption', color: '#94A3B8' }}
                        />
                        <Chip
                          label={item.status}
                          size="small"
                          color={item.status === 'sent' ? 'success' : item.status === 'replied' ? 'primary' : 'default'}
                        />
                      </ListItem>
                      {index < Math.min(recentOutreach.length, 5) - 1 && <Divider sx={{ borderColor: 'rgba(0, 240, 255, 0.08)' }} />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ py: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="#94A3B8">
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
          <Card sx={{ height: '100%', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)' }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" fontWeight={900} color="#F8FAFC" textTransform="uppercase">
                  {pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? '⚡ Top Alpha Roles' : 'Recently Crawled Positions'}
                </Typography>
                <Chip
                  label={pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? `${pendingOutreach.total_jobs || 0} Ready` : `${allJobsTotal || 0} Ingested`}
                  size="small"
                  sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 900, border: '1px solid rgba(0, 255, 163, 0.4)' }}
                />
              </Box>
              <Divider sx={{ mb: 1, borderColor: 'rgba(0, 240, 255, 0.15)' }} />

              {isPendingOutreachLoading || isAllJobsLoading ? (
                <Stack spacing={1.5} sx={{ py: 2 }}>
                  <Skeleton height={50} sx={{ bgcolor: '#161F30' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#161F30' }} />
                  <Skeleton height={50} sx={{ bgcolor: '#161F30' }} />
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
                          borderRadius: '12px',
                          px: 1.5,
                          '&:hover': { backgroundColor: 'rgba(0, 240, 255, 0.06)', transform: 'translateX(4px)' },
                          transition: 'all 0.18s ease',
                        }}
                        onClick={() => navigate(`/opportunities/${job.id}`)}
                      >
                        <ListItemIcon sx={{ minWidth: 38 }}>
                          <Box sx={{ p: 0.75, borderRadius: '10px', bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', border: '1px solid rgba(0, 255, 163, 0.4)' }}>
                            <JobsIcon fontSize="small" />
                          </Box>
                        </ListItemIcon>
                        <ListItemText
                          primary={job.title}
                          secondary={`${job.company || 'Unknown'} • ${job.location || 'Remote'}`}
                          primaryTypographyProps={{
                            variant: 'body2',
                            sx: {
                              fontWeight: 900,
                              background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 100%)',
                              WebkitBackgroundClip: 'text',
                              WebkitTextFillColor: 'transparent',
                            },
                          }}
                          secondaryTypographyProps={{ variant: 'caption', sx: { color: '#FFE600', fontWeight: 700 } }}

                        />
                        <Button size="small" variant="outlined" endIcon={<ArrowForwardIcon fontSize="small" />} sx={{ fontWeight: 900, fontSize: '0.75rem', px: 1.5, py: 0.5 }}>
                          Brief
                        </Button>
                      </ListItem>
                      {index < Math.min((pendingOutreach?.jobs && pendingOutreach.jobs.length > 0 ? pendingOutreach.jobs : allJobs).length, 6) - 1 && (
                        <Divider sx={{ borderColor: 'rgba(0, 240, 255, 0.06)' }} />
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

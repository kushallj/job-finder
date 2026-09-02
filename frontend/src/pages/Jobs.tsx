import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  InputAdornment,
  Pagination,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Grid,
} from '@mui/material';
import {
  Search as SearchIcon,
  OpenInNew as OpenInNewIcon,
  LocationOn as LocationIcon,
  Business as CompanyIcon,
  Refresh as RefreshIcon,
  ViewModule as GridViewIcon,
  ViewList as TableViewIcon,
  Clear as ClearIcon,
  Bolt as FlashIcon,
} from '@mui/icons-material';

import { jobsApi } from '../api';
import { useFilterStore } from '../stores/useFilterStore';
import { formatSource, formatRelativeTime } from '../utils/formatters';
import { GhostBadge } from '../components/ghost_hunter/GhostBadge';
import type { Job, JobsResponse, JobQueryParams } from '../api/types';

const POPULAR_TECH_STACKS = [
  'Python',
  'FastAPI',
  'Go / Golang',
  'Rust',
  'React / Next.js',
  'AWS / Cloud',
  'Kubernetes',
  'Kafka',
  'GenAI & LLMs',
  'PyTorch / AI',
  'Distributed Systems',
  'HFT / C++',
];

const CACHE_TTL_MS = 60 * 1000;

export const Jobs: React.FC = () => {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const [isCacheHit, setIsCacheHit] = useState<boolean>(false);

  const {
    jobSearch,
    setJobSearch,
    jobRegion,
    setJobRegion,
    jobExperienceLevel,
    setJobExperienceLevel,
    jobYearsOfExperience,
    setJobYearsOfExperience,
    jobDatePosted,
    setJobDatePosted,
    jobTechStack,
    toggleJobTechStack,
    jobSource,
    setJobSource,
    jobSortBy,
    setJobSortBy,
    jobSortOrder,
    jobPage,
    setJobPage,
    jobLimit,
    resetJobFilters,
  } = useFilterStore();

  const [searchInput, setSearchInput] = useState(jobSearch);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [totalJobs, setTotalJobs] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const cacheRef = useRef<Map<string, { data: JobsResponse; timestamp: number }>>(new Map());

  useEffect(() => {
    const handler = setTimeout(() => {
      if (searchInput !== jobSearch) {
        setJobSearch(searchInput);
      }
    }, 350);

    return () => clearTimeout(handler);
  }, [searchInput, jobSearch, setJobSearch]);

  useEffect(() => {
    let isCancelled = false;

    const queryParams: JobQueryParams = {
      page: jobPage,
      limit: jobLimit,
      search: jobSearch.trim() || undefined,
      region: jobRegion !== 'all' ? jobRegion : undefined,
      experience_level: jobExperienceLevel !== 'all' ? jobExperienceLevel : undefined,
      years_of_experience: jobYearsOfExperience !== null ? jobYearsOfExperience : undefined,
      date_posted: jobDatePosted !== 'all' ? jobDatePosted : undefined,
      tech_stack: jobTechStack.length > 0 ? jobTechStack.join(',') : undefined,
      source: jobSource !== 'all' ? jobSource : undefined,
      sort_by: jobSortBy,
      sort_order: jobSortOrder,
    };

    const cacheKey = JSON.stringify(queryParams);
    const cachedEntry = cacheRef.current.get(cacheKey);

    if (cachedEntry && Date.now() - cachedEntry.timestamp < CACHE_TTL_MS) {
      setJobs(cachedEntry.data.jobs);
      setTotalJobs(cachedEntry.data.pagination?.total || cachedEntry.data.jobs?.length || 0);
      setTotalPages(cachedEntry.data.pagination?.pages || 1);
      setIsCacheHit(true);
      setError(null);
      return;
    }

    setIsCacheHit(false);
    setIsLoading(true);
    setError(null);

    jobsApi
      .getAllJobs(queryParams)
      .then((data: JobsResponse) => {
        if (!isCancelled) {
          cacheRef.current.set(cacheKey, { data, timestamp: Date.now() });
          setJobs(data.jobs);
          setTotalJobs(data.pagination?.total || data.jobs?.length || 0);
          setTotalPages(data.pagination?.pages || 1);
        }
      })

      .catch((err: any) => {
        if (!isCancelled) {
          setError(err?.response?.data?.message || err.message || 'Failed to fetch job opportunities');
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [
    jobPage,
    jobLimit,
    jobSearch,
    jobRegion,
    jobExperienceLevel,
    jobYearsOfExperience,
    jobDatePosted,
    jobTechStack,
    jobSource,
    jobSortBy,
    jobSortOrder,
  ]);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (jobSearch.trim()) count++;
    if (jobRegion !== 'all') count++;
    if (jobExperienceLevel !== 'all' || jobYearsOfExperience !== null) count++;
    if (jobDatePosted !== 'all') count++;
    if (jobSource !== 'all') count++;
    if (jobTechStack.length > 0) count += jobTechStack.length;
    return count;
  }, [jobSearch, jobRegion, jobExperienceLevel, jobYearsOfExperience, jobDatePosted, jobSource, jobTechStack]);

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setJobPage(value);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleJobClick = (job: Job) => {
    navigate(`/opportunities/${job.id}`);
  };

  const handleManualRefresh = () => {
    cacheRef.current.clear();
    setIsCacheHit(false);
    setJobPage(1);
  };

  const displayedJobs = useMemo(() => jobs || [], [jobs]);

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto', color: '#F8FAFC' }}>
      {/* ── Page Header Banner ── */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, flexDirection: { xs: 'column', sm: 'row' }, gap: 2, mb: 3 }}>
        <Box>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Typography variant="h3" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.03em', textTransform: 'uppercase' }}>
              Opportunities & Alpha Liquidity
            </Typography>
            {isCacheHit && (
              <Chip
                icon={<FlashIcon sx={{ fontSize: '14px !important', color: '#00FFA3 !important' }} />}
                label="Sub-5ms Cache"
                size="small"
                sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, border: '1px solid rgba(0, 255, 163, 0.4)' }}
              />
            )}
          </Stack>
          <Typography variant="body2" sx={{ color: '#94A3B8', mt: 0.5 }}>
            Scanned <strong>{totalJobs.toLocaleString()}</strong> live engineering roles across S&P 500, Nifty 500, YC & FinTech ecosystems.
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5} alignItems="center">
          <Tooltip title="Clear in-memory cache & reload">
            <Button
              variant="outlined"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={handleManualRefresh}
              sx={{ borderRadius: '12px', fontWeight: 800 }}
            >
              Refresh
            </Button>
          </Tooltip>

          <Box sx={{ border: '1.5px solid rgba(0, 240, 255, 0.3)', borderRadius: '12px', p: 0.5, bgcolor: '#080C12' }}>
            <IconButton
              size="small"
              onClick={() => setViewMode('cards')}
              sx={{
                bgcolor: viewMode === 'cards' ? '#00F0FF' : 'transparent',
                color: viewMode === 'cards' ? '#06090E' : '#94A3B8',
                borderRadius: '8px',
              }}
            >
              <GridViewIcon fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              onClick={() => setViewMode('table')}
              sx={{
                bgcolor: viewMode === 'table' ? '#00F0FF' : 'transparent',
                color: viewMode === 'table' ? '#06090E' : '#94A3B8',
                borderRadius: '8px',
              }}
            >
              <TableViewIcon fontSize="small" />
            </IconButton>
          </Box>
        </Stack>
      </Box>

      {/* ── Multi-Facet Filter Bar ── */}
      <Card sx={{ mb: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
        <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
          <Grid container spacing={2} alignItems="center">
            {/* Search Input */}
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search by title, company, skills..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" sx={{ color: '#00F0FF' }} />
                    </InputAdornment>
                  ),
                  endAdornment: searchInput ? (
                    <InputAdornment position="end">
                      <IconButton size="small" onClick={() => { setSearchInput(''); setJobSearch(''); }} sx={{ color: '#94A3B8' }}>
                        <ClearIcon fontSize="small" />
                      </IconButton>
                    </InputAdornment>
                  ) : null,
                }}
              />
            </Grid>

            {/* Region Filter */}
            <Grid size={{ xs: 6, sm: 4, md: 2 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="region-select-label" sx={{ color: '#94A3B8' }}>Region</InputLabel>
                <Select
                  labelId="region-select-label"
                  value={jobRegion}
                  label="Region"
                  onChange={(e) => setJobRegion(e.target.value)}
                >
                  <MenuItem value="all">🌍 All Regions</MenuItem>
                  <MenuItem value="us">🇺🇸 US / S&P 500</MenuItem>
                  <MenuItem value="india">🇮🇳 India (NSE / BLR)</MenuItem>
                  <MenuItem value="remote">⚡ Global Remote</MenuItem>
                  <MenuItem value="europe">🇪🇺 Europe / APAC</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Experience / YOE Filter */}
            <Grid size={{ xs: 6, sm: 4, md: 2 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="exp-select-label" sx={{ color: '#94A3B8' }}>Experience</InputLabel>
                <Select
                  labelId="exp-select-label"
                  value={jobYearsOfExperience !== null ? String(jobYearsOfExperience) : jobExperienceLevel}
                  label="Experience"
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === 'all') {
                      setJobExperienceLevel('all');
                      setJobYearsOfExperience(null);
                    } else if (['1', '4', '7', '10'].includes(val)) {
                      setJobYearsOfExperience(parseInt(val, 10));
                    } else {
                      setJobExperienceLevel(val);
                      setJobYearsOfExperience(null);
                    }
                  }}
                >
                  <MenuItem value="all">🎯 All Experience</MenuItem>
                  <MenuItem value="1">🌱 Entry (0–2y)</MenuItem>
                  <MenuItem value="4">🚀 Mid-Level (3–5y)</MenuItem>
                  <MenuItem value="7">⚡ Senior (5–8y)</MenuItem>
                  <MenuItem value="10">👑 Staff/Principal (8+y)</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Date Posted Filter */}
            <Grid size={{ xs: 6, sm: 4, md: 1.8 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="date-select-label" sx={{ color: '#94A3B8' }}>Date Posted</InputLabel>
                <Select
                  labelId="date-select-label"
                  value={jobDatePosted}
                  label="Date Posted"
                  onChange={(e) => setJobDatePosted(e.target.value)}
                >
                  <MenuItem value="all">⏱️ Anytime</MenuItem>
                  <MenuItem value="24h">Last 24 Hours</MenuItem>
                  <MenuItem value="7d">Last 7 Days</MenuItem>
                  <MenuItem value="14d">Last 14 Days</MenuItem>
                  <MenuItem value="30d">Last 30 Days</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Source Category Filter */}
            <Grid size={{ xs: 6, sm: 4, md: 1.8 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="source-select-label" sx={{ color: '#94A3B8' }}>Source Catalog</InputLabel>
                <Select
                  labelId="source-select-label"
                  value={jobSource}
                  label="Source Catalog"
                  onChange={(e) => setJobSource(e.target.value)}
                >
                  <MenuItem value="all">🌐 All Catalogs</MenuItem>
                  <MenuItem value="sp500">🇺🇸 S&P 500 US</MenuItem>
                  <MenuItem value="nifty500">🇮🇳 NSE Nifty 500</MenuItem>
                  <MenuItem value="tier1">💎 Tier-1 Tech</MenuItem>
                  <MenuItem value="startups">🚀 YC & Accelerators</MenuItem>
                  <MenuItem value="fintech">🏦 FinTech Sponsors</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Sort Filter */}
            <Grid size={{ xs: 6, sm: 4, md: 1.4 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="sort-select-label" sx={{ color: '#94A3B8' }}>Sort Order</InputLabel>
                <Select
                  labelId="sort-select-label"
                  value={jobSortBy}
                  label="Sort Order"
                  onChange={(e) => setJobSortBy(e.target.value)}
                >
                  <MenuItem value="fetched_at">Recent Crawl</MenuItem>
                  <MenuItem value="posted_date">Date Posted</MenuItem>
                  <MenuItem value="title">Role Title</MenuItem>
                  <MenuItem value="company">Company</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          {/* Tech Stack Chip Selector */}
          <Box sx={{ mt: 2, pt: 1.5, borderTop: '1px solid rgba(0, 240, 255, 0.15)' }}>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ gap: 0.75 }}>
              <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 900, mr: 1, textTransform: 'uppercase' }}>
                Tech Stacks:
              </Typography>
              {POPULAR_TECH_STACKS.map((stack) => {
                const isSelected = jobTechStack.includes(stack);
                return (
                  <Chip
                    key={stack}
                    label={stack}
                    size="small"
                    clickable
                    onClick={() => toggleJobTechStack(stack)}
                    sx={{
                      fontWeight: 800,
                      bgcolor: isSelected ? 'rgba(0, 255, 163, 0.25)' : 'rgba(0, 240, 255, 0.06)',
                      color: isSelected ? '#00FFA3' : '#94A3B8',
                      borderColor: isSelected ? '#00FFA3' : 'rgba(0, 240, 255, 0.25)',
                      boxShadow: isSelected ? '0 0 10px rgba(0, 255, 163, 0.3)' : 'none',
                    }}
                  />
                );
              })}

              {activeFiltersCount > 0 && (
                <Button
                  size="small"
                  startIcon={<ClearIcon fontSize="small" />}
                  onClick={() => {
                    resetJobFilters();
                    setSearchInput('');
                  }}
                  sx={{ color: '#FF007A', textTransform: 'none', fontWeight: 800, ml: 'auto' }}
                >
                  Reset ({activeFiltersCount})
                </Button>
              )}
            </Stack>
          </Box>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: '14px', bgcolor: 'rgba(255, 0, 122, 0.15)', color: '#FF007A', border: '1px solid rgba(255, 0, 122, 0.4)' }}>
          {error}
        </Alert>
      )}

      {/* ── Content View ── */}
      {isLoading ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 8 }}>
          <CircularProgress size={40} sx={{ color: '#00FFA3', mb: 2 }} />
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>
            Querying SQLite with optimized HFT & Web3 taxonomy filters...
          </Typography>
        </Box>
      ) : displayedJobs.length === 0 ? (
        <Card sx={{ p: 5, textAlign: 'center', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)' }}>
          <Typography variant="h5" fontWeight={900} sx={{ mb: 1, color: '#F8FAFC' }}>
            No opportunities matched your filters
          </Typography>
          <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2 }}>
            Try resetting your filters or adjusting your tech stack keywords.
          </Typography>
          <Button
            variant="contained"
            size="small"
            onClick={() => {
              resetJobFilters();
              setSearchInput('');
            }}
          >
            Clear All Filters
          </Button>
        </Card>
      ) : viewMode === 'cards' ? (
        /* Grid View */
        <Grid container spacing={2.5}>
          {displayedJobs.map((job) => (
            <Grid key={job.id} size={{ xs: 12, md: 6, lg: 4 }}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  bgcolor: '#0D131F',
                  border: '1.5px solid rgba(0, 240, 255, 0.18)',
                  borderRadius: '20px',
                  boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)',
                  transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    borderColor: '#00F0FF',
                    boxShadow: '0 0 30px rgba(0, 240, 255, 0.3), 0 0 60px rgba(0, 255, 163, 0.15)',
                  },
                }}
              >
                <CardContent sx={{ p: 2.5, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                    <Box sx={{ flexGrow: 1, pr: 1 }}>
                      {/* Vibrant Chromatic Gradient Job Title */}
                      <Typography
                        variant="h6"
                        sx={{
                          fontWeight: 900,
                          background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 60%, #FFE600 100%)',
                          WebkitBackgroundClip: 'text',
                          WebkitTextFillColor: 'transparent',
                          cursor: 'pointer',
                          lineHeight: 1.3,
                          letterSpacing: '-0.02em',
                          '&:hover': { filter: 'brightness(1.2)' },
                        }}
                        onClick={() => handleJobClick(job)}
                      >
                        {job.title}
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.75 }}>
                        <CompanyIcon fontSize="inherit" sx={{ color: '#00F0FF' }} />
                        <Typography variant="body2" sx={{ fontWeight: 800, color: '#FFE600' }}>
                          {job.company || 'Unknown Company'}
                        </Typography>
                      </Stack>
                    </Box>
                    <GhostBadge jobId={job.id} />
                  </Box>

                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5, color: '#94A3B8' }}>
                    <LocationIcon fontSize="inherit" sx={{ color: '#00F0FF' }} />
                    <Typography variant="caption" sx={{ fontWeight: 600, color: '#E2E8F0' }}>
                      {job.location || 'Remote'}
                    </Typography>
                    {job.has_remote && (
                      <Chip label="REMOTE" size="small" sx={{ height: 20, fontSize: '0.65rem', bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', border: '1px solid rgba(0, 255, 163, 0.4)' }} />
                    )}
                  </Stack>

                  {/* Level & Salary */}
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2, flexWrap: 'wrap', gap: 0.5 }}>
                    {job.experience_level && (
                      <Chip
                        label={job.experience_level}
                        size="small"
                        sx={{ height: 22, fontSize: '0.7rem', bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800 }}
                      />
                    )}
                    {job.salary_min && (
                      <Chip
                        label={`$${job.salary_min.toLocaleString()} ${job.salary_max ? `- $${job.salary_max.toLocaleString()}` : ''}`}
                        size="small"
                        sx={{ height: 22, fontSize: '0.7rem', bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 800, border: '1px solid rgba(255, 230, 0, 0.4)' }}
                      />
                    )}
                    <Chip
                      label={formatSource(job.source)}
                      size="small"
                      sx={{ height: 22, fontSize: '0.65rem', bgcolor: 'rgba(121, 40, 202, 0.15)', color: '#A855F7', border: '1px solid rgba(121, 40, 202, 0.3)' }}
                    />
                  </Stack>

                  <Box sx={{ mt: 'auto', pt: 1.5, borderTop: '1px solid rgba(0, 240, 255, 0.15)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>
                      {formatRelativeTime(job.posted_date || job.fetched_at)}
                    </Typography>
                    <Stack direction="row" spacing={1}>
                      <Button size="small" variant="contained" onClick={() => handleJobClick(job)} sx={{ fontWeight: 900 }}>
                        Evaluate
                      </Button>
                      {job.url && (
                        <IconButton size="small" href={job.url} target="_blank" rel="noopener noreferrer" sx={{ color: '#00F0FF', border: '1px solid rgba(0, 240, 255, 0.3)', borderRadius: '8px' }}>
                          <OpenInNewIcon fontSize="small" />
                        </IconButton>
                      )}
                    </Stack>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        /* Table View */
        <TableContainer component={Paper} sx={{ borderRadius: '20px', border: '1.5px solid rgba(0, 240, 255, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
          <Table size="small">
            <TableHead sx={{ bgcolor: '#080C12' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Role & Company</TableCell>
                <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Location</TableCell>
                <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Experience Level</TableCell>
                <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Source Catalog</TableCell>
                <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Posted</TableCell>
                <TableCell align="right" sx={{ fontWeight: 900, color: '#00F0FF' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {displayedJobs.map((job) => (
                <TableRow key={job.id} hover sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'rgba(0, 240, 255, 0.05)' } }} onClick={() => handleJobClick(job)}>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                      {job.title}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#FFE600', fontWeight: 700 }}>
                      {job.company || 'Unknown Company'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ color: '#E2E8F0' }}>{job.location || 'Remote'}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={job.experience_level || 'Mid-Level'} size="small" sx={{ fontSize: '0.7rem', bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF' }} />
                  </TableCell>
                  <TableCell>
                    <Chip label={formatSource(job.source)} size="small" sx={{ fontSize: '0.65rem', bgcolor: 'rgba(121, 40, 202, 0.15)', color: '#A855F7' }} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                      {formatRelativeTime(job.posted_date || job.fetched_at)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button size="small" variant="text" onClick={() => handleJobClick(job)} sx={{ color: '#00FFA3', fontWeight: 900 }}>
                        Brief
                      </Button>
                      {job.url && (
                        <IconButton size="small" href={job.url} target="_blank" rel="noopener noreferrer" sx={{ color: '#00F0FF' }}>
                          <OpenInNewIcon fontSize="small" />
                        </IconButton>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <Pagination
            count={totalPages}
            page={jobPage}
            onChange={handlePageChange}
            color="primary"
            showFirstButton
            showLastButton
            sx={{
              '& .MuiPaginationItem-root': {
                fontWeight: 800,
                borderRadius: '10px',
                color: '#F8FAFC',
                border: '1px solid rgba(0, 240, 255, 0.2)',
                '&.Mui-selected': {
                  bgcolor: '#00F0FF',
                  color: '#06090E',
                  fontWeight: 900,
                },
              },
            }}
          />
        </Box>
      )}
    </Box>
  );
};

export default Jobs;

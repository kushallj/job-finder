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
  alpha,
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
  'Java',
  'React / Next.js',
  'AWS / Cloud',
  'Kubernetes / Docker',
  'Kafka / Event-Driven',
  'GenAI & LLMs',
  'AI / Machine Learning',
  'Mobile (iOS / Android)',
  'Security / Infosec',
  'DevOps / SRE',
];

const CACHE_TTL_MS = 60 * 1000; // 60 seconds TTL

export const Jobs: React.FC = () => {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const [isCacheHit, setIsCacheHit] = useState<boolean>(false);

  // ── Zustand Store for Job Filters ──────────────────────────────────────────
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

  // Local state for immediate text input binding
  const [searchInput, setSearchInput] = useState(jobSearch);

  // Data fetching state
  const [jobs, setJobs] = useState<Job[]>([]);
  const [totalJobs, setTotalJobs] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // ── In-Memory Cache via useRef ─────────────────────────────────────────────
  const cacheRef = useRef<Map<string, { data: JobsResponse; timestamp: number }>>(new Map());

  // ── Side Effect 1: Debounce Search Input into Zustand Store ────────────────
  useEffect(() => {
    const handler = setTimeout(() => {
      if (searchInput !== jobSearch) {
        setJobSearch(searchInput);
      }
    }, 350);

    return () => clearTimeout(handler);
  }, [searchInput, jobSearch, setJobSearch]);

  // ── Side Effect 2: Fetch Data with Caching when Filters or Page Change ─────
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
    const now = Date.now();
    const cached = cacheRef.current.get(cacheKey);

    // Check cache validity
    if (cached && now - cached.timestamp < CACHE_TTL_MS) {
      setJobs(cached.data.jobs);
      setTotalJobs(cached.data.pagination.total);
      setTotalPages(cached.data.pagination.pages);
      setIsCacheHit(true);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setIsCacheHit(false);
    setError(null);

    jobsApi
      .getAllJobs(queryParams)
      .then((res) => {
        if (isCancelled) return;
        setJobs(res.jobs);
        setTotalJobs(res.pagination.total);
        setTotalPages(res.pagination.pages);
        cacheRef.current.set(cacheKey, { data: res, timestamp: Date.now() });
      })
      .catch((err: any) => {
        if (isCancelled) return;
        setError(err.message || 'Failed to fetch jobs.');
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

  // ── Side Effect 3: Scroll to Top on Page Change ────────────────────────────
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [jobPage]);

  // Handlers
  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setJobPage(value);
  };

  const handleManualRefresh = () => {
    cacheRef.current.clear();
    setJobPage(1);
    setSearchInput(jobSearch);
  };

  const handleJobClick = (job: Job) => {
    navigate(`/opportunities/${job.id}`);
  };

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (jobSearch.trim()) count++;
    if (jobRegion !== 'all') count++;
    if (jobExperienceLevel !== 'all' || jobYearsOfExperience !== null) count++;
    if (jobDatePosted !== 'all') count++;
    if (jobTechStack.length > 0) count += jobTechStack.length;
    if (jobSource !== 'all') count++;
    return count;
  }, [jobSearch, jobRegion, jobExperienceLevel, jobYearsOfExperience, jobDatePosted, jobTechStack, jobSource]);

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto', pb: 6 }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em' }}>
              Opportunities & Job Pipeline
            </Typography>
            {isCacheHit && (
              <Chip
                icon={<FlashIcon sx={{ fontSize: '14px !important' }} />}
                label="Instant Cache"
                size="small"
                sx={{ bgcolor: alpha('#10B981', 0.1), color: '#059669', fontWeight: 700 }}
              />
            )}
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Explore <strong>{totalJobs.toLocaleString()}</strong> live engineering roles across 287+ Tier-1 companies, Indian startups & FinTech sponsors.
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5} alignItems="center">
          <Tooltip title="Clear in-memory cache & reload">
            <Button
              variant="outlined"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={handleManualRefresh}
              sx={{ borderRadius: '10px', textTransform: 'none', fontWeight: 600 }}
            >
              Refresh
            </Button>
          </Tooltip>

          <Box sx={{ border: '1px solid #E2E8F0', borderRadius: '10px', p: 0.5, bgcolor: '#FFFFFF' }}>
            <IconButton
              size="small"
              onClick={() => setViewMode('cards')}
              sx={{
                bgcolor: viewMode === 'cards' ? '#4F46E5' : 'transparent',
                color: viewMode === 'cards' ? '#FFFFFF' : '#64748B',
                '&:hover': { bgcolor: viewMode === 'cards' ? '#4338CA' : alpha('#4F46E5', 0.08) },
                borderRadius: '8px',
              }}
            >
              <GridViewIcon fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              onClick={() => setViewMode('table')}
              sx={{
                bgcolor: viewMode === 'table' ? '#4F46E5' : 'transparent',
                color: viewMode === 'table' ? '#FFFFFF' : '#64748B',
                '&:hover': { bgcolor: viewMode === 'table' ? '#4338CA' : alpha('#4F46E5', 0.08) },
                borderRadius: '8px',
              }}
            >
              <TableViewIcon fontSize="small" />
            </IconButton>
          </Box>
        </Stack>
      </Box>

      {/* ── Multi-Facet Filter Bar ─────────────────────────────────────────── */}
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0', borderRadius: '16px', boxShadow: '0 4px 12px -2px rgba(0,0,0,0.03)' }}>
        <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
          <Grid container spacing={2} alignItems="center">
            {/* Search Input */}
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search title, tech stack, company..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" sx={{ color: '#94A3B8' }} />
                    </InputAdornment>
                  ),
                  endAdornment: searchInput ? (
                    <InputAdornment position="end">
                      <IconButton size="small" onClick={() => { setSearchInput(''); setJobSearch(''); }}>
                        <ClearIcon fontSize="small" />
                      </IconButton>
                    </InputAdornment>
                  ) : null,
                }}
                sx={{ bgcolor: '#F8FAFC', borderRadius: '10px' }}
              />
            </Grid>

            {/* Region Filter */}
            <Grid size={{ xs: 6, sm: 4, md: 2 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="region-select-label">Region</InputLabel>
                <Select
                  labelId="region-select-label"
                  value={jobRegion}
                  label="Region"
                  onChange={(e) => setJobRegion(e.target.value)}
                  sx={{ bgcolor: '#F8FAFC', borderRadius: '10px' }}
                >
                  <MenuItem value="all">🌍 All Regions</MenuItem>
                  <MenuItem value="india">🇮🇳 India (BLR, MUM)</MenuItem>
                  <MenuItem value="remote">⚡ Global Remote</MenuItem>
                  <MenuItem value="us">🇺🇸 US / Americas</MenuItem>
                  <MenuItem value="europe">🇪🇺 Europe / APAC</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Experience / YOE Filter */}
            <Grid size={{ xs: 6, sm: 4, md: 2 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="exp-select-label">Experience (YOE)</InputLabel>
                <Select
                  labelId="exp-select-label"
                  value={jobYearsOfExperience !== null ? String(jobYearsOfExperience) : jobExperienceLevel}
                  label="Experience (YOE)"
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
                  sx={{ bgcolor: '#F8FAFC', borderRadius: '10px' }}
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
                <InputLabel id="date-select-label">Date Posted</InputLabel>
                <Select
                  labelId="date-select-label"
                  value={jobDatePosted}
                  label="Date Posted"
                  onChange={(e) => setJobDatePosted(e.target.value)}
                  sx={{ bgcolor: '#F8FAFC', borderRadius: '10px' }}
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
                <InputLabel id="source-select-label">Source</InputLabel>
                <Select
                  labelId="source-select-label"
                  value={jobSource}
                  label="Source"
                  onChange={(e) => setJobSource(e.target.value)}
                  sx={{ bgcolor: '#F8FAFC', borderRadius: '10px' }}
                >
                  <MenuItem value="all">🌐 All Sources</MenuItem>
                  <MenuItem value="tier1">💎 Tier-1 Giants</MenuItem>
                  <MenuItem value="startups">📱 Indian Startups</MenuItem>
                  <MenuItem value="fintech">🏦 FinTech Sponsors</MenuItem>
                  <MenuItem value="usajobs">🇺🇸 USAJOBS Federal</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Sort Filter */}
            <Grid size={{ xs: 6, sm: 4, md: 1.4 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="sort-select-label">Sort</InputLabel>
                <Select
                  labelId="sort-select-label"
                  value={jobSortBy}
                  label="Sort"
                  onChange={(e) => setJobSortBy(e.target.value)}
                  sx={{ bgcolor: '#F8FAFC', borderRadius: '10px' }}
                >
                  <MenuItem value="fetched_at">Recent Crawl</MenuItem>
                  <MenuItem value="posted_date">Date Posted</MenuItem>
                  <MenuItem value="title">Job Title</MenuItem>
                  <MenuItem value="company">Company</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>


          {/* Tech Stack Chip Selector */}
          <Box sx={{ mt: 2, pt: 1.5, borderTop: '1px solid #F1F5F9' }}>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ gap: 0.75 }}>
              <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, mr: 1, textTransform: 'uppercase' }}>
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
                      fontWeight: isSelected ? 700 : 500,
                      bgcolor: isSelected ? '#4F46E5' : '#F1F5F9',
                      color: isSelected ? '#FFFFFF' : '#475569',
                      '&:hover': {
                        bgcolor: isSelected ? '#4338CA' : '#E2E8F0',
                      },
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
                  sx={{ color: '#EF4444', textTransform: 'none', fontWeight: 600, ml: 'auto' }}
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
        <Alert severity="error" sx={{ mb: 3, borderRadius: '12px' }}>
          {error}
        </Alert>
      )}

      {/* ── Content View ───────────────────────────────────────────────────── */}
      {isLoading ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 8 }}>
          <CircularProgress size={40} sx={{ color: '#4F46E5', mb: 2 }} />
          <Typography variant="body2" color="text.secondary">
            Querying SQLite with optimized ORM filters...
          </Typography>
        </Box>
      ) : jobs.length === 0 ? (
        <Card sx={{ p: 5, textAlign: 'center', borderRadius: '16px' }}>
          <Typography variant="h6" fontWeight={700} color="#0F172A" sx={{ mb: 1 }}>
            No opportunities matched your filters
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Try resetting your filters or adjusting your tech stack keywords.
          </Typography>
          <Button
            variant="contained"
            size="small"
            onClick={() => {
              resetJobFilters();
              setSearchInput('');
            }}
            sx={{ bgcolor: '#4F46E5' }}
          >
            Clear All Filters
          </Button>
        </Card>
      ) : viewMode === 'cards' ? (
        /* Grid View */
        <Grid container spacing={2.5}>
          {jobs.map((job) => (
            <Grid key={job.id} size={{ xs: 12, md: 6, lg: 4 }}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  borderRadius: '14px',
                  border: '1px solid #E2E8F0',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    transform: 'translateY(-3px)',
                    boxShadow: '0 12px 24px -6px rgba(0,0,0,0.08)',
                    borderColor: '#4F46E5',
                  },
                }}
              >
                <CardContent sx={{ p: 2.5, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                    <Box sx={{ flexGrow: 1, pr: 1 }}>
                      <Typography
                        variant="subtitle1"
                        sx={{
                          fontWeight: 700,
                          color: '#0F172A',
                          cursor: 'pointer',
                          '&:hover': { color: '#4F46E5' },
                          lineHeight: 1.3,
                        }}
                        onClick={() => handleJobClick(job)}
                      >
                        {job.title}
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}>
                        <CompanyIcon fontSize="inherit" sx={{ color: '#64748B' }} />
                        <Typography variant="body2" sx={{ fontWeight: 600, color: '#475569' }}>
                          {job.company || 'Unknown Company'}
                        </Typography>
                      </Stack>
                    </Box>
                    <GhostBadge jobId={job.id} />
                  </Box>

                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5, color: '#64748B' }}>
                    <LocationIcon fontSize="inherit" />
                    <Typography variant="caption" sx={{ fontWeight: 500 }}>
                      {job.location || 'Remote'}
                    </Typography>
                    {job.has_remote && (
                      <Chip label="Remote" size="small" sx={{ height: 20, fontSize: '0.65rem', bgcolor: alpha('#10B981', 0.1), color: '#059669' }} />
                    )}
                  </Stack>

                  {/* Level & Salary */}
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2, flexWrap: 'wrap', gap: 0.5 }}>
                    {job.experience_level && (
                      <Chip
                        label={job.experience_level}
                        size="small"
                        sx={{ height: 22, fontSize: '0.7rem', bgcolor: alpha('#4F46E5', 0.08), color: '#4F46E5', fontWeight: 600 }}
                      />
                    )}
                    {job.salary_min && (
                      <Chip
                        label={`${job.salary_currency || '₹'} ${job.salary_min.toLocaleString()} ${job.salary_max ? `- ${job.salary_max.toLocaleString()}` : ''}`}
                        size="small"
                        sx={{ height: 22, fontSize: '0.7rem', bgcolor: alpha('#F59E0B', 0.1), color: '#D97706', fontWeight: 700 }}
                      />
                    )}
                    <Chip
                      label={formatSource(job.source)}
                      size="small"
                      sx={{ height: 22, fontSize: '0.65rem', bgcolor: '#F1F5F9', color: '#64748B' }}
                    />
                  </Stack>

                  <Box sx={{ mt: 'auto', pt: 1.5, borderTop: '1px solid #F1F5F9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="caption" color="text.secondary">
                      {formatRelativeTime(job.posted_date || job.fetched_at)}
                    </Typography>
                    <Stack direction="row" spacing={1}>
                      <Button size="small" variant="contained" onClick={() => handleJobClick(job)} sx={{ bgcolor: '#4F46E5', textTransform: 'none', fontWeight: 600 }}>
                        Evaluate
                      </Button>
                      {job.url && (
                        <IconButton size="small" href={job.url} target="_blank" rel="noopener noreferrer" sx={{ color: '#64748B' }}>
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
        <TableContainer component={Paper} sx={{ borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: 'none' }}>
          <Table size="small">
            <TableHead sx={{ bgcolor: '#F8FAFC' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Role & Company</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Location</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Experience Level</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Source</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Posted</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.id} hover sx={{ cursor: 'pointer' }} onClick={() => handleJobClick(job)}>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 700, color: '#0F172A' }}>
                      {job.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {job.company || 'Unknown Company'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{job.location || 'Remote'}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={job.experience_level || 'Mid-Level'} size="small" sx={{ fontSize: '0.7rem' }} />
                  </TableCell>
                  <TableCell>
                    <Chip label={formatSource(job.source)} size="small" sx={{ fontSize: '0.65rem' }} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {formatRelativeTime(job.posted_date || job.fetched_at)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button size="small" variant="text" onClick={() => handleJobClick(job)}>
                        Brief
                      </Button>
                      {job.url && (
                        <IconButton size="small" href={job.url} target="_blank" rel="noopener noreferrer">
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
                fontWeight: 600,
                borderRadius: '8px',
              },
            }}
          />
        </Box>
      )}
    </Box>
  );
};

export default Jobs;

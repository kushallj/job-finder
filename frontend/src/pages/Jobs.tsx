import React, { useState } from 'react';
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
  Tabs,
  Tab,
  alpha,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  OpenInNew as OpenInNewIcon,
  LocationOn as LocationIcon,
  Business as CompanyIcon,
  Refresh as RefreshIcon,
  ViewModule as GridViewIcon,
  ViewList as TableViewIcon,
} from '@mui/icons-material';
import { useJobs } from '../hooks/useJobs';
import { formatSource, formatRelativeTime } from '../utils/formatters';
import { GhostBadge } from '../components/ghost_hunter/GhostBadge';
import type { Job } from '../api/types';

export const Jobs: React.FC = () => {
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const jobsPerPage = 30;
  const navigate = useNavigate();

  const {
    allJobs,
    allJobsTotal,
    allJobsPages,
    isAllJobsLoading,
    allJobsError,
    refetchAllJobs,
  } = useJobs(page, jobsPerPage);

  const handleJobClick = (job: Job) => {
    navigate(`/opportunities/${job.id}`);
  };

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const filteredJobs = allJobs.filter((job) => {
    const matchesSearch =
      job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (job.company && job.company.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (job.location && job.location.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;

    if (stageFilter === 'all') return true;
    if (stageFilter === 'ready') return job.application_status === 'ready';
    if (stageFilter === 'applied') return job.application_status === 'applied';
    if (stageFilter === 'interview') return job.application_status === 'interview';
    if (stageFilter === 'saved') return job.application_status === 'saved' || !job.application_status;
    return true;
  });

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>
            Opportunities & Job Pipeline
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage, evaluate, and track all <strong>{allJobsTotal}</strong> indexed positions across career stages.
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5} alignItems="center">
          <Box sx={{ border: '1px solid #E2E8F0', borderRadius: '10px', p: 0.5, bgcolor: '#FFFFFF' }}>
            <IconButton
              size="small"
              onClick={() => setViewMode('cards')}
              color={viewMode === 'cards' ? 'primary' : 'default'}
              sx={{ bgcolor: viewMode === 'cards' ? alpha('#4F46E5', 0.1) : 'transparent', borderRadius: '8px' }}
            >
              <GridViewIcon fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              onClick={() => setViewMode('table')}
              color={viewMode === 'table' ? 'primary' : 'default'}
              sx={{ bgcolor: viewMode === 'table' ? alpha('#4F46E5', 0.1) : 'transparent', borderRadius: '8px' }}
            >
              <TableViewIcon fontSize="small" />
            </IconButton>
          </Box>

          <Button
            variant="outlined"
            onClick={() => refetchAllJobs()}
            disabled={isAllJobsLoading}
            startIcon={isAllJobsLoading ? <CircularProgress size={16} /> : <RefreshIcon />}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* Stage Filter Tabs & Search Card */}
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} justifyContent="space-between" alignItems="center">
            <Tabs
              value={stageFilter}
              onChange={(_, val) => setStageFilter(val)}
              variant="scrollable"
              scrollButtons="auto"
              sx={{
                minHeight: 40,
                '& .MuiTab-root': {
                  minHeight: 40,
                  py: 0.5,
                  px: 2,
                  fontWeight: 700,
                  fontSize: '0.825rem',
                  borderRadius: '8px',
                },
              }}
            >
              <Tab label="All Roles" value="all" />
              <Tab label="✨ Ready to Apply" value="ready" />
              <Tab label="📤 Applied" value="applied" />
              <Tab label="🎯 Interviewing" value="interview" />
              <Tab label="📌 Saved" value="saved" />
            </Tabs>

            <TextField
              placeholder="Search by title, company, skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              size="small"
              sx={{ width: { xs: '100%', md: 320 } }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ color: '#94A3B8' }} fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
          </Stack>
        </CardContent>
      </Card>

      {allJobsError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Error loading jobs: {String(allJobsError)}
        </Alert>
      )}

      {/* Jobs Content */}
      {isAllJobsLoading ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Loading opportunity catalog...
          </Typography>
        </Box>
      ) : filteredJobs.length === 0 ? (
        <Card sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" fontWeight={700} color="#0F172A" gutterBottom>
            No opportunities match your filter
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Try resetting your search query or switching tabs.
          </Typography>
          <Button variant="outlined" size="small" onClick={() => { setSearchQuery(''); setStageFilter('all'); }}>
            Reset Filters
          </Button>
        </Card>
      ) : viewMode === 'table' ? (
        /* CRM Table View */
        <TableContainer component={Paper} sx={{ borderRadius: '16px', border: '1px solid #E2E8F0', mb: 3 }}>
          <Table size="medium">
            <TableHead sx={{ bgcolor: '#F8FAFC' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 700, color: '#475569' }}>Role & Title</TableCell>
                <TableCell sx={{ fontWeight: 700, color: '#475569' }}>Company</TableCell>
                <TableCell sx={{ fontWeight: 700, color: '#475569' }}>Location</TableCell>
                <TableCell sx={{ fontWeight: 700, color: '#475569' }}>Lifecycle Stage</TableCell>
                <TableCell sx={{ fontWeight: 700, color: '#475569' }}>Source</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, color: '#475569' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredJobs.map((job) => (
                <TableRow
                  key={job.id}
                  hover
                  sx={{ cursor: 'pointer', '&:last-child td, &:last-child th': { border: 0 } }}
                  onClick={() => handleJobClick(job)}
                >
                  <TableCell>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#0F172A' }}>
                      {job.title}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>
                      Posted: {formatRelativeTime(job.posted_date || job.fetched_at)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600, color: '#334155' }}>
                      {job.company || 'Unknown Company'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={job.location || 'Remote'} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={job.application_status || 'saved'}
                      size="small"
                      color={
                        job.application_status === 'ready'
                          ? 'primary'
                          : job.application_status === 'applied'
                          ? 'success'
                          : job.application_status === 'interview'
                          ? 'warning'
                          : 'default'
                      }
                      sx={{ fontWeight: 700, textTransform: 'capitalize' }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>
                      {formatSource(job.source)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      {job.url && (
                        <Tooltip title="Open Original Posting">
                          <IconButton size="small" onClick={() => window.open(job.url ?? undefined, '_blank')}>
                            <OpenInNewIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Button
                        size="small"
                        variant="contained"
                        onClick={() => navigate(`/opportunities/${job.id}`)}
                        sx={{ fontWeight: 700 }}
                      >
                        Brief
                      </Button>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        /* Rich Card View */
        <Stack spacing={2} sx={{ mb: 3 }}>
          {filteredJobs.map((job: Job) => (
            <Card
              key={job.id}
              sx={{
                cursor: 'pointer',
                p: 1,
                border: '1px solid #E2E8F0',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  borderColor: '#CBD5E1',
                  transform: 'translateY(-2px)',
                  boxShadow: '0 8px 24px -4px rgba(0, 0, 0, 0.06)',
                },
              }}
              onClick={() => handleJobClick(job)}
            >
              <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5, gap: 2 }}>
                  <Box sx={{ flex: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.5 }}>
                      <Typography variant="h6" sx={{ fontWeight: 800, color: '#0F172A' }}>
                        {job.title}
                      </Typography>
                      {job.application_status && (
                        <Chip
                          label={job.application_status}
                          size="small"
                          color={
                            job.application_status === 'ready'
                              ? 'primary'
                              : job.application_status === 'applied'
                              ? 'success'
                              : 'default'
                          }
                          sx={{ textTransform: 'capitalize', fontWeight: 700 }}
                        />
                      )}
                    </Stack>

                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
                      <Chip
                        icon={<CompanyIcon fontSize="small" />}
                        label={job.company || 'Unknown Company'}
                        size="small"
                        sx={{ bgcolor: '#F1F5F9', color: '#334155', fontWeight: 600 }}
                      />
                      <Chip
                        icon={<LocationIcon fontSize="small" />}
                        label={job.location || 'Remote'}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={formatSource(job.source)}
                        size="small"
                        variant="outlined"
                        sx={{ color: '#64748B' }}
                      />
                      <GhostBadge jobId={job.id} />
                    </Stack>
                  </Box>

                  <Stack direction="row" spacing={1} onClick={(e) => e.stopPropagation()}>
                    {job.url && (
                      <IconButton
                        size="small"
                        onClick={() => window.open(job.url ?? undefined, '_blank')}
                        title="Open external posting"
                        sx={{ border: '1px solid #E2E8F0', borderRadius: '8px' }}
                      >
                        <OpenInNewIcon fontSize="small" />
                      </IconButton>
                    )}
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => navigate(`/opportunities/${job.id}`)}
                      sx={{ fontWeight: 700 }}
                    >
                      View Brief
                    </Button>
                  </Stack>
                </Box>

                {job.description && (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      mb: 1.5,
                      lineHeight: 1.5,
                    }}
                  >
                    {job.description}
                  </Typography>
                )}

                <Divider sx={{ borderColor: '#F1F5F9', my: 1.5 }} />

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="caption" sx={{ color: '#64748B' }}>
                    📅 Posted: <strong>{formatRelativeTime(job.posted_date || null)}</strong> · Fetched: {formatRelativeTime(job.fetched_at)}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#4F46E5', fontWeight: 700 }}>
                    Click card to open AI Decision Brief →
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Stack>
      )}

      {/* Pagination */}
      {allJobsPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4, mb: 4 }}>
          <Pagination
            count={allJobsPages}
            page={page}
            onChange={handlePageChange}
            color="primary"
            size="large"
            showFirstButton
            showLastButton
            sx={{
              '& .MuiPaginationItem-root': {
                fontWeight: 700,
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

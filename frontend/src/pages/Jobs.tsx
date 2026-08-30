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
} from '@mui/material';
import {
  Search as SearchIcon,
  OpenInNew as OpenInNewIcon,
  Send as SendIcon,
  LocationOn as LocationIcon,
  Business as CompanyIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useJobs } from '../hooks/useJobs';
import { formatSource, formatRelativeTime } from '../utils/formatters';
import type { Job } from '../api/types';

const Jobs: React.FC = () => {
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const jobsPerPage = 50;
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

  const filteredJobs = allJobs.filter((job) =>
    job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (job.company && job.company.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <Box>
      {/* Header Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Jobs
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Browse all {allJobsTotal} jobs • Page {page} of {allJobsPages}
        </Typography>
      </Box>

      {/* Search & Filter Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField
              placeholder="Search jobs by title or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              size="small"
              sx={{ flex: 1, minWidth: 200 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
            />

            <Button
              variant="outlined"
              onClick={() => refetchAllJobs()}
              disabled={isAllJobsLoading}
              startIcon={isAllJobsLoading ? <CircularProgress size={20} /> : <RefreshIcon />}
            >
              Refresh
            </Button>
          </Box>
        </CardContent>
      </Card>

      {allJobsError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Error loading jobs: {String(allJobsError)}
        </Alert>
      )}

      {/* Jobs List */}
      <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
        {filteredJobs.length} Jobs on This Page
      </Typography>

      {isAllJobsLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : filteredJobs.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              {allJobs.length === 0 ? 'No jobs found' : 'No jobs match your search'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {allJobs.length === 0 
                ? 'Try refreshing or checking back later'
                : 'Try adjusting your search query'}
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {filteredJobs.map((job: Job) => (
            <Card
              key={job.id}
              sx={{
                cursor: 'pointer',
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: 3,
                },
              }}
              onClick={() => handleJobClick(job)}
            >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" fontWeight={600} gutterBottom>
                      {job.title}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
                      <Chip
                        icon={<CompanyIcon />}
                        label={job.company || 'Unknown Company'}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        icon={<LocationIcon />}
                        label={job.location || 'Remote'}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={formatSource(job.source)}
                        size="small"
                        color="default"
                      />
                      {job.application_status && (
                        <Chip
                          label={job.application_status}
                          size="small"
                          color="primary"
                        />
                      )}
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {job.url && (
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(job.url ?? undefined, '_blank');
                        }}
                        title="Open job posting"
                      >
                        <OpenInNewIcon fontSize="small" />
                      </IconButton>
                    )}
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/opportunities/${job.id}`);
                      }}
                      title="Open opportunity brief"
                    >
                      <SendIcon fontSize="small" />
                    </IconButton>
                  </Box>
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
                    }}
                  >
                    {job.description}
                  </Typography>
                )}

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="caption" color="text.secondary">
                    Posted: {formatRelativeTime(job.posted_date || null)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Fetched: {formatRelativeTime(job.fetched_at)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Pagination */}
      {allJobsPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4, mb: 2 }}>
          <Pagination
            count={allJobsPages}
            page={page}
            onChange={handlePageChange}
            color="primary"
            size="large"
            showFirstButton
            showLastButton
          />
        </Box>
      )}
    </Box>
  );
};

export default Jobs;

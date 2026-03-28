import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Chip,
  IconButton,
  Drawer,
  Divider,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Alert,
  InputAdornment,
  Pagination,
} from '@mui/material';
import {
  Search as SearchIcon,
  OpenInNew as OpenInNewIcon,
  Send as SendIcon,
  Close as CloseIcon,
  LocationOn as LocationIcon,
  Business as CompanyIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useJobs } from '../hooks/useJobs';
import { useOutreach } from '../hooks/useOutreach';
import { formatSource, formatRelativeTime } from '../utils/formatters';
import type { PendingOutreachJob } from '../api/types';

const Jobs: React.FC = () => {
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [jobsPerPage] = useState(50);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<PendingOutreachJob | null>(null);

  const {
    allJobs,
    allJobsTotal,
    allJobsPages,
    isAllJobsLoading,
    allJobsError,
    refetchAllJobs,
  } = useJobs(page, jobsPerPage);

  const { isSendingOutreach } = useOutreach();

  const handleJobClick = (job: PendingOutreachJob) => {
    setSelectedJob(job);
    setDrawerOpen(true);
  };

  const handleCloseDrawer = () => {
    setDrawerOpen(false);
    setSelectedJob(null);
  };

  const handleSendOutreach = () => {
    if (selectedJob) {
      console.log('Send outreach for job:', selectedJob.id);
    }
  };

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const filteredJobs = allJobs.filter((job) =>
    job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    job.company.toLowerCase().includes(searchQuery.toLowerCase())
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
          {filteredJobs.map((job: PendingOutreachJob) => (
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
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" fontWeight={600}>
                      {job.title}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 1, flexWrap: 'wrap' }}>
                      <Chip
                        icon={<CompanyIcon />}
                        label={job.company}
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
                        color="primary"
                        variant="outlined"
                      />
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {job.url && (
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(job.url, '_blank');
                        }}
                      >
                        <OpenInNewIcon fontSize="small" />
                      </IconButton>
                    )}
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleJobClick(job);
                      }}
                    >
                      <SendIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Pagination */}
      {!isAllJobsLoading && allJobsPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4, mb: 4 }}>
          <Pagination
            count={allJobsPages}
            page={page}
            onChange={handlePageChange}
            color="primary"
            size="large"
          />
        </Box>
      )}

      {/* Job Details Drawer */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={handleCloseDrawer}
        PaperProps={{ sx: { width: { xs: '100%', sm: 450 } } }}
      >
        {selectedJob && (
          <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="h6" fontWeight={600}>
                Job Details
              </Typography>
              <IconButton onClick={handleCloseDrawer}>
                <CloseIcon />
              </IconButton>
            </Box>

            <Divider sx={{ mb: 3 }} />

            <Typography variant="h6" fontWeight={600} gutterBottom>
              {selectedJob.title}
            </Typography>

            <Box sx={{ display: 'flex', gap: 1, mb: 3, flexWrap: 'wrap' }}>
              <Chip icon={<CompanyIcon />} label={selectedJob.company} size="small" />
              <Chip icon={<LocationIcon />} label={selectedJob.location || 'Remote'} size="small" />
            </Box>

            <List dense>
              <ListItem>
                <ListItemText
                  primary="Source"
                  secondary={formatSource(selectedJob.source)}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Posted"
                  secondary={formatRelativeTime(selectedJob.posted_date || null)}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Fetched"
                  secondary={formatRelativeTime(selectedJob.fetched_at)}
                />
              </ListItem>
            </List>

            {selectedJob.url && (
              <Box sx={{ mt: 3 }}>
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<OpenInNewIcon />}
                  onClick={() => window.open(selectedJob.url, '_blank')}
                  sx={{ mb: 2 }}
                >
                  View Original Listing
                </Button>
              </Box>
            )}

            <Button
              variant="outlined"
              color="primary"
              fullWidth
              startIcon={<SendIcon />}
              onClick={handleSendOutreach}
              disabled={isSendingOutreach}
            >
              Send Outreach
            </Button>
          </Box>
        )}
      </Drawer>
    </Box>
  );
};

export default Jobs;


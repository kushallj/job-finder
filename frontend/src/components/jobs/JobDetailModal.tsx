import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Chip,
  Button,
  IconButton,
  Stack,
  Divider,
  LinearProgress,
  alpha,
  Paper,
} from '@mui/material';
import {
  Close as CloseIcon,
  OpenInNew as OpenInNewIcon,
  LocationOn as LocationIcon,
  Business as CompanyIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as UncheckedIcon,
  TrendingUp as TrendingUpIcon,
  Public as PublicIcon,
  Speed as SeniorityIcon,
  AutoAwesome as SparklesIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';
import { TsentaAutoApplyButton } from '../tsenta/TsentaAutoApplyButton';
import { NextRaiseApplyButton } from '../nextraise/NextRaiseApplyButton';
import { WorkdayApplyButton } from '../workday/WorkdayApplyButton';
import { GhostBadge } from '../ghost_hunter/GhostBadge';
import { formatSource, formatRelativeTime } from '../../utils/formatters';
import type { Job } from '../../api/types';
import type { TsentaSubmissionData } from '../../api/endpoints/tsenta';

interface JobDetailModalProps {
  open: boolean;
  job: Job | null;
  onClose: () => void;
  onRequestReview?: (sub: TsentaSubmissionData) => void;
}

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  open,
  job,
  onClose,
  onRequestReview,
}) => {
  const navigate = useNavigate();

  if (!job) return null;

  const matchScore = job.match_score ?? 78;
  const matchedSkills = job.matched_skills ?? [];
  const missingSkills = job.missing_skills ?? [];
  const reasons = job.reasons ?? [
    'Matches core full-stack competencies',
    'Seniority: Matches your 4+ years engineering experience',
    'Location: Remote / hybrid alignment',
  ];

  const getScoreTheme = (score: number) => {
    if (score >= 85) return { color: '#00FFA3', label: 'Exceptional Fit', bg: 'rgba(0, 255, 163, 0.15)', border: 'rgba(0, 255, 163, 0.4)' };
    if (score >= 70) return { color: '#00F0FF', label: 'Strong Alignment', bg: 'rgba(0, 240, 255, 0.15)', border: 'rgba(0, 240, 255, 0.4)' };
    return { color: '#FFE600', label: 'Moderate Match', bg: 'rgba(255, 230, 0, 0.15)', border: 'rgba(255, 230, 0, 0.4)' };
  };

  const scoreTheme = getScoreTheme(matchScore);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#080C12',
          backgroundImage: 'none',
          border: '1.5px solid rgba(0, 240, 255, 0.3)',
          borderRadius: '24px',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.9), 0 0 40px rgba(0, 240, 255, 0.15)',
          color: '#F8FAFC',
          maxHeight: '90vh',
        },
      }}
    >
      {/* Modal Header */}
      <DialogTitle sx={{ p: 3, pb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ pr: 2 }}>
            <Typography
              variant="h5"
              sx={{
                fontWeight: 900,
                background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '-0.02em',
                lineHeight: 1.25,
                mb: 0.75,
              }}
            >
              {job.title}
            </Typography>
            <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" sx={{ gap: 0.75 }}>
              <Stack direction="row" spacing={0.5} alignItems="center">
                <CompanyIcon fontSize="small" sx={{ color: '#00F0FF' }} />
                <Typography variant="body1" sx={{ fontWeight: 800, color: '#FFE600' }}>
                  {job.company || 'Unknown Company'}
                </Typography>
              </Stack>
              <Stack direction="row" spacing={0.5} alignItems="center">
                <LocationIcon fontSize="small" sx={{ color: '#00F0FF' }} />
                <Typography variant="body2" sx={{ color: '#CBD5E1', fontWeight: 600 }}>
                  {job.location || 'Remote'}
                </Typography>
              </Stack>
              {job.has_remote && (
                <Chip
                  label="GLOBAL REMOTE"
                  size="small"
                  sx={{
                    height: 22,
                    fontSize: '0.65rem',
                    bgcolor: 'rgba(0, 255, 163, 0.15)',
                    color: '#00FFA3',
                    border: '1px solid rgba(0, 255, 163, 0.4)',
                    fontWeight: 900,
                  }}
                />
              )}
              <GhostBadge jobId={job.id} />
            </Stack>
          </Box>

          <IconButton
            onClick={onClose}
            sx={{
              color: '#94A3B8',
              bgcolor: 'rgba(255, 255, 255, 0.05)',
              '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.1)', color: '#FFF' },
            }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
      </DialogTitle>

      <Divider sx={{ borderColor: 'rgba(0, 240, 255, 0.15)' }} />

      {/* Modal Content */}
      <DialogContent sx={{ p: 3, pt: 2.5 }}>
        {/* ── Match Scoring Breakdown Card ── */}
        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 3,
            borderRadius: '16px',
            bgcolor: '#0D131F',
            border: `1.5px solid ${scoreTheme.border}`,
            boxShadow: `0 8px 24px ${alpha(scoreTheme.color, 0.1)}`,
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box>
              <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Aarivi Explainable Match Intelligence
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, color: scoreTheme.color, mt: 0.25 }}>
                {scoreTheme.label} — {matchScore}% Alignment
              </Typography>
            </Box>

            <Chip
              icon={<SparklesIcon sx={{ fontSize: '14px !important', color: `${scoreTheme.color} !important` }} />}
              label={`${matchScore}% Match`}
              sx={{
                fontWeight: 900,
                fontSize: '0.85rem',
                bgcolor: scoreTheme.bg,
                color: scoreTheme.color,
                border: `1px solid ${scoreTheme.border}`,
                px: 0.5,
              }}
            />
          </Box>

          <LinearProgress
            variant="determinate"
            value={matchScore}
            sx={{
              height: 8,
              borderRadius: 4,
              mb: 2.5,
              bgcolor: 'rgba(255, 255, 255, 0.08)',
              '& .MuiLinearProgress-bar': {
                background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 100%)',
                borderRadius: 4,
              },
            }}
          />

          {/* 3-Bullet Natural Language Validation Reasons */}
          <Typography variant="caption" sx={{ fontWeight: 900, color: '#00F0FF', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', mb: 1 }}>
            Match Validation Rationale:
          </Typography>
          <Stack spacing={1} sx={{ mb: 2.5 }}>
            {reasons.slice(0, 3).map((reason, idx) => {
              const IconComponent =
                idx === 0 ? TrendingUpIcon : idx === 1 ? SeniorityIcon : PublicIcon;
              const iconColor = idx === 0 ? '#00FFA3' : idx === 1 ? '#00F0FF' : '#FFE600';

              return (
                <Stack key={`detail-reason-${idx}`} direction="row" spacing={1.25} alignItems="flex-start">
                  <IconComponent sx={{ fontSize: '16px', color: iconColor, mt: 0.2, flexShrink: 0 }} />
                  <Typography variant="body2" sx={{ color: '#E2E8F0', fontWeight: 500, lineHeight: 1.4 }}>
                    {reason}
                  </Typography>
                </Stack>
              );
            })}
          </Stack>

          <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.08)', my: 2 }} />

          {/* ── Matched vs. Missing Skills Section ── */}
          <Box>
            {/* 🟢 Matched Skills */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" sx={{ color: '#00FFA3', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                <CheckCircleIcon fontSize="inherit" />
                🟢 Matched Candidate Skills ({matchedSkills.length}):
              </Typography>
              <Stack direction="row" spacing={0.75} flexWrap="wrap" sx={{ gap: 0.75 }}>
                {matchedSkills.length > 0 ? (
                  matchedSkills.map((skill) => (
                    <Chip
                      key={`modal-matched-${skill}`}
                      label={skill}
                      size="small"
                      sx={{
                        fontWeight: 800,
                        fontSize: '0.75rem',
                        bgcolor: 'rgba(0, 255, 163, 0.15)',
                        color: '#00FFA3',
                        border: '1px solid rgba(0, 255, 163, 0.45)',
                        boxShadow: '0 0 10px rgba(0, 255, 163, 0.15)',
                      }}
                    />
                  ))
                ) : (
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Transferable engineering background evaluated.
                  </Typography>
                )}
              </Stack>
            </Box>

            {/* ⚪ Missing Skills */}
            {missingSkills.length > 0 && (
              <Box>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                  <UncheckedIcon fontSize="inherit" />
                  ⚪ Missing Job Keywords ({missingSkills.length}):
                </Typography>
                <Stack direction="row" spacing={0.75} flexWrap="wrap" sx={{ gap: 0.75 }}>
                  {missingSkills.map((skill) => (
                    <Chip
                      key={`modal-missing-${skill}`}
                      label={skill}
                      size="small"
                      sx={{
                        fontWeight: 600,
                        fontSize: '0.75rem',
                        bgcolor: 'rgba(148, 163, 184, 0.08)',
                        color: '#94A3B8',
                        border: '1px dashed rgba(148, 163, 184, 0.35)',
                      }}
                    />
                  ))}
                </Stack>
              </Box>
            )}
          </Box>
        </Paper>

        {/* ── Metadata badges ── */}
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ mb: 2.5, gap: 0.75 }}>
          {job.experience_level && (
            <Chip
              label={`Level: ${job.experience_level}`}
              size="small"
              sx={{ bgcolor: 'rgba(0, 240, 255, 0.12)', color: '#00F0FF', fontWeight: 800 }}
            />
          )}
          {job.salary_min && (
            <Chip
              label={`Compensation: $${job.salary_min.toLocaleString()} ${job.salary_max ? `- $${job.salary_max.toLocaleString()}` : ''}`}
              size="small"
              sx={{ bgcolor: 'rgba(255, 230, 0, 0.12)', color: '#FFE600', fontWeight: 800, border: '1px solid rgba(255, 230, 0, 0.4)' }}
            />
          )}
          <Chip
            label={`Source: ${formatSource(job.source)}`}
            size="small"
            sx={{ bgcolor: 'rgba(121, 40, 202, 0.15)', color: '#A855F7', border: '1px solid rgba(121, 40, 202, 0.3)' }}
          />
          <Chip
            label={`Discovered ${formatRelativeTime(job.posted_date || job.fetched_at)}`}
            size="small"
            sx={{ bgcolor: 'rgba(255, 255, 255, 0.05)', color: '#94A3B8' }}
          />
        </Stack>

        {/* ── Job Description ── */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#00F0FF', mb: 1, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Job Description & Requirements
          </Typography>
          <Paper
            elevation={0}
            sx={{
              p: 2.5,
              maxHeight: 280,
              overflowY: 'auto',
              borderRadius: '14px',
              bgcolor: '#0D131F',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              color: '#CBD5E1',
              fontSize: '0.875rem',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}
          >
            {job.description || 'No detailed job description provided in feed.'}
          </Paper>
        </Box>
      </DialogContent>

      <Divider sx={{ borderColor: 'rgba(0, 240, 255, 0.15)' }} />

      {/* Modal Actions */}
      <DialogActions sx={{ p: 2.5, px: 3, justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
        <Button
          variant="outlined"
          endIcon={<ArrowForwardIcon />}
          onClick={() => {
            onClose();
            navigate(`/opportunities/${job.id}`);
          }}
          sx={{
            color: '#00F0FF',
            borderColor: 'rgba(0, 240, 255, 0.4)',
            fontWeight: 800,
            textTransform: 'none',
            borderRadius: '10px',
            '&:hover': {
              borderColor: '#00F0FF',
              bgcolor: 'rgba(0, 240, 255, 0.08)',
            },
          }}
        >
          Open Deep Brief
        </Button>

        <Stack direction="row" spacing={1} alignItems="center">
          <WorkdayApplyButton
            jobId={job.id}
            initialApplied={job.application_status === 'applied'}
          />
          <NextRaiseApplyButton
            jobId={job.id}
            company={job.company || undefined}
            applicationStatus={job.application_status}
          />
          <TsentaAutoApplyButton
            jobId={job.id}
            company={job.company || undefined}
            applicationStatus={job.application_status}
            onReviewRequested={onRequestReview}
            onSubmitted={onRequestReview}
          />
          {job.url && (
            <Button
              variant="contained"
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              startIcon={<OpenInNewIcon />}
              sx={{
                fontWeight: 900,
                textTransform: 'none',
                borderRadius: '10px',
                background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 100%)',
                color: '#06090E',
                '&:hover': {
                  background: 'linear-gradient(90deg, #00F0FF 0%, #00FFA3 100%)',
                },
              }}
            >
              Apply on Company Portal
            </Button>
          )}
        </Stack>
      </DialogActions>
    </Dialog>
  );
};

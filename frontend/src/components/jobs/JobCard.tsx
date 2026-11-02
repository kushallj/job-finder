import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  IconButton,
  Button,
  Stack,
  alpha,
} from '@mui/material';
import {
  OpenInNew as OpenInNewIcon,
  LocationOn as LocationIcon,
  Business as CompanyIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as UncheckedIcon,
  TrendingUp as TrendingUpIcon,
  Public as PublicIcon,
  Speed as SeniorityIcon,
  AutoAwesome as SparklesIcon,
} from '@mui/icons-material';
import { GhostBadge } from '../ghost_hunter/GhostBadge';
import { TsentaAutoApplyButton } from '../tsenta/TsentaAutoApplyButton';
import { NextRaiseApplyButton } from '../nextraise/NextRaiseApplyButton';
import { WorkdayApplyButton } from '../workday/WorkdayApplyButton';
import { formatSource, formatRelativeTime } from '../../utils/formatters';
import type { Job } from '../../api/types';
import type { TsentaSubmissionData } from '../../api/endpoints/tsenta';

interface JobCardProps {
  job: Job;
  onSelectJob: (job: Job) => void;
  onRequestReview?: (sub: TsentaSubmissionData) => void;
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  onSelectJob,
  onRequestReview,
}) => {
  const matchScore = job.match_score ?? 78;
  const matchedSkills = job.matched_skills ?? [];
  const missingSkills = job.missing_skills ?? [];
  const reasons = job.reasons ?? [
    'Matches core full-stack competencies',
    'Seniority: Matches your 4+ years engineering experience',
    'Location: Remote / hybrid alignment',
  ];

  // Helper for match score color
  const getScoreTheme = (score: number) => {
    if (score >= 85) return { color: '#00FFA3', bg: 'rgba(0, 255, 163, 0.15)', border: 'rgba(0, 255, 163, 0.4)' };
    if (score >= 70) return { color: '#00F0FF', bg: 'rgba(0, 240, 255, 0.15)', border: 'rgba(0, 240, 255, 0.4)' };
    return { color: '#FFE600', bg: 'rgba(255, 230, 0, 0.15)', border: 'rgba(255, 230, 0, 0.4)' };
  };

  const scoreTheme = getScoreTheme(matchScore);

  return (
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
        position: 'relative',
        overflow: 'hidden',
        '&:hover': {
          transform: 'translateY(-4px)',
          borderColor: '#00F0FF',
          boxShadow: '0 0 30px rgba(0, 240, 255, 0.3), 0 0 60px rgba(0, 255, 163, 0.15)',
        },
      }}
    >
      {/* Top chromatic accent line */}
      <Box
        sx={{
          height: '3px',
          width: '100%',
          background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)',
        }}
      />

      <CardContent sx={{ p: 2.5, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header: Title, Company, GhostBadge & Match Score */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
          <Box sx={{ flexGrow: 1, pr: 1.5 }}>
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
              onClick={() => onSelectJob(job)}
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

          <Stack direction="column" spacing={0.75} alignItems="flex-end">
            {/* Match Score Badge */}
            <Chip
              icon={<SparklesIcon sx={{ fontSize: '13px !important', color: `${scoreTheme.color} !important` }} />}
              label={`${matchScore}% Match`}
              size="small"
              sx={{
                fontWeight: 900,
                fontSize: '0.72rem',
                bgcolor: scoreTheme.bg,
                color: scoreTheme.color,
                border: `1px solid ${scoreTheme.border}`,
                boxShadow: `0 0 10px ${alpha(scoreTheme.color, 0.25)}`,
              }}
            />
            <GhostBadge jobId={job.id} />
          </Stack>
        </Box>

        {/* Location & Remote */}
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5, color: '#94A3B8' }}>
          <LocationIcon fontSize="inherit" sx={{ color: '#00F0FF' }} />
          <Typography variant="caption" sx={{ fontWeight: 600, color: '#E2E8F0' }}>
            {job.location || 'Remote'}
          </Typography>
          {job.has_remote && (
            <Chip
              label="REMOTE"
              size="small"
              sx={{
                height: 20,
                fontSize: '0.65rem',
                bgcolor: 'rgba(0, 255, 163, 0.15)',
                color: '#00FFA3',
                border: '1px solid rgba(0, 255, 163, 0.4)',
                fontWeight: 800,
              }}
            />
          )}
        </Stack>

        {/* ── Matched vs. Missing Skills Chips ── */}
        <Box sx={{ mb: 1.75 }}>
          <Typography variant="caption" sx={{ fontWeight: 900, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', mb: 0.75 }}>
            Skill Overlap Analysis:
          </Typography>
          <Stack direction="row" spacing={0.6} flexWrap="wrap" sx={{ gap: 0.6 }}>
            {/* 🟢 Matched Skills Chips */}
            {matchedSkills.map((skill) => (
              <Chip
                key={`matched-${skill}`}
                icon={<CheckCircleIcon sx={{ fontSize: '12px !important', color: '#00FFA3 !important' }} />}
                label={skill}
                size="small"
                sx={{
                  height: 22,
                  fontSize: '0.7rem',
                  fontWeight: 800,
                  bgcolor: 'rgba(0, 255, 163, 0.14)',
                  color: '#00FFA3',
                  border: '1px solid rgba(0, 255, 163, 0.4)',
                }}
              />
            ))}

            {/* ⚪ Missing Skills Chips */}
            {missingSkills.map((skill) => (
              <Chip
                key={`missing-${skill}`}
                icon={<UncheckedIcon sx={{ fontSize: '11px !important', color: '#94A3B8 !important' }} />}
                label={skill}
                size="small"
                sx={{
                  height: 22,
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  bgcolor: 'rgba(148, 163, 184, 0.08)',
                  color: '#94A3B8',
                  border: '1px dashed rgba(148, 163, 184, 0.3)',
                }}
              />
            ))}
          </Stack>
        </Box>

        {/* ── 3-Bullet Natural Language Validation Reasons ── */}
        <Box
          sx={{
            mb: 2,
            p: 1.25,
            borderRadius: '12px',
            bgcolor: 'rgba(0, 240, 255, 0.03)',
            border: '1px solid rgba(0, 240, 255, 0.12)',
          }}
        >
          <Stack spacing={0.75}>
            {reasons.slice(0, 3).map((reason, idx) => {
              const IconComponent =
                idx === 0 ? TrendingUpIcon : idx === 1 ? SeniorityIcon : PublicIcon;
              const iconColor = idx === 0 ? '#00FFA3' : idx === 1 ? '#00F0FF' : '#FFE600';

              return (
                <Stack key={`reason-${idx}`} direction="row" spacing={1} alignItems="flex-start">
                  <IconComponent sx={{ fontSize: '14px', color: iconColor, mt: 0.25, flexShrink: 0 }} />
                  <Typography variant="caption" sx={{ color: '#CBD5E1', fontSize: '0.75rem', lineHeight: 1.35, fontWeight: 500 }}>
                    {reason}
                  </Typography>
                </Stack>
              );
            })}
          </Stack>
        </Box>

        {/* Level, Salary & Source Catalog */}
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

        {/* Footer Actions */}
        <Box sx={{ mt: 'auto', pt: 1.5, borderTop: '1px solid rgba(0, 240, 255, 0.15)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>
            {formatRelativeTime(job.posted_date || job.fetched_at)}
          </Typography>
          <Stack direction="row" spacing={0.8} alignItems="center">
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
            <Button
              size="small"
              variant="contained"
              onClick={() => onSelectJob(job)}
              sx={{
                fontWeight: 900,
                fontSize: '0.75rem',
                textTransform: 'none',
                borderRadius: '8px',
                background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 100%)',
                color: '#06090E',
                '&:hover': {
                  background: 'linear-gradient(90deg, #00F0FF 0%, #00FFA3 100%)',
                },
              }}
            >
              Evaluate
            </Button>
            {job.url && (
              <IconButton
                size="small"
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                sx={{
                  color: '#00F0FF',
                  border: '1px solid rgba(0, 240, 255, 0.3)',
                  borderRadius: '8px',
                }}
              >
                <OpenInNewIcon fontSize="small" />
              </IconButton>
            )}
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
};

import React, { useState } from 'react';
import {
  Chip,
  Popover,
  Box,
  Typography,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
} from '@mui/material';
import FlashOnIcon from '@mui/icons-material/FlashOn';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import SentimentVeryDissatisfiedIcon from '@mui/icons-material/SentimentVeryDissatisfied';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useQuery } from '@tanstack/react-query';
import { ghostHunterApi } from '../../api';
import type { GhostSignal } from '../../api/endpoints/ghost_hunter';

interface GhostBadgeProps {
  jobId?: number | string;
  initialGhostScore?: number;
  initialUrgencyLabel?: string;
  rawJobData?: {
    title: string;
    company: string;
    description: string;
    posted_date?: string;
  };
}

export const GhostBadge: React.FC<GhostBadgeProps> = ({
  jobId,
  initialGhostScore,
  initialUrgencyLabel,
  rawJobData,
}) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

  const { data: ghostData, isLoading } = useQuery({
    queryKey: ['ghostScore', jobId || rawJobData?.title],
    queryFn: async () => {
      if (jobId) {
        const res = await ghostHunterApi.getJobGhostScore(jobId);
        return res.data;
      }
      if (rawJobData) {
        const res = await ghostHunterApi.analyze({
          title: rawJobData.title,
          company: rawJobData.company,
          description: rawJobData.description,
          posted_date: rawJobData.posted_date,
        });
        return res.data;
      }
      return null;
    },
    enabled: Boolean(jobId || rawJobData),
    staleTime: 5 * 60 * 1000,
  });

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);

  const score = ghostData?.ghost_score ?? initialGhostScore ?? 25;
  const label = ghostData?.urgency_label ?? initialUrgencyLabel ?? (score < 35 ? 'Active Hiring ⚡' : score < 58 ? 'Moderate ⚠️' : 'Ghost Risk 👻');

  const getColor = () => {
    if (score < 35) return 'success';
    if (score < 58) return 'warning';
    return 'error';
  };

  const getIcon = () => {
    if (score < 35) return <FlashOnIcon fontSize="small" />;
    if (score < 58) return <WarningAmberIcon fontSize="small" />;
    return <SentimentVeryDissatisfiedIcon fontSize="small" />;
  };

  return (
    <>
      <Chip
        icon={getIcon()}
        label={`${label} (${score}% Ghost Risk)`}
        color={getColor()}
        size="small"
        variant="outlined"
        onClick={handleClick}
        sx={{
          fontWeight: 600,
          cursor: 'pointer',
          '&:hover': { transform: 'scale(1.02)' },
          transition: 'all 0.15s ease',
        }}
      />

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        PaperProps={{
          sx: { width: 340, p: 2, borderRadius: 2, boxShadow: '0 8px 32px rgba(0,0,0,0.15)' },
        }}
      >
        {isLoading ? (
          <Box display="flex" justifyContent="center" p={2}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="subtitle2" fontWeight={700}>
                👻 Ghost Hunter Legitimacy Audit
              </Typography>
              <Chip
                label={`${score}% Risk`}
                color={getColor()}
                size="small"
                sx={{ fontWeight: 700 }}
              />
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              {ghostData?.action_recommendation ||
                'Evaluated against temporal posting velocity, layoff context, and ATS keyword patterns.'}
            </Typography>

            <Divider sx={{ my: 1 }} />

            <Typography variant="caption" fontWeight={700} color="text.secondary" textTransform="uppercase">
              Detected Signals ({ghostData?.signals.length || 0})
            </Typography>

            <List dense sx={{ pt: 0.5, pb: 0 }}>
              {ghostData?.signals.map((sig: GhostSignal, idx: number) => (
                <ListItem key={idx} sx={{ px: 0, py: 0.25 }}>
                  <ListItemIcon sx={{ minWidth: 26 }}>
                    {sig.severity === 'positive' ? (
                      <CheckCircleOutlineIcon color="success" fontSize="small" />
                    ) : sig.severity === 'critical' ? (
                      <ErrorOutlineIcon color="error" fontSize="small" />
                    ) : (
                      <InfoOutlinedIcon color="warning" fontSize="small" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={sig.description}
                    primaryTypographyProps={{ variant: 'caption', fontWeight: 500 }}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}
      </Popover>
    </>
  );
};

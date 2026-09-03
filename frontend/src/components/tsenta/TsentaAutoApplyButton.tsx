import React, { useState } from 'react';
import { Button, CircularProgress, Tooltip } from '@mui/material';
import { Bolt as BoltIcon, CheckCircle as CheckCircleIcon } from '@mui/icons-material';

import { tsentaApi, type TsentaSubmissionData } from '../../api/endpoints/tsenta';

interface TsentaAutoApplyButtonProps {
  jobId: number;
  company?: string;
  applicationStatus?: string | null;
  onReviewRequested?: (submission: TsentaSubmissionData) => void;
  onSubmitted?: (submission: TsentaSubmissionData) => void;
  size?: 'small' | 'medium';
}

export const TsentaAutoApplyButton: React.FC<TsentaAutoApplyButtonProps> = ({
  jobId,
  company,
  applicationStatus,
  onReviewRequested,
  onSubmitted,
  size = 'small',
}) => {
  const [loading, setLoading] = useState(false);
  const [applied, setApplied] = useState(applicationStatus === 'applied');

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (applied || loading) return;

    setLoading(true);
    try {
      const res = await tsentaApi.autoApply(jobId);
      if (res.status === 'review_ready') {
        if (onReviewRequested) {
          onReviewRequested(res.submission);
        }
      } else if (res.status === 'submitted' || res.status === 'already_submitted') {
        setApplied(true);
        if (onSubmitted) {
          onSubmitted(res.submission);
        }
      }
    } catch (err) {
      console.error('Tsenta auto-apply error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (applied) {
    return (
      <Tooltip title="Applied via Tsenta Agent with verified cryptographic receipt">
        <Button
          size={size}
          variant="outlined"
          disabled
          startIcon={<CheckCircleIcon sx={{ color: '#00FFA3 !important' }} />}
          sx={{
            borderColor: 'rgba(0, 255, 163, 0.4) !important',
            color: '#00FFA3 !important',
            bgcolor: 'rgba(0, 255, 163, 0.08)',
            textTransform: 'none',
            fontWeight: 700,
            fontSize: size === 'small' ? '0.75rem' : '0.85rem',
            borderRadius: '8px',
          }}
        >
          Applied via Tsenta
        </Button>
      </Tooltip>
    );
  }

  return (
    <Tooltip title={`1-Click auto-apply to ${company || 'this role'} using Tsenta AI Agent`}>
      <Button
        size={size}
        variant="contained"
        disabled={loading}
        onClick={handleClick}
        startIcon={loading ? <CircularProgress size={14} color="inherit" /> : <BoltIcon sx={{ color: '#06090E' }} />}
        sx={{
          bgcolor: '#00FFA3',
          color: '#06090E',
          fontWeight: 800,
          textTransform: 'none',
          fontSize: size === 'small' ? '0.75rem' : '0.85rem',
          borderRadius: '8px',
          boxShadow: '0 0 15px rgba(0, 255, 163, 0.35)',
          transition: 'all 0.2s ease',
          '&:hover': {
            bgcolor: '#00E592',
            boxShadow: '0 0 25px rgba(0, 255, 163, 0.6)',
            transform: 'translateY(-1px)',
          },
        }}
      >
        {loading ? 'Preparing...' : '⚡ Auto-Apply'}
      </Button>
    </Tooltip>
  );
};

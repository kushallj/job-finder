import React, { useState } from 'react';
import { Button, CircularProgress, Tooltip } from '@mui/material';
import { RocketLaunch as RocketIcon, CheckCircle as CheckCircleIcon } from '@mui/icons-material';

import { nextraiseApi, type NextRaiseSingleApplyResponse } from '../../api/endpoints/nextraise';

interface NextRaiseApplyButtonProps {
  jobId: number;
  company?: string;
  applicationStatus?: string | null;
  onApplied?: (res: NextRaiseSingleApplyResponse) => void;
  size?: 'small' | 'medium';
}

export const NextRaiseApplyButton: React.FC<NextRaiseApplyButtonProps> = ({
  jobId,
  company,
  applicationStatus,
  onApplied,
  size = 'small',
}) => {
  const [loading, setLoading] = useState(false);
  const [applied, setApplied] = useState(applicationStatus === 'applied');
  const [receiptId, setReceiptId] = useState<string | null>(null);

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (applied || loading) return;

    setLoading(true);
    try {
      const res = await nextraiseApi.applySingle(jobId);
      if (res.success || res.already_applied) {
        setApplied(true);
        if (res.receipt_id) {
          setReceiptId(res.receipt_id);
        }
        if (onApplied) {
          onApplied(res);
        }
      }
    } catch (err) {
      console.error('NextRaise auto-apply error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (applied) {
    return (
      <Tooltip title={receiptId ? `Applied via NextRaise (${receiptId}) for canaby007@gmail.com` : "Applied via NextRaise Pro for canaby007@gmail.com"}>
        <Button
          size={size}
          variant="outlined"
          disabled
          startIcon={<CheckCircleIcon sx={{ color: '#A855F7 !important' }} />}
          sx={{
            borderColor: 'rgba(168, 85, 247, 0.4) !important',
            color: '#A855F7 !important',
            bgcolor: 'rgba(168, 85, 247, 0.08)',
            textTransform: 'none',
            fontWeight: 700,
            fontSize: size === 'small' ? '0.75rem' : '0.85rem',
            borderRadius: '8px',
          }}
        >
          NextRaise Applied ✓
        </Button>
      </Tooltip>
    );
  }

  return (
    <Tooltip title={`1-Click auto-apply to ${company || 'this role'} using NextRaise Pro (canaby007@gmail.com)`}>
      <Button
        size={size}
        variant="contained"
        disabled={loading}
        onClick={handleClick}
        startIcon={loading ? <CircularProgress size={14} color="inherit" /> : <RocketIcon sx={{ color: '#FFFFFF', fontSize: '15px' }} />}
        sx={{
          background: 'linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)',
          color: '#FFFFFF',
          fontWeight: 800,
          textTransform: 'none',
          fontSize: size === 'small' ? '0.75rem' : '0.85rem',
          borderRadius: '8px',
          boxShadow: '0 0 14px rgba(168, 85, 247, 0.35)',
          transition: 'all 0.2s ease',
          '&:hover': {
            background: 'linear-gradient(135deg, #6D28D9 0%, #9333EA 100%)',
            boxShadow: '0 0 22px rgba(168, 85, 247, 0.6)',
            transform: 'translateY(-1px)',
          },
        }}
      >
        {loading ? 'Submitting...' : '🚀 NextRaise'}
      </Button>
    </Tooltip>
  );
};

import React, { useState } from 'react';
import { Button, CircularProgress, Tooltip, Chip } from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Layers as LayersIcon,
} from '@mui/icons-material';
import { workdayApi, type WorkdaySingleApplyResponse } from '../../api/endpoints/workday';

interface WorkdayApplyButtonProps {
  jobId: number;
  initialApplied?: boolean;
  size?: 'small' | 'medium' | 'large';
  onAppliedSuccess?: (result: WorkdaySingleApplyResponse) => void;
}

export const WorkdayApplyButton: React.FC<WorkdayApplyButtonProps> = ({
  jobId,
  initialApplied = false,
  size = 'small',
  onAppliedSuccess,
}) => {
  const [applied, setApplied] = useState<boolean>(initialApplied);
  const [loading, setLoading] = useState<boolean>(false);
  const [receiptId, setReceiptId] = useState<string | null>(null);

  const handleApply = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (applied || loading) return;

    try {
      setLoading(true);
      const res = await workdayApi.applySingle(jobId);
      if (res.success) {
        setApplied(true);
        setReceiptId(res.receipt_id || null);
        if (onAppliedSuccess) onAppliedSuccess(res);
      }
    } catch (err) {
      console.error('Workday auto-apply failed:', err);
    } finally {
      setLoading(false);
    }
  };

  if (applied) {
    return (
      <Tooltip title={receiptId ? `Receipt: ${receiptId} (Verified Workday Submission)` : 'Application Submitted via Workday'}>
        <Chip
          icon={<CheckCircleIcon sx={{ fontSize: '14px !important', color: '#00FFA3 !important' }} />}
          label="Workday Applied"
          size="small"
          sx={{
            background: 'rgba(0, 255, 163, 0.12)',
            color: '#00FFA3',
            fontWeight: 700,
            fontSize: '0.75rem',
            border: '1px solid rgba(0, 255, 163, 0.3)',
          }}
        />
      </Tooltip>
    );
  }

  return (
    <Button
      variant="contained"
      size={size}
      onClick={handleApply}
      disabled={loading}
      startIcon={
        loading ? (
          <CircularProgress size={14} color="inherit" />
        ) : (
          <LayersIcon sx={{ fontSize: '15px !important' }} />
        )
      }
      sx={{
        background: 'linear-gradient(135deg, #FFE600 0%, #D97706 100%)',
        color: '#0F172A',
        fontWeight: 700,
        fontSize: size === 'small' ? '0.75rem' : '0.85rem',
        px: 1.8,
        py: size === 'small' ? 0.4 : 0.8,
        borderRadius: 1.5,
        textTransform: 'none',
        boxShadow: '0 2px 8px rgba(255, 230, 0, 0.2)',
        '&:hover': {
          background: 'linear-gradient(135deg, #FFF04D 0%, #F59E0B 100%)',
          boxShadow: '0 4px 14px rgba(255, 230, 0, 0.35)',
        },
      }}
    >
      {loading ? 'Submitting Workday...' : '🚀 Workday'}
    </Button>
  );
};

import React from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Divider, Stack, Typography } from '@mui/material';
import { ArrowForward as ArrowForwardIcon, AutoAwesome as AIIcon, CheckCircle as CheckIcon, OpenInNew as OpenIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useActionQueue } from '../../hooks/useActionQueue';

const stageLabel: Record<string, string> = {
  saved: 'Saved',
  ready: 'Ready',
  applied: 'Applied',
  interview: 'Interview',
  offer: 'Offer',
  negotiation: 'Negotiation',
  accepted: 'Accepted',
  rejected: 'Closed',
};

export const ActionQueue: React.FC<{ limit?: number }> = ({ limit = 8 }) => {
  const navigate = useNavigate();
  const { data, isLoading, isError, doNext, isWorking } = useActionQueue(limit);

  if (isLoading) {
    return (
      <Card>
        <CardContent sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
          <CircularProgress />
        </CardContent>
      </Card>
    );
  }
  if (isError) return <Alert severity="error">Unable to load your next actions.</Alert>;
  const actions = data?.actions || [];

  return (
    <Card sx={{ mb: 4 }}>
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2} sx={{ mb: 2 }}>
          <Box>
            <Stack direction="row" spacing={1} alignItems="center">
              <AIIcon color="secondary" />
              <Typography variant="h6" fontWeight={800}>Do This Next</Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              One queue for the whole career lifecycle — from application to offer.
            </Typography>
          </Box>
          <Chip label={`${data?.total || 0} active`} size="small" variant="outlined" />
        </Stack>
        <Divider sx={{ mb: 1 }} />
        {actions.length === 0 ? (
          <Box sx={{ py: 3 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <CheckIcon color="success" />
              <Typography fontWeight={700}>You are caught up.</Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Review new opportunities when they arrive, or keep your active pipeline moving.
            </Typography>
          </Box>
        ) : (
          actions.map((item) => (
            <Box
              key={`${item.job_id}-${item.action.key}`}
              sx={{
                py: 1.75,
                borderBottom: '1px solid',
                borderColor: 'divider',
                '&:last-child': { borderBottom: 0 },
              }}
            >
              <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}>
                <Box sx={{ minWidth: 0, flex: 1 }}>
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" alignItems="center">
                    <Typography fontWeight={800}>{item.title}</Typography>
                    {item.company && <Typography variant="body2" color="text.secondary">· {item.company}</Typography>}
                    <Chip label={stageLabel[item.stage] || item.stage} size="small" variant="outlined" />
                    {item.fit_score != null && (
                      <Chip label={`Fit ${Math.round(item.fit_score)}%`} size="small" variant="outlined" />
                    )}
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>{item.action.label}</Typography>
                  <Typography variant="caption" color="text.secondary">{item.action.reason}</Typography>
                </Box>
                <Button
                  variant={item.action.priority === 'high' ? 'contained' : 'outlined'}
                  endIcon={item.action.external ? <OpenIcon /> : <ArrowForwardIcon />}
                  disabled={isWorking}
                  onClick={async () => {
                    try {
                      const result = await doNext(item.job_id);
                      if (result.action === 'apply' && result.open_url) {
                        window.open(result.open_url, '_blank', 'noopener,noreferrer');
                        return;
                      }
                      navigate(`/opportunities/${item.job_id}`);
                    } catch {
                      navigate(`/opportunities/${item.job_id}`);
                    }
                  }}
                >
                  {item.action.key === 'complete' ? 'Open' : 'Do it'}
                </Button>
              </Stack>
            </Box>
          ))
        )}
      </CardContent>
    </Card>
  );
};

export default ActionQueue;

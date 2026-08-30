import React from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Typography,
  alpha,
} from '@mui/material';
import {
  ArrowForward as ArrowForwardIcon,
  CheckCircle as CheckIcon,
  OpenInNew as OpenIcon,
  Bolt as FlashIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useActionQueue } from '../../hooks/useActionQueue';

const stageColors: Record<string, { bg: string; text: string; border: string }> = {
  saved: { bg: alpha('#64748B', 0.1), text: '#475569', border: alpha('#64748B', 0.2) },
  ready: { bg: alpha('#4F46E5', 0.1), text: '#4F46E5', border: alpha('#4F46E5', 0.2) },
  applied: { bg: alpha('#06B6D4', 0.1), text: '#0891B2', border: alpha('#06B6D4', 0.2) },
  interview: { bg: alpha('#F59E0B', 0.1), text: '#D97706', border: alpha('#F59E0B', 0.2) },
  offer: { bg: alpha('#10B981', 0.1), text: '#059669', border: alpha('#10B981', 0.2) },
  negotiation: { bg: alpha('#8B5CF6', 0.1), text: '#7C3AED', border: alpha('#8B5CF6', 0.2) },
  accepted: { bg: alpha('#10B981', 0.15), text: '#047857', border: alpha('#10B981', 0.3) },
};

const stageLabel: Record<string, string> = {
  saved: '📌 Saved',
  ready: '✨ Ready to Apply',
  applied: '📤 Applied',
  interview: '🎯 Interviewing',
  offer: '🎉 Offer Received',
  negotiation: '💼 Negotiating',
  accepted: '🏆 Accepted',
  rejected: 'Closed',
};

export const ActionQueue: React.FC<{ limit?: number }> = ({ limit = 8 }) => {
  const navigate = useNavigate();
  const { data, isLoading, isError, doNext, isWorking } = useActionQueue(limit);

  if (isLoading) {
    return (
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 5, gap: 1.5 }}>
          <CircularProgress size={28} />
          <Typography variant="body2" color="text.secondary">Loading priority action queue...</Typography>
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return <Alert severity="error" sx={{ mb: 4 }}>Unable to load your next actions.</Alert>;
  }

  const actions = data?.actions || [];

  return (
    <Card
      sx={{
        mb: 4,
        background: 'linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%)',
        border: '1px solid #E2E8F0',
        boxShadow: '0 4px 16px -4px rgba(0, 0, 0, 0.04)',
      }}
    >
      <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} gap={2} sx={{ mb: 2 }}>
          <Box>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box
                sx={{
                  p: 1,
                  borderRadius: '10px',
                  bgcolor: alpha('#4F46E5', 0.1),
                  color: '#4F46E5',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <FlashIcon />
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.01em' }}>
                  Do This Next — Career Action Queue
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Automated priority engine prescribing the highest ROI step for every opportunity.
                </Typography>
              </Box>
            </Stack>
          </Box>
          <Chip
            label={`${data?.total || 0} Recommended Actions`}
            size="small"
            sx={{
              bgcolor: alpha('#4F46E5', 0.1),
              color: '#4F46E5',
              fontWeight: 700,
              border: `1px solid ${alpha('#4F46E5', 0.2)}`,
            }}
          />
        </Stack>

        <Divider sx={{ borderColor: '#F1F5F9', my: 2 }} />

        {actions.length === 0 ? (
          <Box sx={{ py: 4, textAlign: 'center' }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                bgcolor: alpha('#10B981', 0.1),
                color: '#10B981',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                mb: 1.5,
              }}
            >
              <CheckIcon fontSize="medium" />
            </Box>
            <Typography variant="subtitle1" fontWeight={700} color="#0F172A">
              You're completely caught up!
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 460, mx: 'auto', mt: 0.5 }}>
              All current opportunities have been acted on. Run a new job search above to discover and match fresh roles.
            </Typography>
          </Box>
        ) : (
          <Stack spacing={1.5}>
            {actions.map((item) => {
              const stageStyle = stageColors[item.stage] || stageColors.saved;
              const isHighPriority = item.action.priority === 'high';
              const fitScore = item.fit_score ? Math.round(item.fit_score) : null;

              return (
                <Box
                  key={`${item.job_id}-${item.action.key}`}
                  sx={{
                    p: 2,
                    borderRadius: '12px',
                    border: '1px solid',
                    borderColor: isHighPriority ? alpha('#4F46E5', 0.2) : '#F1F5F9',
                    backgroundColor: isHighPriority ? alpha('#4F46E5', 0.02) : '#FFFFFF',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      borderColor: '#CBD5E1',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
                      transform: 'translateY(-1px)',
                    },
                  }}
                >
                  <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} gap={2}>
                    <Box sx={{ minWidth: 0, flex: 1 }}>
                      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" alignItems="center" sx={{ mb: 0.75 }}>
                        <Typography
                          variant="subtitle1"
                          sx={{
                            fontWeight: 800,
                            color: '#0F172A',
                            cursor: 'pointer',
                            '&:hover': { color: '#4F46E5' },
                          }}
                          onClick={() => navigate(`/opportunities/${item.job_id}`)}
                        >
                          {item.title}
                        </Typography>
                        {item.company && (
                          <Typography variant="body2" sx={{ fontWeight: 600, color: '#64748B' }}>
                            @ {item.company}
                          </Typography>
                        )}
                        <Chip
                          label={stageLabel[item.stage] || item.stage}
                          size="small"
                          sx={{
                            bgcolor: stageStyle.bg,
                            color: stageStyle.text,
                            border: `1px solid ${stageStyle.border}`,
                            fontWeight: 700,
                            fontSize: '0.72rem',
                          }}
                        />
                        {fitScore !== null && (
                          <Chip
                            label={`${fitScore}% Match`}
                            size="small"
                            sx={{
                              bgcolor: fitScore >= 80 ? alpha('#10B981', 0.1) : alpha('#F59E0B', 0.1),
                              color: fitScore >= 80 ? '#059669' : '#D97706',
                              fontWeight: 700,
                              fontSize: '0.72rem',
                            }}
                          />
                        )}
                      </Stack>

                      <Typography variant="body2" sx={{ fontWeight: 700, color: '#1E293B', mb: 0.25 }}>
                        👉 {item.action.label}
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#64748B', display: 'block', lineHeight: 1.4 }}>
                        {item.action.reason}
                      </Typography>
                    </Box>

                    <Stack direction="row" spacing={1} sx={{ flexShrink: 0, width: { xs: '100%', md: 'auto' } }}>
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={() => navigate(`/opportunities/${item.job_id}`)}
                        sx={{ flex: { xs: 1, md: 'none' } }}
                      >
                        View Brief
                      </Button>
                      <Button
                        variant={isHighPriority ? 'contained' : 'outlined'}
                        color="primary"
                        size="small"
                        disabled={isWorking}
                        endIcon={item.action.external ? <OpenIcon fontSize="small" /> : <ArrowForwardIcon fontSize="small" />}
                        sx={{
                          flex: { xs: 1, md: 'none' },
                          fontWeight: 700,
                        }}
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
                        {item.action.key === 'apply' ? 'Apply Direct' : 'Execute Step'}
                      </Button>
                    </Stack>
                  </Stack>
                </Box>
              );
            })}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
};

export default ActionQueue;

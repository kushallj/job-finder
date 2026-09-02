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
} from '@mui/material';
import {
  ArrowForward as ArrowForwardIcon,
  CheckCircle as CheckIcon,
  Bolt as FlashIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useActionQueue } from '../../hooks/useActionQueue';


const stageColors: Record<string, { bg: string; text: string; border: string }> = {
  saved: { bg: 'rgba(148, 163, 184, 0.12)', text: '#94A3B8', border: 'rgba(148, 163, 184, 0.3)' },
  ready: { bg: 'rgba(0, 240, 255, 0.15)', text: '#00F0FF', border: 'rgba(0, 240, 255, 0.4)' },
  applied: { bg: 'rgba(0, 255, 163, 0.15)', text: '#00FFA3', border: 'rgba(0, 255, 163, 0.4)' },
  interview: { bg: 'rgba(255, 230, 0, 0.15)', text: '#FFE600', border: 'rgba(255, 230, 0, 0.4)' },
  offer: { bg: 'rgba(0, 255, 163, 0.2)', text: '#00FFA3', border: 'rgba(0, 255, 163, 0.5)' },
  negotiation: { bg: 'rgba(121, 40, 202, 0.2)', text: '#A855F7', border: 'rgba(121, 40, 202, 0.4)' },
  accepted: { bg: 'rgba(0, 255, 163, 0.25)', text: '#00FFA3', border: 'rgba(0, 255, 163, 0.6)' },
};

const stageLabel: Record<string, string> = {
  saved: '📌 Saved',
  ready: '⚡ Ready to Apply',
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
      <Card sx={{ mb: 4, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)' }}>
        <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 5, gap: 1.5 }}>
          <CircularProgress size={28} sx={{ color: '#00FFA3' }} />
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>Loading priority action queue...</Typography>
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return <Alert severity="error" sx={{ mb: 4, bgcolor: 'rgba(255, 0, 122, 0.15)', color: '#FF007A', border: '1px solid rgba(255, 0, 122, 0.4)' }}>Unable to load your next actions.</Alert>;
  }

  const actions = data?.actions || [];

  return (
    <Card
      sx={{
        mb: 4,
        bgcolor: '#0D131F',
        border: '1.5px solid rgba(0, 240, 255, 0.2)',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(16px)',
      }}
    >
      <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} gap={2} sx={{ mb: 2 }}>
          <Box>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box
                sx={{
                  p: 1.2,
                  borderRadius: '12px',
                  bgcolor: 'rgba(0, 255, 163, 0.15)',
                  color: '#00FFA3',
                  border: '1px solid rgba(0, 255, 163, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  boxShadow: '0 0 15px rgba(0, 255, 163, 0.25)',
                }}
              >
                <FlashIcon />
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC', letterSpacing: '-0.02em', textTransform: 'uppercase' }}>
                  Do This Next — Career Action Queue
                </Typography>
                <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                  Automated priority engine prescribing the highest ROI step for every opportunity.
                </Typography>
              </Box>
            </Stack>
          </Box>
          <Chip
            label={`${data?.total || 0} Recommended Actions`}
            size="small"
            sx={{
              bgcolor: 'rgba(0, 240, 255, 0.15)',
              color: '#00F0FF',
              fontWeight: 800,
              border: '1px solid rgba(0, 240, 255, 0.4)',
              boxShadow: '0 0 10px rgba(0, 240, 255, 0.2)',
            }}
          />
        </Stack>

        <Divider sx={{ borderColor: 'rgba(0, 240, 255, 0.15)', my: 2 }} />

        {actions.length === 0 ? (
          <Box sx={{ py: 4, textAlign: 'center' }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                bgcolor: 'rgba(0, 255, 163, 0.15)',
                color: '#00FFA3',
                border: '1px solid rgba(0, 255, 163, 0.4)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                mb: 1.5,
              }}
            >
              <CheckIcon fontSize="medium" />
            </Box>
            <Typography variant="subtitle1" fontWeight={800} color="#F8FAFC">
              You're completely caught up!
            </Typography>
            <Typography variant="body2" sx={{ color: '#94A3B8', maxWidth: 460, mx: 'auto', mt: 0.5 }}>
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
                    borderRadius: '14px',
                    border: '1px solid',
                    borderColor: isHighPriority ? 'rgba(0, 240, 255, 0.35)' : 'rgba(255, 255, 255, 0.08)',
                    backgroundColor: isHighPriority ? 'rgba(0, 240, 255, 0.04)' : '#080C12',
                    transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    '&:hover': {
                      borderColor: '#00F0FF',
                      boxShadow: '0 0 20px rgba(0, 240, 255, 0.2)',
                      transform: 'translateY(-2px)',
                    },
                  }}
                >
                  <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} gap={2}>
                    <Box sx={{ minWidth: 0, flex: 1 }}>
                      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" alignItems="center" sx={{ mb: 0.75 }}>
                        <Typography
                          variant="subtitle1"
                          sx={{
                            fontWeight: 900,
                            background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 100%)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            cursor: 'pointer',
                            '&:hover': { filter: 'brightness(1.2)' },
                          }}
                          onClick={() => navigate(`/opportunities/${item.job_id}`)}
                        >
                          {item.title}
                        </Typography>
                        {item.company && (
                          <Typography variant="body2" sx={{ fontWeight: 700, color: '#FFE600' }}>
                            @ {item.company}
                          </Typography>
                        )}
                        {fitScore !== null && (
                          <Chip
                            label={`${fitScore}% Match`}
                            size="small"
                            sx={{
                              fontSize: '0.7rem',
                              height: 20,
                              bgcolor: 'rgba(0, 255, 163, 0.15)',
                              color: '#00FFA3',
                              border: '1px solid rgba(0, 255, 163, 0.4)',
                              fontWeight: 800,
                            }}
                          />
                        )}
                        <Chip
                          label={stageLabel[item.stage] || item.stage}
                          size="small"
                          sx={{
                            fontSize: '0.7rem',
                            height: 20,
                            bgcolor: stageStyle.bg,
                            color: stageStyle.text,
                            border: `1px solid ${stageStyle.border}`,
                            fontWeight: 700,
                          }}
                        />
                      </Stack>

                      <Typography variant="body2" sx={{ color: '#E2E8F0', fontWeight: 500 }}>
                        {item.action.reason || item.action.label}
                      </Typography>
                    </Box>

                    <Stack direction="row" spacing={1} alignItems="center" sx={{ flexShrink: 0 }}>
                      <Button
                        variant="contained"
                        color={isHighPriority ? 'primary' : 'secondary'}
                        size="small"
                        onClick={() => doNext(item.job_id)}
                        disabled={isWorking}
                        startIcon={<FlashIcon fontSize="small" />}
                        sx={{ fontWeight: 900 }}
                      >
                        {item.action.label}
                      </Button>
                      <Button
                        variant="outlined"
                        size="small"
                        endIcon={<ArrowForwardIcon fontSize="small" />}
                        onClick={() => navigate(`/opportunities/${item.job_id}`)}
                        sx={{ fontWeight: 800 }}
                      >
                        Brief
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

import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
  alpha,
  Button,
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  Psychology as TransformerIcon,
  ContentCopy as CopyIcon,
  Check as CopiedIcon,
  Speed as ScaleIcon,
  Code as TechIcon,
  TrendingUp as ImpactIcon,
  SupervisorAccount as SeniorityIcon,
} from '@mui/icons-material';
import type { AttentionMatchResponse } from '../../api/endpoints/attention';

interface Props {
  data?: AttentionMatchResponse | null;
  loading?: boolean;
  onSelectProofPoint?: (proof: string) => void;
}

const headIcons: Record<string, React.ReactNode> = {
  tech_stack: <TechIcon fontSize="small" sx={{ color: '#2563EB' }} />,
  scale_systems: <ScaleIcon fontSize="small" sx={{ color: '#7C3AED' }} />,
  business_impact: <ImpactIcon fontSize="small" sx={{ color: '#059669' }} />,
  seniority_leadership: <SeniorityIcon fontSize="small" sx={{ color: '#D97706' }} />,
};

const headLabels: Record<string, string> = {
  tech_stack: 'Tech Stack Alignment',
  scale_systems: 'Scale & Architecture',
  business_impact: 'Business Impact',
  seniority_leadership: 'Seniority & Ownership',
};

export const AttentionHeatmap: React.FC<Props> = ({ data, loading, onSelectProofPoint }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  if (loading) {
    return (
      <Card sx={{ border: '1px solid #E2E8F0', p: 4, textAlign: 'center', mb: 3 }}>
        <CircularProgress size={32} sx={{ mb: 2 }} />
        <Typography variant="subtitle2" fontWeight={700} color="#0F172A">
          Computing 4-Head Transformer Q,K,V Attention Matrix...
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Aligning job requirements against candidate capabilities & metrics
        </Typography>
      </Card>
    );
  }

  if (!data) {
    return null;
  }

  const { overall_score, fit_label, heads, matrix, top_attended_values } = data;
  const queries = matrix.query_tokens || [];
  const keys = matrix.key_tokens || [];
  const weights = matrix.weights || [];

  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
    if (onSelectProofPoint) onSelectProofPoint(text);
  };

  return (
    <Card sx={{ border: '1px solid #E2E8F0', boxShadow: '0 4px 20px -4px rgba(0,0,0,0.05)', mb: 3 }}>
      <CardContent sx={{ p: 3 }}>
        {/* Header Summary */}
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} gap={2} sx={{ mb: 2.5 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Box
              sx={{
                width: 44,
                height: 44,
                borderRadius: '12px',
                bgcolor: alpha('#4F46E5', 0.1),
                color: '#4F46E5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <TransformerIcon />
            </Box>
            <Box>
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="h6" fontWeight={800} color="#0F172A">
                  Transformer Q,K,V Attention Match
                </Typography>
                <Chip
                  label={`${Math.round(overall_score)}% Alignment`}
                  size="small"
                  color={overall_score >= 80 ? 'success' : overall_score >= 65 ? 'primary' : 'warning'}
                  sx={{ fontWeight: 800 }}
                />
              </Stack>
              <Typography variant="caption" color="text.secondary">
                {fit_label} · Multi-Head Scaled Dot-Product Attention (d=128, H=4)
              </Typography>
            </Box>
          </Stack>
        </Stack>

        {/* 4-Head Attention Breakdown Cards */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {Object.entries(heads).map(([hName, hData]) => (
            <Grid key={hName} size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper variant="outlined" sx={{ p: 1.75, borderRadius: '12px', bgcolor: '#F8FAFC' }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    {headIcons[hName] || <AIIcon fontSize="small" />}
                    <Typography variant="caption" fontWeight={700} color="#0F172A">
                      {headLabels[hName] || hName}
                    </Typography>
                  </Stack>
                  <Typography variant="subtitle2" fontWeight={800} color="#4F46E5">
                    {Math.round(hData.head_score)}%
                  </Typography>
                </Stack>
                <LinearProgress
                  variant="determinate"
                  value={hData.head_score}
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    bgcolor: '#E2E8F0',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: hData.head_score >= 80 ? '#10B981' : hData.head_score >= 65 ? '#4F46E5' : '#F59E0B',
                    },
                  }}
                />
              </Paper>
            </Grid>
          ))}
        </Grid>

        {/* Attention Matrix Heatmap Table */}
        <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
          Multi-Head Attention Heatmap (α_ij = Softmax(Q · Kᵀ / √d_k))
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
          Rows: Job Description Requirements (Q_i) · Columns: Candidate Experience Bullets (K_j) · Hover cell to view attended proof value.
        </Typography>

        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: '12px', mb: 3, maxHeight: 380 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 800, bgcolor: '#F1F5F9', minWidth: 200, zIndex: 3 }}>
                  Requirement (Query Q_i)
                </TableCell>
                {keys.map((k, j) => (
                  <TableCell key={k.id} align="center" sx={{ fontWeight: 700, bgcolor: '#F1F5F9', minWidth: 90 }}>
                    <Tooltip title={k.text} arrow>
                      <Typography variant="caption" fontWeight={700} sx={{ cursor: 'pointer', color: '#475569' }}>
                        K_{j + 1}
                      </Typography>
                    </Tooltip>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {queries.map((q, i) => (
                <TableRow key={q.id}>
                  <TableCell sx={{ fontSize: '0.8rem', color: '#1E293B', fontWeight: 600, py: 1 }}>
                    <Chip label={q.category} size="small" sx={{ mr: 1, height: 20, fontSize: '0.65rem', fontWeight: 700 }} />
                    {q.text.length > 55 ? `${q.text.slice(0, 52)}...` : q.text}
                  </TableCell>
                  {keys.map((k, j) => {
                    const weight = weights[i]?.[j] || 0.0;
                    const intensity = Math.min(1.0, weight * 3.0); // Boost contrast for display
                    return (
                      <Tooltip
                        key={k.id}
                        title={
                          <Box sx={{ p: 0.5 }}>
                            <Typography variant="caption" fontWeight={700} display="block">
                              Attention: {(weight * 100).toFixed(1)}%
                            </Typography>
                            <Typography variant="caption" color="inherit" display="block" sx={{ my: 0.5 }}>
                              <strong>Query:</strong> {q.text}
                            </Typography>
                            <Typography variant="caption" color="inherit" display="block">
                              <strong>Key:</strong> {k.text}
                            </Typography>
                          </Box>
                        }
                        arrow
                      >
                        <TableCell
                          align="center"
                          sx={{
                            bgcolor: alpha('#4F46E5', intensity),
                            color: intensity > 0.4 ? '#FFFFFF' : '#0F172A',
                            fontWeight: 800,
                            fontSize: '0.75rem',
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                            '&:hover': {
                              transform: 'scale(1.1)',
                              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                              zIndex: 2,
                            },
                          }}
                        >
                          {(weight * 100).toFixed(0)}%
                        </TableCell>
                      </Tooltip>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        <Divider sx={{ my: 2 }} />

        {/* Top Attended Value Proof Points */}
        <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
          Top Attended Value Proof Points ($V^*$)
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
          These concrete accomplishments received the highest attention weights from this job description.
        </Typography>

        <Stack spacing={1.5}>
          {top_attended_values.map((v, idx) => (
            <Paper key={v.id} variant="outlined" sx={{ p: 1.5, borderRadius: '10px', bgcolor: '#F8FAFC' }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1.5}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" color="#1E293B" fontWeight={600}>
                    {v.proof_point}
                  </Typography>
                  {v.impact_metric && (
                    <Chip
                      label={`Metric: ${v.impact_metric}`}
                      size="small"
                      color="success"
                      sx={{ mt: 0.5, height: 20, fontSize: '0.7rem', fontWeight: 700 }}
                    />
                  )}
                </Box>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={copiedIndex === idx ? <CopiedIcon fontSize="small" /> : <CopyIcon fontSize="small" />}
                  onClick={() => handleCopy(v.proof_point, idx)}
                  sx={{ whiteSpace: 'nowrap', fontWeight: 700 }}
                >
                  {copiedIndex === idx ? 'Copied' : 'Use Bullet'}
                </Button>
              </Stack>
            </Paper>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default AttentionHeatmap;

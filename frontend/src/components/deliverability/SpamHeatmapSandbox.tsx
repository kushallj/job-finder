import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Stack,
  LinearProgress,
  Button,
  CircularProgress,
  alpha,
} from '@mui/material';
import ShieldIcon from '@mui/icons-material/Shield';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { deliverabilityApi } from '../../api';

import type { DeliverabilityDraftResponse, SpamWordMatch } from '../../api/endpoints/deliverability';

interface SpamHeatmapSandboxProps {
  subject: string;
  body: string;
  onReplaceWord?: (oldWord: string, newWord: string) => void;
}

export const SpamHeatmapSandbox: React.FC<SpamHeatmapSandboxProps> = ({
  subject,
  body,
  onReplaceWord,
}) => {
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<DeliverabilityDraftResponse | null>(null);

  useEffect(() => {
    if (!body.trim()) return;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await deliverabilityApi.analyzeDraft({
          subject: subject || 'Quick question',
          body,
        });
        setAnalysis(res.data);
      } catch {
        // silent fail
      } finally {
        setLoading(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [subject, body]);

  if (!body.trim()) return null;

  const score = analysis?.spam_score ?? 0;
  const isSafe = analysis?.is_safe ?? true;

  const getTierColor = () => {
    if (score < 25) return '#10B981';
    if (score < 55) return '#F59E0B';
    return '#EF4444';
  };

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 3,
        border: '1px solid #E2E8F0',
        bgcolor: '#FAFAFB',
        position: 'relative',
      }}
    >
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1.5}>
        <Stack direction="row" spacing={1} alignItems="center">
          <ShieldIcon sx={{ color: getTierColor(), fontSize: 22 }} />
          <Typography variant="subtitle1" fontWeight={700} color="#0F172A">
            🛡️ Cold Email Deliverability Sandbox
          </Typography>
        </Stack>
        {loading ? (
          <CircularProgress size={18} />
        ) : (
          <Chip
            label={analysis?.deliverability_tier || 'Analyzing...'}
            size="small"
            sx={{
              fontWeight: 700,
              bgcolor: alpha(getTierColor(), 0.12),
              color: getTierColor(),
              border: `1px solid ${alpha(getTierColor(), 0.3)}`,
            }}
          />
        )}
      </Box>

      {/* Metrics Row */}
      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
        <Box sx={{ flex: 1, minWidth: 100, p: 1.5, bgcolor: '#FFFFFF', borderRadius: 2, border: '1px solid #E2E8F0' }}>
          <Typography variant="caption" color="text.secondary" fontWeight={600}>
            Spam Risk Score
          </Typography>
          <Typography variant="h6" fontWeight={800} sx={{ color: getTierColor() }}>
            {score}%
          </Typography>
          <LinearProgress
            variant="determinate"
            value={score}
            sx={{
              height: 4,
              borderRadius: 2,
              mt: 0.5,
              bgcolor: '#E2E8F0',
              '& .MuiLinearProgress-bar': { bgcolor: getTierColor() },
            }}
          />
        </Box>

        <Box sx={{ flex: 1, minWidth: 100, p: 1.5, bgcolor: '#FFFFFF', borderRadius: 2, border: '1px solid #E2E8F0' }}>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <MenuBookIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" fontWeight={600}>
              Reading Level
            </Typography>
          </Stack>
          <Typography variant="h6" fontWeight={800} color="#0F172A">
            Grade {analysis?.flesch_kincaid_grade ?? '–'}
          </Typography>
          <Typography variant="caption" color={analysis && analysis.flesch_kincaid_grade <= 8 ? 'success.main' : 'warning.main'}>
            {analysis && analysis.flesch_kincaid_grade <= 8 ? '✓ Optimal Executive Reading' : '⚠️ Complex sentences'}
          </Typography>
        </Box>

        <Box sx={{ flex: 1, minWidth: 100, p: 1.5, bgcolor: '#FFFFFF', borderRadius: 2, border: '1px solid #E2E8F0' }}>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <AccessTimeIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" fontWeight={600}>
              Read Time
            </Typography>
          </Stack>
          <Typography variant="h6" fontWeight={800} color="#0F172A">
            {analysis?.reading_time_seconds ?? 0}s
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {analysis?.word_count ?? 0} words
          </Typography>
        </Box>
      </Stack>

      {/* Spam Trigger Heatmap & 1-Click Replacer */}
      {analysis && analysis.spam_matches.length > 0 && (
        <Box sx={{ mb: 2, p: 1.5, bgcolor: '#FEF2F2', borderRadius: 2, border: '1px solid #FCA5A5' }}>
          <Typography variant="caption" fontWeight={700} color="#991B1B" textTransform="uppercase" display="block" mb={1}>
            ⚠️ {analysis.spam_matches.length} Spam Trigger Word(s) Detected
          </Typography>
          <Stack spacing={1}>
            {analysis.spam_matches.map((m: SpamWordMatch, idx: number) => (
              <Box key={idx} sx={{ p: 1, bgcolor: '#FFFFFF', borderRadius: 1.5, border: '1px solid #FECACA' }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  <Chip
                    label={`"${m.word}"`}
                    size="small"
                    color={m.severity === 'critical' ? 'error' : 'warning'}
                    sx={{ fontWeight: 700 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    Replace with:
                  </Typography>
                  {m.suggested_alternatives.map((alt: string, aIdx: number) => (
                    <Button
                      key={aIdx}
                      size="small"
                      variant="outlined"
                      color="primary"
                      startIcon={<AutoFixHighIcon sx={{ fontSize: 12 }} />}
                      onClick={() => onReplaceWord && onReplaceWord(m.word, alt)}
                      sx={{
                        py: 0.2,
                        px: 0.8,
                        fontSize: '0.75rem',
                        textTransform: 'none',
                        borderRadius: 1.5,
                      }}
                    >
                      {alt}
                    </Button>
                  ))}
                </Stack>
              </Box>
            ))}
          </Stack>
        </Box>
      )}

      {/* Deliverability Recommendations */}
      {analysis && analysis.deliverability_recommendations.length > 0 && (
        <Stack spacing={0.5}>
          {analysis.deliverability_recommendations.map((rec: string, idx: number) => (
            <Stack key={idx} direction="row" spacing={1} alignItems="center">
              <CheckCircleIcon sx={{ fontSize: 14, color: isSafe ? '#10B981' : '#F59E0B' }} />
              <Typography variant="caption" color="text.secondary" fontWeight={500}>
                {rec}
              </Typography>
            </Stack>
          ))}
        </Stack>
      )}
    </Paper>
  );
};

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Stack,
  Divider,
  Button,
  CircularProgress,
  Paper,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  Grid,
} from '@mui/material';

import {
  Forum as ForumIcon,
  Refresh as RefreshIcon,
  Launch as LaunchIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  CheckCircle as GreenFlagIcon,
  Warning as RedFlagIcon,
  AttachMoney as MoneyIcon,
  Psychology as BrainIcon,
  YouTube as YouTubeIcon,
  Article as ArticleIcon,
  QuestionAnswer as RedditIcon,
} from '@mui/icons-material';
import { communityIntelApi } from '../../api';
import type { CompanyCommunityIntel } from '../../api/endpoints/community_intel';

interface CommunityIntelPanelProps {
  company: string;
  roleTitle?: string;
}

export const CommunityIntelPanel: React.FC<CommunityIntelPanelProps> = ({ company, roleTitle }) => {
  const [intel, setIntel] = useState<CompanyCommunityIntel | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [copiedText, setCopiedText] = useState<string | null>(null);

  const fetchIntel = async (force: boolean = false) => {
    if (!company) return;
    setLoading(true);
    try {
      const res = await communityIntelApi.getCompanyIntel(company, roleTitle, force);
      setIntel(res.data);
    } catch {
      // silent fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntel(false);
  }, [company, roleTitle]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'reddit':
        return <RedditIcon sx={{ color: '#FF4500' }} fontSize="small" />;
      case 'hackernews':
        return <ForumIcon sx={{ color: '#FF6600' }} fontSize="small" />;
      case 'youtube':
        return <YouTubeIcon sx={{ color: '#FF0000' }} fontSize="small" />;
      case 'substack':
        return <ArticleIcon sx={{ color: '#FF6719' }} fontSize="small" />;
      case 'medium':
      default:
        return <ArticleIcon sx={{ color: '#2563EB' }} fontSize="small" />;
    }
  };

  return (
    <Card sx={{ border: '1px solid #E2E8F0', borderRadius: 3, mb: 3 }}>
      <CardContent sx={{ p: 3 }}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={1.5} mb={2}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <ForumIcon sx={{ color: '#0284C7', fontSize: 28 }} />
            <Box>
              <Typography variant="h6" fontWeight={800} color="#0F172A">
                🌐 Community Interview Debriefs & Insider Intelligence — {company}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Aggregated from Reddit (r/cscareerquestions, r/leetcode), Hacker News, Medium, Substack & YouTube mock interviews.
              </Typography>
            </Box>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            {intel && (
              <Chip
                label={intel.overall_sentiment}
                size="small"
                sx={{ fontWeight: 700, bgcolor: '#E0F2FE', color: '#0369A1' }}
              />
            )}
            <Button
              size="small"
              variant="outlined"
              startIcon={loading ? <CircularProgress size={12} /> : <RefreshIcon fontSize="small" />}
              onClick={() => fetchIntel(true)}
              disabled={loading}
              sx={{ fontWeight: 700 }}
            >
              Refresh Intel
            </Button>
          </Stack>
        </Box>

        <Divider sx={{ mb: 2 }} />

        {loading && !intel ? (
          <Box display="flex" alignItems="center" justifyContent="center" py={4}>
            <CircularProgress size={28} sx={{ mr: 1.5 }} />
            <Typography variant="body2" color="text.secondary">
              Harvesting community interview debriefs for {company}…
            </Typography>
          </Box>
        ) : intel ? (
          <Box>
            {/* Tabs */}
            <Tabs
              value={activeTab}
              onChange={(_, v) => setActiveTab(v)}
              sx={{ mb: 2.5, minHeight: 38 }}
            >
              <Tab label="Interview Rounds & Roadmap" sx={{ fontWeight: 700, fontSize: '0.85rem' }} />
              <Tab label="Leaked Questions & System Design" sx={{ fontWeight: 700, fontSize: '0.85rem' }} />
              <Tab label="Culture Flags & Negotiation" sx={{ fontWeight: 700, fontSize: '0.85rem' }} />
              <Tab label={`Source Citations (${intel.sources?.length || 0})`} sx={{ fontWeight: 700, fontSize: '0.85rem' }} />
            </Tabs>

            {/* Tab 0: Interview Rounds */}
            {activeTab === 0 && (
              <Box>
                <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
                  Reported Hiring Loop Roadmap:
                </Typography>
                <Grid container spacing={2}>
                  {(intel.interview_debrief?.rounds || []).map((r, idx) => (
                    <Grid size={{ xs: 12, md: 6 }} key={idx}>
                      <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#F8FAFC' }}>
                        <Stack direction="row" spacing={1} alignItems="center" mb={0.5}>
                          <Chip label={r.round} size="small" color="primary" sx={{ fontWeight: 700, height: 20, fontSize: '0.7rem' }} />
                          <Typography variant="subtitle2" fontWeight={800} color="#0F172A">
                            {r.type}
                          </Typography>
                        </Stack>
                        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem' }}>
                          {r.focus}
                        </Typography>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              </Box>
            )}

            {/* Tab 1: Questions & System Design */}
            {activeTab === 1 && (
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
                    🧠 Candidate-Reported Coding / Domain Questions:
                  </Typography>
                  <Stack spacing={1.5}>
                    {intel.interview_debrief.common_questions.map((q, idx) => (
                      <Paper key={idx} variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: '#F8FAFC' }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                          <Typography variant="body2" fontWeight={600} color="#1E293B">
                            {q}
                          </Typography>
                          <Tooltip title="Copy question">
                            <IconButton size="small" onClick={() => handleCopy(q)}>
                              {copiedText === q ? <CheckIcon fontSize="small" color="success" /> : <CopyIcon fontSize="small" />}
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </Paper>
                    ))}
                  </Stack>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
                    🏗️ System Design & Architecture Challenges:
                  </Typography>
                  <Stack spacing={1.5}>
                    {intel.interview_debrief.system_design_topics.map((t, idx) => (
                      <Paper key={idx} variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: '#F0FDF4', borderColor: '#BBF7D0' }}>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <BrainIcon sx={{ color: '#16A34A', fontSize: 18 }} />
                          <Typography variant="body2" fontWeight={700} color="#166534">
                            {t}
                          </Typography>
                        </Stack>
                      </Paper>
                    ))}
                  </Stack>
                </Grid>
              </Grid>
            )}

            {/* Tab 2: Culture Flags & Negotiation */}
            {activeTab === 2 && (
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="subtitle2" fontWeight={800} color="#166534" gutterBottom>
                    ✨ Culture Green Flags:
                  </Typography>
                  <Stack spacing={1}>
                    {intel.interview_debrief.green_flags.map((flag, idx) => (
                      <Paper key={idx} variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: '#F0FDF4', borderColor: '#BBF7D0' }}>
                        <Stack direction="row" spacing={1} alignItems="flex-start">
                          <GreenFlagIcon sx={{ color: '#16A34A', fontSize: 18, mt: 0.2 }} />
                          <Typography variant="body2" color="#14532D">{flag}</Typography>
                        </Stack>
                      </Paper>
                    ))}
                  </Stack>

                  <Typography variant="subtitle2" fontWeight={800} color="#991B1B" sx={{ mt: 2 }} gutterBottom>
                    ⚠️ Culture Red Flags & Process Warnings:
                  </Typography>
                  <Stack spacing={1}>
                    {intel.interview_debrief.red_flags.map((flag, idx) => (
                      <Paper key={idx} variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: '#FEF2F2', borderColor: '#FECACA' }}>
                        <Stack direction="row" spacing={1} alignItems="flex-start">
                          <RedFlagIcon sx={{ color: '#DC2626', fontSize: 18, mt: 0.2 }} />
                          <Typography variant="body2" color="#7F1D1D">{flag}</Typography>
                        </Stack>
                      </Paper>
                    ))}
                  </Stack>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
                    💰 Insider Compensation Negotiation Levers:
                  </Typography>
                  <Stack spacing={1.5}>
                    {intel.interview_debrief.negotiation_tips.map((tip, idx) => (
                      <Paper key={idx} variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: '#FFFBEB', borderColor: '#FDE68A' }}>
                        <Stack direction="row" spacing={1} alignItems="flex-start">
                          <MoneyIcon sx={{ color: '#D97706', fontSize: 18, mt: 0.2 }} />
                          <Typography variant="body2" color="#92400E" fontWeight={500}>{tip}</Typography>
                        </Stack>
                      </Paper>
                    ))}
                  </Stack>
                </Grid>
              </Grid>
            )}

            {/* Tab 3: Source Citations */}
            {activeTab === 3 && (
              <Stack spacing={1.5}>
                {(intel.sources || []).map((src, idx) => (
                  <Paper key={idx} variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#F8FAFC' }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1} mb={0.5}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        {getSourceIcon(src.source)}
                        <Typography variant="subtitle2" fontWeight={700} color="#0F172A">
                          {src.title}
                        </Typography>
                      </Stack>
                      <Button
                        size="small"
                        variant="text"
                        endIcon={<LaunchIcon fontSize="small" />}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ fontWeight: 700, minWidth: 'auto' }}
                      >
                        Open Source
                      </Button>
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem', mb: 1 }}>
                      {src.summary}
                    </Typography>
                    <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                      <Chip label={src.source.toUpperCase()} size="small" sx={{ fontWeight: 700, height: 20, fontSize: '0.65rem' }} />
                      {src.tags.map((t, i) => (
                        <Chip key={i} label={`#${t}`} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.65rem' }} />
                      ))}
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            )}
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
};

export default CommunityIntelPanel;

import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Chip,
  Stack,
  Paper,
  CircularProgress,
  alpha,
  Grid,
} from '@mui/material';

import {
  Send as SendIcon,
  SmartToy as BotIcon,
  Person as UserIcon,
  Launch as LaunchIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  Search as SearchIcon,
  AutoAwesome as SparkleIcon,
  RestartAlt as ResetIcon,
} from '@mui/icons-material';
import { copilotApi } from '../api';
import type { BooleanDorkResult } from '../api/endpoints/copilot';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  dorks?: BooleanDorkResult[];
  followups?: string[];
  timestamp: string;
}

export const Copilot: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        '👋 Welcome to the **JobFinder AI OSINT Copilot**!\n\nI can write precision **Google Boolean Dork queries** to help you discover:\n- 📄 **Unindexed Job Descriptions** (Lever, Greenhouse, Notion, Google Docs)\n- 👤 **Hiring Manager & Director Direct Inboxes**\n- 💰 **Crowdsourced Salary & Equity Spreadsheets**\n- 💻 **GitHub Candidate Take-Home Challenges & Solutions**\n\nAsk me anything or choose a prompt starter below!',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [targetCompany, setTargetCompany] = useState('');
  const [roleTitle, setRoleTitle] = useState('');
  const [starters, setStarters] = useState<Array<{ title: string; prompt: string }>>([]);
  const [copiedQuery, setCopiedQuery] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    copilotApi.getStarters().then((res) => {
      if (res.data.starters) setStarters(res.data.starters);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, loading]);


  const handleSend = async (customText?: string) => {
    const textToSend = customText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = {
      id: String(Date.now()),
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customText) setInput('');
    setLoading(true);

    try {
      const res = await copilotApi.chat({
        message: textToSend,
        session_id: sessionId || undefined,
        target_company: targetCompany || undefined,
        role_title: roleTitle || undefined,
      });

      if (!sessionId && res.data.session_id) {
        setSessionId(res.data.session_id);
      }

      const botMsg: Message = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: res.data.reply,
        dorks: res.data.dorks,
        followups: res.data.suggested_followups,
        timestamp: new Date().toLocaleTimeString(),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          role: 'assistant',
          content: 'Sorry, I encountered an issue generating the queries. Please try again.',
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (query: string) => {
    navigator.clipboard.writeText(query);
    setCopiedQuery(query);
    setTimeout(() => setCopiedQuery(null), 2000);
  };

  const handleReset = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Conversation reset. How can I help you find hidden career opportunities today?',
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
    setSessionId('');
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: { xs: 1, md: 2 } }}>
      {/* Header Banner */}
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2} mb={3}>
        <Box>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <SparkleIcon sx={{ color: '#4F46E5', fontSize: 32 }} />
            <Typography variant="h4" fontWeight={800} color="#0F172A" letterSpacing="-0.02em">
              AI OSINT Boolean Query Copilot
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Synthesize precision Google Boolean search dorks, unearth unindexed Notion & Google Docs job descriptions, and map hidden hiring manager inboxes.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          color="secondary"
          size="small"
          startIcon={<ResetIcon />}
          onClick={handleReset}
          sx={{ fontWeight: 700 }}
        >
          New Session
        </Button>
      </Box>

      {/* Target Role & Company Quick Context */}
      <Card sx={{ border: '1px solid #E2E8F0', borderRadius: 3, mb: 3 }}>
        <CardContent sx={{ p: 2 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, sm: 5 }}>
              <TextField
                label="Target Role Title"
                placeholder="e.g. Senior Distributed Systems Engineer"
                size="small"
                fullWidth
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 5 }}>
              <TextField
                label="Target Company (Optional)"
                placeholder="e.g. Stripe, OpenAI, Figma"
                size="small"
                fullWidth
                value={targetCompany}
                onChange={(e) => setTargetCompany(e.target.value)}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 2 }}>
              <Button
                variant="contained"
                startIcon={<SearchIcon />}
                onClick={() => handleSend(`Generate comprehensive OSINT boolean dorks for ${roleTitle || 'Software Engineer'} at ${targetCompany || 'Tier-1 tech companies'}`)}
                fullWidth
                sx={{ height: 40, fontWeight: 700 }}
              >
                Generate Dorks
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Prompt Starters */}
      {starters.length > 0 && messages.length <= 2 && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 3 }}>
          {starters.map((s, idx) => (
            <Chip
              key={idx}
              label={s.title}
              onClick={() => handleSend(s.prompt)}
              variant="outlined"
              color="primary"
              sx={{ fontWeight: 600, cursor: 'pointer', py: 1.5 }}
            />
          ))}
        </Stack>
      )}

      {/* Chat Stream Window */}
      <Card sx={{ border: '1px solid #E2E8F0', borderRadius: 3, minHeight: 480, mb: 3 }}>
        <CardContent sx={{ p: { xs: 2, md: 3 } }}>
          <Stack spacing={3}>
            {messages.map((m) => (
              <Box key={m.id} display="flex" gap={2} alignItems="flex-start">
                <Paper
                  elevation={0}
                  sx={{
                    width: 38,
                    height: 38,
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: m.role === 'assistant' ? alpha('#4F46E5', 0.1) : '#F1F5F9',
                    color: m.role === 'assistant' ? '#4F46E5' : '#475569',
                    flexShrink: 0,
                  }}
                >
                  {m.role === 'assistant' ? <BotIcon fontSize="small" /> : <UserIcon fontSize="small" />}
                </Paper>

                <Box sx={{ flex: 1 }}>
                  <Typography variant="caption" fontWeight={700} color="text.secondary" display="block" mb={0.5}>
                    {m.role === 'assistant' ? 'JobFinder OSINT Copilot' : 'You'} • {m.timestamp}
                  </Typography>

                  <Typography variant="body1" sx={{ color: '#0F172A', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                    {m.content}
                  </Typography>

                  {/* Render Boolean Dorks */}
                  {m.dorks && m.dorks.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
                        🎯 Generated Google Boolean Dork Queries ({m.dorks.length}):
                      </Typography>
                      <Stack spacing={2}>
                        {m.dorks.map((dork, dIdx) => (
                          <Paper
                            key={dIdx}
                            variant="outlined"
                            sx={{
                              p: 2,
                              borderRadius: 2,
                              bgcolor: '#F8FAFC',
                              borderColor: '#CBD5E1',
                            }}
                          >
                            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                              <Typography variant="subtitle2" fontWeight={800} color="#4F46E5">
                                {dork.title}
                              </Typography>
                              <Stack direction="row" spacing={1}>
                                <Button
                                  size="small"
                                  variant="outlined"
                                  startIcon={copiedQuery === dork.query ? <CheckIcon fontSize="small" color="success" /> : <CopyIcon fontSize="small" />}
                                  onClick={() => handleCopy(dork.query)}
                                  sx={{ fontWeight: 700 }}
                                >
                                  {copiedQuery === dork.query ? 'Copied' : 'Copy Query'}
                                </Button>
                                <Button
                                  size="small"
                                  variant="contained"
                                  color="primary"
                                  endIcon={<LaunchIcon fontSize="small" />}
                                  href={dork.search_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  sx={{ fontWeight: 700 }}
                                >
                                  Launch on Google ↗
                                </Button>
                              </Stack>
                            </Box>

                            {/* Query Box */}
                            <Paper
                              elevation={0}
                              sx={{
                                p: 1.5,
                                bgcolor: '#0F172A',
                                borderRadius: 1.5,
                                fontFamily: 'monospace',
                                fontSize: '0.85rem',
                                color: '#38BDF8',
                                overflowX: 'auto',
                                mb: 1,
                              }}
                            >
                              <code>{dork.query}</code>
                            </Paper>

                            <Typography variant="caption" color="text.secondary">
                              💡 <b>Search Logic:</b> {dork.explanation}
                            </Typography>
                          </Paper>
                        ))}
                      </Stack>
                    </Box>
                  )}

                  {/* Follow-up suggestion chips */}
                  {m.followups && m.followups.length > 0 && (
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
                      {m.followups.map((f, fIdx) => (
                        <Chip
                          key={fIdx}
                          label={`💡 ${f}`}
                          size="small"
                          onClick={() => handleSend(f)}
                          sx={{ cursor: 'pointer', fontWeight: 600 }}
                        />
                      ))}
                    </Stack>
                  )}
                </Box>
              </Box>
            ))}

            {loading && (
              <Box display="flex" gap={2} alignItems="center">
                <Paper
                  elevation={0}
                  sx={{
                    width: 38,
                    height: 38,
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: alpha('#4F46E5', 0.1),
                    color: '#4F46E5',
                  }}
                >
                  <BotIcon fontSize="small" />
                </Paper>
                <Stack direction="row" spacing={1} alignItems="center">
                  <CircularProgress size={18} />
                  <Typography variant="body2" color="text.secondary">
                    Synthesizing Boolean queries and checking repo intelligence…
                  </Typography>
                </Stack>
              </Box>
            )}

            <div ref={messagesEndRef} />
          </Stack>
        </CardContent>
      </Card>

      {/* Input Deck */}
      <Paper
        variant="outlined"
        sx={{
          p: 1.5,
          borderRadius: 3,
          bgcolor: '#FFFFFF',
          display: 'flex',
          gap: 1.5,
          alignItems: 'center',
          borderColor: '#CBD5E1',
        }}
      >
        <TextField
          placeholder="Ask for custom Google Boolean Dorks, unlisted JDs, hiring manager inboxes, or salary spreadsheets…"
          variant="standard"
          fullWidth
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          InputProps={{ disableUnderline: true }}
          sx={{ px: 1 }}
        />
        <Button
          variant="contained"
          color="primary"
          endIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          sx={{ fontWeight: 700, borderRadius: 2, px: 3, height: 44 }}
        >
          Send
        </Button>
      </Paper>
    </Box>
  );
};

export default Copilot;

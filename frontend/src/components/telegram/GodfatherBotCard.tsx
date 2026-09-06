import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Stack,
  Chip,
  Button,
  Paper,
  TextField,
  CircularProgress,
  Switch,
  FormControlLabel,
  IconButton,
} from '@mui/material';
import {
  Send as SendIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  Refresh as RefreshIcon,
  Radar as RadarIcon,
  ElectricBolt as BoltIcon,
  QrCode2 as QrCodeIcon,
  Campaign as BroadcastIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material';
import {
  godfatherApi,
  type BotStatusResponse,
  type BotMessageResponse,
  type ChatMessage,
} from '../../api/endpoints/godfather_api';

export const GodfatherBotCard: React.FC = () => {
  const [status, setStatus] = useState<BotStatusResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(false);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [sending, setSending] = useState<boolean>(false);
  const [scanning, setScanning] = useState<boolean>(false);
  const [broadcastText, setBroadcastText] = useState<string>('');
  const [broadcastSent, setBroadcastSent] = useState<boolean>(false);

  // Chat message history
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init-1',
      sender: 'godfather',
      text: '👑 <b>THE GODFATHER: SOVEREIGN CAREER CONSIGLIERE</b><br/><i>Your 24x7 autonomous career syndicate is active.</i><br/><br/>I am connected directly to all 13 sovereign intelligence agents. Send any natural language query or slash command below to command the fleet.',
      agentInvoked: 'consigliere_menu',
      timestamp: new Date().toLocaleTimeString(),
      replyMarkup: {
        inline_keyboard: [
          [
            { text: '🧠 Profile Interviewer', callback_data: '/profile Stripe' },
            { text: '⚖️ Counter Offer', callback_data: '/counter 45 60 CRED' },
          ],
          [
            { text: '🛠️ Fabricate PoW', callback_data: '/fabricate Razorpay' },
            { text: '📡 Escalate Recruiter', callback_data: '/escalate Swiggy 5' },
          ],
          [
            { text: '🌐 Frontier AI Radar', callback_data: '/frontier' },
            { text: '📐 System Design', callback_data: '/whiteboard trading' },
          ],
        ],
      },
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchStatus = async () => {
    setLoadingStatus(true);
    try {
      const data = await godfatherApi.getStatus();
      setStatus(data);
    } catch (e) {
      console.error('Failed to fetch Godfather status', e);
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async (msgText: string) => {
    const textToSend = (msgText || inputMessage).trim();
    if (!textToSend || sending) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setSending(true);

    try {
      const resp: BotMessageResponse = await godfatherApi.interact(textToSend);
      const botMsg: ChatMessage = {
        id: `bot-${Date.now()}`,
        sender: 'godfather',
        text: resp.text.replace(/\n/g, '<br/>'),
        agentInvoked: resp.agent_invoked,
        timestamp: new Date().toLocaleTimeString(),
        replyMarkup: resp.reply_markup,
      };
      setMessages((prev) => [...prev, botMsg]);
      fetchStatus();
    } catch (err) {
      const errMsg: ChatMessage = {
        id: `bot-err-${Date.now()}`,
        sender: 'godfather',
        text: '❌ <b>Error:</b> Failed to execute command with Consigliere backend.',
        agentInvoked: 'error',
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setSending(false);
    }
  };

  const handleToggleAutopilot = async (enabled: boolean) => {
    try {
      await godfatherApi.toggleAutopilot(enabled);
      fetchStatus();
    } catch (e) {
      console.error(e);
    }
  };

  const handleTriggerRadar = async () => {
    setScanning(true);
    try {
      const scan = await godfatherApi.triggerRadarScan();
      const findingsSummary = scan.findings.map(f => `• <b>${f.category}</b>: ${f.title} (${f.rate || f.reward})`).join('<br/>');
      const scanMsg: ChatMessage = {
        id: `bot-radar-${Date.now()}`,
        sender: 'godfather',
        text: `📡 <b>[ON-DEMAND 24x7 RADAR COMPLETE]</b><br/>Identified <b>${scan.findings_count}</b> high-yield opportunities:<br/><br/>${findingsSummary}<br/><br/><i>Type /frontier or /bounty to inspect complete dossiers.</i>`,
        agentInvoked: 'radar_scan',
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, scanMsg]);
      fetchStatus();
    } catch (e) {
      console.error(e);
    } finally {
      setScanning(false);
    }
  };

  const handleBroadcast = async () => {
    if (!broadcastText.trim()) return;
    try {
      await godfatherApi.broadcastAlert(broadcastText);
      setBroadcastSent(true);
      setBroadcastText('');
      setTimeout(() => setBroadcastSent(false), 3000);
      fetchStatus();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <Card
      sx={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
        border: '1px solid rgba(245, 158, 11, 0.3)',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        borderRadius: 3,
        overflow: 'hidden',
      }}
    >
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        {/* Header Bar */}
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} spacing={2} mb={3}>
          <Box>
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <Typography variant="h5" sx={{ fontWeight: 800, color: '#f59e0b', letterSpacing: -0.5 }}>
                👑 The Godfather Consigliere Bot
              </Typography>
              <Chip
                icon={<BoltIcon sx={{ fontSize: '16px !important', color: '#10b981' }} />}
                label={status?.autopilot_enabled ? '24x7 AUTOPILOT ON' : 'PAUSED'}
                size="small"
                sx={{
                  backgroundColor: status?.autopilot_enabled ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: status?.autopilot_enabled ? '#10b981' : '#ef4444',
                  border: '1px solid',
                  borderColor: status?.autopilot_enabled ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                }}
              />
            </Stack>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', mt: 0.5 }}>
              Executes all 13 sovereign intelligence engines in seconds via pure Telegram commands and natural language.
            </Typography>
          </Box>

          <Stack direction="row" spacing={1} alignItems="center">
            <FormControlLabel
              control={
                <Switch
                  checked={status?.autopilot_enabled ?? true}
                  onChange={(e) => handleToggleAutopilot(e.target.checked)}
                  color="warning"
                />
              }
              label={
                <Typography variant="caption" sx={{ color: '#fff', fontWeight: 600 }}>
                  24x7 Daemon
                </Typography>
              }
            />

            <Button
              variant="outlined"
              size="small"
              startIcon={scanning ? <CircularProgress size={14} color="inherit" /> : <RadarIcon />}
              onClick={handleTriggerRadar}
              disabled={scanning}
              sx={{
                borderColor: 'rgba(245, 158, 11, 0.5)',
                color: '#f59e0b',
                textTransform: 'none',
                fontWeight: 600,
                '&:hover': { borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)' },
              }}
            >
              Scan Radar
            </Button>

            <IconButton size="small" onClick={fetchStatus} sx={{ color: 'rgba(255,255,255,0.7)' }}>
              {loadingStatus ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
            </IconButton>
          </Stack>
        </Stack>

        <Grid container spacing={3}>
          {/* Left Column: Interactive Chat Terminal */}
          <Grid size={{ xs: 12, lg: 7 }}>
            <Paper
              sx={{
                height: 520,
                display: 'flex',
                flexDirection: 'column',
                backgroundColor: 'rgba(10, 15, 29, 0.85)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 2,
                overflow: 'hidden',
              }}
            >
              {/* Terminal Top Bar */}
              <Box sx={{ p: 1.5, backgroundColor: 'rgba(0,0,0,0.4)', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#ef4444' }} />
                  <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#f59e0b' }} />
                  <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#10b981' }} />
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', ml: 1, fontFamily: 'monospace' }}>
                    telegram://@GodfatherCopilotBot (Live Terminal)
                  </Typography>
                </Stack>
                <Chip label={`Commands: ${status?.total_commands_executed || 0}`} size="small" sx={{ height: 20, fontSize: '0.65rem', backgroundColor: 'rgba(255,255,255,0.1)', color: '#fff' }} />
              </Box>

              {/* Chat Message Stream */}
              <Box sx={{ flex: 1, p: 2, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
                {messages.map((m) => (
                  <Box
                    key={m.id}
                    sx={{
                      display: 'flex',
                      justifyContent: m.sender === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    <Stack
                      direction="row"
                      spacing={1}
                      alignItems="flex-start"
                      sx={{ maxWidth: '85%' }}
                    >
                      {m.sender === 'godfather' && (
                        <Box
                          sx={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            backgroundColor: 'rgba(245, 158, 11, 0.2)',
                            border: '1px solid #f59e0b',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                            mt: 0.5,
                          }}
                        >
                          <BotIcon sx={{ color: '#f59e0b', fontSize: 18 }} />
                        </Box>
                      )}

                      <Box>
                        <Paper
                          sx={{
                            p: 1.5,
                            borderRadius: 2,
                            backgroundColor: m.sender === 'user' ? '#2563eb' : 'rgba(30, 41, 59, 0.9)',
                            border: '1px solid',
                            borderColor: m.sender === 'user' ? '#3b82f6' : 'rgba(255,255,255,0.1)',
                            color: '#fff',
                            fontSize: '0.875rem',
                          }}
                        >
                          <Typography
                            variant="body2"
                            component="div"
                            sx={{
                              color: '#fff',
                              lineHeight: 1.5,
                              '& b': { color: '#f59e0b' },
                              '& code': {
                                backgroundColor: 'rgba(0,0,0,0.4)',
                                padding: '2px 4px',
                                borderRadius: '4px',
                                fontFamily: 'monospace',
                                color: '#38bdf8',
                              },
                              '& i': { color: 'rgba(255,255,255,0.8)' },
                            }}
                            dangerouslySetInnerHTML={{ __html: m.text }}
                          />

                          {/* Render Inline Buttons if present */}
                          {m.replyMarkup?.inline_keyboard && (
                            <Box sx={{ mt: 1.5, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                              {m.replyMarkup.inline_keyboard.flat().map((btn, idx) => (
                                <Button
                                  key={idx}
                                  size="small"
                                  variant="outlined"
                                  onClick={() => btn.callback_data && handleSendMessage(btn.callback_data)}
                                  sx={{
                                    borderColor: 'rgba(245, 158, 11, 0.4)',
                                    color: '#fcd34d',
                                    backgroundColor: 'rgba(245, 158, 11, 0.05)',
                                    textTransform: 'none',
                                    fontSize: '0.75rem',
                                    py: 0.25,
                                    px: 1,
                                    borderRadius: 1.5,
                                    '&:hover': {
                                      backgroundColor: 'rgba(245, 158, 11, 0.2)',
                                      borderColor: '#f59e0b',
                                    },
                                  }}
                                >
                                  {btn.text}
                                </Button>
                              ))}
                            </Box>
                          )}
                        </Paper>
                        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', mt: 0.5, display: 'block', textAlign: m.sender === 'user' ? 'right' : 'left' }}>
                          {m.timestamp} {m.agentInvoked ? `• Agent: ${m.agentInvoked}` : ''}
                        </Typography>
                      </Box>

                      {m.sender === 'user' && (
                        <Box
                          sx={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            backgroundColor: 'rgba(59, 130, 246, 0.2)',
                            border: '1px solid #3b82f6',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                            mt: 0.5,
                          }}
                        >
                          <PersonIcon sx={{ color: '#60a5fa', fontSize: 18 }} />
                        </Box>
                      )}
                    </Stack>
                  </Box>
                ))}
                {sending && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: '#f59e0b' }}>
                    <CircularProgress size={16} color="inherit" />
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontStyle: 'italic' }}>
                      The Godfather Consigliere is consulting intelligence agents...
                    </Typography>
                  </Box>
                )}
                <div ref={messagesEndRef} />
              </Box>

              {/* Quick Prompt Chips */}
              <Box sx={{ p: 1, backgroundColor: 'rgba(0,0,0,0.3)', borderTop: '1px solid rgba(255,255,255,0.06)', overflowX: 'auto', display: 'flex', gap: 1 }}>
                <Chip label="🧠 /profile Google" size="small" onClick={() => handleSendMessage('/profile Google')} sx={{ color: '#fff', backgroundColor: 'rgba(255,255,255,0.08)', cursor: 'pointer' }} />
                <Chip label="⚖️ /counter 48 60 Uber" size="small" onClick={() => handleSendMessage('/counter 48 60 Uber')} sx={{ color: '#fff', backgroundColor: 'rgba(255,255,255,0.08)', cursor: 'pointer' }} />
                <Chip label="🛠️ /fabricate Stripe" size="small" onClick={() => handleSendMessage('/fabricate Stripe')} sx={{ color: '#fff', backgroundColor: 'rgba(255,255,255,0.08)', cursor: 'pointer' }} />
                <Chip label="🌐 /frontier" size="small" onClick={() => handleSendMessage('/frontier')} sx={{ color: '#fff', backgroundColor: 'rgba(255,255,255,0.08)', cursor: 'pointer' }} />
                <Chip label="🌍 /geo tokyo" size="small" onClick={() => handleSendMessage('/geo tokyo')} sx={{ color: '#fff', backgroundColor: 'rgba(255,255,255,0.08)', cursor: 'pointer' }} />
                <Chip label="📐 /whiteboard trading" size="small" onClick={() => handleSendMessage('/whiteboard trading')} sx={{ color: '#fff', backgroundColor: 'rgba(255,255,255,0.08)', cursor: 'pointer' }} />
              </Box>

              {/* Input Box */}
              <Box sx={{ p: 1.5, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Ask in English or type /cmd (e.g. 'I have an interview with Stripe tomorrow')..."
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage(inputMessage);
                    }
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: 'rgba(255,255,255,0.05)',
                      color: '#fff',
                      borderRadius: 2,
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.15)' },
                      '&:hover fieldset': { borderColor: '#f59e0b' },
                      '&.Mui-focused fieldset': { borderColor: '#f59e0b' },
                    },
                  }}
                />
                <Button
                  variant="contained"
                  onClick={() => handleSendMessage(inputMessage)}
                  disabled={sending || !inputMessage.trim()}
                  sx={{
                    backgroundColor: '#f59e0b',
                    color: '#000',
                    fontWeight: 700,
                    borderRadius: 2,
                    px: 3,
                    '&:hover': { backgroundColor: '#d97706' },
                  }}
                >
                  <SendIcon />
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Right Column: 24x7 Syndicate Radar & Telegram Connect */}
          <Grid size={{ xs: 12, lg: 5 }}>
            <Stack spacing={2.5}>
              {/* Telegram Phone Connect Card */}
              <Paper
                sx={{
                  p: 2.5,
                  backgroundColor: 'rgba(10, 15, 29, 0.85)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  borderRadius: 2,
                }}
              >
                <Stack direction="row" spacing={1.5} alignItems="center" mb={1.5}>
                  <Box sx={{ p: 1, borderRadius: 1.5, backgroundColor: 'rgba(56, 189, 248, 0.15)' }}>
                    <QrCodeIcon sx={{ color: '#38bdf8' }} />
                  </Box>
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#38bdf8' }}>
                      Connect On Your Phone
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                      Free 24x7 pocket Consigliere on Telegram
                    </Typography>
                  </Box>
                </Stack>

                <Box sx={{ p: 1.5, backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: 1.5, border: '1px dashed rgba(56, 189, 248, 0.3)', mb: 2 }}>
                  <Typography variant="body2" sx={{ color: '#fff', fontFamily: 'monospace' }}>
                    1. Open Telegram app
                    <br />
                    2. Search for: <b>@GodfatherCopilotBot</b>
                    <br />
                    3. Tap <b>START</b> or send any command
                  </Typography>
                </Box>

                <Button
                  fullWidth
                  variant="outlined"
                  href="https://t.me/GodfatherCopilotBot"
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{
                    borderColor: '#38bdf8',
                    color: '#38bdf8',
                    textTransform: 'none',
                    fontWeight: 700,
                    borderRadius: 2,
                    '&:hover': { backgroundColor: 'rgba(56, 189, 248, 0.15)', borderColor: '#38bdf8' },
                  }}
                >
                  🚀 Open @GodfatherCopilotBot in Telegram
                </Button>
              </Paper>

              {/* Live 24x7 Radar Findings Feed */}
              <Paper
                sx={{
                  p: 2.5,
                  backgroundColor: 'rgba(10, 15, 29, 0.85)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 2,
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    🛰️ Active 24x7 Radar Intelligence
                  </Typography>
                  <Chip
                    label={`${status?.latest_findings?.length || 2} Opportunities Indexed`}
                    size="small"
                    sx={{ backgroundColor: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', fontSize: '0.65rem' }}
                  />
                </Stack>

                <Stack spacing={1.5}>
                  {(status?.latest_findings || [
                    { category: 'Frontier AI', title: 'New $50–$85/hr USD Python eval tasks on Alignerr', badge: 'USD Cashflow', rate: '$50–$85/hr' },
                    { category: 'Web3 Bounty', title: 'Solana Actions Indexer ($5,000 USDC) open on Superteam', badge: 'Crypto Reward', reward: '$5,000 USDC' },
                  ]).map((finding, idx) => (
                    <Box
                      key={idx}
                      sx={{
                        p: 1.5,
                        borderRadius: 1.5,
                        backgroundColor: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.06)',
                      }}
                    >
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Chip label={finding.category} size="small" sx={{ height: 20, fontSize: '0.65rem', backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#10b981' }} />
                        <Typography variant="caption" sx={{ color: '#38bdf8', fontWeight: 700 }}>
                          {finding.rate || finding.reward}
                        </Typography>
                      </Stack>
                      <Typography variant="body2" sx={{ color: '#fff', mt: 0.75, fontWeight: 500 }}>
                        {finding.title}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </Paper>

              {/* Broadcast Announcement Bar */}
              <Paper
                sx={{
                  p: 2,
                  backgroundColor: 'rgba(10, 15, 29, 0.85)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 2,
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'rgba(255,255,255,0.8)', mb: 1 }}>
                  📢 Push Intelligence Broadcast
                </Typography>
                <Stack direction="row" spacing={1}>
                  <TextField
                    fullWidth
                    size="small"
                    placeholder="Broadcast alert to all connected mobile sessions..."
                    value={broadcastText}
                    onChange={(e) => setBroadcastText(e.target.value)}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        backgroundColor: 'rgba(255,255,255,0.05)',
                        color: '#fff',
                        borderRadius: 1.5,
                        fontSize: '0.8rem',
                        '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                      },
                    }}
                  />
                  <Button
                    variant="contained"
                    size="small"
                    onClick={handleBroadcast}
                    disabled={!broadcastText.trim()}
                    sx={{
                      backgroundColor: broadcastSent ? '#10b981' : '#3b82f6',
                      color: '#fff',
                      fontWeight: 600,
                      borderRadius: 1.5,
                      textTransform: 'none',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {broadcastSent ? <CheckIcon fontSize="small" /> : <BroadcastIcon fontSize="small" />}
                  </Button>
                </Stack>
              </Paper>
            </Stack>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

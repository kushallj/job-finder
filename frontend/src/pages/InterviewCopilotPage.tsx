import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Stack,
  Chip,
  Button,
  TextField,
  Paper,
  CircularProgress,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Psychology as BrainIcon,
  FlashOn as FlashIcon,
  Shield as ShieldIcon,
  Add as AddIcon,
  Check as CheckIcon,
  PersonSearch as ProfilerIcon,
  AccountBalance as NegotiationIcon,
  LiveTv as HUDIcon,
  GraphicEq as MicWaveIcon,
  Build as BuildIcon,
  Sensors as RadarIcon,
  MonetizationOn as FrontierIcon,
  Description as MemoIcon,
  Handshake as HandshakeIcon,
  Public as WorldIcon,
  CurrencyBitcoin as Web3Icon,
  Architecture as WhiteboardIcon,
  Business as ExecIcon,
  Science as LabIcon,
  SmartToy as GodfatherIcon,
  Sync as SyncIcon,
  Search as SearchIcon,
  TableChart as SheetIcon,
} from '@mui/icons-material';

import { sidekickApi, type KnowledgeDocument, type SidekickStatus } from '../api/endpoints/sidekick';
import { InterviewSidekickHUD } from '../components/sidekick/InterviewSidekickHUD';
import { InterviewerProfilerCard } from '../components/profiler/InterviewerProfilerCard';
import { OfferArbitrageWarRoom } from '../components/negotiation/OfferArbitrageWarRoom';
import { VoiceCadenceCoachWidget } from '../components/cadence/VoiceCadenceCoachWidget';
import { ProofOfWorkFabricatorCard } from '../components/pow/ProofOfWorkFabricatorCard';
import { AntiGhostingSlaCard } from '../components/antighosting/AntiGhostingSlaCard';
import { FrontierAiRadarCard } from '../components/frontier/FrontierAiRadarCard';
import { ExecutiveDecisionMemoCard } from '../components/memo/ExecutiveDecisionMemoCard';
import { ReverseHeadhunterCard } from '../components/headhunter/ReverseHeadhunterCard';
import { GeoArbitrageCard } from '../components/geo/GeoArbitrageCard';
import { Web3BountyCard } from '../components/web3/Web3BountyCard';
import { SystemDesignWhiteboardCard } from '../components/whiteboard/SystemDesignWhiteboardCard';
import { ExecutiveOutreachCard } from '../components/outreach/ExecutiveOutreachCard';
import { LiveSandboxSimulatorCard } from '../components/sandbox/LiveSandboxSimulatorCard';
import { GodfatherBotCard } from '../components/telegram/GodfatherBotCard';

export const InterviewCopilotPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [status, setStatus] = useState<SidekickStatus | null>(null);
  const [bankDocs, setBankDocs] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);

  // Google Sheet Sync state
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatusMsg, setSyncStatusMsg] = useState<string | null>(null);
  const [sheetInputUrl, setSheetInputUrl] = useState('');
  const [showSyncDialog, setShowSyncDialog] = useState(false);

  // Search & Filter state for Knowledge Bank
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  // New question form state
  const [newTitle, setNewTitle] = useState('');
  const [newCategory, setNewCategory] = useState('Data Structures');
  const [newKeywords, setNewKeywords] = useState('');
  const [newBullets, setNewBullets] = useState('');
  const [addSuccess, setAddSuccess] = useState(false);

  const fetchBankAndStatus = async () => {
    try {
      const [s, b] = await Promise.all([
        sidekickApi.getStatus().catch(() => null),
        sidekickApi.getBank().catch(() => ({ total_documents: 0, documents: [] })),
      ]);
      if (s) setStatus(s);
      if (b) setBankDocs(b.documents);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBankAndStatus();
  }, []);

  const handleSyncGoogleSheet = async (overrideUrl?: string) => {
    setIsSyncing(true);
    setSyncStatusMsg(null);
    try {
      const targetUrl = overrideUrl || sheetInputUrl.trim() || undefined;
      const res = await sidekickApi.syncSheet(targetUrl);
      setSyncStatusMsg(
        `✅ Successfully synced ${res.ingested_from_sheet || res.total_questions} questions (${res.trie_keys_indexed || '8,000+'} Trie paths indexed)`
      );
      await fetchBankAndStatus();
      setTimeout(() => setSyncStatusMsg(null), 6000);
    } catch (err: any) {
      console.error('Failed to sync Google Sheet:', err);
      setSyncStatusMsg('❌ Sync failed. Make sure the Google Sheet link is public or shared.');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleAddQuestion = async () => {
    if (!newTitle.trim()) return;
    try {
      const keywords = newKeywords.split(',').map((k) => k.trim()).filter(Boolean);
      const bullets = newBullets.split('\n').map((b) => b.trim()).filter(Boolean);
      const id = newTitle.toLowerCase().replace(/\s+/g, '_');
      await sidekickApi.addCustomQuestion({
        id,
        title: newTitle,
        keywords: keywords.length > 0 ? keywords : [newTitle],
        category: newCategory,
        bullets: bullets.length > 0 ? bullets : ['Core pattern bullet point'],
      });
      setAddSuccess(true);
      setNewTitle('');
      setNewKeywords('');
      setNewBullets('');
      setTimeout(() => setAddSuccess(false), 3000);
      // Refresh bank
      const updated = await sidekickApi.getBank();
      setBankDocs(updated.documents);
    } catch (err) {
      console.error('Failed to add custom question:', err);
    }
  };

  // Filter bank documents
  const categories = ['All', ...Array.from(new Set(bankDocs.map((d) => d.category).filter(Boolean)))];
  const filteredDocs = bankDocs.filter((doc) => {
    const matchesCategory = selectedCategory === 'All' || doc.category === selectedCategory;
    const matchesSearch =
      !searchQuery.trim() ||
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.bullets.some((b) => b.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (doc.category && doc.category.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  return (
    <Box sx={{ width: '100%', maxWidth: '1200px', mx: 'auto', p: { xs: 2, md: 4 } }}>
      {/* Header Banner */}
      <Card
        sx={{
          mb: 4,
          borderRadius: '20px',
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 255, 163, 0.3)',
          boxShadow: '0 0 40px rgba(0, 255, 163, 0.15)',
        }}
      >
        <CardContent sx={{ p: { xs: 3, md: 4 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2}>
            <Box>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: '12px',
                    bgcolor: 'rgba(0, 255, 163, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #00FFA3',
                  }}
                >
                  <BrainIcon sx={{ color: '#00FFA3', fontSize: 26 }} />
                </Box>
                <Typography variant="h5" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #00FFA3, #00F0FF, #FFE600)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  Ghost Interview Copilot (Undetectable Sidekick)
                </Typography>
              </Stack>
              <Typography variant="body2" sx={{ color: '#94A3B8', maxWidth: '750px', lineHeight: 1.6 }}>
                Real-time interview teleprompter with OS screen-share invisibility (<code>NSWindowSharingNone</code> / <code>WDA_EXCLUDEFROMCAPTURE</code>), sub-microsecond in-memory Trie matcher, and hybrid RAG.
              </Typography>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip icon={<ShieldIcon />} label={status?.invisibility_supported ? "OS Invisibility: ACTIVE" : "Screen-Share Ready"} sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800 }} />
              <Chip icon={<FlashIcon />} label={`${status?.total_trie_indexed_keys || 12}+ Trie Keys (<5µs)`} sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800 }} />
            </Stack>

          </Stack>
        </CardContent>
      </Card>

      {/* 6 Strategic Intelligence Feature Tabs */}
      <Box sx={{ mb: 3, borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <Tabs
          value={activeTab}
          onChange={(_, val) => setActiveTab(val)}
          textColor="inherit"
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            '& .MuiTabs-indicator': { bgcolor: '#00FFA3', height: 3 },
            '& .MuiTab-root': {
              color: '#94A3B8',
              fontWeight: 800,
              textTransform: 'none',
              fontSize: '0.88rem',
              '&.Mui-selected': { color: '#00FFA3' },
            },
          }}
        >
          <Tab icon={<HUDIcon />} iconPosition="start" label="⚡ Live HUD & Knowledge Bank" />
          <Tab icon={<ProfilerIcon />} iconPosition="start" label="🧠 Interviewer Profiler" />
          <Tab icon={<NegotiationIcon />} iconPosition="start" label="⚖️ Offer Arbitrage" />
          <Tab icon={<MicWaveIcon />} iconPosition="start" label="🎙️ Voice Cadence HUD" />
          <Tab icon={<BuildIcon />} iconPosition="start" label="🛠️ Proof-of-Work Fabricator" />
          <Tab icon={<RadarIcon />} iconPosition="start" label="📡 Anti-Ghosting SLA Radar" />
          <Tab icon={<FrontierIcon />} iconPosition="start" label="🌐 Frontier AI Radar" />
          <Tab icon={<MemoIcon />} iconPosition="start" label="📑 Executive Decision Memo" />
          <Tab icon={<HandshakeIcon />} iconPosition="start" label="🤝 Reverse Headhunter" />
          <Tab icon={<WorldIcon />} iconPosition="start" label="🌍 Global Geo-Arbitrage" />
          <Tab icon={<Web3Icon />} iconPosition="start" label="⚡ Web3 & OSS Bounties" />
          <Tab icon={<WhiteboardIcon />} iconPosition="start" label="📐 System Design Whiteboard" />
          <Tab icon={<ExecIcon />} iconPosition="start" label="🎯 Executive Outreach" />
          <Tab icon={<LabIcon />} iconPosition="start" label="🧪 Live Architecture Sandbox" />
          <Tab icon={<GodfatherIcon />} iconPosition="start" label="👑 The Godfather Bot" />
        </Tabs>
      </Box>

      {/* Tab 0: Live Teleprompter HUD & Knowledge Bank */}
      {activeTab === 0 && (
        <>
          {/* Live Floating HUD Simulator */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC', mb: 2 }}>
              ⚡ Live Floating Teleprompter HUD (Preview & Test)
            </Typography>
            <InterviewSidekickHUD />
          </Box>

          {/* Google Sheet Sync Banner Card */}
          <Card
            sx={{
              mb: 3,
              borderRadius: '16px',
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(0, 240, 255, 0.3)',
              background: 'linear-gradient(135deg, rgba(13, 19, 31, 0.95), rgba(6, 9, 14, 0.98))',
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} spacing={2}>
                <Box>
                  <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 0.5 }}>
                    <SheetIcon sx={{ color: '#00F0FF', fontSize: 24 }} />
                    <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                      Google Sheet Question Bank Ingestion & Live Sync
                    </Typography>
                  </Stack>
                  <Typography variant="body2" sx={{ color: '#94A3B8', fontSize: '0.88rem' }}>
                    Sync 500+ curated technical questions (JavaScript, Node.js, React, Next.js, TypeScript, SQL, AWS, System Architecture, DSA, Behavioral STAR) directly into sub-microsecond Trie and AI Interviewer.
                  </Typography>
                </Box>

                <Stack direction="row" spacing={1.5} alignItems="center">
                  <Button
                    variant="contained"
                    disabled={isSyncing}
                    startIcon={isSyncing ? <CircularProgress size={16} color="inherit" /> : <SyncIcon />}
                    onClick={() => handleSyncGoogleSheet()}
                    sx={{
                      bgcolor: '#00FFA3',
                      color: '#06090E',
                      fontWeight: 900,
                      textTransform: 'none',
                      px: 2.5,
                      py: 1,
                      borderRadius: '10px',
                      '&:hover': { bgcolor: '#00E592' },
                    }}
                  >
                    {isSyncing ? 'Syncing 500+ Questions...' : '⚡ Sync Curated Google Sheet Bank'}
                  </Button>

                  <Button
                    variant="outlined"
                    onClick={() => setShowSyncDialog(!showSyncDialog)}
                    sx={{
                      borderColor: 'rgba(0, 240, 255, 0.4)',
                      color: '#00F0FF',
                      fontWeight: 800,
                      textTransform: 'none',
                      borderRadius: '10px',
                    }}
                  >
                    Custom URL
                  </Button>
                </Stack>
              </Stack>

              {/* Custom Google Sheet URL input */}
              {showSyncDialog && (
                <Box sx={{ mt: 2.5, pt: 2, borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <Typography variant="caption" sx={{ color: '#CBD5E1', display: 'block', mb: 1, fontWeight: 700 }}>
                    Enter Custom Google Sheets / CSV Export URL:
                  </Typography>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                    <TextField
                      fullWidth
                      size="small"
                      placeholder="https://docs.google.com/spreadsheets/d/1uJ8zyFyubiq_H50SxLXZ0HM0bviyOQ6m41ySlQhd0D8/edit?usp=sharing"
                      value={sheetInputUrl}
                      onChange={(e) => setSheetInputUrl(e.target.value)}
                      sx={{ bgcolor: '#06090E' }}
                    />
                    <Button
                      variant="contained"
                      disabled={isSyncing}
                      onClick={() => handleSyncGoogleSheet(sheetInputUrl)}
                      sx={{
                        bgcolor: '#00F0FF',
                        color: '#06090E',
                        fontWeight: 900,
                        textTransform: 'none',
                        minWidth: 140,
                      }}
                    >
                      Sync Link
                    </Button>
                  </Stack>
                </Box>
              )}

              {/* Live sync message feedback */}
              {syncStatusMsg && (
                <Box sx={{ mt: 2, p: 1.5, bgcolor: 'rgba(0, 255, 163, 0.1)', borderRadius: '8px', border: '1px solid #00FFA3' }}>
                  <Typography variant="body2" sx={{ color: '#00FFA3', fontWeight: 700 }}>
                    {syncStatusMsg}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* Two Column Layout: Knowledge Bank & Custom Question Ingestion */}
          <Grid container spacing={3}>
            {/* Left: Indexed Knowledge Bank */}
            <Grid size={{ xs: 12, md: 7 }}>
              <Card sx={{ height: '100%', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)', borderRadius: '16px' }}>
                <CardContent sx={{ p: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                      📚 Pre-Compiled Knowledge Bank ({filteredDocs.length} of {bankDocs.length} Questions)
                    </Typography>
                    <Chip
                      label={`${status?.total_trie_indexed_keys || bankDocs.length * 15}+ Trie Keys`}
                      size="small"
                      sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800 }}
                    />
                  </Stack>

                  {/* Search Bar */}
                  <TextField
                    fullWidth
                    size="small"
                    placeholder="Search 500+ questions, concepts, keywords, or bullets..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    InputProps={{
                      startAdornment: <SearchIcon sx={{ color: '#94A3B8', mr: 1, fontSize: 20 }} />,
                    }}
                    sx={{ mb: 2, bgcolor: '#06090E' }}
                  />

                  {/* Category Filter Chips */}
                  <Box sx={{ mb: 2.5, display: 'flex', gap: 1, overflowX: 'auto', pb: 1 }}>
                    {categories.slice(0, 12).map((cat) => {
                      const count = cat === 'All' ? bankDocs.length : bankDocs.filter((d) => d.category === cat).length;
                      const isSelected = selectedCategory === cat;
                      return (
                        <Chip
                          key={cat}
                          label={`${cat} (${count})`}
                          size="small"
                          clickable
                          onClick={() => setSelectedCategory(cat)}
                          sx={{
                            fontWeight: 800,
                            fontSize: '0.75rem',
                            bgcolor: isSelected ? 'rgba(0, 255, 163, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                            color: isSelected ? '#00FFA3' : '#94A3B8',
                            border: `1px solid ${isSelected ? '#00FFA3' : 'rgba(255, 255, 255, 0.1)'}`,
                            whiteSpace: 'nowrap',
                          }}
                        />
                      );
                    })}
                  </Box>

                  {loading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                      <CircularProgress size={24} sx={{ color: '#00FFA3' }} />
                    </Box>
                  ) : filteredDocs.length === 0 ? (
                    <Box sx={{ textAlign: 'center', py: 4, color: '#94A3B8' }}>
                      <Typography variant="body2">No questions found matching "{searchQuery}".</Typography>
                    </Box>
                  ) : (
                    <Stack spacing={1.5} sx={{ maxHeight: '460px', overflowY: 'auto', pr: 1 }}>
                      {filteredDocs.map((doc) => (
                        <Paper
                          key={doc.id}
                          variant="outlined"
                          sx={{
                            p: 2,
                            bgcolor: '#06090E',
                            borderRadius: '10px',
                            border: '1px solid rgba(255, 255, 255, 0.08)',
                            transition: 'border-color 0.2s',
                            '&:hover': { borderColor: 'rgba(0, 240, 255, 0.4)' },
                          }}
                        >
                          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1 }}>
                            <Typography variant="body2" sx={{ fontWeight: 800, color: '#00F0FF', flex: 1, pr: 1 }}>
                              {doc.title}
                            </Typography>
                            <Chip
                              label={doc.category}
                              size="small"
                              sx={{ bgcolor: 'rgba(255, 255, 255, 0.06)', color: '#94A3B8', fontSize: '0.65rem', height: 20 }}
                            />
                          </Stack>
                          <Stack spacing={0.5}>
                            {doc.bullets.map((bullet, bIdx) => (
                              <Typography key={bIdx} variant="caption" sx={{ color: '#CBD5E1', display: 'block', lineHeight: 1.4 }}>
                                • {bullet}
                              </Typography>
                            ))}
                          </Stack>
                        </Paper>
                      ))}
                    </Stack>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Right: Custom Question Ingestion */}
            <Grid size={{ xs: 12, md: 5 }}>
              <Card sx={{ height: '100%', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)', borderRadius: '16px' }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#FFE600', mb: 1.5 }}>
                    ➕ Add Custom Interview Question / STAR Story
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2, fontSize: '0.85rem' }}>
                    Indexes your personal projects or specific company questions into the sub-microsecond Trie and Inverted Index RAG.
                  </Typography>

                  <Stack spacing={2}>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      {['Data Structures', 'System Design', 'Behavioral STAR', 'Architecture', 'Node.js'].map((cat) => (
                        <Chip
                          key={cat}
                          label={cat}
                          size="small"
                          clickable
                          onClick={() => setNewCategory(cat)}
                          sx={{
                            fontWeight: 800,
                            bgcolor: newCategory === cat ? 'rgba(0, 255, 163, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                            color: newCategory === cat ? '#00FFA3' : '#94A3B8',
                            border: `1px solid ${newCategory === cat ? '#00FFA3' : 'rgba(255, 255, 255, 0.1)'}`,
                          }}
                        />
                      ))}
                    </Stack>
                    <TextField
                      fullWidth
                      size="small"
                      label="Question or Concept Title"
                      placeholder="e.g. Design Distributed Lock with Redis"
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      sx={{ bgcolor: '#06090E' }}
                    />

                    <TextField
                      fullWidth
                      size="small"
                      label="Keywords / Aliases (comma separated)"
                      placeholder="e.g. redlock, distributed lock, mutex"
                      value={newKeywords}
                      onChange={(e) => setNewKeywords(e.target.value)}
                      sx={{ bgcolor: '#06090E' }}
                    />
                    <TextField
                      fullWidth
                      multiline
                      rows={4}
                      size="small"
                      label="Teleprompter Bullets (one per line)"
                      placeholder="• Core: Redlock algorithm acquires lock across N independent masters&#10;• TTL: Lock validity time must exceed drift&#10;• Trade-off: Clock drift edge cases"
                      value={newBullets}
                      onChange={(e) => setNewBullets(e.target.value)}
                      sx={{ bgcolor: '#06090E' }}
                    />

                    <Button
                      variant="contained"
                      startIcon={addSuccess ? <CheckIcon /> : <AddIcon />}
                      onClick={handleAddQuestion}
                      sx={{
                        bgcolor: addSuccess ? '#00FFA3' : '#00F0FF',
                        color: '#06090E',
                        fontWeight: 900,
                        textTransform: 'none',
                        py: 1,
                      }}
                    >
                      {addSuccess ? 'Indexed Successfully!' : 'Index Into Trie & RAG'}
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}

      {/* Tab 1: Interviewer Cognitive Profiler */}
      {activeTab === 1 && <InterviewerProfilerCard />}

      {/* Tab 2: Multi-Offer Arbitrage & Negotiation War-Room */}
      {activeTab === 2 && <OfferArbitrageWarRoom />}

      {/* Tab 3: Voice Biomarker & Cadence Telemetry HUD */}
      {activeTab === 3 && <VoiceCadenceCoachWidget />}

      {/* Tab 4: Trojan-Horse Proof-of-Work Fabricator */}
      {activeTab === 4 && <ProofOfWorkFabricatorCard />}

      {/* Tab 5: Anti-Ghosting SLA & Recruiter Escalation Radar */}
      {activeTab === 5 && <AntiGhostingSlaCard />}

      {/* Tab 6: Frontier AI & RLHF Arbitrage Radar */}
      {activeTab === 6 && <FrontierAiRadarCard />}

      {/* Tab 7: Executive Decision Memo Closer */}
      {activeTab === 7 && <ExecutiveDecisionMemoCard />}

      {/* Tab 8: Reverse Headhunter Bounty Network */}
      {activeTab === 8 && <ReverseHeadhunterCard />}

      {/* Tab 9: Global Geo-Arbitrage & Cross-Border Engine */}
      {activeTab === 9 && <GeoArbitrageCard />}

      {/* Tab 10: Web3 & Open-Source Bounty Harvester */}
      {activeTab === 10 && <Web3BountyCard />}

      {/* Tab 11: System Design Whiteboard Co-Pilot */}
      {activeTab === 11 && <SystemDesignWhiteboardCard />}

      {/* Tab 12: Autonomous Executive Outbound Engine */}
      {activeTab === 12 && <ExecutiveOutreachCard />}

      {/* Tab 13: Live Architecture Interactive Sandbox */}
      {activeTab === 13 && <LiveSandboxSimulatorCard />}

      {/* Tab 14: The Godfather Telegram Bot & 24x7 Sovereign Autonomous Engine */}
      {activeTab === 14 && <GodfatherBotCard />}
    </Box>
  );
};


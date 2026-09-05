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

export const InterviewCopilotPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [status, setStatus] = useState<SidekickStatus | null>(null);
  const [bankDocs, setBankDocs] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);


  // New question form state
  const [newTitle, setNewTitle] = useState('');
  const [newCategory, setNewCategory] = useState('Data Structures');
  const [newKeywords, setNewKeywords] = useState('');
  const [newBullets, setNewBullets] = useState('');
  const [addSuccess, setAddSuccess] = useState(false);

  useEffect(() => {
    Promise.all([
      sidekickApi.getStatus().catch(() => null),
      sidekickApi.getBank().catch(() => ({ total_documents: 0, documents: [] })),
    ]).then(([s, b]) => {
      if (s) setStatus(s);
      if (b) setBankDocs(b.documents);
      setLoading(false);
    });
  }, []);

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

          {/* Two Column Layout: Knowledge Bank & Custom Question Ingestion */}
          <Grid container spacing={3}>
            {/* Left: Indexed Knowledge Bank */}
            <Grid size={{ xs: 12, md: 7 }}>
              <Card sx={{ height: '100%', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)', borderRadius: '16px' }}>
                <CardContent sx={{ p: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                      📚 Pre-Compiled Knowledge Bank ({bankDocs.length} Concepts Indexed)
                    </Typography>
                    <Chip label="In-Memory Radix" size="small" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800 }} />
                  </Stack>


              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <CircularProgress size={24} sx={{ color: '#00FFA3' }} />
                </Box>
              ) : (
                <Stack spacing={1.5} sx={{ maxHeight: '420px', overflowY: 'auto', pr: 1 }}>
                  {bankDocs.map((doc) => (
                    <Paper
                      key={doc.id}
                      variant="outlined"
                      sx={{
                        p: 2,
                        bgcolor: '#06090E',
                        borderRadius: '10px',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                      }}
                    >
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                        <Typography variant="body2" sx={{ fontWeight: 800, color: '#00F0FF' }}>
                          {doc.title}
                        </Typography>
                        <Chip label={doc.category} size="small" sx={{ bgcolor: 'rgba(255, 255, 255, 0.06)', color: '#94A3B8', fontSize: '0.65rem', height: 20 }} />
                      </Stack>
                      <Typography variant="caption" sx={{ color: '#CBD5E1', display: 'block', lineHeight: 1.4 }}>
                        {doc.bullets[0]}
                      </Typography>
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
                Indexes your personal projects or specific company questions into the sub-microsecond Trie.
              </Typography>

              <Stack spacing={2}>
                <Stack direction="row" spacing={1}>
                  {['Data Structures', 'System Design', 'Behavioral STAR'].map((cat) => (
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
    </Box>
  );
};


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
  Tabs,
  Tab,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Build as BuildIcon,
  Code as CodeIcon,
  BugReport as TestIcon,
  Description as DocIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  Speed as SpeedIcon,
  Storage as DockerIcon,
  Autorenew as CiIcon,
} from '@mui/icons-material';
import {
  sprint3Api,
  type PoWDeliverables,
  type PoWTemplate,
} from '../../api/endpoints/sprint3_api';

export const ProofOfWorkFabricatorCard: React.FC = () => {
  const [templates, setTemplates] = useState<PoWTemplate[]>([]);
  const [companyName, setCompanyName] = useState('Pine Labs');
  const [roleTitle, setRoleTitle] = useState('Senior Backend / Distributed Systems Engineer');
  const [selectedArchetype, setSelectedArchetype] = useState<string>('idempotent_webhook_engine');
  const [techStack, setTechStack] = useState('Python / FastAPI + Redis + PostgreSQL');
  const [loading, setLoading] = useState(false);
  const [deliverables, setDeliverables] = useState<PoWDeliverables | null>(null);
  const [activeCodeTab, setActiveCodeTab] = useState(0);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    sprint3Api.getTemplates().then((res) => {
      if (res && res.templates) {
        setTemplates(res.templates);
      }
    }).catch(console.error);
  }, []);

  const handleFabricate = async () => {
    if (!companyName.trim()) return;
    setLoading(true);
    try {
      const res = await sprint3Api.fabricatePoW({
        company_name: companyName,
        role_title: roleTitle,
        archetype_id: selectedArchetype,
        target_tech_stack: techStack,
      });
      setDeliverables(res);
      setActiveCodeTab(0);
    } catch (err) {
      console.error('PoW fabrication failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header Card */}
      <Card
        sx={{
          mb: 3,
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(255, 230, 0, 0.3)',
          borderRadius: '16px',
          boxShadow: '0 0 30px rgba(255, 230, 0, 0.1)',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2}>
            <Box>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Box
                  sx={{
                    width: 42,
                    height: 42,
                    borderRadius: '10px',
                    bgcolor: 'rgba(255, 230, 0, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #FFE600',
                  }}
                >
                  <BuildIcon sx={{ color: '#FFE600', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    🛠️ Trojan-Horse Proof-of-Work Fabricator (Agent 17)
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Synthesizes production micro-repositories, benchmarked unit tests, Docker, CI/CD, and high-impact PRs.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1}>
              <Chip label="Zero-Downtime Architecture" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, fontSize: '0.75rem' }} />
              <Chip label="Benchmarked P99" sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800, fontSize: '0.75rem' }} />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Generator Controls */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper sx={{ p: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#FFE600', mb: 2 }}>
              🎯 Target Entity & Role Configuration
            </Typography>

            <Stack spacing={2}>
              <TextField
                fullWidth
                size="small"
                label="Target Company Name"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Stack direction="row" spacing={0.8} flexWrap="wrap">
                {['Pine Labs', 'Cashfree', 'Ather Energy', 'CRED', 'Swiggy'].map((comp) => (
                  <Chip
                    key={comp}
                    label={comp}
                    size="small"
                    clickable
                    onClick={() => setCompanyName(comp)}
                    sx={{
                      fontWeight: 800,
                      fontSize: '0.7rem',
                      bgcolor: companyName === comp ? 'rgba(255, 230, 0, 0.2)' : 'rgba(255,255,255,0.05)',
                      color: companyName === comp ? '#FFE600' : '#94A3B8',
                      border: `1px solid ${companyName === comp ? '#FFE600' : 'transparent'}`,
                      mb: 0.5,
                    }}
                  />
                ))}
              </Stack>

              <TextField
                fullWidth
                size="small"
                label="Target Role Title"
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <TextField
                fullWidth
                size="small"
                label="Target Tech Stack"
                value={techStack}
                onChange={(e) => setTechStack(e.target.value)}
                sx={{ bgcolor: '#06090E' }}
              />

              <Button
                variant="contained"
                disabled={loading || !companyName.trim()}
                onClick={handleFabricate}
                startIcon={loading ? <CircularProgress size={18} sx={{ color: '#06090E' }} /> : <BuildIcon />}
                sx={{
                  bgcolor: '#FFE600',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  py: 1.2,
                  '&:hover': { bgcolor: '#E6CF00' },
                }}
              >
                {loading ? 'Synthesizing Micro-Repository...' : 'Fabricate Proof-of-Work Package'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* Archetype Selector */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#00F0FF', mb: 1.5 }}>
              ⚡ Select Architecture Archetype
            </Typography>
            <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 2 }}>
              Tailor the synthesized micro-repository to specific distributed systems and latency patterns.
            </Typography>

            <Stack spacing={1.5}>
              {templates.map((tpl) => (
                <Paper
                  key={tpl.id}
                  variant="outlined"
                  onClick={() => setSelectedArchetype(tpl.id)}
                  sx={{
                    p: 1.8,
                    bgcolor: selectedArchetype === tpl.id ? 'rgba(0, 240, 255, 0.08)' : '#06090E',
                    cursor: 'pointer',
                    borderRadius: '10px',
                    border: `1.5px solid ${selectedArchetype === tpl.id ? '#00F0FF' : 'rgba(255,255,255,0.06)'}`,
                    transition: 'all 0.15s',
                    '&:hover': { borderColor: '#00F0FF' },
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" sx={{ fontWeight: 800, color: selectedArchetype === tpl.id ? '#00F0FF' : '#F8FAFC' }}>
                      {tpl.title}
                    </Typography>
                    <Chip label={tpl.category} size="small" sx={{ bgcolor: 'rgba(255,255,255,0.06)', color: '#94A3B8', fontSize: '0.65rem' }} />
                  </Stack>
                  <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mt: 0.5 }}>
                    {tpl.description}
                  </Typography>
                </Paper>
              ))}
            </Stack>
          </Paper>
        </Grid>
      </Grid>

      {/* Synthesized Deliverables Output */}
      {deliverables && (
        <Card
          sx={{
            bgcolor: '#0D131F',
            border: '2px solid #00FFA3',
            borderRadius: '20px',
            boxShadow: '0 0 40px rgba(0, 255, 163, 0.15)',
          }}
        >
          <CardContent sx={{ p: { xs: 3, md: 4 } }}>
            {/* Header Strip */}
            <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2} sx={{ mb: 2.5 }}>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                  📦 {deliverables.project_title}
                </Typography>
                <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                  {deliverables.architecture_overview}
                </Typography>
              </Box>

              <Stack direction="row" spacing={1}>
                <Chip icon={<SpeedIcon />} label={`P99 Latency: -${deliverables.benchmark_metrics.p99_latency_reduction_percent}%`} sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800 }} />
                <Chip label={`${deliverables.benchmark_metrics.concurrency_rps_tested} RPS Tested`} sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800 }} />
              </Stack>
            </Stack>

            {/* Code Tabs */}
            <Box sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', mb: 2 }}>
              <Tabs
                value={activeCodeTab}
                onChange={(_, v) => setActiveCodeTab(v)}
                textColor="inherit"
                sx={{
                  '& .MuiTabs-indicator': { bgcolor: '#00FFA3', height: 3 },
                  '& .MuiTab-root': {
                    color: '#94A3B8',
                    fontWeight: 800,
                    textTransform: 'none',
                    fontSize: '0.85rem',
                    '&.Mui-selected': { color: '#00FFA3' },
                  },
                }}
              >
                <Tab icon={<DocIcon />} iconPosition="start" label="📝 PR Description (Markdown)" />
                <Tab icon={<CodeIcon />} iconPosition="start" label={`💻 App Code (${deliverables.app_code_filename})`} />
                <Tab icon={<TestIcon />} iconPosition="start" label={`🧪 Concurrency Tests (${deliverables.test_code_filename})`} />
                <Tab icon={<DockerIcon />} iconPosition="start" label="🐳 Dockerfile" />
                <Tab icon={<CiIcon />} iconPosition="start" label="🔄 GitHub Actions CI" />
              </Tabs>
            </Box>

            {/* Tab 0: PR Description */}
            {activeCodeTab === 0 && (
              <Paper sx={{ p: 2.5, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', position: 'relative' }}>
                <Button
                  size="small"
                  startIcon={copiedKey === 'pr' ? <CheckIcon /> : <CopyIcon />}
                  onClick={() => handleCopy(deliverables.pr_description_markdown, 'pr')}
                  sx={{ position: 'absolute', top: 12, right: 12, bgcolor: copiedKey === 'pr' ? '#00FFA3' : 'rgba(255,255,255,0.1)', color: copiedKey === 'pr' ? '#06090E' : '#F8FAFC', fontWeight: 800, textTransform: 'none' }}
                >
                  {copiedKey === 'pr' ? 'Copied!' : 'Copy PR Markdown'}
                </Button>
                <Typography component="pre" sx={{ color: '#CBD5E1', fontFamily: 'monospace', fontSize: '0.82rem', whiteSpace: 'pre-wrap', lineHeight: 1.5, maxHeight: '420px', overflowY: 'auto' }}>
                  {deliverables.pr_description_markdown}
                </Typography>
              </Paper>
            )}

            {/* Tab 1: App Code */}
            {activeCodeTab === 1 && (
              <Paper sx={{ p: 2.5, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', position: 'relative' }}>
                <Button
                  size="small"
                  startIcon={copiedKey === 'app' ? <CheckIcon /> : <CopyIcon />}
                  onClick={() => handleCopy(deliverables.app_code, 'app')}
                  sx={{ position: 'absolute', top: 12, right: 12, bgcolor: copiedKey === 'app' ? '#00FFA3' : 'rgba(255,255,255,0.1)', color: copiedKey === 'app' ? '#06090E' : '#F8FAFC', fontWeight: 800, textTransform: 'none' }}
                >
                  {copiedKey === 'app' ? 'Copied!' : 'Copy App Code'}
                </Button>
                <Typography component="pre" sx={{ color: '#00FFA3', fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap', lineHeight: 1.45, maxHeight: '420px', overflowY: 'auto' }}>
                  {deliverables.app_code}
                </Typography>
              </Paper>
            )}

            {/* Tab 2: Test Code */}
            {activeCodeTab === 2 && (
              <Paper sx={{ p: 2.5, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', position: 'relative' }}>
                <Button
                  size="small"
                  startIcon={copiedKey === 'test' ? <CheckIcon /> : <CopyIcon />}
                  onClick={() => handleCopy(deliverables.test_code, 'test')}
                  sx={{ position: 'absolute', top: 12, right: 12, bgcolor: copiedKey === 'test' ? '#00FFA3' : 'rgba(255,255,255,0.1)', color: copiedKey === 'test' ? '#06090E' : '#F8FAFC', fontWeight: 800, textTransform: 'none' }}
                >
                  {copiedKey === 'test' ? 'Copied!' : 'Copy Tests'}
                </Button>
                <Typography component="pre" sx={{ color: '#00F0FF', fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap', lineHeight: 1.45, maxHeight: '420px', overflowY: 'auto' }}>
                  {deliverables.test_code}
                </Typography>
              </Paper>
            )}

            {/* Tab 3: Dockerfile */}
            {activeCodeTab === 3 && (
              <Paper sx={{ p: 2.5, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', position: 'relative' }}>
                <Button
                  size="small"
                  startIcon={copiedKey === 'docker' ? <CheckIcon /> : <CopyIcon />}
                  onClick={() => handleCopy(deliverables.dockerfile, 'docker')}
                  sx={{ position: 'absolute', top: 12, right: 12, bgcolor: copiedKey === 'docker' ? '#00FFA3' : 'rgba(255,255,255,0.1)', color: copiedKey === 'docker' ? '#06090E' : '#F8FAFC', fontWeight: 800, textTransform: 'none' }}
                >
                  {copiedKey === 'docker' ? 'Copied!' : 'Copy Dockerfile'}
                </Button>
                <Typography component="pre" sx={{ color: '#FFE600', fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap', lineHeight: 1.45, maxHeight: '420px', overflowY: 'auto' }}>
                  {deliverables.dockerfile}
                </Typography>
              </Paper>
            )}

            {/* Tab 4: GitHub Actions CI */}
            {activeCodeTab === 4 && (
              <Paper sx={{ p: 2.5, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', position: 'relative' }}>
                <Button
                  size="small"
                  startIcon={copiedKey === 'ci' ? <CheckIcon /> : <CopyIcon />}
                  onClick={() => handleCopy(deliverables.github_actions_ci, 'ci')}
                  sx={{ position: 'absolute', top: 12, right: 12, bgcolor: copiedKey === 'ci' ? '#00FFA3' : 'rgba(255,255,255,0.1)', color: copiedKey === 'ci' ? '#06090E' : '#F8FAFC', fontWeight: 800, textTransform: 'none' }}
                >
                  {copiedKey === 'ci' ? 'Copied!' : 'Copy CI Workflow'}
                </Button>
                <Typography component="pre" sx={{ color: '#E2E8F0', fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap', lineHeight: 1.45, maxHeight: '420px', overflowY: 'auto' }}>
                  {deliverables.github_actions_ci}
                </Typography>
              </Paper>
            )}

            <Alert severity="info" sx={{ mt: 2.5, bgcolor: 'rgba(0, 240, 255, 0.1)', border: '1px solid rgba(0, 240, 255, 0.3)', color: '#CBD5E1' }}>
              💡 <strong>Candidate Take-Home Weapon:</strong> Send this GitHub repository link directly to the engineering hiring manager or attach as a post-interview debrief attachment. Demonstrates immediate production readiness.
            </Alert>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

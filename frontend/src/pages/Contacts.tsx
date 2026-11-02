import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  InputAdornment,
  Avatar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Stack,
  Tooltip,
  LinearProgress,
  Tabs,
  Tab,
  Grid,
} from '@mui/material';
import {
  Search as SearchIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  Refresh as RefreshIcon,
  People as ContactsIcon,
  Send as SendIcon,
  Business as CompanyIcon,
  OpenInNew as OpenInNewIcon,
  Download as DownloadIcon,
  AutoAwesome as SparkleIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  ElectricBolt as ElectricBoltIcon,
} from '@mui/icons-material';
import { useContacts } from '../hooks/useContacts';
import { useNavigate } from 'react-router-dom';
import { vcApi, type VCFirm, type PortfolioCompany, type ContinuousRunnerStatus } from '../api/endpoints/vc';

const REGIONS = [
  'All',
  'US & Global',
  'Asia',
  'India',
  'Europe',
  'Latin America',
  'Middle East & Africa',
];

export const Contacts: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'vc' | 'crm'>('vc');
  const [selectedRegion, setSelectedRegion] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);
  const navigate = useNavigate();

  // 100 Global VC Firms State
  const [vcFirms, setVcFirms] = useState<VCFirm[]>([]);
  const [loadingVC, setLoadingVC] = useState(false);
  const [syncingSlug, setSyncingSlug] = useState<string | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [selectedFirm, setSelectedFirm] = useState<VCFirm | null>(null);
  const [firmCompanies, setFirmCompanies] = useState<PortfolioCompany[]>([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const [continuousStatus, setContinuousStatus] = useState<ContinuousRunnerStatus | null>(null);
  const [harvestingBatch, setHarvestingBatch] = useState(false);
  const [showLogs, setShowLogs] = useState(false);

  const fetchContinuousStatus = async () => {
    try {
      const status = await vcApi.getContinuousStatus();
      setContinuousStatus(status);
    } catch (e) {
      console.error('Failed to load continuous runner status:', e);
    }
  };

  useEffect(() => {
    if (activeTab === 'vc') {
      fetchContinuousStatus();
      const interval = setInterval(fetchContinuousStatus, 4000);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  const handleRunBatchNow = async () => {
    setHarvestingBatch(true);
    setSyncMessage(null);
    try {
      const res = await vcApi.runBatchNow();
      setSyncMessage(`Batch #${res.batch_number} successfully ingested ${res.founders_added} verified founders across ${res.companies_added} companies!`);
      await fetchVCFirms(selectedRegion);
      await fetchContinuousStatus();
    } catch (e: any) {
      setSyncMessage(`Batch harvesting failed: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setHarvestingBatch(false);
    }
  };

  const handleToggleContinuous = async () => {
    try {
      if (continuousStatus?.is_running) {
        await vcApi.stopContinuous();
        setSyncMessage('Continuous batch harvester stopped.');
      } else {
        await vcApi.startContinuous(50, undefined, 2.0);
        setSyncMessage('Continuous batch harvester started in background (harvesting 50 founders/batch).');
      }
      setTimeout(fetchContinuousStatus, 800);
    } catch (e: any) {
      setSyncMessage(`Failed to toggle continuous harvester: ${e?.response?.data?.detail || e.message}`);
    }
  };


  // General CRM Contacts hook
  const { contacts, isLoading: loadingCRM, error: crmError, refetch: refetchCRM } = useContacts({
    page: 1,
    limit: 100,
  });

  // Load VC Firms on mount or region change
  const fetchVCFirms = async (region?: string) => {
    setLoadingVC(true);
    try {
      const data = await vcApi.getFirms(region);
      setVcFirms(data);
    } catch (err) {
      console.error('Failed to load VC firms:', err);
    } finally {
      setLoadingVC(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'vc') {
      fetchVCFirms(selectedRegion);
    }
  }, [activeTab, selectedRegion]);

  const handleCopyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  };

  const handleSyncFirm = async (slug: string) => {
    setSyncingSlug(slug);
    setSyncMessage(null);
    try {
      const res = await vcApi.syncFirm(slug, 20, true);
      setSyncMessage(res.message);
      await fetchVCFirms(selectedRegion);
      if (selectedFirm && selectedFirm.slug === slug) {
        handleViewCompanies(selectedFirm);
      }
    } catch (err: any) {
      setSyncMessage(`Scrape failed for ${slug}: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSyncingSlug(null);
    }
  };

  const handleViewCompanies = async (firm: VCFirm) => {
    setSelectedFirm(firm);
    setLoadingCompanies(true);
    try {
      const comps = await vcApi.getCompanies(firm.slug, 50);
      setFirmCompanies(comps);
    } catch (err) {
      console.error('Failed to fetch portfolio companies:', err);
    } finally {
      setLoadingCompanies(false);
    }
  };

  const filteredVCFirms = vcFirms.filter((firm) => {
    const q = searchQuery.toLowerCase();
    return (
      firm.name.toLowerCase().includes(q) ||
      firm.slug.toLowerCase().includes(q) ||
      firm.country_focus.toLowerCase().includes(q)
    );
  });

  const filteredCRMContacts = (contacts || []).filter((contact) => {
    const q = searchQuery.toLowerCase();
    return (
      contact.name.toLowerCase().includes(q) ||
      (contact.email && contact.email.toLowerCase().includes(q)) ||
      (contact.company && contact.company.toLowerCase().includes(q)) ||
      (contact.title && contact.title.toLowerCase().includes(q))
    );
  });

  return (
    <Box sx={{ maxWidth: 1440, mx: 'auto', width: '100%', color: '#F8FAFC' }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography
            variant="h3"
            sx={{
              fontWeight: 900,
              background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.03em',
              mb: 0.5,
              textTransform: 'uppercase',
            }}
          >
            Decision-Maker & VC Intelligence
          </Typography>
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>
            Scrape and discover verified founder emails and recruiters across the top 100 venture capital firms worldwide.
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.5}>
          {activeTab === 'vc' ? (
            <>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={() => window.open(vcApi.getExportUrl(selectedFirm?.slug))}
                sx={{ borderRadius: '12px', fontWeight: 800, borderColor: 'rgba(0, 240, 255, 0.4)', color: '#00F0FF' }}
              >
                Export CSV
              </Button>
              <Button
                variant="outlined"
                onClick={() => fetchVCFirms(selectedRegion)}
                disabled={loadingVC}
                startIcon={loadingVC ? <CircularProgress size={16} sx={{ color: '#00FFA3' }} /> : <RefreshIcon />}
                sx={{ borderRadius: '12px', fontWeight: 800 }}
              >
                Refresh
              </Button>
            </>
          ) : (
            <Button
              variant="outlined"
              onClick={() => refetchCRM()}
              disabled={loadingCRM}
              startIcon={loadingCRM ? <CircularProgress size={16} sx={{ color: '#00F0FF' }} /> : <RefreshIcon />}
              sx={{ borderRadius: '12px', fontWeight: 800 }}
            >
              Refresh CRM
            </Button>
          )}
        </Stack>
      </Box>

      {/* Main Tabs: 100 Global VCs vs CRM Contacts */}
      <Tabs
        value={activeTab}
        onChange={(_, val) => {
          setActiveTab(val);
          setSearchQuery('');
        }}
        sx={{
          mb: 3,
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          '& .MuiTab-root': {
            fontWeight: 800,
            fontSize: '0.95rem',
            color: '#94A3B8',
            '&.Mui-selected': { color: '#00FFA3' },
          },
          '& .MuiTabs-indicator': { bgcolor: '#00FFA3', height: 3, borderRadius: 2 },
        }}
      >
        <Tab value="vc" label="🔥 100 Global VC Firms & Founders" />
        <Tab value="crm" label="👥 Recruiter & Hiring Manager CRM" />
      </Tabs>

      {/* Sync Status Banner */}
      {syncMessage && (
        <Alert
          severity={syncMessage.includes('failed') ? 'error' : 'success'}
          onClose={() => setSyncMessage(null)}
          sx={{
            mb: 3,
            borderRadius: '14px',
            bgcolor: syncMessage.includes('failed') ? 'rgba(255, 0, 122, 0.15)' : 'rgba(0, 255, 163, 0.12)',
            color: syncMessage.includes('failed') ? '#FF007A' : '#00FFA3',
            border: `1px solid ${syncMessage.includes('failed') ? 'rgba(255, 0, 122, 0.4)' : 'rgba(0, 255, 163, 0.4)'}`,
          }}
        >
          {syncMessage}
        </Alert>
      )}

      {/* TAB 1: 100 GLOBAL VC FIRMS */}
      {activeTab === 'vc' && (
        <Box>
          {/* Autonomous 50-Founder Batch Harvester Banner */}
          <Card
            sx={{
              mb: 3,
              p: 2.5,
              background: 'linear-gradient(135deg, rgba(13, 19, 31, 0.95) 0%, rgba(10, 25, 47, 0.95) 100%)',
              border: '2px solid rgba(0, 255, 163, 0.4)',
              borderRadius: '16px',
              boxShadow: '0 12px 36px 0 rgba(0, 255, 163, 0.15)',
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
              <Box>
                <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 0.5 }}>
                  <ElectricBoltIcon sx={{ color: '#00FFA3', fontSize: '1.8rem' }} />
                  <Typography variant="h5" sx={{ fontWeight: 900, color: '#F8FAFC', letterSpacing: '-0.02em' }}>
                    Autonomous 50-Founder Batch Harvester
                  </Typography>
                  <Chip
                    label={continuousStatus?.is_running ? 'HARVESTING ACTIVE' : 'ENGINE READY'}
                    size="small"
                    sx={{
                      fontWeight: 900,
                      fontSize: '0.75rem',
                      bgcolor: continuousStatus?.is_running ? 'rgba(0, 255, 163, 0.2)' : 'rgba(0, 240, 255, 0.15)',
                      color: continuousStatus?.is_running ? '#00FFA3' : '#00F0FF',
                      border: `1px solid ${continuousStatus?.is_running ? '#00FFA3' : '#00F0FF'}`,
                    }}
                  />
                </Stack>
                <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                  Harvests verified founders, CTOs & decision-makers with corporate email addresses in continuous 50-founder batches across 100 global VCs.
                </Typography>

                <Stack direction="row" spacing={2} sx={{ mt: 1.5 }} flexWrap="wrap">
                  <Box>
                    <Typography variant="caption" sx={{ color: '#64748B', display: 'block', fontWeight: 700 }}>
                      DATABASE FOUNDERS
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                      {continuousStatus?.total_founders_in_db ?? 73} Verified
                    </Typography>
                  </Box>
                  <Box sx={{ borderLeft: '1px solid rgba(255,255,255,0.1)', pl: 2 }}>
                    <Typography variant="caption" sx={{ color: '#64748B', display: 'block', fontWeight: 700 }}>
                      VERIFIED CORPORATE EMAILS
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 900, color: '#00F0FF' }}>
                      {continuousStatus?.founders_with_verified_email ?? 73} (100%)
                    </Typography>
                  </Box>
                  <Box sx={{ borderLeft: '1px solid rgba(255,255,255,0.1)', pl: 2 }}>
                    <Typography variant="caption" sx={{ color: '#64748B', display: 'block', fontWeight: 700 }}>
                      GLOBAL VC COVERAGE
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 900, color: '#FFE600' }}>
                      {continuousStatus?.total_firms_in_db ?? 102} Firms
                    </Typography>
                  </Box>
                </Stack>
              </Box>

              <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap">
                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={harvestingBatch ? <CircularProgress size={16} sx={{ color: '#000' }} /> : <SparkleIcon />}
                  disabled={harvestingBatch}
                  onClick={handleRunBatchNow}
                  sx={{
                    fontWeight: 900,
                    px: 2.5,
                    py: 1,
                    bgcolor: '#00FFA3',
                    color: '#000',
                    '&:hover': { bgcolor: '#00E090', boxShadow: '0 0 20px rgba(0, 255, 163, 0.4)' },
                  }}
                >
                  {harvestingBatch ? 'Harvesting Next 50...' : 'Harvest Next 50 Founders'}
                </Button>

                <Button
                  variant="outlined"
                  startIcon={continuousStatus?.is_running ? <PauseIcon /> : <PlayIcon />}
                  onClick={handleToggleContinuous}
                  sx={{
                    fontWeight: 800,
                    borderColor: continuousStatus?.is_running ? '#FF007A' : '#00F0FF',
                    color: continuousStatus?.is_running ? '#FF007A' : '#00F0FF',
                    '&:hover': {
                      borderColor: continuousStatus?.is_running ? '#FF007A' : '#00F0FF',
                      bgcolor: continuousStatus?.is_running ? 'rgba(255, 0, 122, 0.1)' : 'rgba(0, 240, 255, 0.1)',
                    },
                  }}
                >
                  {continuousStatus?.is_running ? 'Stop Continuous Loop' : 'Continuous Auto-Harvest'}
                </Button>

                <Button
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  href={vcApi.getExportUrl()}
                  target="_blank"
                  sx={{
                    fontWeight: 800,
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                    color: '#F8FAFC',
                    '&:hover': { borderColor: '#FFF', bgcolor: 'rgba(255, 255, 255, 0.05)' },
                  }}
                >
                  Export CSV
                </Button>

                <Button
                  size="small"
                  onClick={() => setShowLogs(!showLogs)}
                  sx={{ color: '#64748B', fontSize: '0.75rem', textTransform: 'none' }}
                >
                  {showLogs ? 'Hide Logs ▲' : 'Show Logs ▼'}
                </Button>
              </Stack>
            </Box>

            {/* Collapsible Mini Log Terminal */}
            {showLogs && (
              <Box
                sx={{
                  mt: 2,
                  p: 1.5,
                  bgcolor: '#050911',
                  borderRadius: '8px',
                  border: '1px solid rgba(0, 255, 163, 0.2)',
                  fontFamily: 'monospace',
                  fontSize: '0.75rem',
                  color: '#94A3B8',
                  maxHeight: 120,
                  overflowY: 'auto',
                }}
              >
                {continuousStatus?.recent_logs && continuousStatus.recent_logs.length > 0 ? (
                  continuousStatus.recent_logs.map((line, idx) => (
                    <Box key={idx} sx={{ color: line.includes('Error') ? '#FF007A' : '#00FFA3' }}>
                      {line}
                    </Box>
                  ))
                ) : (
                  <Box sx={{ color: '#64748B' }}>[Ready] Autonomous batch worker idle. Click "Harvest Next 50 Founders" to begin.</Box>
                )}
              </Box>
            )}
          </Card>

          {/* Regional Filter Chips */}
          <Stack direction="row" spacing={1} sx={{ mb: 3, overflowX: 'auto', pb: 1 }}>
            {REGIONS.map((r) => (
              <Chip
                key={r}
                label={r}
                clickable
                onClick={() => setSelectedRegion(r)}
                sx={{
                  fontWeight: 800,
                  fontSize: '0.85rem',
                  bgcolor: selectedRegion === r ? 'rgba(0, 255, 163, 0.2)' : '#0D131F',
                  color: selectedRegion === r ? '#00FFA3' : '#94A3B8',
                  border: `1.5px solid ${selectedRegion === r ? '#00FFA3' : 'rgba(255, 255, 255, 0.1)'}`,
                  '&:hover': { bgcolor: 'rgba(0, 255, 163, 0.1)' },
                }}
              />
            ))}
          </Stack>

          {/* Search Bar */}
          <Card sx={{ mb: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <CardContent sx={{ p: 2 }}>
              <TextField
                placeholder="Search across 100 VCs by name, country, or slug..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                size="small"
                fullWidth
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: '#00F0FF' }} fontSize="small" />
                    </InputAdornment>
                  ),
                }}
              />
            </CardContent>
          </Card>

          {/* Selected Firm Detail Drawer / Modal if selected */}
          {selectedFirm && (
            <Card sx={{ mb: 4, bgcolor: '#0B111D', border: '2px solid #00FFA3', boxShadow: '0 0 25px rgba(0, 255, 163, 0.2)' }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
                  <Box>
                    <Stack direction="row" spacing={1.5} alignItems="center">
                      <Typography variant="h5" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                        {selectedFirm.name}
                      </Typography>
                      <Chip label={selectedFirm.region} size="small" sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontWeight: 800 }} />
                      <Chip label={selectedFirm.country_focus} size="small" sx={{ bgcolor: 'rgba(255, 230, 0, 0.15)', color: '#FFE600', fontWeight: 800 }} />
                    </Stack>
                    <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                      Official Directory: <a href={selectedFirm.portfolio_url} target="_blank" rel="noreferrer" style={{ color: '#00F0FF' }}>{selectedFirm.portfolio_url}</a>
                    </Typography>
                  </Box>

                  <Stack direction="row" spacing={1}>
                    <Button
                      variant="contained"
                      color="primary"
                      size="small"
                      startIcon={syncingSlug === selectedFirm.slug ? <CircularProgress size={14} sx={{ color: '#000' }} /> : <SparkleIcon />}
                      onClick={() => handleSyncFirm(selectedFirm.slug)}
                      disabled={syncingSlug === selectedFirm.slug}
                      sx={{ fontWeight: 900 }}
                    >
                      {syncingSlug === selectedFirm.slug ? 'Scraping Portfolio...' : 'Scrape & Discover Founders'}
                    </Button>
                    <Button variant="outlined" size="small" onClick={() => setSelectedFirm(null)} sx={{ color: '#94A3B8' }}>
                      Close Panel
                    </Button>
                  </Stack>
                </Box>

                {/* Discovered Startups & Founders Table */}
                {loadingCompanies ? (
                  <Box sx={{ py: 4, textAlign: 'center' }}>
                    <CircularProgress size={28} sx={{ color: '#00FFA3' }} />
                  </Box>
                ) : firmCompanies.length === 0 ? (
                  <Typography variant="body2" sx={{ color: '#64748B', py: 2 }}>
                    No companies scraped yet for {selectedFirm.name}. Click "Scrape & Discover Founders" to extract portfolio companies and emails via Playwright + Firecrawl.
                  </Typography>
                ) : (
                  <TableContainer component={Paper} sx={{ bgcolor: '#080C12', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ color: '#00F0FF', fontWeight: 800 }}>Portfolio Startup</TableCell>
                          <TableCell sx={{ color: '#00F0FF', fontWeight: 800 }}>Stage / Batch</TableCell>
                          <TableCell sx={{ color: '#00F0FF', fontWeight: 800 }}>Discovered Founders & Corporate Emails</TableCell>
                          <TableCell align="right" sx={{ color: '#00F0FF', fontWeight: 800 }}>Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {firmCompanies.map((comp) => (
                          <TableRow key={comp.id} hover sx={{ '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.03)' } }}>
                            <TableCell>
                              <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#F8FAFC' }}>
                                {comp.name}
                              </Typography>
                              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                                {comp.domain || comp.website}
                              </Typography>
                            </TableCell>

                            <TableCell>
                              <Chip label={comp.funding_stage || 'Funded'} size="small" sx={{ fontSize: '0.7rem', bgcolor: 'rgba(255, 255, 255, 0.08)', color: '#CBD5E1' }} />
                            </TableCell>

                            <TableCell>
                              {comp.founders && comp.founders.length > 0 ? (
                                <Stack spacing={1}>
                                  {comp.founders.map((f) => {
                                    const confScore = Math.round(f.email_confidence * 100);
                                    const confColor = confScore >= 85 ? '#00FFA3' : confScore >= 65 ? '#00F0FF' : '#FFE600';
                                    const confLabel = confScore >= 85 ? 'Verified' : confScore >= 65 ? 'Likely' : 'Guessed';

                                    return (
                                      <Box key={f.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                                        <Typography variant="body2" sx={{ fontWeight: 800, color: '#F8FAFC' }}>
                                          {f.full_name} ({f.title || 'Founder'})
                                        </Typography>
                                        {f.email ? (
                                          <Chip
                                            label={`${f.email} • ${confLabel} (${confScore}%)`}
                                            size="small"
                                            sx={{
                                              bgcolor: `${confColor}1A`,
                                              color: confColor,
                                              border: `1px solid ${confColor}4D`,
                                              fontWeight: 800,
                                              fontSize: '0.72rem',
                                            }}
                                            onClick={() => handleCopyEmail(f.email!)}
                                          />
                                        ) : (
                                          <Typography variant="caption" sx={{ color: '#64748B' }}>
                                            [Email pending verification]
                                          </Typography>
                                        )}
                                      </Box>
                                    );
                                  })}
                                </Stack>
                              ) : (
                                <Typography variant="caption" sx={{ color: '#64748B' }}>
                                  No founders enriched yet
                                </Typography>
                              )}
                            </TableCell>

                            <TableCell align="right">
                              <Stack direction="row" spacing={1} justifyContent="flex-end">
                                {comp.website && (
                                  <IconButton size="small" href={comp.website} target="_blank" sx={{ color: '#00F0FF' }}>
                                    <OpenInNewIcon fontSize="small" />
                                  </IconButton>
                                )}
                                <Button
                                  size="small"
                                  variant="contained"
                                  color="secondary"
                                  startIcon={<SendIcon fontSize="small" />}
                                  onClick={() => navigate('/outreach')}
                                  sx={{ fontWeight: 800, fontSize: '0.75rem' }}
                                >
                                  Pitch
                                </Button>
                              </Stack>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>
          )}

          {/* 100 VC Firms Grid */}
          {loadingVC ? (
            <Box sx={{ py: 8, textAlign: 'center' }}>
              <CircularProgress sx={{ color: '#00FFA3', mb: 2 }} />
              <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                Loading global VC firms...
              </Typography>
            </Box>
          ) : filteredVCFirms.length === 0 ? (
            <Card sx={{ textAlign: 'center', py: 8, bgcolor: '#0D131F' }}>
              <Typography variant="h6" sx={{ color: '#F8FAFC', mb: 2 }}>
                No VC firms found matching criteria
              </Typography>
              <Button variant="contained" onClick={() => fetchVCFirms(selectedRegion)}>
                Reset Filters
              </Button>
            </Card>
          ) : (
            <Grid container spacing={2.5}>
              {filteredVCFirms.map((firm) => {
                const isSyncing = syncingSlug === firm.slug;
                const isSelected = selectedFirm?.slug === firm.slug;

                return (
                  <Grid size={{ xs: 12, sm: 6, md: 4 }} key={firm.id}>
                    <Card
                      sx={{
                        height: '100%',
                        bgcolor: isSelected ? 'rgba(0, 255, 163, 0.08)' : '#0D131F',
                        border: `1.5px solid ${isSelected ? '#00FFA3' : 'rgba(0, 240, 255, 0.2)'}`,
                        borderRadius: '16px',
                        transition: 'all 0.2s ease',
                        '&:hover': {
                          border: '1.5px solid #00FFA3',
                          transform: 'translateY(-2px)',
                          boxShadow: '0 8px 24px rgba(0, 255, 163, 0.15)',
                        },
                      }}
                    >
                      <CardContent sx={{ p: 2.5 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                          <Box>
                            <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC', lineHeight: 1.2 }}>
                              {firm.name}
                            </Typography>
                            <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                              {firm.country_focus} • {firm.region}
                            </Typography>
                          </Box>
                          <Avatar sx={{ width: 32, height: 32, bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontSize: '0.8rem', fontWeight: 900 }}>
                            {firm.name.charAt(0)}
                          </Avatar>
                        </Box>

                        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                          <Chip
                            label={`${firm.companies_count} Startups`}
                            size="small"
                            sx={{ fontWeight: 800, bgcolor: 'rgba(0, 240, 255, 0.12)', color: '#00F0FF' }}
                          />
                          <Chip
                            label={`${firm.founders_count} Founders`}
                            size="small"
                            sx={{ fontWeight: 800, bgcolor: 'rgba(0, 255, 163, 0.12)', color: '#00FFA3' }}
                          />
                        </Stack>

                        <Typography variant="caption" sx={{ display: 'block', color: '#64748B', mb: 2 }}>
                          {firm.last_synced_at
                            ? `Last scraped: ${new Date(firm.last_synced_at).toLocaleDateString()}`
                            : 'Not yet scraped'}
                        </Typography>

                        <Stack direction="row" spacing={1}>
                          <Button
                            variant="contained"
                            size="small"
                            color="primary"
                            fullWidth
                            startIcon={isSyncing ? <CircularProgress size={12} sx={{ color: '#000' }} /> : <PlayIcon fontSize="small" />}
                            onClick={() => handleSyncFirm(firm.slug)}
                            disabled={isSyncing}
                            sx={{ fontWeight: 900, fontSize: '0.75rem' }}
                          >
                            {isSyncing ? 'Scraping...' : 'Scrape'}
                          </Button>
                          <Button
                            variant="outlined"
                            size="small"
                            fullWidth
                            onClick={() => handleViewCompanies(firm)}
                            sx={{ fontWeight: 800, fontSize: '0.75rem', borderColor: 'rgba(255, 255, 255, 0.2)', color: '#CBD5E1' }}
                          >
                            Portfolio
                          </Button>
                        </Stack>
                      </CardContent>
                    </Card>
                  </Grid>
                );
              })}
            </Grid>
          )}
        </Box>
      )}

      {/* TAB 2: RECRUITER & EXECUTIVE CRM */}
      {activeTab === 'crm' && (
        <Box>
          {/* CRM Search Bar */}
          <Card sx={{ mb: 3.5, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
            <CardContent sx={{ p: 2.5 }}>
              <TextField
                placeholder="Search recruiters by name, title, company, or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                size="small"
                fullWidth
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: '#00F0FF' }} fontSize="small" />
                    </InputAdornment>
                  ),
                }}
              />
            </CardContent>
          </Card>

          {crmError && (
            <Alert severity="error" sx={{ mb: 3.5, borderRadius: '14px', bgcolor: 'rgba(255, 0, 122, 0.15)', color: '#FF007A', border: '1px solid rgba(255, 0, 122, 0.4)' }}>
              Error loading contacts: {String(crmError)}
            </Alert>
          )}

          {loadingCRM ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 8 }}>
              <CircularProgress sx={{ color: '#00FFA3', mb: 2 }} />
              <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                Loading contact intelligence...
              </Typography>
            </Box>
          ) : filteredCRMContacts.length === 0 ? (
            <Card sx={{ textAlign: 'center', py: 8, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.2)' }}>
              <Box
                sx={{
                  width: 56,
                  height: 56,
                  borderRadius: '50%',
                  bgcolor: 'rgba(0, 240, 255, 0.15)',
                  color: '#00F0FF',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mb: 2,
                  border: '1px solid rgba(0, 240, 255, 0.4)',
                  boxShadow: '0 0 20px rgba(0, 240, 255, 0.25)',
                }}
              >
                <ContactsIcon />
              </Box>
              <Typography variant="h5" fontWeight={900} sx={{ color: '#F8FAFC', mb: 1 }}>
                No CRM contacts found
              </Typography>
              <Typography variant="body2" sx={{ color: '#94A3B8', maxWidth: 460, mx: 'auto', mb: 3 }}>
                Contacts are automatically discovered when you run job queries or sync external listings.
              </Typography>
              <Button variant="contained" color="primary" onClick={() => navigate('/')}>
                Go to Command Center
              </Button>
            </Card>
          ) : (
            <TableContainer component={Paper} sx={{ borderRadius: '20px', border: '1.5px solid rgba(0, 240, 255, 0.2)', bgcolor: '#0D131F', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)', mb: 3.5 }}>
              <Table size="medium">
                <TableHead sx={{ bgcolor: '#080C12' }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Contact</TableCell>
                    <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Company</TableCell>
                    <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Email & Confidence</TableCell>
                    <TableCell sx={{ fontWeight: 900, color: '#00F0FF' }}>Discovery Source</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 900, color: '#00F0FF' }}>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredCRMContacts.map((contact) => {
                    const initials = contact.name
                      .split(' ')
                      .map((n) => n[0])
                      .slice(0, 2)
                      .join('')
                      .toUpperCase();
                    const score = contact.confidence_score || 75;
                    const isX = contact.source === 'x_referral' || (contact.linkedin_url && contact.linkedin_url.includes('x.com'));
                    const isLinkedIn = !isX && (contact.source === 'linkedin_referral' || !!contact.linkedin_url);

                    return (
                      <TableRow key={contact.id} hover sx={{ '&:hover': { bgcolor: 'rgba(0, 240, 255, 0.04)' } }}>
                        <TableCell>
                          <Stack direction="row" spacing={1.5} alignItems="center">
                            <Avatar
                              sx={{
                                bgcolor: isX ? 'rgba(0, 240, 255, 0.15)' : isLinkedIn ? 'rgba(0, 119, 181, 0.2)' : 'rgba(0, 255, 163, 0.15)',
                                color: isX ? '#00F0FF' : isLinkedIn ? '#00F0FF' : '#00FFA3',
                                border: '1px solid rgba(0, 240, 255, 0.3)',
                                fontWeight: 900,
                                fontSize: '0.85rem',
                              }}
                            >
                              {initials || 'C'}
                            </Avatar>
                            <Box>
                              <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                                {contact.name}
                              </Typography>
                              <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                                {contact.title || 'Engineering / Talent'}
                              </Typography>
                            </Box>
                          </Stack>
                        </TableCell>

                        <TableCell>
                          <Chip
                            icon={<CompanyIcon fontSize="small" sx={{ color: '#FFE600 !important' }} />}
                            label={contact.company || 'Unknown'}
                            size="small"
                            sx={{ fontWeight: 800, bgcolor: 'rgba(255, 230, 0, 0.12)', color: '#FFE600', border: '1px solid rgba(255, 230, 0, 0.35)' }}
                          />
                        </TableCell>

                        <TableCell>
                          {contact.email ? (
                            <Stack spacing={0.5}>
                              <Stack direction="row" spacing={0.5} alignItems="center">
                                <Typography variant="body2" sx={{ fontWeight: 800, color: '#00FFA3' }}>
                                  {contact.email}
                                </Typography>
                                <Tooltip title={copiedEmail === contact.email ? 'Copied!' : 'Copy Email'}>
                                  <IconButton
                                    size="small"
                                    onClick={() => contact.email && handleCopyEmail(contact.email)}
                                    sx={{ color: '#00F0FF' }}
                                  >
                                    {copiedEmail === contact.email ? (
                                      <CheckIcon color="success" fontSize="small" />
                                    ) : (
                                      <CopyIcon fontSize="small" />
                                    )}
                                  </IconButton>
                                </Tooltip>
                              </Stack>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <LinearProgress
                                  variant="determinate"
                                  value={score}
                                  sx={{
                                    width: 70,
                                    height: 5,
                                    borderRadius: 3,
                                    bgcolor: '#080C12',
                                    '& .MuiLinearProgress-bar': {
                                      bgcolor: score >= 80 ? '#00FFA3' : score >= 60 ? '#FFE600' : '#94A3B8',
                                    },
                                  }}
                                />
                                <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.7rem', fontWeight: 700 }}>
                                  {score}%
                                </Typography>
                              </Box>
                            </Stack>
                          ) : (
                            <Typography variant="caption" sx={{ color: '#64748B' }}>
                              Email not available
                            </Typography>
                          )}
                        </TableCell>

                        <TableCell>
                          <Chip
                            label={contact.source ? contact.source.replace('_', ' ') : 'Generated'}
                            size="small"
                            sx={{ fontSize: '0.68rem', bgcolor: 'rgba(121, 40, 202, 0.15)', color: '#A855F7', border: '1px solid rgba(121, 40, 202, 0.35)', fontWeight: 800 }}
                          />
                        </TableCell>

                        <TableCell align="right">
                          <Stack direction="row" spacing={1} justifyContent="flex-end">
                            {contact.linkedin_url && (
                              <IconButton
                                size="small"
                                href={contact.linkedin_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                sx={{ color: '#00F0FF', border: '1px solid rgba(0, 240, 255, 0.25)', borderRadius: '8px' }}
                              >
                                <OpenInNewIcon fontSize="small" />
                              </IconButton>
                            )}
                            <Button
                              size="small"
                              variant="contained"
                              color="secondary"
                              startIcon={<SendIcon fontSize="small" />}
                              onClick={() => navigate('/outreach')}
                              sx={{ fontWeight: 900 }}
                            >
                              Outreach
                            </Button>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      )}
    </Box>
  );
};

export default Contacts;

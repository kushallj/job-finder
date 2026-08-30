import React, { useState } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Chip,
  Stack,
  Paper,
  IconButton,
  CircularProgress,
  Tabs,
  Tab,
  Grid,
} from '@mui/material';
import {
  Close as CloseIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  AutoAwesome as SparkleIcon,
  Build as BuildIcon,
} from '@mui/icons-material';
import { skillBridgeApi } from '../../api';
import type { SkillBridgeProjectResponse } from '../../api/endpoints/skill_bridge';


interface ProofOfWorkModalProps {
  open: boolean;
  onClose: () => void;
  company: string;
  roleTitle: string;
  jobDescription?: string;
}

export const ProofOfWorkModal: React.FC<ProofOfWorkModalProps> = ({
  open,
  onClose,
  company,
  roleTitle,
  jobDescription,
}) => {
  const [projectData, setProjectData] = useState<SkillBridgeProjectResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeFileTab, setActiveFileTab] = useState(0);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const generateProject = async () => {
    setLoading(true);
    try {
      const res = await skillBridgeApi.generateProject({
        company,
        role_title: roleTitle,
        job_description: jobDescription,
      });
      setProjectData(res.data);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (open && !projectData) {
      generateProject();
    }
  }, [open, company, roleTitle]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(text);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const fileNames = projectData ? Object.keys(projectData.project_spec.starter_code_files) : [];
  const currentFileName = fileNames[activeFileTab] || 'main.py';
  const currentCode = projectData?.project_spec.starter_code_files[currentFileName] || '';

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ fontWeight: 800, color: '#0F172A', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <BuildIcon sx={{ color: '#F59E0B' }} />
          <span>🛠️ 24h Proof-of-Work Micro-Project Generator — {company}</span>
        </Stack>
        <IconButton size="small" onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ p: 3, bgcolor: '#F8FAFC' }}>
        {loading || !projectData ? (
          <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={6}>
            <CircularProgress size={36} sx={{ mb: 2 }} />
            <Typography variant="subtitle2" color="text.secondary">
              Analyzing skill requirements & synthesizing production micro-project for {company}…
            </Typography>
          </Box>
        ) : (
          <Box>
            {/* Skill Gap & Match Banner */}
            <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3, bgcolor: '#FFFFFF', mb: 3 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 12, sm: 8 }}>
                  <Typography variant="h6" fontWeight={800} color="#0F172A">
                    {projectData.project_spec.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {projectData.project_spec.tagline}
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
                    <Chip label={`⏱️ Estimate: ${projectData.project_spec.duration_estimate}`} size="small" sx={{ fontWeight: 700 }} />
                    <Chip
                      label={`Skills Proven: ${projectData.project_spec.skills_proven.join(', ')}`}
                      size="small"
                      color="primary"
                      sx={{ fontWeight: 700 }}
                    />
                  </Stack>
                </Grid>

                <Grid size={{ xs: 12, sm: 4 }}>
                  <Box textAlign={{ xs: 'left', sm: 'right' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={700}>SKILL MATCH INDEX</Typography>
                    <Typography variant="h4" fontWeight={900} color="#16A34A">
                      {projectData.gap_analysis.match_percentage}%
                    </Typography>
                    <Typography variant="caption" color="#166534" display="block">
                      Bypasses Pedigree Filtering
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </Paper>

            {/* Recruiter Pitch Script */}
            <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#FEF3C7', borderColor: '#FDE68A', mb: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1} mb={0.5}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <SparkleIcon sx={{ color: '#D97706', fontSize: 18 }} />
                  <Typography variant="subtitle2" fontWeight={800} color="#92400E">
                    Recruiter Demonstration Pitch Note (Attach in Application):
                  </Typography>
                </Stack>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={copiedCode === projectData.project_spec.demonstration_prompt ? <CheckIcon fontSize="small" color="success" /> : <CopyIcon fontSize="small" />}
                  onClick={() => handleCopy(projectData.project_spec.demonstration_prompt)}
                  sx={{ fontWeight: 700 }}
                >
                  {copiedCode === projectData.project_spec.demonstration_prompt ? 'Copied' : 'Copy Pitch'}
                </Button>
              </Stack>
              <Typography variant="body2" color="#78350F" sx={{ fontStyle: 'italic', fontSize: '0.85rem' }}>
                {projectData.project_spec.demonstration_prompt}
              </Typography>
            </Paper>

            {/* Starter Code Viewer */}
            <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
              📦 Generated Starter Code Repository & Scaffolding:
            </Typography>

            <Paper variant="outlined" sx={{ borderRadius: 2, overflow: 'hidden', bgcolor: '#0F172A' }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" bgcolor="#1E293B" px={2} py={0.5}>
                <Tabs
                  value={activeFileTab}
                  onChange={(_, v) => setActiveFileTab(v)}
                  textColor="inherit"
                  sx={{ minHeight: 36 }}
                >
                  {fileNames.map((f, i) => (
                    <Tab key={i} label={f} sx={{ color: '#94A3B8', '&.Mui-selected': { color: '#38BDF8', fontWeight: 800 }, textTransform: 'none', minHeight: 36, py: 0 }} />
                  ))}
                </Tabs>

                <Button
                  size="small"
                  startIcon={copiedCode === currentCode ? <CheckIcon fontSize="small" color="success" /> : <CopyIcon fontSize="small" />}
                  onClick={() => handleCopy(currentCode)}
                  sx={{ color: '#E2E8F0', fontWeight: 700 }}
                >
                  Copy File
                </Button>
              </Box>

              <Box p={2} sx={{ maxHeight: 320, overflowY: 'auto' }}>
                <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '0.82rem', color: '#E2E8F0', whiteSpace: 'pre-wrap' }}>
                  {currentCode}
                </pre>
              </Box>
            </Paper>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} sx={{ fontWeight: 700 }}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ProofOfWorkModal;

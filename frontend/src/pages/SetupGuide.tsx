import React, { useState } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Card,
  CardContent,
  Stack,
  Paper,
} from '@mui/material';
import {
  Person as PersonIcon,
  Key as KeyIcon,
  CloudUpload as CloudUploadIcon,
  Public as PublicIcon,
} from '@mui/icons-material';
import { ApiKeySetupWizard } from '../components/setup/ApiKeySetupWizard';
import { ResumeOnboardingWizard } from '../components/onboarding/ResumeOnboardingWizard';

export const SetupGuide: React.FC = () => {
  const [tabIndex, setTabIndex] = useState(0);

  return (
    <Box sx={{ width: '100%', minHeight: '100vh', pb: 8 }}>
      {/* Top Tabs */}
      <Box sx={{ borderBottom: '1px solid rgba(0, 240, 255, 0.2)', bgcolor: '#06090E', px: { xs: 2, md: 4 }, pt: 2 }}>
        <Tabs
          value={tabIndex}
          onChange={(_, val) => setTabIndex(val)}
          textColor="inherit"
          variant="scrollable"
          scrollButtons="auto"
          TabIndicatorProps={{ style: { backgroundColor: '#00FFA3', height: 3 } }}
          sx={{
            '& .MuiTab-root': {
              color: '#94A3B8',
              fontWeight: 800,
              textTransform: 'none',
              fontSize: '0.95rem',
              '&.Mui-selected': { color: '#00FFA3' },
            },
          }}
        >
          <Tab icon={<PersonIcon />} iconPosition="start" label="1. Candidate Profile & Target Accounts" />
          <Tab icon={<KeyIcon />} iconPosition="start" label="2. Interactive API Setup & .env" />
          <Tab icon={<CloudUploadIcon />} iconPosition="start" label="3. Deploy Backend (Render / Cloud)" />
          <Tab icon={<PublicIcon />} iconPosition="start" label="4. Deploy Frontend (GitHub Pages)" />
        </Tabs>
      </Box>

      {/* Tab 0: Resume & Profile Onboarding */}
      {tabIndex === 0 && <ResumeOnboardingWizard />}

      {/* Tab 1: Interactive API Keys Wizard */}
      {tabIndex === 1 && <ApiKeySetupWizard />}

      {/* Tab 2: Backend Cloud Deploy Guide */}
      {tabIndex === 2 && (
        <Box sx={{ maxWidth: '1000px', mx: 'auto', p: { xs: 2, md: 4 } }}>
          <Card sx={{ bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', borderRadius: '20px', mb: 3 }}>
            <CardContent sx={{ p: 4 }}>
              <Typography variant="h5" sx={{ fontWeight: 900, color: '#00FFA3', mb: 2 }}>
                ⚡ Deploying FastAPI Backend to Render (100% Free)
              </Typography>
              <Typography variant="body1" sx={{ color: '#E2E8F0', mb: 3, lineHeight: 1.7 }}>
                Render provides a free web service tier that will automatically build your Docker container or Python FastAPI service directly from your GitHub repository.
              </Typography>

              <Stack spacing={2.5}>
                <Paper sx={{ p: 2.5, bgcolor: '#06090E', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '12px' }}>
                  <Typography variant="subtitle2" sx={{ color: '#00F0FF', fontWeight: 800, mb: 1 }}>
                    STEP 1: Log in to Render.com & Connect GitHub Repo
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#94A3B8', lineHeight: 1.6 }}>
                    1. Go to <a href="https://render.com" target="_blank" rel="noopener noreferrer" style={{ color: '#00FFA3' }}>Render.com</a> and sign in.<br />
                    2. Click <strong>New +</strong> &rarr; <strong>Blueprint</strong> or <strong>Web Service</strong>.<br />
                    3. Select your repository: <code>kushallj/job-finder</code>.
                  </Typography>
                </Paper>

                <Paper sx={{ p: 2.5, bgcolor: '#06090E', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '12px' }}>
                  <Typography variant="subtitle2" sx={{ color: '#00F0FF', fontWeight: 800, mb: 1 }}>
                    STEP 2: Configure Environment Variables
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#94A3B8', lineHeight: 1.6 }}>
                    In Render's <strong>Environment</strong> tab, paste the variables you generated in the <strong>Interactive API Setup</strong> tab:
                    <br />
                    <code>GEMINI_API_KEY</code>, <code>SERPAPI_API_KEY</code>, <code>GMAIL_ADDRESS</code>, <code>GMAIL_PASSWORD</code>, <code>SENDER_NAME</code>, <code>LINKEDIN_URL</code>.
                  </Typography>
                </Paper>

                <Paper sx={{ p: 2.5, bgcolor: '#06090E', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '12px' }}>
                  <Typography variant="subtitle2" sx={{ color: '#00F0FF', fontWeight: 800, mb: 1 }}>
                    STEP 3: Copy Your Live Backend URL
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#94A3B8', lineHeight: 1.6 }}>
                    Once deployed, Render assigns a public URL like <code>https://job-finder-api.onrender.com</code>. Paste this URL into the <strong>Target Backend Instance URL</strong> field on this website to connect immediately!
                  </Typography>
                </Paper>
              </Stack>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Tab 3: Frontend GitHub Pages Guide */}
      {tabIndex === 3 && (
        <Box sx={{ maxWidth: '1000px', mx: 'auto', p: { xs: 2, md: 4 } }}>
          <Card sx={{ bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', borderRadius: '20px', mb: 3 }}>
            <CardContent sx={{ p: 4 }}>
              <Typography variant="h5" sx={{ fontWeight: 900, color: '#00F0FF', mb: 2 }}>
                🌐 Deploying Frontend to GitHub Pages (2 Minutes)
              </Typography>
              <Typography variant="body1" sx={{ color: '#E2E8F0', mb: 3, lineHeight: 1.7 }}>
                This repository includes a ready-to-run GitHub Actions workflow (<code>.github/workflows/deploy-frontend.yml</code>) that builds Vite and publishes to GitHub Pages automatically on every push!
              </Typography>

              <Stack spacing={2.5}>
                <Paper sx={{ p: 2.5, bgcolor: '#06090E', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '12px' }}>
                  <Typography variant="subtitle2" sx={{ color: '#00FFA3', fontWeight: 800, mb: 1 }}>
                    STEP 1: Enable GitHub Pages in Repository Settings
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#94A3B8', lineHeight: 1.6 }}>
                    1. Open your repository on GitHub: <code>https://github.com/kushallj/job-finder</code><br />
                    2. Click <strong>Settings</strong> &rarr; <strong>Pages</strong> (left sidebar).<br />
                    3. Under <strong>Build and deployment &rarr; Source</strong>, choose <strong>GitHub Actions</strong>.
                  </Typography>
                </Paper>

                <Paper sx={{ p: 2.5, bgcolor: '#06090E', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '12px' }}>
                  <Typography variant="subtitle2" sx={{ color: '#00FFA3', fontWeight: 800, mb: 1 }}>
                    STEP 2: Automatic Live URL
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#94A3B8', lineHeight: 1.6 }}>
                    Your site will be live at:
                    <br />
                    <code style={{ color: '#00FFA3', fontSize: '1rem', fontWeight: 'bold' }}>
                      https://kushallj.github.io/job-finder/
                    </code>
                  </Typography>
                </Paper>
              </Stack>
            </CardContent>
          </Card>
        </Box>
      )}
    </Box>
  );
};

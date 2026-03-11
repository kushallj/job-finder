import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Grid,
  Chip,
} from '@mui/material';
import {
  Save as SaveIcon,
  Storage as DatabaseIcon,
  Email as EmailIcon,
  Api as ApiIcon,
} from '@mui/icons-material';

export const Settings: React.FC = () => {
  const [apiUrl, setApiUrl] = React.useState('http://localhost:8000');
  const [autoRefresh, setAutoRefresh] = React.useState(true);
  const [saved, setSaved] = React.useState(false);

  const handleSave = () => {
    // Save settings to localStorage
    localStorage.setItem('apiUrl', apiUrl);
    localStorage.setItem('autoRefresh', String(autoRefresh));
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <Box>
      {/* Header Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Settings
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Configure your job finder application
        </Typography>
      </Box>

      {saved && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Settings saved successfully!
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* API Configuration */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <ApiIcon color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  API Configuration
                </Typography>
              </Box>
              <Divider sx={{ mb: 3 }} />
              
              <TextField
                label="API Base URL"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                fullWidth
                helperText="The URL of your backend API server"
                sx={{ mb: 2 }}
              />
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Current API Endpoints:
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Chip label="GET /api/health" size="small" variant="outlined" />
                <Chip label="POST /run-query" size="small" variant="outlined" />
                <Chip label="GET /api/jobs/pending-outreach" size="small" variant="outlined" />
                <Chip label="POST /api/outreach/send" size="small" variant="outlined" />
                <Chip label="GET /api/stats" size="small" variant="outlined" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Application Settings */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <DatabaseIcon color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  Application Settings
                </Typography>
              </Box>
              <Divider sx={{ mb: 3 }} />
              
              <FormControlLabel
                control={
                  <Switch
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                  />
                }
                label="Auto-refresh data"
                sx={{ mb: 2, display: 'block' }}
              />
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                When enabled, the dashboard will automatically refresh data every 5 minutes.
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Email Configuration */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <EmailIcon color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  Email Configuration
                </Typography>
              </Box>
              <Divider sx={{ mb: 3 }} />
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Email settings are configured on the backend server. Make sure your Gmail credentials and app password are properly set in the environment variables.
              </Typography>
              
              <Alert severity="info">
                Check the OUTREACH_SETUP.md file for email configuration details.
              </Alert>
            </CardContent>
          </Card>
        </Grid>

        {/* Database Info */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <DatabaseIcon color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  Database
                </Typography>
              </Box>
              <Divider sx={{ mb: 3 }} />
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Your job data, contacts, and outreach records are stored in a SQLite database. The database file is located at:
              </Typography>
              
              <Box sx={{ 
                p: 2, 
                bgcolor: 'grey.100', 
                borderRadius: 1, 
                fontFamily: 'monospace',
                fontSize: '0.875rem'
              }}>
                job_finder.db
              </Box>
              
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                You can use the CLI tool to manage the database:
              </Typography>
              
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
                <Typography variant="caption" fontFamily="monospace">
                  python outreach_cli.py setup
                </Typography>
                <Typography variant="caption" fontFamily="monospace">
                  python outreach_cli.py stats
                </Typography>
                <Typography variant="caption" fontFamily="monospace">
                  python outreach_cli.py jobs --limit 10
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Save Button */}
      <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          size="large"
        >
          Save Settings
        </Button>
      </Box>
    </Box>
  );
};

export default Settings;


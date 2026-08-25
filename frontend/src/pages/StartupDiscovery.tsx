import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
  Chip,
  Paper,
} from '@mui/material';
import { RocketLaunch as DiscoveryIcon, Search as SearchIcon } from '@mui/icons-material';
import { startupsApi, StartupDiscoveryResponse } from '../api';

const StartupDiscovery: React.FC = () => {
  const [provider, setProvider] = useState<'firecrawl' | 'newsapi'>('firecrawl');
  const [targetCount, setTargetCount] = useState<number>(10);
  const [location, setLocation] = useState<string>('India');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<StartupDiscoveryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDiscover = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await startupsApi.discover({
        provider,
        target_count: targetCount,
        location,
      });
      setResult(response);
    } catch (err: any) {
      console.error('Discovery failed:', err);
      setError(err.response?.data?.message || 'Failed to discover startups. Please check your API keys.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
          <DiscoveryIcon sx={{ mr: 2, color: 'primary.main' }} />
          Startup Discovery
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Find recently funded startups that are likely to be hiring.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Search Parameters
              </Typography>
              <Box sx={{ mt: 2 }}>
                <FormControl fullWidth sx={{ mb: 3 }}>
                  <InputLabel>Provider</InputLabel>
                  <Select
                    value={provider}
                    label="Provider"
                    onChange={(e) => setProvider(e.target.value as any)}
                  >
                    <MenuItem value="firecrawl">Firecrawl (News Search)</MenuItem>
                    <MenuItem value="newsapi">NewsAPI (Business News)</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  fullWidth
                  label="Target Count"
                  type="number"
                  value={targetCount}
                  onChange={(e) => setTargetCount(parseInt(e.target.value))}
                  sx={{ mb: 3 }}
                  helperText="Maximum number of companies to look for"
                />

                <TextField
                  fullWidth
                  label="Location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  sx={{ mb: 3 }}
                  helperText="e.g. India, Bangalore, Remote"
                />

                <Button
                  fullWidth
                  variant="contained"
                  size="large"
                  startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
                  onClick={handleDiscover}
                  disabled={loading}
                >
                  {loading ? 'Discovering...' : 'Start Discovery'}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {result && (
            <Box>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                    <Typography variant="h4">{result.startups_found}</Typography>
                    <Typography variant="body2">Startups Found</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'secondary.light', color: 'secondary.contrastText' }}>
                    <Typography variant="h4">{result.new_startups_added}</Typography>
                    <Typography variant="body2">New to List</Typography>
                  </Paper>
                </Grid>
              </Grid>

              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Found Companies
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                    {result.companies.map((company, index) => (
                      <Chip 
                        key={index} 
                        label={company} 
                        variant="outlined" 
                        color="primary" 
                      />
                    ))}
                  </Box>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" color="text.secondary">
                    Trace ID: {result.trace_id} | Found at: {new Date(result.timestamp).toLocaleString()}
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          )}

          {!loading && !result && !error && (
            <Paper
              sx={{
                p: 5,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                border: '2px dashed',
                borderColor: 'divider',
                bgcolor: 'transparent',
              }}
            >
              <DiscoveryIcon sx={{ fontSize: 60, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" color="text.disabled">
                No discovery results yet
              </Typography>
              <Typography variant="body2" color="text.disabled">
                Configure parameters and click "Start Discovery" to find recently funded startups.
              </Typography>
            </Paper>
          )}

          {loading && (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 10 }}>
              <CircularProgress size={60} sx={{ mb: 2 }} />
              <Typography variant="h6">Analyzing News Feeds...</Typography>
              <Typography variant="body2" color="text.secondary">
                This might take a minute as we extract company names from recent funding news.
              </Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Container>
  );
};

export default StartupDiscovery;

import React from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Divider, IconButton,
  Stack, TextField, Tooltip, Typography,
} from '@mui/material';
import { ContentCopy as CopyIcon, RequestQuote as RequestQuoteIcon } from '@mui/icons-material';
import CompanySelect from './CompanySelect';
import { useNegotiationBenchmark, useNegotiationCounter } from '../../hooks/useAgents';

const NegotiatorTab: React.FC = () => {
  const [company, setCompany] = React.useState('');
  const [offer, setOffer] = React.useState<number | ''>('');
  const benchmarkQuery = useNegotiationBenchmark(company, company.trim().length > 0);
  const counter = useNegotiationCounter();

  const handleCopy = (text: string) => navigator.clipboard.writeText(text);
  const band = benchmarkQuery.data?.data.band;

  return (
    <Box>
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Negotiator</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Uses only comp numbers already on file in config/target_companies.yml and your own target
            range in config/profile.yml — never invents a market figure. If a company has no benchmark
            on file, it says so explicitly instead of pretending it has data it doesn't.
          </Typography>
          <CompanySelect value={company} onChange={setCompany} />
        </CardContent>
      </Card>

      {company.trim() && (
        <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
          <CardContent sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Comp benchmark</Typography>
            {benchmarkQuery.isLoading ? (
              <CircularProgress size={24} />
            ) : benchmarkQuery.data?.data.suggested_ask_lpa == null ? (
              <Alert severity="warning">
                {benchmarkQuery.data?.warnings?.[0] ??
                  'No comp benchmark on file for this company — add one to config/target_companies.yml before negotiating.'}
              </Alert>
            ) : (
              <Stack direction="row" spacing={3} flexWrap="wrap">
                <Box>
                  <Typography variant="caption" color="text.secondary">Band (₹ LPA)</Typography>
                  <Typography variant="h6">
                    {band?.min ?? '—'} / {band?.median ?? '—'} / {band?.max ?? '—'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">min / median / max</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Position vs. your target</Typography>
                  <Typography variant="h6">
                    <Chip label={benchmarkQuery.data.data.position.replace('_', ' ')} />
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Suggested anchor ask</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#4F46E5' }}>
                    {benchmarkQuery.data.data.suggested_ask_lpa} LPA
                  </Typography>
                </Box>
              </Stack>
            )}
            {band?.source && (
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Source: {band.source} (as of {band.as_of ?? 'unknown'})
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      <Card sx={{ border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Counter-offer script</Typography>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
            <TextField
              label="Offer received (₹ LPA)"
              size="small"
              type="number"
              value={offer}
              onChange={(e) => setOffer(e.target.value === '' ? '' : Number(e.target.value))}
              sx={{ width: 220 }}
            />
            <Button
              variant="contained"
              startIcon={counter.isPending ? <CircularProgress size={16} color="inherit" /> : <RequestQuoteIcon />}
              onClick={() => offer !== '' && counter.mutate({ company, offerAmountLpa: Number(offer) })}
              disabled={!company.trim() || offer === '' || counter.isPending}
            >
              Get counter script
            </Button>
          </Stack>

          {counter.data && (
            <Box>
              {counter.data.warnings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 2 }}>{counter.data.warnings[0]}</Alert>
              )}
              <Stack direction="row" spacing={3} sx={{ mb: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Position in band</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{counter.data.data.position_in_band}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Counter ask</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700, color: '#4F46E5' }}>
                    {counter.data.data.counter_ask_lpa} LPA
                  </Typography>
                </Box>
              </Stack>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ p: 2, bgcolor: '#F8FAFC', borderRadius: 2, position: 'relative' }}>
                <Tooltip title="Copy">
                  <IconButton
                    size="small"
                    sx={{ position: 'absolute', top: 8, right: 8 }}
                    onClick={() => handleCopy(counter.data!.data.script)}
                  >
                    <CopyIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', pr: 4 }}>{counter.data.data.script}</Typography>
              </Box>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                {counter.data.data.confidence_note}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default NegotiatorTab;

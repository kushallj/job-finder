import React from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Divider,
  FormControlLabel, Checkbox, Stack, Table, TableBody, TableCell, TableHead, TableRow,
  Typography, Accordion, AccordionSummary, AccordionDetails, alpha,
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon, PlayArrow as PlayArrowIcon } from '@mui/icons-material';
import { useCompanies, useDailyPipeline } from '../../hooks/useAgents';

const probabilityColor: Record<string, 'success' | 'info' | 'warning' | 'default'> = {
  High: 'success', 'Medium-High': 'info', Medium: 'warning', 'Low-Medium': 'default', Low: 'default',
};

const CompaniesOverviewTab: React.FC = () => {
  const { data, isLoading } = useCompanies();
  const daily = useDailyPipeline();
  const [tiers, setTiers] = React.useState<number[]>([1]);

  const toggleTier = (t: number) => {
    setTiers((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const companies = data?.companies ?? [];

  return (
    <Box>
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Run daily pipeline</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Signal check → live ATS job discovery → fit scoring → priority queue → tailored resume
            framing → contact ranking → outreach drafts. Nothing is sent automatically — review the
            drafts below and send from the Outreach page yourself.
          </Typography>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
            {[1, 2, 3].map((t) => (
              <FormControlLabel
                key={t}
                control={<Checkbox checked={tiers.includes(t)} onChange={() => toggleTier(t)} size="small" />}
                label={`Tier ${t}`}
              />
            ))}
          </Stack>
          <Button
            variant="contained"
            startIcon={daily.isPending ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
            onClick={() => daily.mutate(tiers)}
            disabled={daily.isPending}
          >
            {daily.isPending ? 'Running…' : 'Run daily pipeline'}
          </Button>
        </CardContent>
      </Card>

      {daily.isError && (
        <Alert severity="error" sx={{ mb: 3 }}>Pipeline run failed — check the server logs.</Alert>
      )}

      {daily.data && (
        <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
          <CardContent sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>
              Today's queue ({daily.data.queue.length} of {daily.data.roles_found} roles found)
            </Typography>
            {daily.data.queue.length === 0 ? (
              <Alert severity="info">
                No roles queued yet. Either no ATS matches this run, or nothing cleared the fit threshold.
              </Alert>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Priority</TableCell>
                    <TableCell>Company</TableCell>
                    <TableCell>Role</TableCell>
                    <TableCell>Recommendation</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {daily.data.queue.map((q, i) => (
                    <TableRow key={i}>
                      <TableCell>{q.priority_score}</TableCell>
                      <TableCell>{q.company}</TableCell>
                      <TableCell>{q.title}</TableCell>
                      <TableCell><Chip size="small" label={q.recommendation} /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            {daily.data.drafts.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }} gutterBottom>
                  Draft outreach (review before sending)
                </Typography>
                {daily.data.drafts.map((d, i) => (
                  <Accordion key={i} sx={{ border: '1px solid #E2E8F0', boxShadow: 'none', '&:before': { display: 'none' } }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{d.company} — {d.title}</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" fontWeight={600}>Subject: {d.subject}</Typography>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mt: 1 }}>{d.body}</Typography>
                    </AccordionDetails>
                  </Accordion>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      <Divider sx={{ mb: 3 }} />
      <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>
        Target companies ({companies.length})
      </Typography>
      <Stack spacing={2}>
        {companies.map((c) => (
          <Card key={c.name} variant="outlined" sx={{ border: '1px solid #E2E8F0' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{c.name}</Typography>
                <Stack direction="row" spacing={1}>
                  <Chip size="small" label={`Tier ${c.tier}`} sx={{ bgcolor: alpha('#4F46E5', 0.08), color: '#4F46E5', fontWeight: 600 }} />
                  <Chip size="small" color={probabilityColor[c.hiring_probability] ?? 'default'} label={c.hiring_probability} />
                </Stack>
              </Stack>
              <Typography variant="body2" color="text.secondary">{c.industry} · {c.hq}</Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>{c.why_target_now}</Typography>
              {c.signals.length > 0 && (
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                  Latest signal: {c.signals[0].detail} ({c.signals[0].date})
                </Typography>
              )}
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Box>
  );
};

export default CompaniesOverviewTab;

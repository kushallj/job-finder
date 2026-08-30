import React from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, IconButton,
  MenuItem, Select, Stack, Table, TableBody, TableCell, TableHead, TableRow, Tooltip,
  Typography, Link as MuiLink,
} from '@mui/material';
import {
  Search as SearchIcon, ContentCopy as CopyIcon, OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import { useLeads, useLeadsList } from '../../hooks/useAgents';
import type { BooleanLead } from '../../api/types';

const CATEGORY_LABELS: Record<string, string> = {
  ats: 'ATS Platforms', yc: 'YC / Wellfound', funding: 'Funding Signals', content: 'Blogs / Substack',
  github: 'GitHub', video: 'YouTube', social_search: 'X / LinkedIn (search-indexed)',
  india_boards: 'India Job Boards', careers_page: 'Careers Pages', compound: 'Compound / Precision',
};

const statusColor: Record<BooleanLead['status'], 'default' | 'info' | 'success'> = {
  new: 'default', reviewed: 'info', converted: 'success',
};

const LeadsTab: React.FC = () => {
  const { runLeads, queryBank, updateLeadStatus } = useLeads();
  const [selectedCategories, setSelectedCategories] = React.useState<string[]>([]);
  const leadsListQuery = useLeadsList();

  const categories = React.useMemo(
    () => Array.from(new Set((queryBank.data?.queries ?? []).map((q) => q.category))),
    [queryBank.data]
  );

  const handleCopy = (text: string) => navigator.clipboard.writeText(text);

  return (
    <Box>
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>X-ray / boolean lead sourcing</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            30 queries across ATS platforms, YC/Wellfound, funding press, Medium/Substack, GitHub, YouTube,
            and search-indexed X/LinkedIn posts. Runs through the Google Custom Search API or Serper.dev if
            configured — never raw scraping. Without a key, queries render below for you to paste into Google
            manually.
          </Typography>
          <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" gap={1}>
            <Select
              multiple
              size="small"
              displayEmpty
              value={selectedCategories}
              onChange={(e) => setSelectedCategories(typeof e.target.value === 'string' ? [] : e.target.value)}
              sx={{ minWidth: 240 }}
              renderValue={(selected) =>
                selected.length === 0 ? 'All categories' : selected.map((c) => CATEGORY_LABELS[c] ?? c).join(', ')
              }
            >
              {categories.map((c) => (
                <MenuItem key={c} value={c}>{CATEGORY_LABELS[c] ?? c}</MenuItem>
              ))}
            </Select>
            <Button
              variant="contained"
              startIcon={runLeads.isPending ? <CircularProgress size={16} color="inherit" /> : <SearchIcon />}
              onClick={() => runLeads.mutate(selectedCategories.length ? selectedCategories : undefined)}
              disabled={runLeads.isPending}
            >
              {runLeads.isPending ? 'Running…' : 'Run queries'}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {runLeads.data && !runLeads.data.executed && (
        <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
          <CardContent sx={{ p: 2.5 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              No search backend configured (set google_cse_api_key + google_cse_id, or serper_api_key, in .env
              to auto-execute). Here are the rendered queries — copy and paste into Google.
            </Alert>
            <Stack spacing={1.5}>
              {runLeads.data.rendered_queries.map((q) => (
                <Box key={q.id} sx={{ border: '1px solid #F1F5F9', borderRadius: 2, p: 1.5 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                    <Box sx={{ flex: 1, mr: 1 }}>
                      <Chip size="small" label={CATEGORY_LABELS[q.category] ?? q.category} sx={{ mb: 0.5 }} />
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {q.query}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                        {q.purpose}
                      </Typography>
                    </Box>
                    <Tooltip title="Copy query">
                      <IconButton size="small" onClick={() => handleCopy(q.query)}><CopyIcon fontSize="small" /></IconButton>
                    </Tooltip>
                  </Stack>
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}

      {runLeads.data?.executed && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Found {runLeads.data.leads.length} leads — see the CRM table below.
        </Alert>
      )}

      <Card sx={{ border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Lead CRM</Typography>
          {leadsListQuery.isLoading ? (
            <CircularProgress size={24} />
          ) : (leadsListQuery.data?.leads ?? []).length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No leads captured yet — run queries above with a search backend configured.
            </Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Title</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Link</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(leadsListQuery.data?.leads ?? []).map((lead) => (
                  <TableRow key={lead.id}>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{lead.title}</Typography>
                      <Typography variant="caption" color="text.secondary">{lead.snippet}</Typography>
                    </TableCell>
                    <TableCell>{CATEGORY_LABELS[lead.category] ?? lead.category}</TableCell>
                    <TableCell>
                      <Select
                        size="small"
                        value={lead.status}
                        onChange={(e) =>
                          updateLeadStatus.mutate({ leadId: lead.id, status: e.target.value as BooleanLead['status'] })
                        }
                        sx={{ minWidth: 110 }}
                      >
                        <MenuItem value="new">New</MenuItem>
                        <MenuItem value="reviewed">Reviewed</MenuItem>
                        <MenuItem value="converted">Converted</MenuItem>
                      </Select>
                      <Chip size="small" sx={{ ml: 1 }} color={statusColor[lead.status]} label={lead.status} />
                    </TableCell>
                    <TableCell align="right">
                      <MuiLink href={lead.url} target="_blank" rel="noopener noreferrer">
                        <IconButton size="small"><OpenInNewIcon fontSize="small" /></IconButton>
                      </MuiLink>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default LeadsTab;

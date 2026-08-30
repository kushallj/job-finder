import React, { useState } from 'react';
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
  alpha,
  LinearProgress,
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
} from '@mui/icons-material';
import { useContacts } from '../hooks/useContacts';
import { useNavigate } from 'react-router-dom';

export const Contacts: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);
  const navigate = useNavigate();

  const { contacts, isLoading, error, refetch } = useContacts({
    page: 1,
    limit: 100,
    company: companyFilter || undefined,
  });

  const handleCopyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  };

  const filteredContacts = (contacts || []).filter((contact) =>
    contact.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (contact.email && contact.email.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (contact.company && contact.company.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (contact.title && contact.title.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>
            Decision-Maker & Contact CRM
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Discovered recruiters, engineering managers, and LinkedIn employee referrals linked to target opportunities.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          onClick={() => refetch()}
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={16} /> : <RefreshIcon />}
        >
          Refresh Contacts
        </Button>
      </Box>

      {/* Filter Card */}
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              placeholder="Search by name, title, company, or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              size="small"
              fullWidth
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ color: '#94A3B8' }} fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
            {companyFilter && (
              <Chip
                label={`Company: ${companyFilter}`}
                onDelete={() => setCompanyFilter('')}
                color="primary"
                sx={{ alignSelf: 'center' }}
              />
            )}
          </Stack>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Error loading contacts: {String(error)}
        </Alert>
      )}

      {/* Content */}
      {isLoading ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Loading contact intelligence...
          </Typography>
        </Box>
      ) : filteredContacts.length === 0 ? (
        <Card sx={{ textAlign: 'center', py: 8 }}>
          <Box
            sx={{
              width: 52,
              height: 52,
              borderRadius: '50%',
              bgcolor: alpha('#4F46E5', 0.1),
              color: '#4F46E5',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              mb: 2,
            }}
          >
            <ContactsIcon />
          </Box>
          <Typography variant="h6" fontWeight={700} color="#0F172A" gutterBottom>
            No contacts found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 450, mx: 'auto', mb: 2 }}>
            Contacts are automatically discovered when you run job queries, sync external listings, or run the LinkedIn Referral Automator.
          </Typography>
          <Button variant="contained" onClick={() => navigate('/')}>
            Go to Command Center
          </Button>
        </Card>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: '16px', border: '1px solid #E2E8F0', mb: 3 }}>
          <Table size="medium">
            <TableHead sx={{ bgcolor: '#F8FAFC' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 700, color: '#475569' }}>Contact</TableCell>
                <TableCell sx={{ fontWeight: 700, color: '#475569' }}>Company</TableCell>
                <TableCell sx={{ fontWeight: 700, color: '#475569' }}>Email & Confidence</TableCell>
                <TableCell sx={{ fontWeight: 700, color: '#475569' }}>Discovery Source</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, color: '#475569' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredContacts.map((contact) => {
                const initials = contact.name
                  .split(' ')
                  .map((n) => n[0])
                  .slice(0, 2)
                  .join('')
                  .toUpperCase();
                const score = contact.confidence_score || 75;
                const isLinkedIn = contact.source === 'linkedin_referral' || !!contact.linkedin_url;

                return (
                  <TableRow key={contact.id} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                    <TableCell>
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <Avatar
                          sx={{
                            bgcolor: isLinkedIn ? alpha('#0077B5', 0.1) : alpha('#4F46E5', 0.1),
                            color: isLinkedIn ? '#0077B5' : '#4F46E5',
                            fontWeight: 700,
                            fontSize: '0.85rem',
                          }}
                        >
                          {initials || 'C'}
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#0F172A' }}>
                            {contact.name}
                          </Typography>
                          <Typography variant="caption" sx={{ color: '#64748B' }}>
                            {contact.title || 'Engineering / Talent'}
                          </Typography>
                        </Box>
                      </Stack>
                    </TableCell>

                    <TableCell>
                      <Chip
                        icon={<CompanyIcon fontSize="small" />}
                        label={contact.company || 'Unknown'}
                        size="small"
                        sx={{ fontWeight: 600, bgcolor: '#F1F5F9' }}
                      />
                    </TableCell>

                    <TableCell>
                      {contact.email ? (
                        <Stack spacing={0.5}>
                          <Stack direction="row" spacing={0.5} alignItems="center">
                            <Typography variant="body2" sx={{ fontWeight: 600, color: '#0F172A' }}>
                              {contact.email}
                            </Typography>
                            <Tooltip title={copiedEmail === contact.email ? 'Copied!' : 'Copy Email'}>
                              <IconButton
                                size="small"
                                onClick={() => contact.email && handleCopyEmail(contact.email)}
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
                                bgcolor: '#E2E8F0',
                                '& .MuiLinearProgress-bar': {
                                  bgcolor: score >= 80 ? '#10B981' : score >= 60 ? '#F59E0B' : '#64748B',
                                },
                              }}
                            />
                            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>
                              {score}% confidence
                            </Typography>
                          </Box>
                        </Stack>
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          Direct LinkedIn profile
                        </Typography>
                      )}
                    </TableCell>

                    <TableCell>
                      <Chip
                        label={isLinkedIn ? 'LinkedIn Referral' : contact.source || 'Apollo / Hunter'}
                        size="small"
                        color={isLinkedIn ? 'info' : 'default'}
                        variant={isLinkedIn ? 'filled' : 'outlined'}
                        sx={{ fontSize: '0.72rem', fontWeight: 700 }}
                      />
                    </TableCell>

                    <TableCell align="right">
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        {contact.linkedin_url && (
                          <Tooltip title="Open LinkedIn Profile">
                            <IconButton
                              size="small"
                              onClick={() => window.open(contact.linkedin_url ?? undefined, '_blank')}
                              sx={{ border: '1px solid #E2E8F0', borderRadius: '8px' }}
                            >
                              <OpenInNewIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        <Button
                          variant="contained"
                          size="small"
                          startIcon={<SendIcon fontSize="small" />}
                          onClick={() => navigate(`/outreach?email=${encodeURIComponent(contact.email || '')}&name=${encodeURIComponent(contact.name)}`)}
                          sx={{ fontWeight: 700 }}
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
  );
};

export default Contacts;

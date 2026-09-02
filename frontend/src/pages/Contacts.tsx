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
    <Box sx={{ maxWidth: 1440, mx: 'auto', width: '100%', color: '#F8FAFC' }}>
      {/* Header Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, mb: 3.5, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h3" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.03em', mb: 0.5, textTransform: 'uppercase' }}>
            Decision-Maker & Contact CRM
          </Typography>
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>
            Discovered recruiters, engineering managers, and LinkedIn employee referrals across target companies.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          onClick={() => refetch()}
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={16} sx={{ color: '#00F0FF' }} /> : <RefreshIcon />}
          sx={{ borderRadius: '12px', fontWeight: 800 }}
        >
          Refresh Contacts
        </Button>
      </Box>

      {/* Filter Card */}
      <Card sx={{ mb: 3.5, bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6)' }}>
        <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
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
                    <SearchIcon sx={{ color: '#00F0FF' }} fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
            {companyFilter && (
              <Chip
                label={`Company: ${companyFilter}`}
                onDelete={() => setCompanyFilter('')}
                color="primary"
                sx={{ alignSelf: 'center', fontWeight: 800 }}
              />
            )}
          </Stack>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3.5, borderRadius: '14px', bgcolor: 'rgba(255, 0, 122, 0.15)', color: '#FF007A', border: '1px solid rgba(255, 0, 122, 0.4)' }}>
          Error loading contacts: {String(error)}
        </Alert>
      )}

      {/* Content */}
      {isLoading ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#00FFA3', mb: 2 }} />
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>
            Loading contact intelligence...
          </Typography>
        </Box>
      ) : filteredContacts.length === 0 ? (
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
            No contacts found
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
              {filteredContacts.map((contact) => {
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
  );
};

export default Contacts;

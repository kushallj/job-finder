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
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  Avatar,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  Business as CompanyIcon,
  Email as EmailIcon,
  Person as PersonIcon,
  LinkedIn as LinkedInIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
} from '@mui/icons-material';
import { useContacts } from '../hooks/useContacts';
import { capitalizeFirst } from '../utils/formatters';
import type { Contact } from '../api/types';

export const Contacts: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCompany, setSelectedCompany] = useState('');
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);
  
  const { contacts, isLoading, refetch, search, isSearching } = useContacts(selectedCompany || undefined);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      search({ company_name: searchQuery });
    }
  };

  const handleCopyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  };

  // Get unique companies from contacts
  const companies = [...new Set(contacts.map((c: Contact) => c.company))];

  const filteredContacts = contacts.filter((contact: Contact) =>
    contact.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    contact.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (contact.email && contact.email.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // Group contacts by company
  const groupedContacts = filteredContacts.reduce((acc: Record<string, Contact[]>, contact: Contact) => {
    const company = contact.company || 'Unknown';
    if (!acc[company]) {
      acc[company] = [];
    }
    acc[company].push(contact);
    return acc;
  }, {} as Record<string, Contact[]>);

  return (
    <Box>
      {/* Header Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Contacts
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage your professional contacts and network
        </Typography>
      </Box>

      {/* Search Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <TextField
              placeholder="Search by name, company, or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              size="small"
              sx={{ flex: 1, minWidth: 250 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
            />
            
            <TextField
              select
              label="Filter by Company"
              value={selectedCompany}
              onChange={(e) => setSelectedCompany(e.target.value)}
              size="small"
              sx={{ minWidth: 200 }}
              SelectProps={{ native: true }}
            >
              <option value="">All Companies</option>
              {companies.map((company: string) => (
                <option key={company} value={company}>
                  {company}
                </option>
              ))}
            </TextField>

            <Button
              variant="contained"
              onClick={handleSearch}
              disabled={isSearching || !searchQuery.trim()}
            >
              {isSearching ? <CircularProgress size={20} /> : 'Search'}
            </Button>

            <Button
              variant="outlined"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              Refresh
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Contacts by Company */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : filteredContacts.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No contacts found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Search for contacts by company name to discover contacts
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {Object.entries(groupedContacts).map(([company, companyContacts]) => (
            <Card key={company}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <CompanyIcon color="primary" />
                  <Typography variant="h6" fontWeight={600}>
                    {company}
                  </Typography>
                  <Chip label={`${companyContacts.length}`} size="small" color="primary" variant="outlined" />
                </Box>
                
                <Divider sx={{ mb: 2 }} />
                
                <List disablePadding>
                  {companyContacts.map((contact: Contact, index: number) => (
                    <React.Fragment key={contact.id}>
                      <ListItem
                        sx={{
                          px: 0,
                          py: 2,
                          '&:hover': { backgroundColor: 'action.hover' },
                        }}
                        secondaryAction={
                          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                            {contact.confidence_score > 0 && (
                              <Chip
                                label={`${contact.confidence_score}%`}
                                size="small"
                                color={contact.confidence_score >= 80 ? 'success' : contact.confidence_score >= 60 ? 'warning' : 'default'}
                              />
                            )}
                            {contact.email && (
                              <IconButton
                                size="small"
                                onClick={() => handleCopyEmail(contact.email!)}
                                title="Copy email"
                              >
                                {copiedEmail === contact.email ? (
                                  <CheckIcon color="success" fontSize="small" />
                                ) : (
                                  <CopyIcon fontSize="small" />
                                )}
                              </IconButton>
                            )}
                          </Box>
                        }
                      >
                        <Avatar sx={{ mr: 2, bgcolor: 'primary.light' }}>
                          <PersonIcon />
                        </Avatar>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="body1" fontWeight={500}>
                                {contact.name}
                              </Typography>
                              {contact.title && (
                                <Typography variant="body2" color="text.secondary">
                                  - {contact.title}
                                </Typography>
                              )}
                            </Box>
                          }
                          secondary={
                            <Box sx={{ display: 'flex', gap: 2, mt: 0.5, flexWrap: 'wrap' }}>
                              {contact.email && (
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  <EmailIcon fontSize="small" color="action" />
                                  <Typography variant="caption">{contact.email}</Typography>
                                </Box>
                              )}
                              {contact.linkedin_url && (
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  <LinkedInIcon fontSize="small" color="action" />
                                  <Typography variant="caption">LinkedIn</Typography>
                                </Box>
                              )}
                              {contact.source && (
                                <Chip
                                  label={capitalizeFirst(contact.source)}
                                  size="small"
                                  variant="outlined"
                                />
                              )}
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < companyContacts.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default Contacts;


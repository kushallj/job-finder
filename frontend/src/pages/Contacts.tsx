import React from 'react';
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
  Pagination,
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
import { useFilterStore } from '../stores/useFilterStore';
import { capitalizeFirst } from '../utils/formatters';
import type { Contact } from '../api/types';

export const Contacts: React.FC = () => {
  const filterStore = useFilterStore();
  const [copiedEmail, setCopiedEmail] = React.useState<string | null>(null);
  
  const filters = {
    page: filterStore.contactsPage,
    limit: filterStore.contactsLimit,
    company: filterStore.contactCompanyFilter[0] ?? '',
  };
  
  const { contacts, pagination, isLoading, refetch, search, isSearching } = useContacts(filters);

  React.useEffect(() => {
    refetch();
  }, [filterStore.contactsPage, filterStore.contactsLimit, filterStore.contactCompanyFilter, refetch]);

  const handleSearch = () => {
    if (filterStore.contactSearch.trim()) {
      search({ company_name: filterStore.contactSearch.trim() });
    }
  };

  const handleCopyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  };

  const companies = [...new Set(contacts.map((c) => c.company))];

  const filteredContacts = contacts.filter((contact) =>
    contact.name.toLowerCase().includes(filterStore.contactSearch.toLowerCase()) ||
    contact.company.toLowerCase().includes(filterStore.contactSearch.toLowerCase()) ||
    contact.email?.toLowerCase().includes(filterStore.contactSearch.toLowerCase()) ||
    filterStore.contactCompanyFilter.some((f) => contact.company.toLowerCase().includes(f.toLowerCase()))
  );

  const groupedContacts = filteredContacts.reduce((acc: Record<string, Contact[]>, contact) => {
    const company = contact.company || 'Unknown';
    if (!acc[company]) {
      acc[company] = [];
    }
    acc[company].push(contact);
    return acc;
  }, {} as Record<string, Contact[]>);

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Contacts
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage your professional contacts and network
        </Typography>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'end' }}>
            <TextField
              placeholder="Search by name, company, or email..."
              value={filterStore.contactSearch}
              onChange={(e) => filterStore.setContactSearch(e.target.value)}
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
              value={filterStore.contactCompanyFilter[0] || ''}
              onChange={(e) => {
                const val = e.target.value;
                if (val) {
                  filterStore.setContactCompanyFilter([val]);
                } else {
                  filterStore.setContactCompanyFilter([]);
                }
              }}
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
              disabled={isSearching || !filterStore.contactSearch.trim()}
            >
              {isSearching ? <CircularProgress size={20} /> : 'Search Contacts'}
            </Button>

            <Button
              variant="outlined"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              Refresh
            </Button>

            <Button
              variant="outlined"
              onClick={() => filterStore.resetContactFilters()}
            >
              Reset Filters
            </Button>
          </Box>
        </CardContent>
      </Card>

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : contacts.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No contacts found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Run job search first to populate contacts
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Showing {filteredContacts.length} of {pagination.total} contacts
            </Typography>
            <Pagination 
              count={Math.ceil(pagination.total / filterStore.contactsLimit)} 
              page={filterStore.contactsPage} 
              onChange={(_, page) => filterStore.setContactsPage(page)} 
              color="primary" 
            />
          </Box>
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
                    {companyContacts.map((contact, index) => (
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
                                  onClick={() => handleCopyEmail(contact.email)}
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
        </>
      )}
    </Box>
  );
};

export default Contacts;

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  IconButton,
  Button,
  Tabs,
  Tab,
  Box,
  Typography,
  Chip,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import BoltIcon from '@mui/icons-material/Bolt';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import api from '../../api/axios';
import { useAuth } from '../../context/AuthContext';

interface PricingModalProps {
  open: boolean;
  onClose: () => void;
}

interface PlanItem {
  id: string;
  name: string;
  price: number;
  interval: string;
  credits: number;
  popular?: boolean;
  features: string[];
}

interface CreditPackItem {
  id: string;
  name: string;
  price: number;
  credits: number;
  description: string;
}

export const PricingModal: React.FC<PricingModalProps> = ({ open, onClose }) => {
  const { user, isAuthenticated, setIsAuthModalOpen, refreshUser } = useAuth();
  const [tab, setTab] = useState<'plans' | 'packs'>('plans');
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [packs, setPacks] = useState<CreditPackItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [purchasingTarget, setPurchasingTarget] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      loadCatalog();
    }
  }, [open]);

  const loadCatalog = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/billing/plans');
      setPlans(res.data.plans || []);
      setPacks(res.data.credit_packs || []);
    } catch (err) {
      console.error('Failed to load plans catalog:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTarget = async (target: string) => {
    if (!isAuthenticated) {
      onClose();
      setIsAuthModalOpen(true);
      return;
    }

    try {
      setPurchasingTarget(target);
      const res = await api.post('/api/billing/create-checkout-session', { target });
      const checkoutUrl = res.data.checkout_url;

      if (checkoutUrl) {
        if (checkoutUrl.includes('#mock-checkout')) {
          // In test/demo mode, complete the mock transaction via demo topup or alert
          const isPack = target.startsWith('pack_');
          const granted = isPack ? (target === 'pack_100' ? 100 : 300) : (target === 'pro' ? 1000 : target === 'starter' ? 300 : 9999);
          await api.post('/api/auth/credits/topup', { amount: granted });
          await refreshUser();
          alert(`🎉 Simulated Payment Succeeded! You have been granted ${granted} credits.`);
          onClose();
        } else {
          // Live Stripe redirect
          window.location.href = checkoutUrl;
        }
      }
    } catch (err: any) {
      console.error('Checkout creation error:', err);
      alert(err.response?.data?.detail || 'Failed to initiate checkout');
    } finally {
      setPurchasingTarget(null);
    }
  };

  const handleOpenPortal = async () => {
    try {
      const res = await api.post('/api/billing/create-portal-session', {});
      if (res.data.portal_url) {
        if (res.data.portal_url.includes('#mock-portal')) {
          alert('Self-serve Stripe Customer Portal will open here in production mode.');
        } else {
          window.location.href = res.data.portal_url;
        }
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Could not open billing portal');
    }
  };

  const currentTier = user?.subscription_tier || 'free';

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#0B0F17',
          color: '#F8FAFC',
          borderRadius: 3,
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.85)',
        },
      }}
    >
      <Box sx={{ p: 2.5, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2 }}>
          <Box sx={{ p: 0.8, borderRadius: 2, bgcolor: 'rgba(0, 240, 255, 0.1)', color: '#00F0FF' }}>
            <RocketLaunchIcon fontSize="small" />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 800, fontSize: '1.2rem', letterSpacing: '-0.02em' }}>
              Accelerate Your Career with Job Finder Pro
            </Typography>
            <Typography variant="caption" sx={{ color: '#94A3B8' }}>
              Full-autopilot Workday & NextRaise applications powered by central AI intelligence.
            </Typography>
          </Box>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: '#94A3B8' }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <DialogContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
          <Tabs
            value={tab}
            onChange={(_, val) => setTab(val)}
            sx={{
              bgcolor: 'rgba(255,255,255,0.04)',
              borderRadius: 2,
              p: 0.5,
              minHeight: 40,
              '& .MuiTabs-indicator': { bgcolor: '#00F0FF', borderRadius: 1 },
              '& .MuiTab-root': {
                minHeight: 36,
                color: '#94A3B8',
                fontWeight: 700,
                fontSize: '0.85rem',
                textTransform: 'none',
                '&.Mui-selected': { color: '#00F0FF' },
              },
            }}
          >
            <Tab value="plans" label="Monthly Subscription" />
            <Tab value="packs" label="Instant Credit Packs" />
          </Tabs>

          {isAuthenticated && currentTier !== 'free' && (
            <Button
              size="small"
              onClick={handleOpenPortal}
              endIcon={<OpenInNewIcon fontSize="small" />}
              sx={{ color: '#94A3B8', textTransform: 'none', fontSize: '0.8rem', '&:hover': { color: '#FFF' } }}
            >
              Manage Subscription & Invoices
            </Button>
          )}
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress color="info" />
          </Box>
        ) : tab === 'plans' ? (
          <Grid container spacing={2}>
            {plans.map((p) => {
              const isCurrent = currentTier === p.id;
              const isPopular = p.popular;

              return (
                <Grid size={{ xs: 12, md: p.id === 'free' ? 12 : 4 }} key={p.id} sx={p.id === 'free' ? { display: 'none' } : {}}>
                  <Card
                    sx={{
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      bgcolor: isPopular ? 'rgba(0, 240, 255, 0.04)' : 'rgba(255,255,255,0.02)',
                      border: isPopular ? '1.5px solid #00F0FF' : '1px solid rgba(255,255,255,0.08)',
                      borderRadius: 3,
                      position: 'relative',
                      boxShadow: isPopular ? '0 10px 30px rgba(0, 240, 255, 0.15)' : 'none',
                    }}
                  >
                    {isPopular && (
                      <Chip
                        label="MOST POPULAR"
                        size="small"
                        sx={{
                          position: 'absolute',
                          top: -12,
                          right: 20,
                          bgcolor: '#00F0FF',
                          color: '#080C12',
                          fontWeight: 900,
                          fontSize: '0.65rem',
                          letterSpacing: '0.05em',
                        }}
                      />
                    )}
                    <CardContent sx={{ p: 2.5, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="h6" sx={{ fontWeight: 800, color: '#FFF', fontSize: '1.1rem' }}>
                        {p.name}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'baseline', mt: 1, mb: 1.5 }}>
                        <Typography variant="h4" sx={{ fontWeight: 900, color: isPopular ? '#00F0FF' : '#FFF' }}>
                          ${p.price}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#94A3B8', ml: 0.5 }}>
                          / month
                        </Typography>
                      </Box>
                      <Chip
                        icon={<BoltIcon sx={{ color: '#00FFA3 !important', fontSize: 16 }} />}
                        label={`${p.credits.toLocaleString()} Applications / Mo`}
                        size="small"
                        sx={{
                          bgcolor: 'rgba(0, 255, 163, 0.1)',
                          color: '#00FFA3',
                          border: '1px solid rgba(0, 255, 163, 0.3)',
                          fontWeight: 700,
                          fontSize: '0.75rem',
                          mb: 2,
                          width: 'fit-content',
                        }}
                      />

                      <List sx={{ p: 0, mb: 3, flexGrow: 1 }}>
                        {p.features.map((feat, idx) => (
                          <ListItem key={idx} disableGutters sx={{ py: 0.6, alignItems: 'flex-start' }}>
                            <ListItemIcon sx={{ minWidth: 24, mt: 0.3 }}>
                              <CheckCircleIcon sx={{ fontSize: 16, color: '#00F0FF' }} />
                            </ListItemIcon>
                            <ListItemText
                              primary={feat}
                              primaryTypographyProps={{ sx: { fontSize: '0.8rem', color: '#CBD5E1', lineHeight: 1.3 } }}
                            />
                          </ListItem>
                        ))}
                      </List>

                      <Button
                        variant={isPopular ? 'contained' : 'outlined'}
                        fullWidth
                        disabled={isCurrent || purchasingTarget === p.id}
                        onClick={() => handleSelectTarget(p.id)}
                        sx={{
                          mt: 'auto',
                          py: 1,
                          fontWeight: 800,
                          textTransform: 'none',
                          borderRadius: 2,
                          bgcolor: isPopular ? '#00F0FF' : 'transparent',
                          color: isPopular ? '#080C12' : '#FFF',
                          borderColor: isPopular ? 'transparent' : 'rgba(255,255,255,0.2)',
                          '&:hover': {
                            bgcolor: isPopular ? '#38BDF8' : 'rgba(255,255,255,0.08)',
                          },
                        }}
                      >
                        {purchasingTarget === p.id ? (
                          <CircularProgress size={20} color="inherit" />
                        ) : isCurrent ? (
                          'Current Plan'
                        ) : (
                          `Upgrade to ${p.name.split(' ')[0]}`
                        )}
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        ) : (
          <Grid container spacing={3}>
            {packs.map((pack) => (
              <Grid size={{ xs: 12, sm: 6 }} key={pack.id}>
                <Card
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 3,
                    p: 2.5,
                  }}
                >
                  <Typography variant="h6" sx={{ fontWeight: 800, color: '#FFF' }}>
                    {pack.name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 2 }}>
                    {pack.description}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'baseline', mb: 2 }}>
                    <Typography variant="h4" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                      ${pack.price}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#94A3B8', ml: 1 }}>
                      one-time payment
                    </Typography>
                  </Box>
                  <Button
                    variant="contained"
                    fullWidth
                    disabled={purchasingTarget === pack.id}
                    onClick={() => handleSelectTarget(pack.id)}
                    sx={{
                      bgcolor: '#00FFA3',
                      color: '#080C12',
                      fontWeight: 800,
                      textTransform: 'none',
                      py: 1,
                      borderRadius: 2,
                      '&:hover': { bgcolor: '#10B981' },
                    }}
                  >
                    {purchasingTarget === pack.id ? <CircularProgress size={20} color="inherit" /> : `Buy ${pack.credits} Credits`}
                  </Button>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </DialogContent>
    </Dialog>
  );
};

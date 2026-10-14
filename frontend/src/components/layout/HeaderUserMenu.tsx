import React, { useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Menu,
  MenuItem,
  Typography,
  Avatar,
  Divider,
  Snackbar,
  Alert,
} from '@mui/material';
import BoltIcon from '@mui/icons-material/Bolt';
import PersonIcon from '@mui/icons-material/Person';
import LogoutIcon from '@mui/icons-material/Logout';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import { useAuth } from '../../context/AuthContext';
import { AuthModal } from '../auth/AuthModal';
import { PricingModal } from '../billing/PricingModal';

export const HeaderUserMenu: React.FC = () => {
  const {
    user,
    isAuthenticated,
    logout,
    topupCredits,
    isAuthModalOpen,
    setIsAuthModalOpen,
    creditDepletedData,
    clearCreditDepletedAlert,
  } = useAuth();

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [isPricingModalOpen, setIsPricingModalOpen] = useState(false);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleTopup = async (amount: number) => {
    handleClose();
    await topupCredits(amount);
  };

  const handleOpenPricing = () => {
    handleClose();
    setIsPricingModalOpen(true);
  };

  const getCreditBadgeColor = (balance: number) => {
    if (balance > 15) return { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: 'rgba(16, 185, 129, 0.3)' };
    if (balance > 0) return { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' };
    return { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: 'rgba(239, 68, 68, 0.3)' };
  };

  return (
    <>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        {isAuthenticated && user ? (
          <>
            {/* Credit Balance Badge */}
            {(() => {
              const colors = getCreditBadgeColor(user.credits_balance);
              return (
                <Chip
                  icon={<BoltIcon sx={{ color: `${colors.text} !important`, fontSize: 16 }} />}
                  label={`${user.credits_balance} Credits`}
                  onClick={handleOpenPricing}
                  size="small"
                  sx={{
                    bgcolor: colors.bg,
                    color: colors.text,
                    border: `1px solid ${colors.border}`,
                    fontWeight: 700,
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    '&:hover': {
                      filter: 'brightness(1.15)',
                    },
                  }}
                />
              );
            })()}

            {/* User Avatar Menu Trigger */}
            <Button
              onClick={handleClick}
              sx={{
                textTransform: 'none',
                color: '#f8fafc',
                bgcolor: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 2,
                px: 1.5,
                py: 0.5,
                gap: 1,
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.1)',
                },
              }}
            >
              <Avatar
                sx={{
                  width: 24,
                  height: 24,
                  bgcolor: '#3b82f6',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                }}
              >
                {user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}
              </Avatar>
              <Box sx={{ textAlign: 'left', display: { xs: 'none', sm: 'block' } }}>
                <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', lineHeight: 1.2 }}>
                  {user.full_name || user.email.split('@')[0]}
                </Typography>
                <Typography variant="caption" sx={{ color: '#94a3b8', fontSize: '0.65rem' }}>
                  {user.subscription_tier.toUpperCase()}
                </Typography>
              </Box>
            </Button>

            {/* Menu */}
            <Menu
              anchorEl={anchorEl}
              open={open}
              onClose={handleClose}
              PaperProps={{
                sx: {
                  bgcolor: '#0f172a',
                  color: '#f8fafc',
                  border: '1px solid rgba(255,255,255,0.1)',
                  minWidth: 220,
                  boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                  mt: 1,
                },
              }}
            >
              <Box sx={{ px: 2, py: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {user.full_name || 'Candidate Account'}
                </Typography>
                <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                  {user.email}
                </Typography>
              </Box>
              <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)' }} />
              <MenuItem onClick={handleOpenPricing} sx={{ gap: 1, py: 1.2, color: '#00F0FF' }}>
                <BoltIcon fontSize="small" />
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  Upgrade Plan / Top Up
                </Typography>
              </MenuItem>
              <MenuItem onClick={() => handleTopup(50)} sx={{ gap: 1, py: 1.2 }}>
                <AddCircleOutlineIcon fontSize="small" sx={{ color: '#10b981' }} />
                <Typography variant="body2">Quick +50 Demo Credits</Typography>
              </MenuItem>
              <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)' }} />
              <MenuItem
                onClick={() => {
                  handleClose();
                  logout();
                }}
                sx={{ gap: 1, py: 1.2, color: '#f87171' }}
              >
                <LogoutIcon fontSize="small" />
                <Typography variant="body2">Sign Out</Typography>
              </MenuItem>
            </Menu>
          </>
        ) : (
          <Button
            variant="contained"
            size="small"
            onClick={() => setIsAuthModalOpen(true)}
            sx={{
              bgcolor: '#10b981',
              color: '#fff',
              fontWeight: 700,
              textTransform: 'none',
              px: 1.8,
              py: 0.6,
              borderRadius: 2,
              boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)',
              gap: 0.8,
              '&:hover': {
                bgcolor: '#059669',
              },
            }}
          >
            <PersonIcon fontSize="small" />
            Sign In / Register
            <Chip
              label="+50 Free"
              size="small"
              sx={{
                height: 18,
                fontSize: '0.65rem',
                fontWeight: 800,
                bgcolor: 'rgba(255,255,255,0.2)',
                color: '#fff',
                ml: 0.5,
              }}
            />
          </Button>
        )}
      </Box>

      {/* Auth Modal */}
      <AuthModal open={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} />

      {/* Pricing & Billing Modal */}
      <PricingModal open={isPricingModalOpen} onClose={() => setIsPricingModalOpen(false)} />

      {/* Insufficient Credits 402 Alert Snackbar */}
      <Snackbar
        open={Boolean(creditDepletedData)}
        autoHideDuration={8000}
        onClose={clearCreditDepletedAlert}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          severity="warning"
          onClose={clearCreditDepletedAlert}
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => {
                clearCreditDepletedAlert();
                setIsPricingModalOpen(true);
              }}
              sx={{ fontWeight: 800, textTransform: 'none' }}
            >
              Upgrade / Top Up
            </Button>
          }
          sx={{
            bgcolor: '#1e293b',
            color: '#f8fafc',
            border: '1px solid rgba(245, 158, 11, 0.4)',
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
          }}
        >
          {creditDepletedData?.detail?.message ||
            'Insufficient Credits: Upgrade your subscription or top up to continue.'}
        </Alert>
      </Snackbar>
    </>
  );
};

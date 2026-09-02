import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Divider,
  useTheme,
  useMediaQuery,
  Stack,
  Chip,
} from '@mui/material';

import {
  Dashboard as DashboardIcon,
  WorkOutline as JobsIcon,
  PeopleOutline as ContactsIcon,
  SendOutlined as OutreachIcon,
  BarChartOutlined as StatsIcon,
  SettingsOutlined as SettingsIcon,
  AutoAwesome as SparkleIcon,
  SmartToyOutlined as AgentsIcon,
  Public as GlobalIcon,
} from '@mui/icons-material';
import { useUIStore } from '../../stores/useUIStore';

const DRAWER_WIDTH = 260;

interface SidebarProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const mainNavItems = [
  { text: 'Command Center', icon: <DashboardIcon fontSize="small" />, path: '/' },
  { text: 'Opportunities & Jobs', icon: <JobsIcon fontSize="small" />, path: '/jobs' },
  { text: 'AI Agents Fleet', icon: <AgentsIcon fontSize="small" />, path: '/agents' },
  { text: 'AI OSINT Copilot', icon: <SparkleIcon fontSize="small" />, path: '/copilot' },
  { text: 'Global Remote Radar', icon: <GlobalIcon fontSize="small" />, path: '/market-radar' },
  { text: 'Contacts CRM', icon: <ContactsIcon fontSize="small" />, path: '/contacts' },
  { text: 'Outreach Engine', icon: <OutreachIcon fontSize="small" />, path: '/outreach' },
];

const intelligenceNavItems = [
  { text: 'Analytics & Funnel', icon: <StatsIcon fontSize="small" />, path: '/stats' },
  { text: 'Settings & Config', icon: <SettingsIcon fontSize="small" />, path: '/settings' },
];

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen, onMobileClose }) => {
  const theme = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { sidebarOpen } = useUIStore();

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      onMobileClose();
    }
  };

  const drawerContent = (
    <Box sx={{ overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#0E131F' }}>
      {/* Brand Header */}
      <Toolbar sx={{ px: 3, py: 2.5, minHeight: 70 }}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Box
            sx={{
              width: 38,
              height: 38,
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366F1 0%, #38BDF8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(56, 189, 248, 0.4)',
              color: '#0B0F19',
            }}
          >
            <SparkleIcon fontSize="small" sx={{ color: '#0B0F19' }} />
          </Box>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 800, color: '#F8FAFC', lineHeight: 1.1, letterSpacing: '-0.02em' }}>
              JobFinder <span style={{ color: '#38BDF8' }}>AI</span>
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600, fontSize: '0.7rem' }}>
              ui.dev Edition • Autonomous
            </Typography>
          </Box>
        </Stack>
      </Toolbar>

      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.08)' }} />

      {/* Nav List */}
      <Box sx={{ px: 2, py: 2, flexGrow: 1 }}>
        <Typography
          variant="caption"
          sx={{ px: 1.5, py: 0.5, color: '#64748B', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}
        >
          Core Pipeline
        </Typography>
        <List sx={{ mt: 0.5, mb: 2 }}>
          {mainNavItems.map((item) => {
            const isSelected = location.pathname === item.path;
            return (
              <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
                <ListItemButton
                  selected={isSelected}
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    borderRadius: '10px',
                    py: 1,
                    px: 1.5,
                    transition: 'all 0.15s ease',
                    color: isSelected ? '#38BDF8' : '#94A3B8',
                    backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                    border: isSelected ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid transparent',
                    boxShadow: isSelected ? '0 0 15px rgba(56, 189, 248, 0.12)' : 'none',
                    fontWeight: isSelected ? 700 : 500,
                    '&:hover': {
                      backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.18)' : 'rgba(255, 255, 255, 0.04)',
                      color: isSelected ? '#38BDF8' : '#F8FAFC',
                    },
                    '&.Mui-selected': {
                      backgroundColor: 'rgba(56, 189, 248, 0.12)',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 32,
                      color: isSelected ? '#38BDF8' : '#64748B',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontSize: '0.875rem',
                      fontWeight: isSelected ? 700 : 500,
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>

        <Typography
          variant="caption"
          sx={{ px: 1.5, py: 0.5, color: '#64748B', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}
        >
          Intelligence & Setup
        </Typography>
        <List sx={{ mt: 0.5 }}>
          {intelligenceNavItems.map((item) => {
            const isSelected = location.pathname === item.path;
            return (
              <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
                <ListItemButton
                  selected={isSelected}
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    borderRadius: '10px',
                    py: 1,
                    px: 1.5,
                    transition: 'all 0.15s ease',
                    color: isSelected ? '#38BDF8' : '#94A3B8',
                    backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                    border: isSelected ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid transparent',
                    boxShadow: isSelected ? '0 0 15px rgba(56, 189, 248, 0.12)' : 'none',
                    fontWeight: isSelected ? 700 : 500,
                    '&:hover': {
                      backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.18)' : 'rgba(255, 255, 255, 0.04)',
                      color: isSelected ? '#38BDF8' : '#F8FAFC',
                    },
                    '&.Mui-selected': {
                      backgroundColor: 'rgba(56, 189, 248, 0.12)',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 32,
                      color: isSelected ? '#38BDF8' : '#64748B',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontSize: '0.875rem',
                      fontWeight: isSelected ? 700 : 500,
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* Footer Catalogs Status Card */}
      <Box sx={{ p: 2, m: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: '#34D399',
              boxShadow: '0 0 8px #34D399',
            }}
          />
          <Typography variant="caption" sx={{ fontWeight: 700, color: '#F8FAFC' }}>
            2,050+ Live Jobs
          </Typography>
        </Stack>
        <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ gap: 0.5 }}>
          <Chip label="S&P 500" size="small" sx={{ fontSize: '0.65rem', height: 20, bgcolor: 'rgba(99, 102, 241, 0.15)', color: '#818CF8', border: '1px solid rgba(99, 102, 241, 0.3)' }} />
          <Chip label="Nifty 500" size="small" sx={{ fontSize: '0.65rem', height: 20, bgcolor: 'rgba(56, 189, 248, 0.15)', color: '#38BDF8', border: '1px solid rgba(56, 189, 248, 0.3)' }} />
          <Chip label="YC / GFF" size="small" sx={{ fontSize: '0.65rem', height: 20, bgcolor: 'rgba(52, 211, 153, 0.15)', color: '#34D399', border: '1px solid rgba(52, 211, 153, 0.3)' }} />
        </Stack>
      </Box>
    </Box>
  );

  return (
    <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH, borderRight: '1px solid rgba(255, 255, 255, 0.08)', bgcolor: '#0E131F' },
        }}
      >
        {drawerContent}
      </Drawer>
      <Drawer
        variant="persistent"
        open={sidebarOpen}
        sx={{
          display: { xs: 'none', md: 'block' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: DRAWER_WIDTH,
            borderRight: '1px solid rgba(255, 255, 255, 0.08)',
            bgcolor: '#0E131F',
            transition: theme.transitions.create('transform', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
            transform: sidebarOpen ? 'translateX(0)' : `translateX(-${DRAWER_WIDTH}px)`,
          },
        }}
      >
        {drawerContent}
      </Drawer>
    </Box>
  );
};

export default Sidebar;

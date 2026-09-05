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
  LocalFireDepartment as FlameIcon,
  SmartToyOutlined as AgentsIcon,
  Public as GlobalIcon,
  Psychology as CopilotIcon,
  RocketLaunch as RocketIcon,
  VisibilityOff as StealthIcon,
} from '@mui/icons-material';
import { useUIStore } from '../../stores/useUIStore';

export const DRAWER_WIDTH = 260;

interface SidebarProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const mainNavItems = [
  { text: 'Command Center', icon: <DashboardIcon fontSize="small" />, path: '/', tag: '100s' },
  { text: 'Opportunities', icon: <JobsIcon fontSize="small" />, path: '/jobs', tag: '2,050+' },
  { text: 'AI Agents Fleet', icon: <AgentsIcon fontSize="small" />, path: '/agents', tag: '15' },
  { text: 'Ghost Copilot', icon: <StealthIcon fontSize="small" />, path: '/interview-copilot', tag: '<5µs' },
  { text: 'AI OSINT Copilot', icon: <CopilotIcon fontSize="small" />, path: '/copilot', tag: 'AI' },
  { text: 'Global Radar', icon: <GlobalIcon fontSize="small" />, path: '/market-radar' },
  { text: 'Decision Makers', icon: <ContactsIcon fontSize="small" />, path: '/contacts', tag: '1,043' },
  { text: 'Outreach Engine', icon: <OutreachIcon fontSize="small" />, path: '/outreach', tag: '211' },
];


const intelligenceNavItems = [
  { text: 'Setup & Deploy Guide', icon: <RocketIcon fontSize="small" />, path: '/setup', tag: 'FREE' },
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
    <Box sx={{ overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#080C12' }}>
      {/* Brand Header */}
      <Toolbar sx={{ px: 2.5, minHeight: '68px', height: '68px', display: 'flex', alignItems: 'center' }}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Box
            sx={{
              width: 38,
              height: 38,
              borderRadius: '12px',
              bgcolor: 'rgba(0, 255, 163, 0.15)',
              border: '1.5px solid #00FFA3',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px rgba(0, 255, 163, 0.3)',
              color: '#00FFA3',
            }}
          >
            <FlameIcon sx={{ fontSize: '22px' }} />
          </Box>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, background: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1.1, textTransform: 'uppercase', letterSpacing: '-0.02em' }}>
              JobFinder AI
            </Typography>
            <Typography variant="caption" sx={{ color: '#FFE600', fontWeight: 900, fontSize: '0.7rem', textTransform: 'uppercase' }}>
              Web3 / HFT Alpha
            </Typography>
          </Box>
        </Stack>
      </Toolbar>

      <Divider sx={{ borderColor: 'rgba(0, 240, 255, 0.15)' }} />

      {/* Main Navigation */}
      <Box sx={{ px: 1.5, py: 2, flexGrow: 1 }}>
        <Typography variant="caption" sx={{ px: 1.5, py: 0.5, fontWeight: 900, color: '#00F0FF', display: 'block', textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: '0.7rem' }}>
          Autonomous Sourcing
        </Typography>

        <List sx={{ mt: 0.5, p: 0 }}>
          {mainNavItems.map((item) => {
            const isSelected = item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);

            return (
              <ListItem key={item.text} disablePadding sx={{ mb: 0.75 }}>
                <ListItemButton
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    borderRadius: '12px',
                    px: 1.5,
                    py: 1,
                    backgroundColor: isSelected ? 'rgba(0, 240, 255, 0.15)' : 'transparent',
                    border: isSelected ? '1.5px solid #00F0FF' : '1.5px solid transparent',
                    boxShadow: isSelected ? '0 0 15px rgba(0, 240, 255, 0.25)' : 'none',
                    transition: 'all 0.15s ease',
                    '&:hover': {
                      backgroundColor: 'rgba(0, 240, 255, 0.08)',
                      borderColor: 'rgba(0, 240, 255, 0.4)',
                      transform: 'translateX(3px)',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 34,
                      color: isSelected ? '#00FFA3' : '#94A3B8',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontSize: '0.85rem',
                      fontWeight: isSelected ? 900 : 700,
                      color: isSelected ? '#F8FAFC' : '#94A3B8',
                    }}
                  />
                  {item.tag && (
                    <Chip
                      label={item.tag}
                      size="small"
                      sx={{
                        height: 18,
                        fontSize: '0.65rem',
                        fontWeight: 900,
                        bgcolor: isSelected ? 'rgba(0, 255, 163, 0.2)' : 'rgba(0, 240, 255, 0.1)',
                        color: isSelected ? '#00FFA3' : '#00F0FF',
                        border: isSelected ? '1px solid #00FFA3' : '1px solid rgba(0, 240, 255, 0.3)',
                      }}
                    />
                  )}
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>

        <Typography variant="caption" sx={{ px: 1.5, pt: 2, pb: 0.5, fontWeight: 900, color: '#00F0FF', display: 'block', textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: '0.7rem' }}>
          Intelligence & Analytics
        </Typography>

        <List sx={{ mt: 0.5, p: 0 }}>
          {intelligenceNavItems.map((item) => {
            const isSelected = location.pathname === item.path;

            return (
              <ListItem key={item.text} disablePadding sx={{ mb: 0.75 }}>
                <ListItemButton
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    borderRadius: '12px',
                    px: 1.5,
                    py: 1,
                    backgroundColor: isSelected ? 'rgba(0, 240, 255, 0.15)' : 'transparent',
                    border: isSelected ? '1.5px solid #00F0FF' : '1.5px solid transparent',
                    boxShadow: isSelected ? '0 0 15px rgba(0, 240, 255, 0.25)' : 'none',
                    transition: 'all 0.15s ease',
                    '&:hover': {
                      backgroundColor: 'rgba(0, 240, 255, 0.08)',
                      borderColor: 'rgba(0, 240, 255, 0.4)',
                      transform: 'translateX(3px)',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 34,
                      color: isSelected ? '#00FFA3' : '#94A3B8',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontSize: '0.85rem',
                      fontWeight: isSelected ? 900 : 700,
                      color: isSelected ? '#F8FAFC' : '#94A3B8',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* Footer System Status Card */}
      <Box sx={{ p: 2, m: 1.5, borderRadius: '16px', bgcolor: '#0D131F', border: '1.5px solid rgba(0, 240, 255, 0.25)', boxShadow: '0 0 15px rgba(0, 0, 0, 0.5)' }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.75 }}>
          <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#00FFA3', boxShadow: '0 0 8px #00FFA3' }} />
          <Typography variant="caption" sx={{ fontWeight: 900, color: '#00FFA3', letterSpacing: '0.04em' }}>
            HFT CRAWLER: LIVE
          </Typography>
        </Stack>
        <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', fontSize: '0.72rem', lineHeight: 1.3 }}>
          2,050 jobs ingested across S&P 500, Nifty 500 & YC.
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box
      component="nav"
      sx={{
        width: { md: sidebarOpen ? DRAWER_WIDTH : 0 },
        flexShrink: { md: 0 },
      }}
    >
      {/* Mobile Drawer */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{
          keepMounted: true,
        }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: DRAWER_WIDTH,
            borderRight: '1.5px solid rgba(0, 240, 255, 0.25)',
            bgcolor: '#080C12',
          },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Desktop Drawer */}
      <Drawer
        variant="persistent"
        open={sidebarOpen}
        sx={{
          display: { xs: 'none', md: 'block' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: DRAWER_WIDTH,
            borderRight: '1.5px solid rgba(0, 240, 255, 0.2)',
            bgcolor: '#080C12',
          },
        }}
      >
        {drawerContent}
      </Drawer>
    </Box>
  );
};

export default Sidebar;

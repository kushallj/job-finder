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
} from '@mui/icons-material';
import { useUIStore } from '../../stores/useUIStore';

const DRAWER_WIDTH = 270;

interface SidebarProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const mainNavItems = [
  { text: 'Command Center', icon: <DashboardIcon fontSize="small" />, path: '/', tag: '100s' },
  { text: 'Speedrun Jobs', icon: <JobsIcon fontSize="small" />, path: '/jobs', tag: '2,050+' },
  { text: 'AI Agents Fleet', icon: <AgentsIcon fontSize="small" />, path: '/agents', tag: '15' },
  { text: 'AI OSINT Copilot', icon: <CopilotIcon fontSize="small" />, path: '/copilot', tag: 'AI' },
  { text: 'Global Remote Radar', icon: <GlobalIcon fontSize="small" />, path: '/market-radar' },
  { text: 'Decision Makers', icon: <ContactsIcon fontSize="small" />, path: '/contacts', tag: '1,043' },
  { text: 'Outreach Engine', icon: <OutreachIcon fontSize="small" />, path: '/outreach', tag: '211' },
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
    <Box sx={{ overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#0A0D0E' }}>
      {/* Fireship Brand Header */}
      <Toolbar sx={{ px: 3, py: 2.5, minHeight: 70 }}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Box
            sx={{
              width: 42,
              height: 42,
              borderRadius: '14px',
              bgcolor: '#FF3E00',
              border: '2.5px solid #000',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '4px 4px 0px #000',
              color: '#FFFFFF',
            }}
          >
            <FlameIcon sx={{ fontSize: '24px' }} />
          </Box>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F6F1D7', lineHeight: 1.1, textTransform: 'uppercase', letterSpacing: '-0.02em' }}>
              JobFinder <span style={{ color: '#FF3E00' }}>🔥</span>
            </Typography>
            <Typography variant="caption" sx={{ color: '#FFDE59', fontWeight: 900, fontSize: '0.7rem', textTransform: 'uppercase' }}>
              Fireship Speedrun
            </Typography>
          </Box>
        </Stack>
      </Toolbar>

      <Divider sx={{ borderColor: '#2A363F', borderWidth: '1px' }} />

      {/* Nav List */}
      <Box sx={{ px: 2, py: 2, flexGrow: 1 }}>
        <Typography
          variant="caption"
          sx={{ px: 1.5, py: 0.5, color: '#A0AEC0', fontWeight: 900, letterSpacing: '0.08em', textTransform: 'uppercase' }}
        >
          Speedrun Pipeline
        </Typography>
        <List sx={{ mt: 0.5, mb: 2 }}>
          {mainNavItems.map((item) => {
            const isSelected = location.pathname === item.path;
            return (
              <ListItem key={item.text} disablePadding sx={{ mb: 1 }}>
                <ListItemButton
                  selected={isSelected}
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    borderRadius: '12px',
                    py: 1.2,
                    px: 1.5,
                    border: '2px solid',
                    borderColor: isSelected ? '#000000' : 'transparent',
                    boxShadow: isSelected ? '4px 4px 0px #FFDE59' : 'none',
                    bgcolor: isSelected ? '#FF3E00' : 'transparent',
                    color: isSelected ? '#FFFFFF' : '#F6F1D7',
                    transition: 'all 0.12s ease',
                    '&:hover': {
                      bgcolor: isSelected ? '#FF5722' : '#181E24',
                      color: isSelected ? '#FFFFFF' : '#FFDE59',
                      transform: 'translate(-2px, -2px)',
                      boxShadow: '4px 4px 0px #000000',
                    },
                    '&.Mui-selected': {
                      bgcolor: '#FF3E00',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 32,
                      color: isSelected ? '#FFFFFF' : '#FF3E00',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontSize: '0.875rem',
                      fontWeight: 900,
                      textTransform: 'uppercase',
                    }}
                  />
                  {item.tag && (
                    <Chip
                      label={item.tag}
                      size="small"
                      sx={{
                        fontSize: '0.65rem',
                        height: 20,
                        bgcolor: isSelected ? '#000000' : '#181E24',
                        color: isSelected ? '#FFDE59' : '#00E676',
                        border: '1.5px solid #000',
                      }}
                    />
                  )}
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>

        <Typography
          variant="caption"
          sx={{ px: 1.5, py: 0.5, color: '#A0AEC0', fontWeight: 900, letterSpacing: '0.08em', textTransform: 'uppercase' }}
        >
          Config & Intel
        </Typography>
        <List sx={{ mt: 0.5 }}>
          {intelligenceNavItems.map((item) => {
            const isSelected = location.pathname === item.path;
            return (
              <ListItem key={item.text} disablePadding sx={{ mb: 1 }}>
                <ListItemButton
                  selected={isSelected}
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    borderRadius: '12px',
                    py: 1.2,
                    px: 1.5,
                    border: '2px solid',
                    borderColor: isSelected ? '#000000' : 'transparent',
                    boxShadow: isSelected ? '4px 4px 0px #FFDE59' : 'none',
                    bgcolor: isSelected ? '#FF3E00' : 'transparent',
                    color: isSelected ? '#FFFFFF' : '#F6F1D7',
                    transition: 'all 0.12s ease',
                    '&:hover': {
                      bgcolor: isSelected ? '#FF5722' : '#181E24',
                      color: isSelected ? '#FFFFFF' : '#FFDE59',
                      transform: 'translate(-2px, -2px)',
                      boxShadow: '4px 4px 0px #000000',
                    },
                    '&.Mui-selected': {
                      bgcolor: '#FF3E00',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 32,
                      color: isSelected ? '#FFFFFF' : '#FF3E00',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontSize: '0.875rem',
                      fontWeight: 900,
                      textTransform: 'uppercase',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* Footer Sticker Card */}
      <Box sx={{ p: 2, m: 2, borderRadius: '16px', bgcolor: '#12181B', border: '2.5px solid #000', boxShadow: '4px 4px 0px #000' }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
          <span style={{ fontSize: '18px' }}>🚀</span>
          <Typography variant="caption" sx={{ fontWeight: 900, color: '#FFDE59', textTransform: 'uppercase' }}>
            Push to Prod
          </Typography>
        </Stack>
        <Typography variant="caption" sx={{ color: '#A0AEC0', display: 'block', fontSize: '0.72rem', lineHeight: 1.3 }}>
          2,050 live jobs in S&P 500 & Nifty 500 with automatic &le; 2/company cap.
        </Typography>
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
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH, borderRight: '3px solid #2A363F', bgcolor: '#0A0D0E' },
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
            borderRight: '3px solid #2A363F',
            bgcolor: '#0A0D0E',
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

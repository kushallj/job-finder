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
  alpha,
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
  { text: 'AI Agents', icon: <AgentsIcon fontSize="small" />, path: '/agents' },
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
    <Box sx={{ overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#FFFFFF' }}>
      {/* Brand Header */}
      <Toolbar sx={{ px: 3, py: 2.5, minHeight: 70 }}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Box
            sx={{
              width: 38,
              height: 38,
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(79, 70, 229, 0.3)',
              color: '#FFFFFF',
            }}
          >
            <SparkleIcon fontSize="small" />
          </Box>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 800, color: '#0F172A', lineHeight: 1.1 }}>
              JobFinder <span style={{ color: '#4F46E5' }}>AI</span>
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600, fontSize: '0.7rem' }}>
              Autonomous Career CRM
            </Typography>
          </Box>
        </Stack>
      </Toolbar>

      <Divider sx={{ borderColor: '#F1F5F9' }} />

      {/* Nav List */}
      <Box sx={{ px: 2, py: 2, flexGrow: 1 }}>
        <Typography
          variant="caption"
          sx={{ px: 1.5, py: 0.5, color: '#94A3B8', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}
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
                    color: isSelected ? '#4F46E5' : '#475569',
                    backgroundColor: isSelected ? alpha('#4F46E5', 0.08) : 'transparent',
                    fontWeight: isSelected ? 700 : 500,
                    '&:hover': {
                      backgroundColor: isSelected ? alpha('#4F46E5', 0.12) : '#F8FAFC',
                      color: isSelected ? '#4F46E5' : '#0F172A',
                    },
                    '&.Mui-selected': {
                      backgroundColor: alpha('#4F46E5', 0.08),
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 32,
                      color: isSelected ? '#4F46E5' : '#64748B',
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
          sx={{ px: 1.5, py: 0.5, color: '#94A3B8', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}
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
                    color: isSelected ? '#4F46E5' : '#475569',
                    backgroundColor: isSelected ? alpha('#4F46E5', 0.08) : 'transparent',
                    '&:hover': {
                      backgroundColor: isSelected ? alpha('#4F46E5', 0.12) : '#F8FAFC',
                      color: isSelected ? '#4F46E5' : '#0F172A',
                    },
                    '&.Mui-selected': {
                      backgroundColor: alpha('#4F46E5', 0.08),
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 32,
                      color: isSelected ? '#4F46E5' : '#64748B',
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

      {/* Footer System Status Card */}
      <Box sx={{ p: 2, m: 2, borderRadius: '12px', bgcolor: '#F8FAFC', border: '1px solid #E2E8F0' }}>
        <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: '#10B981',
              boxShadow: '0 0 0 3px rgba(16, 185, 129, 0.2)',
            }}
          />
          <Typography variant="caption" sx={{ fontWeight: 700, color: '#0F172A' }}>
            AI Pipeline Ready
          </Typography>
        </Stack>
        <Typography variant="caption" sx={{ color: '#64748B', display: 'block', fontSize: '0.72rem', lineHeight: 1.3 }}>
          15 autonomous agents active with resume routing & outreach scheduler.
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
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH, borderRight: '1px solid #E2E8F0' },
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
            borderRight: '1px solid #E2E8F0',
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

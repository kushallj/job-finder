import React, { useState } from 'react';
import {
  Box,
  Toolbar,
  useTheme,
  Paper,
  BottomNavigation,
  BottomNavigationAction,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Work as JobsIcon,
  SmartToy as AgentsIcon,
  Send as OutreachIcon,
  BarChart as StatsIcon,
} from '@mui/icons-material';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import Header, { DRAWER_WIDTH } from './Header';
import Sidebar from './Sidebar';
import { useUIStore } from '../../stores/useUIStore';

// Map paths to titles
const pageTitles: Record<string, string> = {
  '/': 'Command Center',
  '/jobs': 'Opportunities & Alpha Pipeline',
  '/contacts': 'Decision Makers CRM',
  '/outreach': 'Outreach Engine',
  '/stats': 'Analytics & Funnel',
  '/settings': 'Settings & System Health',
  '/agents': 'Autonomous Agents Hub',
  '/copilot': 'AI OSINT Copilot',
  '/market-radar': 'Global Remote Radar',
};

export const Layout: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const { sidebarOpen } = useUIStore();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const handleMobileToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleMobileClose = () => {
    setMobileOpen(false);
  };

  let currentTitle = pageTitles[location.pathname];
  if (!currentTitle && location.pathname.startsWith('/opportunities/')) {
    currentTitle = 'Executive Opportunity Brief';
  }
  if (!currentTitle) {
    currentTitle = 'JobFinder AI';
  }

  const getActiveTab = () => {
    const path = location.pathname;
    if (path === '/') return '/';
    if (path.startsWith('/jobs') || path.startsWith('/opportunities')) return '/jobs';
    if (path.startsWith('/agents') || path.startsWith('/copilot')) return '/agents';
    if (path.startsWith('/outreach')) return '/outreach';
    if (path.startsWith('/stats')) return '/stats';
    return '/';
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', width: '100%', bgcolor: '#06090E', overflowX: 'hidden' }}>
      <Header onMenuClick={handleMobileToggle} title={currentTitle} />
      <Sidebar mobileOpen={mobileOpen} onMobileClose={handleMobileClose} />

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          px: { xs: 2, sm: 3, md: 4, lg: 5 },
          py: { xs: 2, sm: 3, md: 3.5 },
          pb: { xs: 10, md: 5 }, // Extra bottom padding on mobile for BottomNavigation bar
          width: { md: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%' },
          ml: { md: sidebarOpen ? `${DRAWER_WIDTH}px` : 0 },
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          backgroundColor: '#06090E',
          minHeight: '100vh',
          maxWidth: '100%',
          overflowX: 'hidden',
        }}
      >
        <Toolbar sx={{ minHeight: '68px', height: '68px' }} />
        <Box sx={{ maxWidth: 1440, mx: 'auto', width: '100%' }}>
          <Outlet />
        </Box>
      </Box>

      {/* ── Mobile 1-Thumb Bottom Navigation Bar (Hidden on md/desktop) ── */}
      <Paper
        sx={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          display: { xs: 'block', md: 'none' },
          zIndex: 1200,
          borderTop: '1.5px solid rgba(0, 240, 255, 0.25)',
          bgcolor: '#080C12',
          backdropFilter: 'blur(20px)',
        }}
        elevation={6}
      >
        <BottomNavigation
          showLabels
          value={getActiveTab()}
          onChange={(_event, newValue) => {
            navigate(newValue);
          }}
          sx={{
            bgcolor: 'transparent',
            height: 64,
            '& .MuiBottomNavigationAction-root': {
              minWidth: 'auto',
              padding: '6px 0',
              color: '#94A3B8',
              '&.Mui-selected': {
                color: '#00FFA3',
                '& .MuiBottomNavigationAction-label': {
                  fontSize: '0.72rem',
                  fontWeight: 800,
                },
              },
            },
          }}
        >
          <BottomNavigationAction label="Command" value="/" icon={<DashboardIcon fontSize="small" />} />
          <BottomNavigationAction label="Jobs" value="/jobs" icon={<JobsIcon fontSize="small" />} />
          <BottomNavigationAction label="AI Agents" value="/agents" icon={<AgentsIcon fontSize="small" />} />
          <BottomNavigationAction label="Outreach" value="/outreach" icon={<OutreachIcon fontSize="small" />} />
          <BottomNavigationAction label="Analytics" value="/stats" icon={<StatsIcon fontSize="small" />} />
        </BottomNavigation>
      </Paper>
    </Box>
  );
};

export default Layout;

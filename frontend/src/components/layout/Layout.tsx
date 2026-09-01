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
import Header from './Header';
import Sidebar from './Sidebar';
import { useUIStore } from '../../stores/useUIStore';

const DRAWER_WIDTH = 260;

// Map paths to titles
const pageTitles: Record<string, string> = {
  '/': 'Command Center',
  '/jobs': 'Opportunities & Jobs',
  '/contacts': 'Contacts CRM',
  '/outreach': 'Outreach Engine',
  '/stats': 'Analytics & Funnel',
  '/settings': 'Settings & System Health',
  '/agents': 'Autonomous Agents Hub',
  '/copilot': 'AI Career Copilot',
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

  // Handle dynamic paths like /opportunities/:id
  let currentTitle = pageTitles[location.pathname];
  if (!currentTitle && location.pathname.startsWith('/opportunities/')) {
    currentTitle = 'Executive Opportunity Brief';
  }
  if (!currentTitle) {
    currentTitle = 'Job Finder AI';
  }

  // Determine current active mobile bottom tab
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
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#F8FAFC' }}>
      <Header onMenuClick={handleMobileToggle} title={currentTitle} />
      <Sidebar mobileOpen={mobileOpen} onMobileClose={handleMobileClose} />

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 1.5, sm: 2.5, md: 4 },
          pb: { xs: 9, md: 4 }, // Extra bottom padding on mobile for BottomNavigation bar
          width: { md: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%' },
          ml: { md: sidebarOpen ? `${DRAWER_WIDTH}px` : 0 },
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          backgroundColor: 'background.default',
          minHeight: '100vh',
          maxWidth: '100%',
          overflowX: 'hidden',
        }}
      >
        <Toolbar sx={{ minHeight: { xs: '56px', sm: '70px' } }} />
        <Outlet />
      </Box>

      {/* ── Mobile 1-Thumb Bottom Navigation Bar (Hidden on md/desktop) ── */}
      <Paper
        sx={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          display: { xs: 'block', md: 'none' },
          zIndex: 1300,
          borderTop: '1px solid #E2E8F0',
          boxShadow: '0 -4px 16px rgba(0,0,0,0.06)',
          bgcolor: '#FFFFFF',
        }}
        elevation={3}
      >
        <BottomNavigation
          showLabels
          value={getActiveTab()}
          onChange={(_event, newValue) => {
            navigate(newValue);
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
          sx={{
            height: 62,
            '& .MuiBottomNavigationAction-root': {
              minWidth: 0,
              padding: '6px 0',
              color: '#64748B',
              '&.Mui-selected': {
                color: '#4F46E5',
                fontWeight: 700,
              },
            },
          }}
        >
          <BottomNavigationAction label="Dashboard" value="/" icon={<DashboardIcon fontSize="small" />} />
          <BottomNavigationAction label="Jobs" value="/jobs" icon={<JobsIcon fontSize="small" />} />
          <BottomNavigationAction label="Agents" value="/agents" icon={<AgentsIcon fontSize="small" />} />
          <BottomNavigationAction label="Outreach" value="/outreach" icon={<OutreachIcon fontSize="small" />} />
          <BottomNavigationAction label="Stats" value="/stats" icon={<StatsIcon fontSize="small" />} />
        </BottomNavigation>
      </Paper>
    </Box>
  );
};

export default Layout;

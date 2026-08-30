import React, { useState } from 'react';
import { Box, Toolbar, useTheme } from '@mui/material';
import { Outlet, useLocation } from 'react-router-dom';
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
};

export const Layout: React.FC = () => {
  const theme = useTheme();
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

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#F8FAFC' }}>
      <Header onMenuClick={handleMobileToggle} title={currentTitle} />
      <Sidebar mobileOpen={mobileOpen} onMobileClose={handleMobileClose} />
      
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, sm: 3, md: 4 },
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
        <Toolbar sx={{ minHeight: '70px !important' }} />
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;

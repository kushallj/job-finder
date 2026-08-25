import React, { useState } from 'react';
import { Box, Toolbar, useTheme } from '@mui/material';
import { Outlet, useLocation } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import { useUIStore } from '../../stores/useUIStore';

const DRAWER_WIDTH = 240;

// Map paths to titles
const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/jobs': 'Jobs',
  '/contacts': 'Contacts',
  '/outreach': 'Outreach',
  '/stats': 'Statistics',
  '/discovery': 'Startup Discovery',
  '/settings': 'Settings',
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

  // Get current page title
  const currentTitle = pageTitles[location.pathname] || 'Job Finder';

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Header onMenuClick={handleMobileToggle} title={currentTitle} />
      <Sidebar mobileOpen={mobileOpen} onMobileClose={handleMobileClose} />
      
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%' },
          ml: { md: sidebarOpen ? `${DRAWER_WIDTH}px` : 0 },
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          backgroundColor: 'background.default',
          minHeight: '100vh',
        }}
      >
        <Toolbar /> {/* Spacer for fixed header */}
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;


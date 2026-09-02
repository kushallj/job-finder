import React from 'react';
import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Box,
  useTheme,
  Button,
  Chip,
  Stack,
} from '@mui/material';

import {
  Menu as MenuIcon,
  RefreshOutlined as RefreshIcon,
  Bolt as ActionIcon,
  CheckCircle as HealthyIcon,
} from '@mui/icons-material';
import { useUIStore } from '../../stores/useUIStore';
import { useNavigate } from 'react-router-dom';

const DRAWER_WIDTH = 260;

interface HeaderProps {
  onMenuClick: () => void;
  title: string;
}

export const Header: React.FC<HeaderProps> = ({ onMenuClick, title }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const { sidebarOpen, toggleSidebar } = useUIStore();

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        width: { md: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%' },
        ml: { md: sidebarOpen ? `${DRAWER_WIDTH}px` : 0 },
        transition: theme.transitions.create(['width', 'margin'], {
          easing: theme.transitions.easing.sharp,
          duration: theme.transitions.duration.leavingScreen,
        }),
        backgroundColor: 'rgba(11, 15, 25, 0.85)',
        backdropFilter: 'blur(16px)',
        color: '#F8FAFC',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        zIndex: theme.zIndex.drawer + 1,
      }}
    >
      <Toolbar sx={{ minHeight: 70, px: { xs: 2, sm: 3 } }}>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={onMenuClick}
          sx={{ mr: 2, display: { md: 'none' } }}
        >
          <MenuIcon />
        </IconButton>

        <IconButton
          color="inherit"
          aria-label="toggle sidebar"
          edge="start"
          onClick={toggleSidebar}
          sx={{ mr: 2, display: { xs: 'none', md: 'flex' }, color: '#94A3B8', '&:hover': { color: '#38BDF8' } }}
        >
          <MenuIcon />
        </IconButton>

        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 800, color: '#F8FAFC', letterSpacing: '-0.025em' }}>
            {title}
          </Typography>
        </Box>

        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Chip
            icon={<HealthyIcon sx={{ fontSize: '14px !important', color: '#34D399 !important' }} />}
            label="System Online"
            size="small"
            sx={{
              bgcolor: 'rgba(52, 211, 153, 0.12)',
              color: '#34D399',
              border: '1px solid rgba(52, 211, 153, 0.3)',
              fontWeight: 700,
              fontSize: '0.75rem',
              display: { xs: 'none', sm: 'inline-flex' },
            }}
          />

          <Button
            variant="contained"
            size="small"
            color="primary"
            startIcon={<ActionIcon fontSize="small" />}
            onClick={() => navigate('/jobs')}
            sx={{
              display: { xs: 'none', sm: 'inline-flex' },
              fontWeight: 700,
            }}
          >
            Explore Jobs
          </Button>

          <IconButton
            color="inherit"
            title="Refresh View"
            onClick={() => window.location.reload()}
            sx={{
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '10px',
              p: 1,
              color: '#94A3B8',
              backgroundColor: 'rgba(255, 255, 255, 0.02)',
              '&:hover': { bgcolor: 'rgba(56, 189, 248, 0.1)', color: '#38BDF8', borderColor: 'rgba(56, 189, 248, 0.3)' },
            }}
          >
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Stack>
      </Toolbar>
    </AppBar>
  );
};

export default Header;

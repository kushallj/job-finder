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
  alpha,
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
        backgroundColor: '#FFFFFF',
        color: '#0F172A',
        borderBottom: '1px solid #E2E8F0',
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
          sx={{ mr: 2, display: { xs: 'none', md: 'flex' } }}
        >
          <MenuIcon />
        </IconButton>

        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em' }}>
            {title}
          </Typography>
        </Box>

        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Chip
            icon={<HealthyIcon sx={{ fontSize: '14px !important', color: '#10B981 !important' }} />}
            label="System Online"
            size="small"
            sx={{
              bgcolor: alpha('#10B981', 0.08),
              color: '#059669',
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
              boxShadow: '0 2px 8px rgba(79, 70, 229, 0.25)',
            }}
          >
            Explore Jobs
          </Button>

          <IconButton
            color="inherit"
            title="Refresh View"
            onClick={() => window.location.reload()}
            sx={{
              border: '1px solid #E2E8F0',
              borderRadius: '10px',
              p: 1,
              '&:hover': { bgcolor: '#F8FAFC' },
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

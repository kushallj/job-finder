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
  LocalFireDepartment as FlameIcon,
} from '@mui/icons-material';
import { useUIStore } from '../../stores/useUIStore';
import { useNavigate } from 'react-router-dom';

export const DRAWER_WIDTH = 260;

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
        backgroundColor: '#080C12',
        color: '#F8FAFC',
        borderBottom: '1.5px solid rgba(0, 240, 255, 0.2)',
        boxShadow: '0 4px 24px rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(16px)',
        zIndex: theme.zIndex.drawer + 1,
      }}
    >
      <Toolbar sx={{ minHeight: '68px', height: '68px', px: { xs: 2, sm: 3, md: 4 } }}>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={onMenuClick}
          sx={{ mr: 1.5, display: { md: 'none' }, color: '#00F0FF' }}
        >
          <MenuIcon />
        </IconButton>

        <IconButton
          color="inherit"
          aria-label="toggle sidebar"
          edge="start"
          onClick={toggleSidebar}
          sx={{ mr: 2, display: { xs: 'none', md: 'flex' }, color: '#94A3B8', '&:hover': { color: '#00F0FF' } }}
        >
          <MenuIcon />
        </IconButton>

        <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 900, color: '#F8FAFC', letterSpacing: '-0.02em', textTransform: 'uppercase' }}>
            {title}
          </Typography>
          <Chip
            icon={<FlameIcon sx={{ fontSize: '15px !important', color: '#00FFA3 !important' }} />}
            label="HFT Liquidity"
            size="small"
            sx={{
              bgcolor: 'rgba(0, 255, 163, 0.15)',
              color: '#00FFA3',
              border: '1px solid rgba(0, 255, 163, 0.4)',
              fontWeight: 900,
              display: { xs: 'none', sm: 'inline-flex' },
            }}
          />
        </Box>

        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Chip
            label="2,050+ Live Pools"
            size="small"
            sx={{
              bgcolor: 'rgba(0, 240, 255, 0.15)',
              color: '#00F0FF',
              border: '1px solid rgba(0, 240, 255, 0.4)',
              fontWeight: 900,
              display: { xs: 'none', md: 'inline-flex' },
            }}
          />

          <Button
            variant="contained"
            color="primary"
            size="small"
            startIcon={<ActionIcon />}
            onClick={() => navigate('/jobs')}
            sx={{ fontWeight: 900, px: 2, py: 0.8, fontSize: '0.8rem' }}
          >
            ⚡ Alpha Jobs
          </Button>

          <IconButton
            size="small"
            onClick={() => window.location.reload()}
            title="Hard Reload UI"
            sx={{
              p: 1,
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(0, 240, 255, 0.25)',
              color: '#00F0FF',
              '&:hover': { bgcolor: 'rgba(0, 240, 255, 0.15)', borderColor: '#00F0FF' },
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

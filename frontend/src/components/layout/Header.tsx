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

const DRAWER_WIDTH = 270;

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
        backgroundColor: '#0A0D0E',
        color: '#F6F1D7',
        borderBottom: '3px solid #2A363F',
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
          sx={{ mr: 2, display: { xs: 'none', md: 'flex' }, color: '#A0AEC0', '&:hover': { color: '#FFDE59' } }}
        >
          <MenuIcon />
        </IconButton>

        <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 900, color: '#F6F1D7', letterSpacing: '-0.02em', textTransform: 'uppercase' }}>
            {title}
          </Typography>
          <Chip
            icon={<FlameIcon sx={{ fontSize: '15px !important', color: '#FF3E00 !important' }} />}
            label="100s Mode"
            size="small"
            sx={{
              bgcolor: '#FFDE59',
              color: '#0A0D0E',
              border: '2px solid #000',
              fontWeight: 900,
              display: { xs: 'none', sm: 'inline-flex' },
            }}
          />
        </Box>

        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Chip
            label="2,050+ Live Jobs"
            size="small"
            sx={{
              bgcolor: '#00E676',
              color: '#0A0D0E',
              border: '2px solid #000',
              fontWeight: 900,
              display: { xs: 'none', md: 'inline-flex' },
            }}
          />

          <Button
            variant="contained"
            color="primary"
            size="small"
            startIcon={<ActionIcon fontSize="small" />}
            onClick={() => navigate('/jobs')}
            sx={{
              display: { xs: 'none', sm: 'inline-flex' },
            }}
          >
            Speedrun Jobs
          </Button>

          <IconButton
            color="inherit"
            title="Refresh View"
            onClick={() => window.location.reload()}
            sx={{
              border: '2px solid #000',
              borderRadius: '12px',
              p: 1,
              bgcolor: '#12181B',
              color: '#F6F1D7',
              boxShadow: '3px 3px 0px #000',
              '&:hover': { bgcolor: '#FFDE59', color: '#0A0D0E', transform: 'translate(-1px, -1px)', boxShadow: '4px 4px 0px #FF3E00' },
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

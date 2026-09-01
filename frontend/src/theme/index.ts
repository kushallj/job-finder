import { createTheme, alpha } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#4F46E5', // Modern Indigo
      light: '#6366F1',
      dark: '#3730A3',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#7C3AED', // Electric Violet
      light: '#8B5CF6',
      dark: '#5B21B6',
      contrastText: '#FFFFFF',
    },
    success: {
      main: '#10B981', // Emerald
      light: '#34D399',
      dark: '#047857',
      contrastText: '#FFFFFF',
    },
    warning: {
      main: '#F59E0B', // Warm Amber
      light: '#FBBF24',
      dark: '#B45309',
      contrastText: '#FFFFFF',
    },
    error: {
      main: '#EF4444', // Rose Red
      light: '#F87171',
      dark: '#B91C1C',
      contrastText: '#FFFFFF',
    },
    info: {
      main: '#06B6D4', // Cyan
      light: '#22D3EE',
      dark: '#0E7490',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#F8FAFC', // Slate 50
      paper: '#FFFFFF',
    },
    text: {
      primary: '#0F172A', // Slate 900
      secondary: '#64748B', // Slate 500
      disabled: '#94A3B8',
    },
    divider: '#E2E8F0', // Slate 200
  },
  typography: {
    fontFamily: '"Plus Jakarta Sans", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 800,
      letterSpacing: '-0.03em',
      lineHeight: 1.2,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 700,
      letterSpacing: '-0.025em',
      lineHeight: 1.25,
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
      lineHeight: 1.3,
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 700,
      letterSpacing: '-0.015em',
      lineHeight: 1.35,
    },
    h5: {
      fontSize: '1.1rem',
      fontWeight: 600,
      letterSpacing: '-0.01em',
      lineHeight: 1.4,
    },
    h6: {
      fontSize: '0.95rem',
      fontWeight: 600,
      letterSpacing: '-0.005em',
      lineHeight: 1.45,
    },
    subtitle1: {
      fontSize: '0.95rem',
      fontWeight: 500,
      lineHeight: 1.5,
    },
    subtitle2: {
      fontSize: '0.85rem',
      fontWeight: 600,
      lineHeight: 1.5,
    },
    body1: {
      fontSize: '0.925rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.825rem',
      lineHeight: 1.55,
    },
    button: {
      textTransform: 'none',
      fontWeight: 600,
      fontSize: '0.875rem',
      letterSpacing: '0.01em',
    },
    caption: {
      fontSize: '0.75rem',
      fontWeight: 500,
      letterSpacing: '0.02em',
    },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: [
    'none',
    '0 1px 2px 0 rgba(0, 0, 0, 0.03)',
    '0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px -1px rgba(0, 0, 0, 0.06)',
    '0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
    '0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04)',
    '0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)',
    '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
    ...Array(18).fill('0 10px 15px -3px rgba(0, 0, 0, 0.08)'),
  ] as any,
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#F8FAFC',
          scrollbarColor: '#CBD5E1 transparent',
          '&::-webkit-scrollbar': {
            width: 8,
            height: 8,
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#CBD5E1',
            borderRadius: 4,
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#94A3B8',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          padding: '8px 18px',
          boxShadow: 'none',
          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(79, 70, 229, 0.25)',
            transform: 'translateY(-1px)',
          },
          '&:active': {
            transform: 'translateY(0)',
          },
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #4F46E5 0%, #4338CA 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #4338CA 0%, #3730A3 100%)',
          },
        },
        containedSuccess: {
          background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
          },
        },
        outlined: {
          borderWidth: '1.5px',
          borderColor: '#E2E8F0',
          backgroundColor: '#FFFFFF',
          color: '#334155',
          '&:hover': {
            borderWidth: '1.5px',
            borderColor: '#CBD5E1',
            backgroundColor: '#F8FAFC',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid #E2E8F0',
          backgroundColor: '#FFFFFF',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.02)',
          transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid #E2E8F0',
          backgroundImage: 'none',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          fontSize: '0.75rem',
          borderRadius: 8,
          transition: 'all 0.2s ease',
        },
        colorPrimary: {
          backgroundColor: alpha('#4F46E5', 0.1),
          color: '#4F46E5',
          border: `1px solid ${alpha('#4F46E5', 0.2)}`,
        },
        colorSuccess: {
          backgroundColor: alpha('#10B981', 0.1),
          color: '#059669',
          border: `1px solid ${alpha('#10B981', 0.2)}`,
        },
        colorWarning: {
          backgroundColor: alpha('#F59E0B', 0.1),
          color: '#D97706',
          border: `1px solid ${alpha('#F59E0B', 0.2)}`,
        },
        colorError: {
          backgroundColor: alpha('#EF4444', 0.1),
          color: '#DC2626',
          border: `1px solid ${alpha('#EF4444', 0.2)}`,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 10,
            backgroundColor: '#FFFFFF',
            transition: 'all 0.2s ease',
            '& fieldset': {
              borderColor: '#E2E8F0',
              borderWidth: '1.5px',
            },
            '&:hover fieldset': {
              borderColor: '#CBD5E1',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#4F46E5',
              borderWidth: '2px',
            },
          },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          backgroundColor: '#EEF2F6',
        },
        bar: {
          borderRadius: 8,
          backgroundImage: 'linear-gradient(90deg, #4F46E5 0%, #8B5CF6 100%)',
        },
      },
    },
  },
});

export { theme };
export default theme;


import { createTheme } from '@mui/material/styles';


/**
 * UI.dev Design System Theme for JobFinder AI
 * 
 * Signature Aesthetics:
 * - Deep Obsidian Navy Canvas (#0B0F19)
 * - Translucent Glassmorphism Cards (#111827 / #161F30) with fine borders
 * - Vibrant Neon Accents: Electric Cyan (#38BDF8), Modern Indigo (#6366F1), Violet (#A855F7)
 * - Crisp High-Contrast Typography with Geometric Sans & Monospace Accents
 * - Glowing Pill Badges, Linear Progress Gradients & Micro-interactions
 */

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#38BDF8', // Electric Cyan
      light: '#7DD3FC',
      dark: '#0284C7',
      contrastText: '#0B0F19',
    },
    secondary: {
      main: '#818CF8', // Neon Indigo
      light: '#A5B4FC',
      dark: '#4F46E5',
      contrastText: '#FFFFFF',
    },
    success: {
      main: '#34D399', // Emerald Neon
      light: '#6EE7B7',
      dark: '#059669',
      contrastText: '#0B0F19',
    },
    warning: {
      main: '#FBBF24', // Amber
      light: '#FDE68A',
      dark: '#D97706',
      contrastText: '#0B0F19',
    },
    error: {
      main: '#F87171', // Coral Rose
      light: '#FCA5A5',
      dark: '#DC2626',
      contrastText: '#FFFFFF',
    },
    info: {
      main: '#22D3EE', // Sky Cyan
      light: '#67E8F9',
      dark: '#0891B2',
      contrastText: '#0B0F19',
    },
    background: {
      default: '#0B0F19', // Deep Obsidian Dark
      paper: '#111827',   // Slate Navy Surface
    },
    text: {
      primary: '#F8FAFC',   // Pure White/Slate
      secondary: '#94A3B8', // Soft Muted Slate
      disabled: '#64748B',
    },
    divider: 'rgba(255, 255, 255, 0.08)', // Fine subtle divider
  },
  typography: {
    fontFamily: '"Plus Jakarta Sans", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 800,
      letterSpacing: '-0.035em',
      lineHeight: 1.2,
      color: '#F8FAFC',
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 700,
      letterSpacing: '-0.03em',
      lineHeight: 1.25,
      color: '#F8FAFC',
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 700,
      letterSpacing: '-0.025em',
      lineHeight: 1.3,
      color: '#F8FAFC',
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
      lineHeight: 1.35,
      color: '#F8FAFC',
    },
    h5: {
      fontSize: '1.1rem',
      fontWeight: 600,
      letterSpacing: '-0.015em',
      lineHeight: 1.4,
      color: '#F8FAFC',
    },
    h6: {
      fontSize: '0.95rem',
      fontWeight: 600,
      letterSpacing: '-0.01em',
      lineHeight: 1.45,
      color: '#F8FAFC',
    },
    subtitle1: {
      fontSize: '0.95rem',
      fontWeight: 500,
      lineHeight: 1.5,
      color: '#94A3B8',
    },
    subtitle2: {
      fontSize: '0.85rem',
      fontWeight: 600,
      lineHeight: 1.5,
      color: '#CBD5E1',
    },
    body1: {
      fontSize: '0.925rem',
      lineHeight: 1.6,
      color: '#E2E8F0',
    },
    body2: {
      fontSize: '0.825rem',
      lineHeight: 1.55,
      color: '#94A3B8',
    },
    button: {
      textTransform: 'none',
      fontWeight: 700,
      fontSize: '0.875rem',
      letterSpacing: '0.01em',
    },
    caption: {
      fontSize: '0.75rem',
      fontWeight: 500,
      letterSpacing: '0.02em',
      color: '#64748B',
    },
  },
  shape: {
    borderRadius: 14,
  },
  shadows: [
    'none',
    '0 1px 2px 0 rgba(0, 0, 0, 0.4)',
    '0 1px 3px 0 rgba(0, 0, 0, 0.5), 0 1px 2px -1px rgba(0, 0, 0, 0.4)',
    '0 4px 6px -1px rgba(0, 0, 0, 0.6), 0 2px 4px -2px rgba(0, 0, 0, 0.4)',
    '0 10px 15px -3px rgba(0, 0, 0, 0.6), 0 4px 6px -4px rgba(0, 0, 0, 0.4)',
    '0 20px 25px -5px rgba(0, 0, 0, 0.7), 0 8px 10px -6px rgba(0, 0, 0, 0.5)',
    '0 25px 50px -12px rgba(0, 0, 0, 0.85)',
    ...Array(18).fill('0 10px 25px -5px rgba(0, 0, 0, 0.7)'),
  ] as any,
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#0B0F19',
          color: '#F8FAFC',
          backgroundImage: 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.12), transparent)',
          scrollbarColor: '#334155 transparent',
          '&::-webkit-scrollbar': {
            width: 8,
            height: 8,
          },
          '&::-webkit-scrollbar-track': {
            background: '#0B0F19',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#1E293B',
            borderRadius: 4,
            border: '2px solid #0B0F19',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#334155',
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
            transform: 'translateY(-1px)',
          },
          '&:active': {
            transform: 'translateY(0)',
          },
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #6366F1 0%, #38BDF8 100%)',
          color: '#0B0F19',
          fontWeight: 700,
          boxShadow: '0 4px 14px rgba(56, 189, 248, 0.3)',
          '&:hover': {
            background: 'linear-gradient(135deg, #4F46E5 0%, #0284C7 100%)',
            boxShadow: '0 6px 20px rgba(56, 189, 248, 0.45)',
          },
        },
        containedSecondary: {
          background: 'linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%)',
          color: '#FFFFFF',
          fontWeight: 700,
          boxShadow: '0 4px 14px rgba(139, 92, 246, 0.3)',
          '&:hover': {
            background: 'linear-gradient(135deg, #7C3AED 0%, #DB2777 100%)',
            boxShadow: '0 6px 20px rgba(139, 92, 246, 0.45)',
          },
        },
        containedSuccess: {
          background: 'linear-gradient(135deg, #10B981 0%, #34D399 100%)',
          color: '#0B0F19',
          fontWeight: 700,
          boxShadow: '0 4px 14px rgba(52, 211, 153, 0.3)',
          '&:hover': {
            background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
            boxShadow: '0 6px 20px rgba(52, 211, 153, 0.45)',
          },
        },
        outlined: {
          borderWidth: '1px',
          borderColor: 'rgba(255, 255, 255, 0.12)',
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          color: '#F8FAFC',
          backdropFilter: 'blur(8px)',
          '&:hover': {
            borderWidth: '1px',
            borderColor: 'rgba(56, 189, 248, 0.4)',
            backgroundColor: 'rgba(56, 189, 248, 0.06)',
            boxShadow: '0 0 15px rgba(56, 189, 248, 0.15)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: '#111827',
          backgroundImage: 'linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0) 100%)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.35)',
          transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            borderColor: 'rgba(99, 102, 241, 0.35)',
            boxShadow: '0 10px 30px -10px rgba(99, 102, 241, 0.25)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: '#111827',
          backgroundImage: 'none',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 700,
          fontSize: '0.75rem',
          borderRadius: 8,
          transition: 'all 0.2s ease',
        },
        colorPrimary: {
          backgroundColor: 'rgba(56, 189, 248, 0.12)',
          color: '#38BDF8',
          border: '1px solid rgba(56, 189, 248, 0.3)',
        },
        colorSecondary: {
          backgroundColor: 'rgba(129, 140, 248, 0.12)',
          color: '#818CF8',
          border: '1px solid rgba(129, 140, 248, 0.3)',
        },
        colorSuccess: {
          backgroundColor: 'rgba(52, 211, 153, 0.12)',
          color: '#34D399',
          border: '1px solid rgba(52, 211, 153, 0.3)',
        },
        colorWarning: {
          backgroundColor: 'rgba(251, 191, 36, 0.12)',
          color: '#FBBF24',
          border: '1px solid rgba(251, 191, 36, 0.3)',
        },
        colorError: {
          backgroundColor: 'rgba(248, 113, 113, 0.12)',
          color: '#F87171',
          border: '1px solid rgba(248, 113, 113, 0.3)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 10,
            backgroundColor: '#0F172A',
            transition: 'all 0.2s ease',
            color: '#F8FAFC',
            '& fieldset': {
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderWidth: '1px',
            },
            '&:hover fieldset': {
              borderColor: 'rgba(56, 189, 248, 0.4)',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#38BDF8',
              borderWidth: '1.5px',
              boxShadow: '0 0 12px rgba(56, 189, 248, 0.25)',
            },
          },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          backgroundColor: '#1E293B',
        },
        bar: {
          borderRadius: 8,
          backgroundImage: 'linear-gradient(90deg, #6366F1 0%, #38BDF8 100%)',
        },
      },
    },
  },
});

export { theme };
export default theme;

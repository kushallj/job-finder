import { createTheme } from '@mui/material/styles';


/**
 * Web3 / Crypto / HFT Cyberpunk Design System for JobFinder AI
 * 
 * Signature Aesthetics:
 * - Ultra-Deep Pitch Black Canvas (#06090E) & Obsidian Glass Cards (#0D131F)
 * - Chromatic Neon Accents: Cyber Cyan (#00F0FF), Electric HFT Lime (#00FFA3), Solar Gold (#FFE600), Laser Pink (#FF007A), Hyper Violet (#7928CA)
 * - Glowing Multi-Layer Shadows (0 0 25px rgba(0, 240, 255, 0.25))
 * - Zero plain white divs or inputs — pure dark high-contrast luminescence
 * - Fluid hover micro-interactions & pulsing HFT liquidity indicators
 */

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00F0FF', // Cyber Cyan
      light: '#70F7FF',
      dark: '#00A3AD',
      contrastText: '#06090E',
    },
    secondary: {
      main: '#00FFA3', // Electric HFT Lime
      light: '#66FFC7',
      dark: '#00B875',
      contrastText: '#06090E',
    },
    success: {
      main: '#00FFA3', // Lime Green
      light: '#66FFC7',
      dark: '#00B875',
      contrastText: '#06090E',
    },
    warning: {
      main: '#FFE600', // Solar Gold
      light: '#FFF066',
      dark: '#B8A500',
      contrastText: '#06090E',
    },
    error: {
      main: '#FF007A', // Laser Pink
      light: '#FF66AC',
      dark: '#B80058',
      contrastText: '#FFFFFF',
    },
    info: {
      main: '#7928CA', // Hyper Violet
      light: '#A855F7',
      dark: '#581C87',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#06090E', // Deep Cyber Pitch Dark
      paper: '#0D131F',   // Obsidian Surface
    },
    text: {
      primary: '#F8FAFC',   // Crisp White/Silver
      secondary: '#94A3B8', // Muted Cyber Steel
      disabled: '#64748B',
    },
    divider: 'rgba(0, 240, 255, 0.15)',
  },
  typography: {
    fontFamily: '"Cabinet Grotesk", "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: {
      fontSize: '2.85rem',
      fontWeight: 900,
      letterSpacing: '-0.04em',
      lineHeight: 1.15,
      color: '#F8FAFC',
    },
    h2: {
      fontSize: '2.25rem',
      fontWeight: 900,
      letterSpacing: '-0.035em',
      lineHeight: 1.2,
      color: '#F8FAFC',
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 800,
      letterSpacing: '-0.03em',
      lineHeight: 1.25,
      color: '#F8FAFC',
    },
    h4: {
      fontSize: '1.4rem',
      fontWeight: 800,
      letterSpacing: '-0.02em',
      lineHeight: 1.3,
      color: '#F8FAFC',
    },
    h5: {
      fontSize: '1.2rem',
      fontWeight: 800,
      letterSpacing: '-0.015em',
      lineHeight: 1.35,
      color: '#F8FAFC',
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 800,
      letterSpacing: '-0.01em',
      lineHeight: 1.4,
      color: '#F8FAFC',
    },
    subtitle1: {
      fontSize: '0.95rem',
      fontWeight: 600,
      lineHeight: 1.5,
      color: '#94A3B8',
    },
    subtitle2: {
      fontSize: '0.85rem',
      fontWeight: 700,
      lineHeight: 1.5,
      color: '#00F0FF',
    },
    body1: {
      fontSize: '0.95rem',
      lineHeight: 1.6,
      color: '#E2E8F0',
    },
    body2: {
      fontSize: '0.85rem',
      lineHeight: 1.55,
      color: '#94A3B8',
    },
    button: {
      textTransform: 'uppercase',
      fontWeight: 900,
      fontSize: '0.875rem',
      letterSpacing: '0.04em',
    },
    caption: {
      fontSize: '0.75rem',
      fontWeight: 600,
      letterSpacing: '0.03em',
      color: '#94A3B8',
    },
  },
  shape: {
    borderRadius: 16,
  },
  shadows: [
    'none',
    '0 0 10px rgba(0, 240, 255, 0.1)',
    '0 0 15px rgba(0, 240, 255, 0.15)',
    '0 0 20px rgba(0, 240, 255, 0.2)',
    '0 0 25px rgba(0, 255, 163, 0.25)',
    '0 0 35px rgba(0, 240, 255, 0.3)',
    '0 0 50px rgba(0, 255, 163, 0.35)',
    ...Array(18).fill('0 0 25px rgba(0, 240, 255, 0.2)'),
  ] as any,
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#06090E',
          color: '#F8FAFC',
          backgroundImage: `
            radial-gradient(circle at 50% 0%, rgba(0, 240, 255, 0.12) 0%, transparent 60%),
            radial-gradient(circle at 90% 80%, rgba(0, 255, 163, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 10% 90%, rgba(121, 40, 202, 0.1) 0%, transparent 50%)
          `,
          scrollbarColor: 'rgba(0, 240, 255, 0.3) #06090E',
          '&::-webkit-scrollbar': {
            width: 8,
            height: 8,
          },
          '&::-webkit-scrollbar-track': {
            background: '#06090E',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'rgba(0, 240, 255, 0.25)',
            borderRadius: 4,
            border: '2px solid #06090E',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#00F0FF',
            boxShadow: '0 0 10px #00F0FF',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: '10px 22px',
          boxShadow: 'none',
          transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          '&:hover': {
            transform: 'translateY(-2px)',
          },
          '&:active': {
            transform: 'translateY(1px)',
          },
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #00FFA3 0%, #00F0FF 100%)',
          color: '#06090E',
          fontWeight: 900,
          border: '1px solid #00F0FF',
          boxShadow: '0 0 20px rgba(0, 255, 163, 0.4)',
          '&:hover': {
            background: 'linear-gradient(135deg, #00F0FF 0%, #00FFA3 100%)',
            boxShadow: '0 0 30px rgba(0, 240, 255, 0.7)',
          },
        },
        containedSecondary: {
          background: 'linear-gradient(135deg, #7928CA 0%, #FF007A 100%)',
          color: '#FFFFFF',
          fontWeight: 900,
          border: '1px solid #FF007A',
          boxShadow: '0 0 20px rgba(255, 0, 122, 0.4)',
          '&:hover': {
            background: 'linear-gradient(135deg, #FF007A 0%, #7928CA 100%)',
            boxShadow: '0 0 30px rgba(255, 0, 122, 0.7)',
          },
        },
        outlined: {
          borderWidth: '1.5px',
          borderColor: 'rgba(0, 240, 255, 0.35)',
          backgroundColor: 'rgba(13, 19, 31, 0.85)',
          color: '#00F0FF',
          backdropFilter: 'blur(12px)',
          '&:hover': {
            borderWidth: '1.5px',
            borderColor: '#00F0FF',
            backgroundColor: 'rgba(0, 240, 255, 0.12)',
            boxShadow: '0 0 20px rgba(0, 240, 255, 0.4)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          border: '1.5px solid rgba(0, 240, 255, 0.2)',
          backgroundColor: '#0D131F',
          backgroundImage: 'linear-gradient(180deg, rgba(0, 240, 255, 0.05) 0%, rgba(13, 19, 31, 0) 100%)',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(16px)',
          transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
          '&:hover': {
            borderColor: '#00F0FF',
            boxShadow: '0 0 30px rgba(0, 240, 255, 0.3), 0 0 60px rgba(0, 255, 163, 0.15)',
            transform: 'translateY(-3px)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          border: '1.5px solid rgba(0, 240, 255, 0.2)',
          backgroundColor: '#0D131F',
          backgroundImage: 'none',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 800,
          fontSize: '0.75rem',
          borderRadius: 9999,
          border: '1px solid rgba(0, 240, 255, 0.35)',
          backgroundColor: 'rgba(0, 240, 255, 0.1)',
          color: '#00F0FF',
          letterSpacing: '0.04em',
          transition: 'all 0.2s ease',
          '&:hover': {
            transform: 'translateY(-1px)',
            boxShadow: '0 0 12px rgba(0, 240, 255, 0.4)',
            borderColor: '#00F0FF',
          },
        },
        colorPrimary: {
          backgroundColor: 'rgba(0, 240, 255, 0.15)',
          color: '#00F0FF',
          border: '1px solid rgba(0, 240, 255, 0.4)',
        },
        colorSecondary: {
          backgroundColor: 'rgba(0, 255, 163, 0.15)',
          color: '#00FFA3',
          border: '1px solid rgba(0, 255, 163, 0.4)',
        },
        colorSuccess: {
          backgroundColor: 'rgba(0, 255, 163, 0.15)',
          color: '#00FFA3',
          border: '1px solid rgba(0, 255, 163, 0.4)',
        },
        colorWarning: {
          backgroundColor: 'rgba(255, 230, 0, 0.15)',
          color: '#FFE600',
          border: '1px solid rgba(255, 230, 0, 0.4)',
        },
        colorError: {
          backgroundColor: 'rgba(255, 0, 122, 0.15)',
          color: '#FF007A',
          border: '1px solid rgba(255, 0, 122, 0.4)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 14,
            backgroundColor: '#080C12',
            color: '#F8FAFC',
            transition: 'all 0.2s ease',
            '& fieldset': {
              borderColor: 'rgba(0, 240, 255, 0.25)',
              borderWidth: '1.5px',
            },
            '&:hover fieldset': {
              borderColor: 'rgba(0, 240, 255, 0.6)',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#00F0FF',
              borderWidth: '2px',
              boxShadow: '0 0 20px rgba(0, 240, 255, 0.4)',
            },
          },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          backgroundColor: '#080C12',
          border: '1px solid rgba(0, 240, 255, 0.2)',
          height: 10,
        },
        bar: {
          borderRadius: 8,
          backgroundImage: 'linear-gradient(90deg, #00FFA3 0%, #00F0FF 50%, #FFE600 100%)',
          boxShadow: '0 0 10px #00FFA3',
        },
      },
    },
  },
});

export { theme };
export default theme;

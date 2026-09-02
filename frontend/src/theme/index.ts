import { createTheme } from '@mui/material/styles';

/**
 * Fireship.dev Neo-Brutalist Design System Theme
 * 
 * Signature Aesthetics:
 * - Classy Deep Charcoal Black Canvas (#0A0D0E) & Card Surface (#12181B)
 * - Warm Cartoonist Beige Typography (#F6F1D7) & Muted Steel (#A0AEC0)
 * - Iconic Fireship Flame Orange (#FF3E00), Acid Yellow (#FFDE59), & Electric Violet (#8A2BE2)
 * - Neo-Brutalist Hard 3D Shadow Buttons (4px 4px 0px #000) & Chunky Pill Stickers
 * - Irreverent Developer Pun & High-Speed Performance Feel
 */

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#FF3E00', // Fireship Flame Orange
      light: '#FF5722',
      dark: '#D83200',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#FFDE59', // Cartoon Acid Yellow
      light: '#FFF08A',
      dark: '#E5C000',
      contrastText: '#0A0D0E',
    },
    success: {
      main: '#00E676', // Acid Green
      light: '#69F0AE',
      dark: '#00B248',
      contrastText: '#0A0D0E',
    },
    warning: {
      main: '#FFDE59', // Yellow
      light: '#FFEAA7',
      dark: '#D4AC0D',
      contrastText: '#0A0D0E',
    },
    error: {
      main: '#FF007A', // Neon Magenta Pink
      light: '#FF4081',
      dark: '#C51162',
      contrastText: '#FFFFFF',
    },
    info: {
      main: '#8A2BE2', // Fireship Pro Purple
      light: '#BA68C8',
      dark: '#6A1B9A',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#0A0D0E', // Charcoal Black
      paper: '#12181B',   // Dark Surface
    },
    text: {
      primary: '#F6F1D7',   // Warm Fireship Cream Beige
      secondary: '#A0AEC0', // Slate Steel
      disabled: '#64748B',
    },
    divider: '#2A363F',
  },
  typography: {
    fontFamily: '"Plus Jakarta Sans", "Cabinet Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: {
      fontSize: '2.75rem',
      fontWeight: 900,
      letterSpacing: '-0.04em',
      textTransform: 'uppercase',
      lineHeight: 1.15,
      color: '#F6F1D7',
    },
    h2: {
      fontSize: '2.15rem',
      fontWeight: 900,
      letterSpacing: '-0.03em',
      textTransform: 'uppercase',
      lineHeight: 1.2,
      color: '#F6F1D7',
    },
    h3: {
      fontSize: '1.65rem',
      fontWeight: 800,
      letterSpacing: '-0.025em',
      lineHeight: 1.25,
      color: '#F6F1D7',
    },
    h4: {
      fontSize: '1.35rem',
      fontWeight: 800,
      letterSpacing: '-0.02em',
      lineHeight: 1.3,
      color: '#F6F1D7',
    },
    h5: {
      fontSize: '1.15rem',
      fontWeight: 800,
      letterSpacing: '-0.015em',
      lineHeight: 1.35,
      color: '#F6F1D7',
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 800,
      letterSpacing: '-0.01em',
      lineHeight: 1.4,
      color: '#F6F1D7',
    },
    subtitle1: {
      fontSize: '0.95rem',
      fontWeight: 600,
      lineHeight: 1.5,
      color: '#A0AEC0',
    },
    subtitle2: {
      fontSize: '0.85rem',
      fontWeight: 700,
      lineHeight: 1.5,
      color: '#F6F1D7',
    },
    body1: {
      fontSize: '0.95rem',
      lineHeight: 1.6,
      color: '#E2E8F0',
    },
    body2: {
      fontSize: '0.85rem',
      lineHeight: 1.55,
      color: '#A0AEC0',
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
      letterSpacing: '0.02em',
      color: '#A0AEC0',
    },
  },
  shape: {
    borderRadius: 16,
  },
  shadows: [
    'none',
    '3px 3px 0px #000000',
    '4px 4px 0px #000000',
    '5px 5px 0px #000000',
    '6px 6px 0px #000000',
    '8px 8px 0px #000000',
    '10px 10px 0px #000000',
    ...Array(18).fill('6px 6px 0px #000000'),
  ] as any,
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#0A0D0E',
          color: '#F6F1D7',
          scrollbarColor: '#2A363F #0A0D0E',
          '&::-webkit-scrollbar': {
            width: 10,
            height: 10,
          },
          '&::-webkit-scrollbar-track': {
            background: '#0A0D0E',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#2A363F',
            borderRadius: 6,
            border: '2px solid #0A0D0E',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#FF3E00',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: '10px 22px',
          border: '2.5px solid #000000',
          boxShadow: '4px 4px 0px #000000',
          transition: 'all 0.12s ease-in-out',
          '&:hover': {
            transform: 'translate(-2px, -2px)',
            boxShadow: '6px 6px 0px #FFDE59',
          },
          '&:active': {
            transform: 'translate(2px, 2px)',
            boxShadow: '1px 1px 0px #000000',
          },
        },
        containedPrimary: {
          background: '#FF3E00',
          color: '#FFFFFF',
          border: '2.5px solid #000000',
          boxShadow: '4px 4px 0px #000000',
          '&:hover': {
            background: '#FF5722',
            boxShadow: '6px 6px 0px #FFDE59',
          },
        },
        containedSecondary: {
          background: '#FFDE59',
          color: '#0A0D0E',
          border: '2.5px solid #000000',
          boxShadow: '4px 4px 0px #000000',
          '&:hover': {
            background: '#FFF08A',
            boxShadow: '6px 6px 0px #FF3E00',
          },
        },
        containedSuccess: {
          background: '#00E676',
          color: '#0A0D0E',
          border: '2.5px solid #000000',
          boxShadow: '4px 4px 0px #000000',
          '&:hover': {
            background: '#69F0AE',
            boxShadow: '6px 6px 0px #FFDE59',
          },
        },
        outlined: {
          borderWidth: '2.5px',
          borderColor: '#2A363F',
          backgroundColor: '#12181B',
          color: '#F6F1D7',
          boxShadow: '4px 4px 0px #000000',
          '&:hover': {
            borderWidth: '2.5px',
            borderColor: '#FFDE59',
            backgroundColor: '#181E24',
            boxShadow: '6px 6px 0px #FF3E00',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          border: '3px solid #2A363F',
          backgroundColor: '#12181B',
          boxShadow: '6px 6px 0px #000000',
          transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          '&:hover': {
            borderColor: '#FFDE59',
            boxShadow: '8px 8px 0px #FF3E00',
            transform: 'translateY(-2px)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          border: '3px solid #2A363F',
          backgroundColor: '#12181B',
          backgroundImage: 'none',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 900,
          fontSize: '0.75rem',
          borderRadius: 9999,
          border: '2px solid #000000',
          boxShadow: '2px 2px 0px #000000',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          transition: 'all 0.15s ease',
          '&:hover': {
            transform: 'translateY(-1px)',
            boxShadow: '3px 3px 0px #000000',
          },
        },
        colorPrimary: {
          backgroundColor: '#FF3E00',
          color: '#FFFFFF',
        },
        colorSecondary: {
          backgroundColor: '#FFDE59',
          color: '#0A0D0E',
        },
        colorSuccess: {
          backgroundColor: '#00E676',
          color: '#0A0D0E',
        },
        colorWarning: {
          backgroundColor: '#FFDE59',
          color: '#0A0D0E',
        },
        colorError: {
          backgroundColor: '#FF007A',
          color: '#FFFFFF',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 14,
            backgroundColor: '#0A0D0E',
            color: '#F6F1D7',
            transition: 'all 0.15s ease',
            '& fieldset': {
              borderColor: '#2A363F',
              borderWidth: '2px',
            },
            '&:hover fieldset': {
              borderColor: '#FFDE59',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#FF3E00',
              borderWidth: '2.5px',
              boxShadow: '4px 4px 0px #FFDE59',
            },
          },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          backgroundColor: '#181E24',
          border: '2px solid #000000',
          height: 12,
        },
        bar: {
          borderRadius: 8,
          backgroundImage: 'linear-gradient(90deg, #FF3E00 0%, #FFDE59 100%)',
        },
      },
    },
  },
});

export { theme };
export default theme;

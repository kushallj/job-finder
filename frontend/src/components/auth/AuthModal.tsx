import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  IconButton,
  TextField,
  Button,
  Tabs,
  Tab,
  Box,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import PersonAddOutlinedIcon from '@mui/icons-material/PersonAddOutlined';
import { useAuth } from '../../context/AuthContext';

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ open, onClose }) => {
  const { login, register } = useAuth();
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (tab === 'login') {
        await login(email, password);
      } else {
        await register(email, password, fullName);
      }
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Authentication failed';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#0f172a',
          color: '#f8fafc',
          borderRadius: 3,
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.75)',
        },
      }}
    >
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ p: 0.8, borderRadius: 2, bgcolor: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>
            <AutoAwesomeIcon fontSize="small" />
          </Box>
          <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem', letterSpacing: '-0.02em' }}>
            Job Finder Cloud
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: '#94a3b8' }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <DialogContent sx={{ p: 3 }}>
        <Tabs
          value={tab}
          onChange={(_, val) => {
            setTab(val);
            setError(null);
          }}
          variant="fullWidth"
          sx={{
            mb: 2.5,
            minHeight: 40,
            bgcolor: 'rgba(255,255,255,0.03)',
            borderRadius: 2,
            p: 0.5,
            '& .MuiTabs-indicator': {
              bgcolor: '#10b981',
              borderRadius: 1,
            },
            '& .MuiTab-root': {
              minHeight: 36,
              color: '#94a3b8',
              fontWeight: 600,
              fontSize: '0.85rem',
              textTransform: 'none',
              '&.Mui-selected': {
                color: '#fff',
              },
            },
          }}
        >
          <Tab value="login" label="Sign In" icon={<LockOutlinedIcon fontSize="small" />} iconPosition="start" />
          <Tab value="register" label="Create Account" icon={<PersonAddOutlinedIcon fontSize="small" />} iconPosition="start" />
        </Tabs>

        {tab === 'register' && (
          <Box sx={{ mb: 2.5, p: 1.5, borderRadius: 2, bgcolor: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            <Typography variant="body2" sx={{ color: '#34d399', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 0.8 }}>
              ⚡ Complimentary Starting Package
            </Typography>
            <Typography variant="caption" sx={{ color: '#94a3b8', display: 'block', mt: 0.5 }}>
              Register today to receive <strong>50 free credits</strong> for automated Workday/NextRaise applications and AI resume tailoring.
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2, bgcolor: 'rgba(239, 68, 68, 0.1)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {tab === 'register' && (
              <TextField
                label="Full Name"
                placeholder="Sarah Connor"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                variant="outlined"
                size="small"
                fullWidth
                InputLabelProps={{ sx: { color: '#94a3b8' } }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    color: '#fff',
                    bgcolor: 'rgba(255,255,255,0.03)',
                    '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                    '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.2)' },
                    '&.Mui-focused fieldset': { borderColor: '#10b981' },
                  },
                }}
              />
            )}

            <TextField
              label="Email Address"
              type="email"
              required
              placeholder="candidate@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              variant="outlined"
              size="small"
              fullWidth
              InputLabelProps={{ sx: { color: '#94a3b8' } }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  color: '#fff',
                  bgcolor: 'rgba(255,255,255,0.03)',
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                  '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.2)' },
                  '&.Mui-focused fieldset': { borderColor: '#10b981' },
                },
              }}
            />

            <TextField
              label="Password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              variant="outlined"
              size="small"
              fullWidth
              InputLabelProps={{ sx: { color: '#94a3b8' } }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  color: '#fff',
                  bgcolor: 'rgba(255,255,255,0.03)',
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                  '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.2)' },
                  '&.Mui-focused fieldset': { borderColor: '#10b981' },
                },
              }}
            />

            <Button
              type="submit"
              variant="contained"
              disabled={submitting}
              sx={{
                mt: 1,
                py: 1.2,
                bgcolor: '#10b981',
                color: '#fff',
                fontWeight: 700,
                textTransform: 'none',
                borderRadius: 2,
                boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)',
                '&:hover': {
                  bgcolor: '#059669',
                },
              }}
            >
              {submitting ? (
                <CircularProgress size={22} color="inherit" />
              ) : tab === 'login' ? (
                'Sign In'
              ) : (
                'Create Account & Claim 50 Credits'
              )}
            </Button>
          </Box>
        </form>
      </DialogContent>
    </Dialog>
  );
};

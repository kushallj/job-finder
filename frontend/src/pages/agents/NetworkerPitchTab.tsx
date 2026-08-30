import React from 'react';
import {
  Alert, Box, Button, Card, CardContent, CircularProgress, Divider, IconButton,
  Stack, TextField, Tooltip, Typography,
} from '@mui/material';
import {
  ContentCopy as CopyIcon, Lightbulb as LightbulbIcon, Description as DescriptionIcon,
} from '@mui/icons-material';
import CompanySelect from './CompanySelect';
import { useNetworker, usePitch } from '../../hooks/useAgents';

const NetworkerPitchTab: React.FC = () => {
  const [company, setCompany] = React.useState('');
  const [jd, setJd] = React.useState('');
  const networker = useNetworker();
  const pitch = usePitch();

  const handleCopy = (text: string) => navigator.clipboard.writeText(text);
  const canRun = company.trim().length > 0;

  return (
    <Box>
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Networker & Pitcher</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Finds a real, evidenced challenge at the company — from the job description if you paste one,
            otherwise from a known funding/hiring signal — and never invents one. Use it to draft topical
            LinkedIn/X content (copy-paste only, nothing auto-posts) or a formal WIN one-pager.
          </Typography>
          <Stack spacing={2}>
            <CompanySelect value={company} onChange={setCompany} />
            <TextField
              label="Job description (optional, much stronger result)"
              multiline
              minRows={3}
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              fullWidth
            />
            <Stack direction="row" spacing={2}>
              <Button
                variant="contained"
                startIcon={networker.isPending ? <CircularProgress size={16} color="inherit" /> : <LightbulbIcon />}
                onClick={() => networker.mutate({ company, jobDescription: jd })}
                disabled={!canRun || networker.isPending}
              >
                Find challenge & draft content
              </Button>
              <Button
                variant="outlined"
                startIcon={pitch.isPending ? <CircularProgress size={16} /> : <DescriptionIcon />}
                onClick={() => pitch.mutate({ company, jobDescription: jd })}
                disabled={!canRun || pitch.isPending}
              >
                Build WIN pitch
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {networker.data && (
        <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
          <CardContent sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Networker result</Typography>
            {networker.data.challenge.identified_challenge ? (
              <>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Identified challenge</Typography>
                <Typography variant="body2" sx={{ mb: 2 }}>{networker.data.challenge.identified_challenge}</Typography>
                {networker.data.challenge.evidence.length > 0 && (
                  <>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Evidence</Typography>
                    {networker.data.challenge.evidence.map((e, i) => (
                      <Typography key={i} variant="body2" color="text.secondary">• {e}</Typography>
                    ))}
                  </>
                )}
              </>
            ) : (
              <Alert severity="warning" sx={{ mb: 2 }}>
                No specific challenge found — paste a real job description above for a stronger result.
              </Alert>
            )}
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }} gutterBottom>
              Content drafts (copy-paste only — nothing auto-posts)
            </Typography>
            {(['linkedin', 'x'] as const).map((platform) => (
              <Box key={platform} sx={{ mb: 2, p: 2, border: '1px solid #F1F5F9', borderRadius: 2 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>
                    {platform === 'linkedin' ? 'LinkedIn' : 'X'}
                  </Typography>
                  <Tooltip title="Copy">
                    <IconButton size="small" onClick={() => handleCopy(networker.data!.content_drafts.platform_drafts[platform])}>
                      <CopyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Stack>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {networker.data.content_drafts.platform_drafts[platform]}
                </Typography>
              </Box>
            ))}
          </CardContent>
        </Card>
      )}

      {pitch.data && (
        <Card sx={{ border: '1px solid #E2E8F0' }}>
          <CardContent sx={{ p: 2.5 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>WIN pitch</Typography>
              <Tooltip title="Copy markdown">
                <IconButton size="small" onClick={() => handleCopy(pitch.data!.data.win_markdown)}>
                  <CopyIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Stack>
            {pitch.data.warnings.length > 0 && (
              <Alert severity="warning" sx={{ mb: 2 }}>{pitch.data.warnings[0]}</Alert>
            )}
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.82rem' }}>
              {pitch.data.data.win_markdown}
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default NetworkerPitchTab;

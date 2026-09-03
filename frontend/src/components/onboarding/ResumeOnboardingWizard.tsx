import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Stack,
  Chip,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
  Alert,
  Paper,
} from '@mui/material';
import {

  CloudUpload as CloudUploadIcon,
  Person as PersonIcon,
  Add as AddIcon,
  Save as SaveIcon,
  ArrowForward as NextIcon,
  ArrowBack as BackIcon,
} from '@mui/icons-material';

import { profileApi, type CandidateProfileData, type TargetCompanyData } from '../../api/endpoints/profile';

const POPULAR_SKILLS = [
  'Python', 'FastAPI', 'Django', 'React', 'TypeScript', 'PostgreSQL',
  'Redis', 'Docker', 'Kubernetes', 'AWS', 'Kafka', 'Go', 'GraphQL', 'PyTorch', 'LLMs'
];

interface ResumeOnboardingWizardProps {
  onComplete?: (profile: CandidateProfileData) => void;
}

export const ResumeOnboardingWizard: React.FC<ResumeOnboardingWizardProps> = ({ onComplete }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [profile, setProfile] = useState<CandidateProfileData>({
    full_name: '',
    email: '',
    phone: '',
    location: 'Remote',
    linkedin_url: '',
    github_url: '',
    years_of_experience: 3.0,
    current_title: 'Full Stack Engineer',
    bio_summary: '',
    skills: ['Python', 'FastAPI', 'React', 'PostgreSQL'],
    target_roles: ['Senior Backend Engineer', 'Full Stack Engineer'],
    target_locations: ['Remote', 'India', 'United States'],
  });

  const [companies, setCompanies] = useState<TargetCompanyData[]>([]);
  const [newCompany, setNewCompany] = useState({ name: '', domain: '', tier: 'tier1' });
  const [newSkillInput, setNewSkillInput] = useState('');

  useEffect(() => {
    // Load existing profile if available
    profileApi.getCurrentProfile()
      .then((p) => {
        if (p) setProfile(p);
      })
      .catch(() => {});

    profileApi.getTargetCompanies()
      .then((c) => setCompanies(c))
      .catch(() => {});
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setErrorMsg(null);
    try {
      const parsed = await profileApi.uploadResume(file);
      setProfile(parsed);
      setSuccessMsg('Resume parsed and skills extracted successfully!');
      setActiveStep(1);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Failed to parse resume PDF.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSkill = (skill: string) => {
    const exists = profile.skills.includes(skill);
    const updated = exists
      ? profile.skills.filter((s) => s !== skill)
      : [...profile.skills, skill];
    setProfile({ ...profile, skills: updated });
  };

  const handleAddCustomSkill = () => {
    if (!newSkillInput.trim() || profile.skills.includes(newSkillInput.trim())) return;
    setProfile({ ...profile, skills: [...profile.skills, newSkillInput.trim()] });
    setNewSkillInput('');
  };

  const handleSaveProfile = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const updated = await profileApi.updateProfile(profile);
      setProfile(updated);
      setSuccessMsg('Profile calibrated and target accounts locked in!');
      if (onComplete) onComplete(updated);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Failed to save profile.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddCompany = async () => {
    if (!newCompany.name.trim() || !newCompany.domain.trim()) return;
    try {
      const added = await profileApi.addTargetCompany(newCompany);
      setCompanies([...companies, added]);
      setNewCompany({ name: '', domain: '', tier: 'tier1' });
    } catch (err: any) {
      setErrorMsg('Failed to add target company.');
    }
  };

  const steps = ['Upload Resume (PDF)', 'Confirm Skills & Experience', 'Review 15-20 Target Accounts'];

  return (
    <Box sx={{ width: '100%', maxWidth: '1000px', mx: 'auto', p: { xs: 2, md: 4 } }}>
      <Card
        sx={{
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 240, 255, 0.25)',
          borderRadius: '20px',
          boxShadow: '0 0 50px rgba(0, 240, 255, 0.1)',
        }}
      >
        <CardContent sx={{ p: { xs: 3, md: 4 } }}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: '10px',
                bgcolor: 'rgba(0, 255, 163, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid #00FFA3',
              }}
            >
              <PersonIcon sx={{ color: '#00FFA3' }} />
            </Box>
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                Candidate Profile & Account-Based Onboarding
              </Typography>
              <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                Calibrate the 15-agent pipeline to your exact background, skills, and target companies.
              </Typography>
            </Box>
          </Stack>

          {/* Stepper */}
          <Stepper
            activeStep={activeStep}
            sx={{
              my: 3,
              '& .MuiStepLabel-label': { color: '#94A3B8', fontWeight: 700 },
              '& .MuiStepLabel-label.Mui-active': { color: '#00FFA3' },
              '& .MuiStepLabel-label.Mui-completed': { color: '#00F0FF' },
              '& .MuiStepIcon-root.Mui-active': { color: '#00FFA3' },
              '& .MuiStepIcon-root.Mui-completed': { color: '#00F0FF' },
            }}
          >
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {errorMsg && (
            <Alert severity="error" sx={{ mb: 3, bgcolor: 'rgba(255, 0, 122, 0.15)', color: '#FF007A' }}>
              {errorMsg}
            </Alert>
          )}

          {successMsg && (
            <Alert severity="success" sx={{ mb: 3, bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3' }}>
              {successMsg}
            </Alert>
          )}

          {/* ── STEP 0: Upload Resume ── */}
          {activeStep === 0 && (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Paper
                variant="outlined"
                sx={{
                  p: 5,
                  border: '2px dashed rgba(0, 240, 255, 0.4)',
                  bgcolor: '#06090E',
                  borderRadius: '16px',
                  cursor: 'pointer',
                  '&:hover': { borderColor: '#00FFA3', bgcolor: 'rgba(0, 255, 163, 0.03)' },
                }}
                component="label"
              >
                <input type="file" accept=".pdf" hidden onChange={handleFileUpload} />
                <CloudUploadIcon sx={{ color: '#00FFA3', fontSize: 56, mb: 1.5 }} />
                <Typography variant="h6" sx={{ fontWeight: 800, color: '#F8FAFC', mb: 1 }}>
                  {loading ? 'Extracting Skills from PDF...' : 'Click to Upload Your Resume PDF'}
                </Typography>
                <Typography variant="body2" sx={{ color: '#94A3B8', maxWidth: '500px', mx: 'auto' }}>
                  Our AI parser will automatically extract your contact info, tech stack keywords, years of experience, and summary.
                </Typography>
                {loading && <CircularProgress size={24} sx={{ color: '#00FFA3', mt: 2 }} />}
              </Paper>

              <Box sx={{ mt: 3 }}>
                <Button
                  variant="text"
                  onClick={() => setActiveStep(1)}
                  sx={{ color: '#00F0FF', textTransform: 'none', fontWeight: 700 }}
                >
                  Or enter profile details manually &rarr;
                </Button>
              </Box>
            </Box>
          )}

          {/* ── STEP 1: Skills & Profile Confirmation ── */}
          {activeStep === 1 && (
            <Box>
              <Grid container spacing={2.5}>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Full Name"
                    value={profile.full_name}
                    onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Email Address"
                    value={profile.email}
                    onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="LinkedIn Profile URL"
                    value={profile.linkedin_url || ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_url: e.target.value })}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="GitHub Profile URL"
                    value={profile.github_url || ''}
                    onChange={(e) => setProfile({ ...profile, github_url: e.target.value })}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <TextField
                    fullWidth
                    size="small"
                    type="number"
                    label="Years of Experience"
                    value={profile.years_of_experience}
                    onChange={(e) => setProfile({ ...profile, years_of_experience: parseFloat(e.target.value) || 0 })}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 8 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Primary Target Title"
                    value={profile.current_title || ''}
                    onChange={(e) => setProfile({ ...profile, current_title: e.target.value })}
                    sx={{ bgcolor: '#06090E' }}
                  />
                </Grid>
              </Grid>

              {/* Skill Chips */}
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#00FFA3', mb: 1, textTransform: 'uppercase' }}>
                  Extracted Tech Stack ({profile.skills.length} Skills Selected):
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1, mb: 2 }}>
                  {POPULAR_SKILLS.map((skill) => {
                    const isSelected = profile.skills.includes(skill);
                    return (
                      <Chip
                        key={skill}
                        label={skill}
                        clickable
                        onClick={() => handleToggleSkill(skill)}
                        sx={{
                          fontWeight: 800,
                          bgcolor: isSelected ? 'rgba(0, 255, 163, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                          color: isSelected ? '#00FFA3' : '#94A3B8',
                          border: `1px solid ${isSelected ? '#00FFA3' : 'rgba(255, 255, 255, 0.1)'}`,
                        }}
                      />
                    );
                  })}
                </Stack>

                <Stack direction="row" spacing={1} sx={{ maxWidth: '400px' }}>
                  <TextField
                    size="small"
                    placeholder="Add custom skill (e.g. Terraform)"
                    value={newSkillInput}
                    onChange={(e) => setNewSkillInput(e.target.value)}
                    sx={{ bgcolor: '#06090E', flexGrow: 1 }}
                  />
                  <Button variant="outlined" onClick={handleAddCustomSkill} startIcon={<AddIcon />} sx={{ textTransform: 'none', fontWeight: 800 }}>
                    Add
                  </Button>
                </Stack>
              </Box>

              {/* Bio Summary */}
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#00F0FF', mb: 1 }}>
                  Professional Bio / Value Proposition:
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  value={profile.bio_summary || ''}
                  onChange={(e) => setProfile({ ...profile, bio_summary: e.target.value })}
                  sx={{ bgcolor: '#06090E' }}
                />
              </Box>

              <Stack direction="row" justifyContent="space-between" sx={{ mt: 4 }}>
                <Button variant="outlined" onClick={() => setActiveStep(0)} startIcon={<BackIcon />} sx={{ textTransform: 'none', fontWeight: 700 }}>
                  Back
                </Button>
                <Button variant="contained" onClick={() => setActiveStep(2)} endIcon={<NextIcon />} sx={{ bgcolor: '#00FFA3', color: '#06090E', fontWeight: 900, textTransform: 'none' }}>
                  Next: Target Accounts &rarr;
                </Button>
              </Stack>
            </Box>
          )}

          {/* ── STEP 2: Target Companies ── */}
          {activeStep === 2 && (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#00F0FF', mb: 1.5 }}>
                Active Target Company Accounts ({companies.length} Targeted):
              </Typography>
              <Grid container spacing={1.5} sx={{ mb: 3 }}>
                {companies.map((comp) => (
                  <Grid key={comp.id || comp.name} size={{ xs: 12, sm: 6, md: 4 }}>
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 1.5,
                        bgcolor: '#06090E',
                        borderRadius: '10px',
                        border: '1px solid rgba(0, 240, 255, 0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <Box>
                        <Typography variant="body2" sx={{ fontWeight: 800, color: '#F8FAFC' }}>
                          {comp.name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                          {comp.domain} • {comp.tier.toUpperCase()}
                        </Typography>
                      </Box>
                      <Chip label={`${comp.signal_score || 85}% Fit`} size="small" sx={{ bgcolor: 'rgba(0, 255, 163, 0.15)', color: '#00FFA3', fontWeight: 800, fontSize: '0.7rem' }} />
                    </Paper>
                  </Grid>
                ))}
              </Grid>

              {/* Add Company Box */}
              <Paper variant="outlined" sx={{ p: 2, bgcolor: '#06090E', borderRadius: '12px', mb: 3 }}>
                <Typography variant="caption" sx={{ fontWeight: 800, color: '#FFE600', textTransform: 'uppercase', display: 'block', mb: 1 }}>
                  Add Custom Target Account:
                </Typography>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                  <TextField
                    size="small"
                    placeholder="Company Name (e.g. Databricks)"
                    value={newCompany.name}
                    onChange={(e) => setNewCompany({ ...newCompany, name: e.target.value })}
                    sx={{ flexGrow: 1 }}
                  />
                  <TextField
                    size="small"
                    placeholder="Domain (e.g. databricks.com)"
                    value={newCompany.domain}
                    onChange={(e) => setNewCompany({ ...newCompany, domain: e.target.value })}
                    sx={{ flexGrow: 1 }}
                  />
                  <Button variant="outlined" onClick={handleAddCompany} startIcon={<AddIcon />} sx={{ fontWeight: 800, textTransform: 'none' }}>
                    Add Account
                  </Button>
                </Stack>
              </Paper>

              <Stack direction="row" justifyContent="space-between" sx={{ mt: 4 }}>
                <Button variant="outlined" onClick={() => setActiveStep(1)} startIcon={<BackIcon />} sx={{ textTransform: 'none', fontWeight: 700 }}>
                  Back
                </Button>
                <Button
                  variant="contained"
                  disabled={loading}
                  onClick={handleSaveProfile}
                  startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SaveIcon />}
                  sx={{
                    bgcolor: '#00FFA3',
                    color: '#06090E',
                    fontWeight: 900,
                    textTransform: 'none',
                    px: 3,
                    boxShadow: '0 0 25px rgba(0, 255, 163, 0.4)',
                    '&:hover': { bgcolor: '#00E592' },
                  }}
                >
                  {loading ? 'Saving...' : '🚀 Lock In Profile & Calibrate Agents'}
                </Button>
              </Stack>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

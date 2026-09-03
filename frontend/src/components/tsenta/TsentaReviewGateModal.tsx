import React, { useState } from 'react';
import {
  Modal,
  Box,
  Typography,
  IconButton,
  Button,
  Chip,
  Tabs,
  Tab,
  TextField,
  Divider,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Close as CloseIcon,
  Bolt as BoltIcon,
  CheckCircle as CheckCircleIcon,
  Article as ArticleIcon,
  QuestionAnswer as QuestionAnswerIcon,
  ContactMail as ContactMailIcon,
  OpenInNew as OpenInNewIcon,
  Receipt as ReceiptIcon,
} from '@mui/icons-material';
import { tsentaApi, type TsentaSubmissionData, type TsentaQAItem } from '../../api/endpoints/tsenta';

interface TsentaReviewGateModalProps {
  open: boolean;
  onClose: () => void;
  submission: TsentaSubmissionData | null;
  onSubmitted?: (updated: TsentaSubmissionData) => void;
}

export const TsentaReviewGateModal: React.FC<TsentaReviewGateModalProps> = ({
  open,
  onClose,
  submission,
  onSubmitted,
}) => {
  const [tabIndex, setTabIndex] = useState(0);
  const [coverLetter, setCoverLetter] = useState(submission?.cover_letter_text || '');
  const [answers, setAnswers] = useState<TsentaQAItem[]>(submission?.answers || []);
  const [submitting, setSubmitting] = useState(false);
  const [receipt, setReceipt] = useState<TsentaSubmissionData | null>(
    submission?.status === 'submitted' ? submission : null
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  React.useEffect(() => {
    if (submission) {
      setCoverLetter(submission.cover_letter_text || '');
      setAnswers(submission.answers || []);
      setReceipt(submission.status === 'submitted' ? submission : null);
      setErrorMsg(null);
    }
  }, [submission]);

  if (!submission) return null;

  const handleAnswerChange = (index: number, newAnswer: string) => {
    const updated = [...answers];
    updated[index].answer = newAnswer;
    setAnswers(updated);
  };

  const handleApproveAndSubmit = async () => {
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await tsentaApi.approveAndSubmit(submission.id, coverLetter, answers);
      setReceipt(res.submission);
      if (onSubmitted) {
        onSubmitted(res.submission);
      }
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Failed to submit application via Tsenta.');
    } finally {
      setSubmitting(false);
    }
  };

  const atsColors: Record<string, string> = {
    greenhouse: '#00FFA3',
    lever: '#00F0FF',
    workday: '#FFE600',
    ashby: '#FF007A',
    smartrecruiters: '#7928CA',
    bamboohr: '#10B981',
  };

  const badgeColor = atsColors[submission.ats_type] || '#00FFA3';

  return (
    <Modal open={open} onClose={onClose} aria-labelledby="tsenta-modal-title">
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: { xs: '92%', sm: '800px' },
          maxHeight: '90vh',
          bgcolor: '#0A0F1D',
          border: '1px solid rgba(0, 255, 163, 0.3)',
          borderRadius: '16px',
          boxShadow: '0 0 50px rgba(0, 255, 163, 0.15)',
          color: '#F8FAFC',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 3,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            bgcolor: '#06090E',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box
              sx={{
                width: 38,
                height: 38,
                borderRadius: '10px',
                bgcolor: 'rgba(0, 255, 163, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(0, 255, 163, 0.4)',
              }}
            >
              <BoltIcon sx={{ color: '#00FFA3', fontSize: 24 }} />
            </Box>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800, color: '#FFFFFF', fontSize: '1.15rem' }}>
                Tsenta Auto-Apply Review Gate
              </Typography>
              <Typography variant="body2" sx={{ color: '#94A3B8', fontSize: '0.85rem' }}>
                {submission.company_name} — {submission.job_title}
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Chip
              label={submission.ats_type.toUpperCase()}
              size="small"
              sx={{
                bgcolor: `${badgeColor}22`,
                color: badgeColor,
                border: `1px solid ${badgeColor}`,
                fontWeight: 700,
                fontSize: '0.75rem',
              }}
            />
            <IconButton onClick={onClose} sx={{ color: '#94A3B8', '&:hover': { color: '#FFF' } }}>
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>

        {/* Content Body */}
        <Box sx={{ p: 3, overflowY: 'auto', flex: 1 }}>
          {errorMsg && (
            <Alert severity="error" sx={{ mb: 2, bgcolor: 'rgba(239, 68, 68, 0.2)', color: '#FCA5A5' }}>
              {errorMsg}
            </Alert>
          )}

          {receipt ? (
            /* Receipt View */
            <Box
              sx={{
                p: 3,
                bgcolor: 'rgba(0, 255, 163, 0.05)',
                border: '1px solid rgba(0, 255, 163, 0.3)',
                borderRadius: '12px',
                textAlign: 'center',
              }}
            >
              <CheckCircleIcon sx={{ color: '#00FFA3', fontSize: 48, mb: 1.5 }} />
              <Typography variant="h5" sx={{ fontWeight: 800, color: '#00FFA3', mb: 1 }}>
                Application Verified & Submitted!
              </Typography>
              <Typography variant="body2" sx={{ color: '#94A3B8', mb: 3 }}>
                Tsenta successfully submitted your application to {submission.company_name}.
              </Typography>

              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  gap: 3,
                  bgcolor: '#06090E',
                  p: 2,
                  borderRadius: '8px',
                  mb: 3,
                }}
              >
                <Box>
                  <Typography variant="caption" sx={{ color: '#64748B' }}>
                    RECEIPT ID
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 700, color: '#00F0FF', fontFamily: 'monospace' }}>
                    {receipt.receipt_id || 'TSENTA-VERIFIED-2026'}
                  </Typography>
                </Box>
                <Divider orientation="vertical" flexItem sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />
                <Box>
                  <Typography variant="caption" sx={{ color: '#64748B' }}>
                    STATUS
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 700, color: '#00FFA3' }}>
                    SUBMITTED
                  </Typography>
                </Box>
              </Box>

              {receipt.proof_url && (
                <Button
                  variant="outlined"
                  href={receipt.proof_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  startIcon={<ReceiptIcon />}
                  endIcon={<OpenInNewIcon />}
                  sx={{
                    borderColor: '#00FFA3',
                    color: '#00FFA3',
                    fontWeight: 700,
                    textTransform: 'none',
                    '&:hover': {
                      borderColor: '#00F0FF',
                      bgcolor: 'rgba(0, 255, 163, 0.1)',
                    },
                  }}
                >
                  View Cryptographic Submission Proof
                </Button>
              )}
            </Box>
          ) : (
            /* Review & Edit Tabs */
            <>
              <Tabs
                value={tabIndex}
                onChange={(_, val) => setTabIndex(val)}
                textColor="inherit"
                TabIndicatorProps={{ style: { backgroundColor: '#00FFA3' } }}
                sx={{
                  borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                  mb: 2.5,
                  '& .MuiTab-root': {
                    color: '#94A3B8',
                    textTransform: 'none',
                    fontWeight: 700,
                    '&.Mui-selected': { color: '#00FFA3' },
                  },
                }}
              >
                <Tab icon={<ArticleIcon />} iconPosition="start" label="Tailored Resume Diff" />
                <Tab icon={<ContactMailIcon />} iconPosition="start" label="AI Cover Letter" />
                <Tab icon={<QuestionAnswerIcon />} iconPosition="start" label={`Screening Q&A (${answers.length})`} />
              </Tabs>

              {tabIndex === 0 && (
                <Box>
                  <Typography variant="subtitle2" sx={{ color: '#00F0FF', fontWeight: 700, mb: 1 }}>
                    ATS-Optimized Resume Summary:
                  </Typography>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: '#06090E',
                      borderRadius: '8px',
                      border: '1px solid rgba(255,255,255,0.1)',
                      color: '#E2E8F0',
                      fontSize: '0.9rem',
                      lineHeight: 1.6,
                    }}
                  >
                    {submission.tailored_resume_text ||
                      'Results-driven Software Engineer with 4 years of experience scaling high-throughput distributed backend services, FastAPI, PostgreSQL, Redis, and modern full-stack web applications.'}
                  </Box>
                </Box>
              )}

              {tabIndex === 1 && (
                <Box>
                  <Typography variant="subtitle2" sx={{ color: '#00F0FF', fontWeight: 700, mb: 1 }}>
                    Contextual Cover Letter (Editable):
                  </Typography>
                  <TextField
                    multiline
                    rows={8}
                    fullWidth
                    value={coverLetter}
                    onChange={(e) => setCoverLetter(e.target.value)}
                    sx={{
                      bgcolor: '#06090E',
                      borderRadius: '8px',
                      '& .MuiOutlinedInput-root': {
                        color: '#F8FAFC',
                        '& fieldset': { borderColor: 'rgba(255,255,255,0.15)' },
                        '&:hover fieldset': { borderColor: '#00FFA3' },
                        '&.Mui-focused fieldset': { borderColor: '#00FFA3' },
                      },
                    }}
                  />
                </Box>
              )}

              {tabIndex === 2 && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {answers.map((qa, idx) => (
                    <Box
                      key={idx}
                      sx={{
                        p: 2,
                        bgcolor: '#06090E',
                        borderRadius: '8px',
                        border: '1px solid rgba(255,255,255,0.1)',
                      }}
                    >
                      <Typography variant="subtitle2" sx={{ color: '#FFE600', fontWeight: 700, mb: 1 }}>
                        Q: {qa.question}
                      </Typography>
                      <TextField
                        fullWidth
                        size="small"
                        value={qa.answer}
                        onChange={(e) => handleAnswerChange(idx, e.target.value)}
                        sx={{
                          bgcolor: '#0D131F',
                          borderRadius: '6px',
                          '& .MuiOutlinedInput-root': {
                            color: '#F8FAFC',
                            '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                            '&:hover fieldset': { borderColor: '#00F0FF' },
                          },
                        }}
                      />
                    </Box>
                  ))}
                </Box>
              )}
            </>
          )}
        </Box>

        {/* Footer */}
        <Box
          sx={{
            p: 2.5,
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            bgcolor: '#06090E',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 2,
          }}
        >
          <Button
            variant="outlined"
            onClick={onClose}
            sx={{
              borderColor: 'rgba(255,255,255,0.2)',
              color: '#94A3B8',
              textTransform: 'none',
              fontWeight: 600,
              '&:hover': { borderColor: '#FFF', color: '#FFF' },
            }}
          >
            {receipt ? 'Close' : 'Cancel'}
          </Button>

          {!receipt && (
            <Button
              variant="contained"
              disabled={submitting}
              onClick={handleApproveAndSubmit}
              startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <BoltIcon />}
              sx={{
                bgcolor: '#00FFA3',
                color: '#06090E',
                fontWeight: 800,
                textTransform: 'none',
                px: 3,
                boxShadow: '0 0 20px rgba(0, 255, 163, 0.4)',
                '&:hover': {
                  bgcolor: '#00E592',
                  boxShadow: '0 0 30px rgba(0, 255, 163, 0.6)',
                },
              }}
            >
              {submitting ? 'Submitting Application...' : '⚡ Approve & Submit via Tsenta'}
            </Button>
          )}
        </Box>
      </Box>
    </Modal>
  );
};

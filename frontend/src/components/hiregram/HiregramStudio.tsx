import React, { useState, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Stack,
  Button,
  CircularProgress,
  Paper,
  IconButton,
  Tooltip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  TextField,
  MenuItem,
  Grid,
} from '@mui/material';
import {
  VolumeUp as VolumeUpIcon,
  Mic as MicIcon,
  Stop as StopIcon,
  PlayArrow as PlayIcon,
  CheckCircle as CheckCircleIcon,
  WarningAmber as WarningIcon,
  Speed as SpeedIcon,
  AutoAwesome as SparkleIcon,
  Assignment as ScorecardIcon,
  Print as PrintIcon,
  Close as CloseIcon,
  RecordVoiceOver as VoiceIcon,
} from '@mui/icons-material';
import { hiregramApi } from '../../api';
import type {
  InterviewerPersona,
  TurnDialogue,
  InterviewDiagnosticScorecard,
} from '../../api/endpoints/hiregram';

const PERSONA_OPTIONS: Array<{ value: InterviewerPersona; label: string; avatar: string; desc: string }> = [
  {
    value: 'recruiter_sara',
    label: 'Sara Chen (Technical Recruiter)',
    avatar: '👩‍💼',
    desc: 'Focuses on background alignment, motivation, team collaboration, and compensation.',
  },
  {
    value: 'architect_alex',
    label: 'Alex Mercer (Staff Architect)',
    avatar: '👨‍💻',
    desc: 'Deep technical probing on concurrency, distributed systems bottlenecks, and reliability.',
  },
  {
    value: 'bar_raiser_marcus',
    label: 'Marcus Vance (Principal Bar Raiser)',
    avatar: '🎯',
    desc: 'Rigid STAR behavioral questioning demanding hard ownership and self-reflection.',
  },
  {
    value: 'startup_cto_elena',
    label: 'Elena Rostova (Startup CTO)',
    avatar: '🚀',
    desc: 'Pragmatic 0-to-1 velocity, engineering trade-offs, and product architecture intuition.',
  },
];

interface HiregramStudioProps {
  initialCompany?: string;
  initialRole?: string;
  jobDescription?: string;
}

export const HiregramStudio: React.FC<HiregramStudioProps> = ({
  initialCompany = 'Stripe',
  initialRole = 'Senior Distributed Systems Engineer',
  jobDescription,
}) => {
  const [company, setCompany] = useState(initialCompany);
  const [roleTitle, setRoleTitle] = useState(initialRole);
  const [persona, setPersona] = useState<InterviewerPersona>('architect_alex');
  const [sessionId, setSessionId] = useState<string | null>(null);

  const [currentTurn, setCurrentTurn] = useState<TurnDialogue | null>(null);
  const [completedTurns, setCompletedTurns] = useState<TurnDialogue[]>([]);
  const [isFinished, setIsFinished] = useState(false);
  const [scorecard, setScorecard] = useState<InterviewDiagnosticScorecard | null>(null);
  const [scorecardModalOpen, setScorecardModalOpen] = useState(false);

  const [answerText, setAnswerText] = useState('');
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  const timerRef = useRef<any>(null);
  const recognitionRef = useRef<any>(null);


  // Initialize Web Speech Synthesis & Recognition
  const playAudioPrompt = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = persona === 'architect_alex' ? 0.9 : 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  const startSession = async () => {
    setLoading(true);
    setCompletedTurns([]);
    setIsFinished(false);
    setScorecard(null);
    try {
      const res = await hiregramApi.startSession({
        company,
        role_title: roleTitle,
        persona,
        job_description: jobDescription,
        total_questions_target: 4,
      });
      setSessionId(res.data.session_id);
      setCurrentTurn(res.data.current_turn);
      setAnswerText('');
      playAudioPrompt(res.data.current_turn.question);
    } catch {
      // silent fallback
    } finally {
      setLoading(false);
    }
  };

  const startRecording = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech Recognition is not supported in this browser. Please type your answer below.');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript + ' ';
        }
        setAnswerText(transcript);
      };

      recognition.onerror = () => {
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognition.start();
      recognitionRef.current = recognition;
      setIsRecording(true);
      setRecordingSeconds(0);
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch {
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    setIsRecording(false);
  };

  const submitTurn = async () => {
    if (!sessionId || !answerText.trim() || loading) return;
    if (isRecording) stopRecording();

    setLoading(true);
    try {
      const res = await hiregramApi.submitTurn({
        session_id: sessionId,
        answer_text: answerText,
        duration_seconds: Math.max(recordingSeconds, 15),
      });

      setCompletedTurns((prev) => [...prev, res.data.evaluated_turn]);
      setAnswerText('');
      setRecordingSeconds(0);

      if (res.data.is_finished || !res.data.next_turn) {
        setIsFinished(true);
        setCurrentTurn(null);
        // Automatically fetch final scorecard
        const scoreRes = await hiregramApi.finalizeSession(sessionId);
        setScorecard(scoreRes.data.scorecard);
        setScorecardModalOpen(true);
      } else {
        setCurrentTurn(res.data.next_turn);
        playAudioPrompt(res.data.next_turn.question);
      }
    } catch {
      // silent fallback
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      {/* Configuration Header */}
      <Card sx={{ border: '1px solid #E2E8F0', borderRadius: 3, mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" spacing={1.5} alignItems="center" mb={2}>
            <VoiceIcon sx={{ color: '#6366F1', fontSize: 32 }} />
            <Box>
              <Typography variant="h6" fontWeight={800} color="#0F172A">
                🎙️ Hiregram Voice AI Mock Interview Studio
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Turn-by-turn conversational AI simulation with real-time speech cadence (WPM), STAR diagnostics, and gold-standard ideal answers.
              </Typography>
            </Box>
          </Stack>

          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, sm: 3 }}>
              <TextField
                label="Target Company"
                size="small"
                fullWidth
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                disabled={!!sessionId && !isFinished}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Role Title"
                size="small"
                fullWidth
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
                disabled={!!sessionId && !isFinished}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 3 }}>
              <TextField
                select
                label="Interviewer Persona"
                size="small"
                fullWidth
                value={persona}
                onChange={(e) => setPersona(e.target.value as InterviewerPersona)}
                disabled={!!sessionId && !isFinished}
              >
                {PERSONA_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.avatar} {opt.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, sm: 2 }}>
              <Button
                variant="contained"
                startIcon={<PlayIcon />}
                onClick={startSession}
                disabled={loading || !company || !roleTitle}
                fullWidth
                sx={{ height: 40, fontWeight: 700 }}
              >
                {sessionId && !isFinished ? 'Restart' : 'Start Simulation'}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Active Live Turn Window */}
      {currentTurn && (
        <Card sx={{ border: '2px solid #6366F1', borderRadius: 3, mb: 3, bgcolor: '#FAF5FF' }}>
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1.5}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Chip
                  label={`Question ${currentTurn.turn_index} of 4`}
                  size="small"
                  color="primary"
                  sx={{ fontWeight: 800 }}
                />
                <Typography variant="subtitle2" fontWeight={800} color="#581C87">
                  {currentTurn.interviewer_persona}
                </Typography>
              </Stack>
              <Tooltip title="Listen to question again">
                <IconButton size="small" onClick={() => playAudioPrompt(currentTurn.question)} sx={{ color: '#6366F1' }}>
                  <VolumeUpIcon />
                </IconButton>
              </Tooltip>
            </Box>

            <Typography variant="h6" fontWeight={700} color="#1E1B4B" sx={{ mb: 2.5, lineHeight: 1.4 }}>
              "{currentTurn.question}"
            </Typography>

            {/* Answer Input Deck */}
            <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#FFFFFF', mb: 2 }}>
              <TextField
                multiline
                rows={4}
                placeholder="Speak via microphone or type your response using the STAR method (Situation, Task, Action, Result)..."
                variant="standard"
                fullWidth
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                InputProps={{ disableUnderline: true }}
              />

              <Divider sx={{ my: 1.5 }} />

              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Stack direction="row" spacing={1} alignItems="center">
                  {!isRecording ? (
                    <Button
                      variant="outlined"
                      color="secondary"
                      startIcon={<MicIcon />}
                      onClick={startRecording}
                      sx={{ fontWeight: 700 }}
                    >
                      Record Voice
                    </Button>
                  ) : (
                    <Button
                      variant="contained"
                      color="error"
                      startIcon={<StopIcon />}
                      onClick={stopRecording}
                      sx={{ fontWeight: 700, animation: 'pulse 1.5s infinite' }}
                    >
                      Stop ({recordingSeconds}s)
                    </Button>
                  )}
                  {isRecording && (
                    <Typography variant="caption" color="error.main" fontWeight={700}>
                      Listening live… speak clearly into your mic.
                    </Typography>
                  )}
                </Stack>

                <Button
                  variant="contained"
                  color="primary"
                  onClick={submitTurn}
                  disabled={!answerText.trim() || loading}
                  sx={{ fontWeight: 700, px: 3 }}
                >
                  {loading ? <CircularProgress size={18} color="inherit" /> : 'Submit Answer →'}
                </Button>
              </Stack>
            </Paper>
          </CardContent>
        </Card>
      )}

      {/* Completed Turns History & Real-Time Diagnostics */}
      {completedTurns.length > 0 && (
        <Stack spacing={2.5} sx={{ mb: 3 }}>
          <Typography variant="subtitle1" fontWeight={800} color="#0F172A">
            Turn Diagnostics & Gold-Standard Comparisons ({completedTurns.length}):
          </Typography>

          {completedTurns.map((turn, idx) => (
            <Card key={idx} sx={{ border: '1px solid #E2E8F0', borderRadius: 3 }}>
              <CardContent sx={{ p: 2.5 }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="subtitle2" fontWeight={800} color="#0F172A">
                    Turn #{turn.turn_index}: {turn.question}
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Chip
                      icon={<SpeedIcon fontSize="small" />}
                      label={`${turn.wpm} WPM`}
                      size="small"
                      sx={{ fontWeight: 700 }}
                    />
                    <Chip
                      label={`Score: ${turn.turn_score}/100`}
                      size="small"
                      color={turn.turn_score >= 75 ? 'success' : 'warning'}
                      sx={{ fontWeight: 800 }}
                    />
                  </Stack>
                </Box>

                <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: '#F8FAFC', mb: 1.5 }}>
                  <Typography variant="caption" fontWeight={700} color="text.secondary" display="block" mb={0.5}>
                    Your Transcribed Answer:
                  </Typography>
                  <Typography variant="body2" color="#1E293B">
                    {turn.candidate_answer}
                  </Typography>
                </Paper>

                {/* STAR Breakdown */}
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
                  {Object.entries(turn.star_breakdown).map(([k, v]) => (
                    <Chip
                      key={k}
                      label={`${k.toUpperCase()}: ${v}/25`}
                      size="small"
                      variant="outlined"
                      sx={{ fontWeight: 700, fontSize: '0.75rem' }}
                    />
                  ))}
                  {turn.filler_words_detected.length > 0 && (
                    <Chip
                      icon={<WarningIcon fontSize="small" />}
                      label={`Fillers (${turn.filler_words_detected.length}): ${turn.filler_words_detected.slice(0, 3).join(', ')}`}
                      size="small"
                      color="warning"
                      sx={{ fontWeight: 600, fontSize: '0.75rem' }}
                    />
                  )}
                </Stack>

                {/* Gold Standard Ideal Answer */}
                {turn.gold_standard_ideal_answer && (
                  <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: '#F0FDF4', borderColor: '#BBF7D0' }}>
                    <Stack direction="row" spacing={1} alignItems="center" mb={0.5}>
                      <SparkleIcon sx={{ color: '#16A34A', fontSize: 18 }} />
                      <Typography variant="subtitle2" fontWeight={800} color="#166534">
                        Gold Standard Ideal Answer:
                      </Typography>
                    </Stack>
                    <Typography variant="body2" color="#14532D" sx={{ fontSize: '0.85rem', fontStyle: 'italic' }}>
                      {turn.gold_standard_ideal_answer}
                    </Typography>
                  </Paper>
                )}
              </CardContent>
            </Card>
          ))}
        </Stack>
      )}

      {/* Final Scorecard Trigger */}
      {scorecard && (
        <Card sx={{ border: '2px solid #10B981', borderRadius: 3, bgcolor: '#ECFDF5', p: 1, mb: 3 }}>
          <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <CheckCircleIcon sx={{ color: '#10B981', fontSize: 36 }} />
              <Box>
                <Typography variant="h6" fontWeight={800} color="#065F46">
                  Simulation Complete — {scorecard.readiness_verdict} ({scorecard.overall_score}/100)
                </Typography>
                <Typography variant="caption" color="#047857">
                  Technical Depth: {scorecard.technical_depth_score} · STAR Structure: {scorecard.star_structure_score} · Delivery: {scorecard.delivery_cadence_score}
                </Typography>
              </Box>
            </Stack>
            <Button
              variant="contained"
              color="success"
              startIcon={<ScorecardIcon />}
              onClick={() => setScorecardModalOpen(true)}
              sx={{ fontWeight: 800 }}
            >
              View Diagnostic Scorecard
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Diagnostic Scorecard Modal */}
      <Dialog
        open={scorecardModalOpen}
        onClose={() => setScorecardModalOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 800, color: '#0F172A', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <ScorecardIcon sx={{ color: '#6366F1' }} />
            <span>Hiregram Interview Diagnostic Scorecard — {scorecard?.company}</span>
          </Stack>
          <IconButton size="small" onClick={() => setScorecardModalOpen(false)}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        <DialogContent dividers>
          {scorecard && (
            <Box>
              {/* Verdict Banner */}
              <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3, bgcolor: '#F8FAFC', mb: 3 }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={700}>
                      OVERALL READINESS VERDICT:
                    </Typography>
                    <Typography variant="h5" fontWeight={900} color="#6366F1">
                      {scorecard.readiness_verdict}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      Target Role: <b>{scorecard.role_title}</b> @ {scorecard.company}
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Box textAlign={{ xs: 'left', sm: 'right' }}>
                      <Typography variant="h3" fontWeight={900} color="#0F172A">
                        {scorecard.overall_score}
                        <Typography component="span" variant="h6" color="text.secondary">/100</Typography>
                      </Typography>
                      <Chip label={`Persona: ${scorecard.persona.toUpperCase()}`} size="small" sx={{ fontWeight: 700 }} />
                    </Box>
                  </Grid>
                </Grid>
              </Paper>

              {/* 4 Competency Scores */}
              <Typography variant="subtitle2" fontWeight={800} color="#0F172A" gutterBottom>
                Competency Rubric Breakdown:
              </Typography>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={700}>TECHNICAL DEPTH</Typography>
                    <Typography variant="h6" fontWeight={800} color="#2563EB">{scorecard.technical_depth_score}%</Typography>
                    <LinearProgress variant="determinate" value={scorecard.technical_depth_score} sx={{ mt: 1, borderRadius: 1 }} />
                  </Paper>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={700}>STAR STRUCTURE</Typography>
                    <Typography variant="h6" fontWeight={800} color="#16A34A">{scorecard.star_structure_score}%</Typography>
                    <LinearProgress variant="determinate" value={scorecard.star_structure_score} color="success" sx={{ mt: 1, borderRadius: 1 }} />
                  </Paper>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={700}>VERBAL DELIVERY</Typography>
                    <Typography variant="h6" fontWeight={800} color="#D97706">{scorecard.delivery_cadence_score}%</Typography>
                    <LinearProgress variant="determinate" value={scorecard.delivery_cadence_score} color="warning" sx={{ mt: 1, borderRadius: 1 }} />
                  </Paper>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={700}>LEADERSHIP IMPACT</Typography>
                    <Typography variant="h6" fontWeight={800} color="#7C3AED">{scorecard.leadership_impact_score}%</Typography>
                    <LinearProgress variant="determinate" value={scorecard.leadership_impact_score} color="secondary" sx={{ mt: 1, borderRadius: 1 }} />
                  </Paper>
                </Grid>
              </Grid>

              {/* Strengths & Practice Drills */}
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="subtitle2" fontWeight={800} color="#166534" gutterBottom>
                    ✨ Key Demonstrated Strengths:
                  </Typography>
                  <Stack spacing={1}>
                    {scorecard.key_strengths.map((s, i) => (
                      <Paper key={i} variant="outlined" sx={{ p: 1.25, borderRadius: 1.5, bgcolor: '#F0FDF4', borderColor: '#BBF7D0' }}>
                        <Typography variant="body2" color="#14532D">{s}</Typography>
                      </Paper>
                    ))}
                  </Stack>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="subtitle2" fontWeight={800} color="#4F46E5" gutterBottom>
                    🎯 Recommended Practice Drills:
                  </Typography>
                  <Stack spacing={1}>
                    {scorecard.practice_drills_recommended.map((d, i) => (
                      <Paper key={i} variant="outlined" sx={{ p: 1.25, borderRadius: 1.5, bgcolor: '#EEF2FF', borderColor: '#C7D2FE' }}>
                        <Typography variant="body2" color="#312E81">{d}</Typography>
                      </Paper>
                    ))}
                  </Stack>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>

        <DialogActions sx={{ p: 2 }}>
          <Button
            variant="outlined"
            startIcon={<PrintIcon />}
            onClick={() => window.print()}
            sx={{ fontWeight: 700 }}
          >
            Print / Save as PDF
          </Button>
          <Button
            variant="contained"
            onClick={() => setScorecardModalOpen(false)}
            sx={{ fontWeight: 700 }}
          >
            Done
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default HiregramStudio;

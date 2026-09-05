import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Stack,
  Chip,
  Button,
  TextField,
  Paper,
  LinearProgress,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  Mic as MicIcon,
  MicOff as MicOffIcon,
  Speed as SpeedIcon,
  Timer as TimerIcon,
  AutoAwesome as SparkleIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Refresh as RefreshIcon,
  GraphicEq as WaveformIcon,
  RecordVoiceOver as VoiceIcon,
} from '@mui/icons-material';
import {
  cadenceCoachApi,
  type CadenceAnalysisResult,
  type VoiceScorecardResult,
} from '../../api/endpoints/cadence_api';

const PRESET_SIMULATIONS = [
  {
    title: '🌟 High-Impact STAR Response',
    duration: 52,
    text: 'In my last role at FinTech Corp, the situation was our distributed ledger was bottlenecked at 1,200 RPS during flash loan events. The task assigned to me was redesigning the transactional consistency pipeline. For my action, I designed and implemented an asynchronous Redis lock with Kafka event streaming, refactoring our core DB writes. As a result, our P99 latency dropped by 64% and throughput increased to 8,500 RPS without a single state inconsistency.',
  },
  {
    title: '⚠️ Rambling & Filler-Heavy Answer',
    duration: 82,
    text: 'Um, basically what happened was, like, we had this problem with our microservices. And to be honest, I mean, you know, it was kind of messy. So like, basically I sort of looked into the logs and uh, actually found that the database connections were pooling incorrectly. So like, I basically restarted the services and uh, you know, wrote some scripts to kind of handle it.',
  },
  {
    title: '🐢 Slow & Hesitant Delivery',
    duration: 35,
    text: 'Well... we used... PostgreSQL... for storing user sessions... and... we had a few indexes...',
  },
  {
    title: '⚡ Fast / Panic Speed Explanation',
    duration: 18,
    text: 'SoWeImplementedConsistentHashingUsingAVirtualNodeRingWith200NodesPerMachineAndWhenANewNodeJoinsItOnlyMigratesOneOverNthOfTheKeysToPreventHotspottingInTheCluster!',
  },
];

export const VoiceCadenceCoachWidget: React.FC = () => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [speechSeconds, setSpeechSeconds] = useState(0);
  const [analysis, setAnalysis] = useState<CadenceAnalysisResult | null>(null);
  const [scorecard, setScorecard] = useState<VoiceScorecardResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGeneratingScorecard, setIsGeneratingScorecard] = useState(false);

  const timerRef = useRef<any>(null);
  const recognitionRef = useRef<any>(null);

  // Initialize Web Speech API if supported
  useEffect(() => {
    if (typeof window !== 'undefined' && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const rec = new SpeechRec();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'en-US';

      rec.onresult = (event: any) => {
        const current = Array.from(event.results)
          .map((r: any) => r[0].transcript)
          .join(' ');
        setTranscript(current);
      };

      rec.onerror = (e: any) => {
        console.warn('Speech Recognition error:', e);
      };

      recognitionRef.current = rec;
    }
  }, []);

  // Timer tick for monologue duration
  useEffect(() => {
    if (isListening) {
      timerRef.current = setInterval(() => {
        setSpeechSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isListening]);

  // Trigger analysis when transcript or timer updates (debounced)
  useEffect(() => {
    if (!transcript.trim()) return;

    const timeout = setTimeout(async () => {
      try {
        const result = await cadenceCoachApi.analyzeCadence({
          transcript,
          duration_seconds: Math.max(speechSeconds, 1),
        });
        setAnalysis(result);
      } catch (err) {
        console.error('Cadence analysis failed:', err);
      }
    }, 600);

    return () => clearTimeout(timeout);
  }, [transcript, speechSeconds]);

  const toggleMic = () => {
    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
      setIsListening(false);
    } else {
      setTranscript('');
      setSpeechSeconds(0);
      setAnalysis(null);
      setScorecard(null);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch (_) {}
      }
      setIsListening(true);
    }
  };

  const handleSimulatePreset = async (preset: typeof PRESET_SIMULATIONS[0]) => {
    if (isListening) toggleMic();
    setTranscript(preset.text);
    setSpeechSeconds(preset.duration);
    setIsAnalyzing(true);
    try {
      const res = await cadenceCoachApi.analyzeCadence({
        transcript: preset.text,
        duration_seconds: preset.duration,
      });
      setAnalysis(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGenerateScorecard = async () => {
    if (!transcript.trim()) return;
    setIsGeneratingScorecard(true);
    try {
      const res = await cadenceCoachApi.generateScorecard({
        session_id: `cadence_sess_${Date.now()}`,
        total_duration_seconds: Math.max(speechSeconds, 5),
        transcripts: [transcript],
      });
      setScorecard(res);
    } catch (err) {
      console.error('Scorecard failed:', err);
    } finally {
      setIsGeneratingScorecard(false);
    }
  };

  const currentWpm = analysis?.wpm || (speechSeconds > 0 ? Math.round((transcript.trim().split(/\s+/).filter(Boolean).length / (speechSeconds / 60)) || 0) : 0);
  const rambleProgress = Math.min((speechSeconds / 75) * 100, 100);

  return (
    <Box sx={{ width: '100%' }}>
      {/* Top Telemetry Header */}
      <Card
        sx={{
          mb: 3,
          bgcolor: '#0D131F',
          border: '1.5px solid rgba(0, 240, 255, 0.3)',
          borderRadius: '16px',
          boxShadow: '0 0 30px rgba(0, 240, 255, 0.1)',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2}>
            <Box>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: '10px',
                    bgcolor: 'rgba(0, 240, 255, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #00F0FF',
                  }}
                >
                  <WaveformIcon sx={{ color: '#00F0FF', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 900, color: '#F8FAFC' }}>
                    🎙️ Live Voice Biomarker & Cadence Telemetry HUD
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                    Real-time WPM speedometer, 75s ramble alarm, filler-word suppression, & STAR delivery scorecard.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Stack direction="row" spacing={1.5} alignItems="center">
              <Button
                variant="contained"
                startIcon={isListening ? <MicOffIcon /> : <MicIcon />}
                onClick={toggleMic}
                sx={{
                  bgcolor: isListening ? '#FF0055' : '#00FFA3',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  px: 2.5,
                  '&:hover': { bgcolor: isListening ? '#E0004C' : '#00D88B' },
                }}
              >
                {isListening ? 'Stop Listening' : 'Start Live Mic'}
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Real-Time Live HUD Gauges */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Speedometer (WPM) */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper
            sx={{
              p: 3,
              height: '100%',
              bgcolor: '#0D131F',
              border: `1.5px solid ${analysis?.cadence_color || 'rgba(0, 255, 163, 0.3)'}`,
              borderRadius: '16px',
            }}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#94A3B8', display: 'flex', alignItems: 'center', gap: 1 }}>
                <SpeedIcon sx={{ fontSize: 18, color: analysis?.cadence_color || '#00FFA3' }} /> SPEECH CADENCE
              </Typography>
              <Chip
                label={analysis?.cadence_status || (currentWpm > 0 ? 'Evaluating...' : 'Golden: 110–155')}
                size="small"
                sx={{
                  bgcolor: 'rgba(0, 0, 0, 0.4)',
                  color: analysis?.cadence_color || '#00FFA3',
                  fontWeight: 800,
                  fontSize: '0.7rem',
                  border: `1px solid ${analysis?.cadence_color || 'rgba(0, 255, 163, 0.4)'}`,
                }}
              />
            </Stack>

            <Box sx={{ textAlign: 'center', my: 2 }}>
              <Typography variant="h2" sx={{ fontWeight: 900, color: analysis?.cadence_color || '#00FFA3', fontFamily: 'monospace' }}>
                {currentWpm}
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, letterSpacing: 1 }}>
                WORDS PER MINUTE (WPM)
              </Typography>
            </Box>

            <Typography variant="caption" sx={{ color: '#CBD5E1', display: 'block', textAlign: 'center', bgcolor: 'rgba(255,255,255,0.03)', p: 1, borderRadius: '8px' }}>
              {analysis?.pacing_advice || 'Maintain 110–155 WPM for executive authority and clarity.'}
            </Typography>
          </Paper>
        </Grid>

        {/* 75s Ramble Alarm */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper
            sx={{
              p: 3,
              height: '100%',
              bgcolor: '#0D131F',
              border: `1.5px solid ${speechSeconds >= 70 ? '#FF0055' : 'rgba(255, 230, 0, 0.3)'}`,
              borderRadius: '16px',
            }}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#94A3B8', display: 'flex', alignItems: 'center', gap: 1 }}>
                <TimerIcon sx={{ fontSize: 18, color: speechSeconds >= 70 ? '#FF0055' : '#FFE600' }} /> MONOLOGUE DURATION
              </Typography>
              <Chip
                label={speechSeconds >= 70 ? '⚠️ RAMBLE LIMIT' : '75s Max Target'}
                size="small"
                sx={{
                  bgcolor: speechSeconds >= 70 ? 'rgba(255,0,85,0.2)' : 'rgba(255,230,0,0.15)',
                  color: speechSeconds >= 70 ? '#FF0055' : '#FFE600',
                  fontWeight: 800,
                  fontSize: '0.7rem',
                }}
              />
            </Stack>

            <Box sx={{ textAlign: 'center', my: 2 }}>
              <Typography variant="h2" sx={{ fontWeight: 900, color: speechSeconds >= 70 ? '#FF0055' : '#FFE600', fontFamily: 'monospace' }}>
                {speechSeconds}s
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, letterSpacing: 1 }}>
                CONTINUOUS MONOLOGUE
              </Typography>
            </Box>

            <LinearProgress
              variant="determinate"
              value={rambleProgress}
              sx={{
                height: 8,
                borderRadius: 4,
                bgcolor: 'rgba(255,255,255,0.08)',
                '& .MuiLinearProgress-bar': {
                  bgcolor: speechSeconds >= 70 ? '#FF0055' : speechSeconds >= 50 ? '#FFE600' : '#00FFA3',
                },
              }}
            />
          </Paper>
        </Grid>

        {/* Filler Word Suppression & Clarity */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper
            sx={{
              p: 3,
              height: '100%',
              bgcolor: '#0D131F',
              border: '1.5px solid rgba(0, 240, 255, 0.3)',
              borderRadius: '16px',
            }}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#94A3B8', display: 'flex', alignItems: 'center', gap: 1 }}>
                <SparkleIcon sx={{ fontSize: 18, color: '#00F0FF' }} /> CLARITY & FILLERS
              </Typography>
              <Chip
                label={`${analysis?.total_fillers_detected || 0} Fillers`}
                size="small"
                sx={{
                  bgcolor: (analysis?.total_fillers_detected || 0) > 2 ? 'rgba(255,0,85,0.2)' : 'rgba(0,240,255,0.15)',
                  color: (analysis?.total_fillers_detected || 0) > 2 ? '#FF0055' : '#00F0FF',
                  fontWeight: 800,
                  fontSize: '0.7rem',
                }}
              />
            </Stack>

            <Box sx={{ textAlign: 'center', my: 2 }}>
              <Typography variant="h2" sx={{ fontWeight: 900, color: '#00F0FF', fontFamily: 'monospace' }}>
                {analysis?.clarity_score !== undefined ? `${analysis.clarity_score}%` : '100%'}
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 700, letterSpacing: 1 }}>
                ARTICULATION PURITY
              </Typography>
            </Box>

            {analysis?.filler_breakdown && Object.keys(analysis.filler_breakdown).length > 0 ? (
              <Stack direction="row" spacing={0.5} flexWrap="wrap" justifyContent="center">
                {Object.entries(analysis.filler_breakdown).map(([word, count]) => (
                  <Chip
                    key={word}
                    label={`"${word}": ${count}`}
                    size="small"
                    sx={{ bgcolor: 'rgba(255,0,85,0.15)', color: '#FF0055', fontSize: '0.65rem', fontWeight: 700, mb: 0.5 }}
                  />
                ))}
              </Stack>
            ) : (
              <Typography variant="caption" sx={{ color: '#00FFA3', display: 'block', textAlign: 'center', fontWeight: 700 }}>
                ✨ Zero filler words detected. Crisp executive delivery.
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Ramble Monologue Warning Banner */}
      {speechSeconds >= 70 && (
        <Alert
          severity="warning"
          sx={{
            mb: 3,
            bgcolor: 'rgba(255, 0, 85, 0.15)',
            border: '1.5px solid #FF0055',
            color: '#F8FAFC',
            borderRadius: '12px',
            '& .MuiAlert-icon': { color: '#FF0055' },
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#FF0055' }}>
            ⚠️ 75s MONOLOGUE THRESHOLD REACHED
          </Typography>
          <Typography variant="body2" sx={{ color: '#CBD5E1', mt: 0.5 }}>
            {analysis?.ramble_check_in_cue ||
              "Wrap up your current point and pass the conversational baton: 'Does this high-level architecture align with what you had in mind?'"}
          </Typography>
        </Alert>
      )}

      {/* Interactive Transcript & Simulation Presets */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#F8FAFC', display: 'flex', alignItems: 'center', gap: 1 }}>
                  <VoiceIcon sx={{ color: '#00FFA3', fontSize: 20 }} /> Live Spoken Transcript Stream
                </Typography>
                {isAnalyzing && (
                  <Chip
                    label="Analyzing DSP..."
                    size="small"
                    sx={{ bgcolor: 'rgba(0, 240, 255, 0.15)', color: '#00F0FF', fontSize: '0.65rem', fontWeight: 800 }}
                  />
                )}
              </Stack>
              <Button
                size="small"
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={() => {
                  setTranscript('');
                  setSpeechSeconds(0);
                  setAnalysis(null);
                  setScorecard(null);
                }}
                sx={{ color: '#94A3B8', borderColor: 'rgba(255,255,255,0.1)', textTransform: 'none' }}
              >
                Reset
              </Button>
            </Stack>

            <TextField
              fullWidth
              multiline
              rows={4}
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Speak using microphone or type/paste your candidate response to test cadence..."
              sx={{
                bgcolor: '#06090E',
                borderRadius: '8px',
                '& .MuiOutlinedInput-root': {
                  color: '#E2E8F0',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                },
              }}
            />

            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mt: 2 }}>
              <Typography variant="caption" sx={{ color: '#64748B' }}>
                {transcript.split(/\s+/).filter(Boolean).length} words spoken over {speechSeconds}s
              </Typography>
              <Button
                variant="contained"
                disabled={!transcript.trim() || isGeneratingScorecard}
                onClick={handleGenerateScorecard}
                startIcon={isGeneratingScorecard ? <CircularProgress size={16} sx={{ color: '#06090E' }} /> : <CheckCircleIcon />}
                sx={{
                  bgcolor: '#00FFA3',
                  color: '#06090E',
                  fontWeight: 900,
                  textTransform: 'none',
                  '&:hover': { bgcolor: '#00D88B' },
                }}
              >
                {isGeneratingScorecard ? 'Compiling Scorecard...' : 'Generate STAR Scorecard'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* Quick Simulation Presets */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper sx={{ p: 3, bgcolor: '#0D131F', border: '1.5px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, color: '#FFE600', mb: 1 }}>
              ⚡ Pacing & Telemetry Test Scenarios
            </Typography>
            <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', mb: 2 }}>
              Simulate candidate delivery archetypes to test real-time DSP filters and STAR grading.
            </Typography>

            <Stack spacing={1.5}>
              {PRESET_SIMULATIONS.map((preset) => (
                <Paper
                  key={preset.title}
                  variant="outlined"
                  onClick={() => handleSimulatePreset(preset)}
                  sx={{
                    p: 1.5,
                    bgcolor: '#06090E',
                    cursor: 'pointer',
                    borderRadius: '10px',
                    border: '1px solid rgba(255,255,255,0.06)',
                    transition: 'all 0.2s',
                    '&:hover': {
                      borderColor: '#00FFA3',
                      bgcolor: 'rgba(0, 255, 163, 0.05)',
                    },
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" sx={{ fontWeight: 800, color: '#F8FAFC' }}>
                      {preset.title}
                    </Typography>
                    <Chip label={`${preset.duration}s`} size="small" sx={{ bgcolor: 'rgba(255,255,255,0.06)', color: '#94A3B8', fontSize: '0.65rem' }} />
                  </Stack>
                  <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mt: 0.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {preset.text}
                  </Typography>
                </Paper>
              ))}
            </Stack>
          </Paper>
        </Grid>
      </Grid>

      {/* End-of-Session STAR Delivery Scorecard */}
      {scorecard && (
        <Card
          sx={{
            bgcolor: '#0D131F',
            border: '2px solid #00FFA3',
            borderRadius: '20px',
            boxShadow: '0 0 40px rgba(0, 255, 163, 0.2)',
          }}
        >
          <CardContent sx={{ p: { xs: 3, md: 4 } }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 900, color: '#00FFA3' }}>
                  🏆 Executive Delivery Scorecard
                </Typography>
                <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                  Holistic evaluation of speech cadence, filler suppression, and STAR structural completion.
                </Typography>
              </Box>
              <Chip
                label={scorecard.executive_rating}
                sx={{
                  bgcolor: 'rgba(0, 255, 163, 0.2)',
                  color: '#00FFA3',
                  fontWeight: 900,
                  fontSize: '0.85rem',
                  py: 2.2,
                  px: 1.5,
                  border: '1.5px solid #00FFA3',
                }}
              />
            </Stack>

            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 4 }}>
                <Paper sx={{ p: 2.5, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 800 }}>
                    OVERALL COMPOSITE SCORE
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 900, color: '#00FFA3', my: 1 }}>
                    {scorecard.overall_executive_score} / 100
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#CBD5E1' }}>
                    60% Articulation & Cadence | 40% STAR Adherence
                  </Typography>
                </Paper>
              </Grid>

              <Grid size={{ xs: 12, md: 8 }}>
                <Paper sx={{ p: 2.5, bgcolor: '#06090E', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 800, mb: 1.5, display: 'block' }}>
                    STAR METHODOLOGY CHECKLIST
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid size={{ xs: 6, sm: 3 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        {scorecard.star_framework_adherence.situation_detected ? (
                          <CheckCircleIcon sx={{ color: '#00FFA3', fontSize: 20 }} />
                        ) : (
                          <CancelIcon sx={{ color: '#64748B', fontSize: 20 }} />
                        )}
                        <Typography variant="body2" sx={{ fontWeight: 800, color: scorecard.star_framework_adherence.situation_detected ? '#F8FAFC' : '#64748B' }}>
                          Situation
                        </Typography>
                      </Stack>
                    </Grid>

                    <Grid size={{ xs: 6, sm: 3 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        {scorecard.star_framework_adherence.task_detected ? (
                          <CheckCircleIcon sx={{ color: '#00FFA3', fontSize: 20 }} />
                        ) : (
                          <CancelIcon sx={{ color: '#64748B', fontSize: 20 }} />
                        )}
                        <Typography variant="body2" sx={{ fontWeight: 800, color: scorecard.star_framework_adherence.task_detected ? '#F8FAFC' : '#64748B' }}>
                          Task
                        </Typography>
                      </Stack>
                    </Grid>

                    <Grid size={{ xs: 6, sm: 3 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        {scorecard.star_framework_adherence.action_detected ? (
                          <CheckCircleIcon sx={{ color: '#00FFA3', fontSize: 20 }} />
                        ) : (
                          <CancelIcon sx={{ color: '#64748B', fontSize: 20 }} />
                        )}
                        <Typography variant="body2" sx={{ fontWeight: 800, color: scorecard.star_framework_adherence.action_detected ? '#F8FAFC' : '#64748B' }}>
                          Action
                        </Typography>
                      </Stack>
                    </Grid>

                    <Grid size={{ xs: 6, sm: 3 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        {scorecard.star_framework_adherence.result_metrics_detected ? (
                          <CheckCircleIcon sx={{ color: '#00FFA3', fontSize: 20 }} />
                        ) : (
                          <CancelIcon sx={{ color: '#64748B', fontSize: 20 }} />
                        )}
                        <Typography variant="body2" sx={{ fontWeight: 800, color: scorecard.star_framework_adherence.result_metrics_detected ? '#F8FAFC' : '#64748B' }}>
                          Result / Metrics
                        </Typography>
                      </Stack>
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 1.5, borderColor: 'rgba(255,255,255,0.06)' }} />

                  <Typography variant="caption" sx={{ color: '#CBD5E1' }}>
                    {scorecard.star_framework_adherence.result_metrics_detected
                      ? '✅ Quantifiable metrics and business outcomes successfully detected.'
                      : '💡 Recommendation: Include measurable metrics (% latency reduction, saved cost, throughput gains) in your Result phase.'}
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

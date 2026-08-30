import React, { useState, useRef } from 'react';
import {
  Box, Button, Card, CardContent, Chip, CircularProgress, LinearProgress,
  Stack, TextField, Typography, IconButton, Tooltip,
} from '@mui/material';
import {
  QuestionAnswer as QuestionIcon,
  Send as SendIcon,
  VolumeUp as VolumeUpIcon,
  Mic as MicIcon,
  Stop as StopIcon,
  RecordVoiceOver as VoiceIcon,
} from '@mui/icons-material';

import CompanySelect from './CompanySelect';
import { useInterviewQuestions, useScoreAnswer } from '../../hooks/useAgents';
import { voiceInterviewerApi } from '../../api';
import type { InterviewQuestion, InterviewScore } from '../../api/types';
import type { VoiceFeedbackResponse } from '../../api/endpoints/voice_interviewer';
import { HiregramStudio } from '../../components/hiregram/HiregramStudio';


const typeColor: Record<InterviewQuestion['type'], 'secondary' | 'info' | 'default'> = {
  company_specific: 'secondary', technical: 'info', behavioral: 'default',
};

const STAR_LABELS: Record<keyof InterviewScore['star_scores'], string> = {
  situation: 'Situation', task: 'Task', action: 'Action', result: 'Result',
};

const QuestionCard: React.FC<{ question: InterviewQuestion }> = ({ question }) => {
  const [answer, setAnswer] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const [voiceAnalysis, setVoiceAnalysis] = useState<VoiceFeedbackResponse | null>(null);
  const [voiceLoading, setVoiceLoading] = useState(false);

  const recognitionRef = useRef<any>(null);
  const timerRef = useRef<any>(null);
  const scoreAnswer = useScoreAnswer();

  const handleSpeakQuestion = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(question.text);
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  const startVoiceRecording = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please type your answer or use Google Chrome.');
      return;
    }

    try {
      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'en-US';

      let currentTranscript = '';
      rec.onresult = (e: any) => {
        let transcript = '';
        for (let i = 0; i < e.results.length; i++) {
          transcript += e.results[i][0].transcript + ' ';
        }
        currentTranscript = transcript.trim();
        setAnswer(currentTranscript);
      };

      rec.onerror = () => {
        stopVoiceRecording();
      };

      rec.start();
      recognitionRef.current = rec;
      setIsRecording(true);
      setRecordDuration(0);

      timerRef.current = setInterval(() => {
        setRecordDuration((prev) => prev + 1);
      }, 1000);
    } catch {
      setIsRecording(false);
    }
  };

  const stopVoiceRecording = async () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);

    if (answer.trim()) {
      setVoiceLoading(true);
      try {
        const res = await voiceInterviewerApi.analyzeVoiceResponse({
          transcript: answer,
          duration_seconds: Math.max(5, recordDuration),
          target_focus: question.focus_area || 'Distributed Systems',
        });
        setVoiceAnalysis(res.data);
      } catch {
        // silent fallback
      } finally {
        setVoiceLoading(false);
      }
    }
  };

  return (
    <Card variant="outlined" sx={{ mb: 2, border: '1px solid #E2E8F0', borderRadius: 2 }}>
      <CardContent sx={{ p: 2.5 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ flex: 1 }}>
            <Typography variant="body1" sx={{ fontWeight: 700, color: '#0F172A' }}>{question.text}</Typography>
            <Tooltip title="Listen to Question (AI Voice)">
              <IconButton size="small" onClick={handleSpeakQuestion} sx={{ color: '#4F46E5' }}>
                <VolumeUpIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
          <Chip size="small" color={typeColor[question.type]} label={question.type.replace('_', ' ')} sx={{ fontWeight: 600 }} />
        </Stack>

        <TextField
          placeholder="Speak your answer using the microphone or type here (Situation → Task → Action → Result)…"
          multiline
          minRows={3}
          fullWidth
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          sx={{ mb: 1.5 }}
        />

        <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap>
          {!isRecording ? (
            <Button
              size="small"
              variant="outlined"
              color="secondary"
              startIcon={<MicIcon />}
              onClick={startVoiceRecording}
              sx={{ fontWeight: 600, borderRadius: 2 }}
            >
              🎙️ Speak Answer (Live Audio)
            </Button>
          ) : (
            <Button
              size="small"
              variant="contained"
              color="error"
              startIcon={<StopIcon />}
              onClick={stopVoiceRecording}
              sx={{ fontWeight: 700, borderRadius: 2, animation: 'pulse 1.5s infinite' }}
            >
              ⏹️ Stop Recording ({recordDuration}s)
            </Button>
          )}

          <Button
            size="small"
            variant="contained"
            startIcon={scoreAnswer.isPending ? <CircularProgress size={14} color="inherit" /> : <SendIcon />}
            onClick={() => scoreAnswer.mutate({ question: question.text, answer, focusArea: question.focus_area })}
            disabled={!answer.trim() || scoreAnswer.isPending || isRecording}
            sx={{ fontWeight: 700, borderRadius: 2 }}
          >
            Score STAR Answer
          </Button>

          {voiceLoading && <CircularProgress size={18} />}
        </Stack>

        {/* Spoken Audio Verbal Delivery Analytics */}
        {voiceAnalysis && (
          <Box sx={{ mt: 2, p: 2, bgcolor: '#F0FDF4', borderRadius: 2, border: '1px solid #BBF7D0' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
              <Stack direction="row" spacing={1} alignItems="center">
                <VoiceIcon sx={{ color: '#16A34A' }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#166534' }}>
                  🎙️ Verbal Delivery & Fluency Score: {voiceAnalysis.speech_delivery_score}/100
                </Typography>
              </Stack>
              <Chip
                label={voiceAnalysis.cadence_stats.cadence_rating}
                size="small"
                sx={{ fontWeight: 700, bgcolor: '#DCFCE7', color: '#15803D' }}
              />
            </Stack>

            <Stack direction="row" spacing={2} sx={{ mb: 1.5 }}>
              <Box sx={{ flex: 1, p: 1, bgcolor: '#FFFFFF', borderRadius: 1.5, border: '1px solid #DCFCE7' }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>Cadence</Typography>
                <Typography variant="body2" fontWeight={800} color="#0F172A">{voiceAnalysis.cadence_stats.wpm} WPM</Typography>
              </Box>
              <Box sx={{ flex: 1, p: 1, bgcolor: '#FFFFFF', borderRadius: 1.5, border: '1px solid #DCFCE7' }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>Filler Words</Typography>
                <Typography variant="body2" fontWeight={800} color={voiceAnalysis.filler_stats.total_fillers > 3 ? '#DC2626' : '#16A34A'}>
                  {voiceAnalysis.filler_stats.total_fillers} ({voiceAnalysis.filler_stats.filler_percentage}%)
                </Typography>
              </Box>
              <Box sx={{ flex: 1, p: 1, bgcolor: '#FFFFFF', borderRadius: 1.5, border: '1px solid #DCFCE7' }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>Duration</Typography>
                <Typography variant="body2" fontWeight={800} color="#0F172A">{voiceAnalysis.cadence_stats.duration_seconds}s</Typography>
              </Box>
            </Stack>

            {voiceAnalysis.delivery_tips.map((tip, idx) => (
              <Typography key={idx} variant="caption" color="#166534" display="block" sx={{ mt: 0.5, fontWeight: 500 }}>
                💡 {tip}
              </Typography>
            ))}
          </Box>
        )}

        {/* Standard STAR Score Breakdown */}
        {scoreAnswer.data && (
          <Box sx={{ mt: 2, p: 2, bgcolor: '#F8FAFC', borderRadius: 2, border: '1px solid #E2E8F0' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                STAR Score: {scoreAnswer.data.data.overall}/100
              </Typography>
              {scoreAnswer.data.data.used_llm && <Chip size="small" label="AI STAR Checked" color="success" />}
            </Stack>
            <Stack direction="row" spacing={2} sx={{ mb: 1 }}>
              {(Object.keys(STAR_LABELS) as Array<keyof InterviewScore['star_scores']>).map((key) => (
                <Box key={key} sx={{ flex: 1 }}>
                  <Typography variant="caption" color="text.secondary">{STAR_LABELS[key]}</Typography>
                  <LinearProgress
                    variant="determinate"
                    value={scoreAnswer.data!.data.star_scores[key] * 100}
                    color={scoreAnswer.data!.data.star_scores[key] > 0 ? 'success' : 'error'}
                    sx={{ height: 6, borderRadius: 3, mt: 0.5 }}
                  />
                </Box>
              ))}
            </Stack>
            <Typography variant="body2" color="text.secondary">{scoreAnswer.data.data.feedback}</Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export const InterviewSimulatorTab: React.FC = () => {
  const [activeMode, setActiveMode] = useState<'hiregram' | 'drill'>('hiregram');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  const [jd, setJd] = useState('');
  const [numQuestions, setNumQuestions] = useState(5);
  const getQuestions = useInterviewQuestions();

  return (
    <Box>
      {/* Mode Switcher */}
      <Stack direction="row" spacing={1.5} sx={{ mb: 3 }}>
        <Button
          variant={activeMode === 'hiregram' ? 'contained' : 'outlined'}
          color="primary"
          startIcon={<VoiceIcon />}
          onClick={() => setActiveMode('hiregram')}
          sx={{ fontWeight: 800, borderRadius: 2 }}
        >
          🎙️ Hiregram Voice AI Studio
        </Button>
        <Button
          variant={activeMode === 'drill' ? 'contained' : 'outlined'}
          color="secondary"
          startIcon={<QuestionIcon />}
          onClick={() => setActiveMode('drill')}
          sx={{ fontWeight: 800, borderRadius: 2 }}
        >
          📝 Custom Question Drill & STAR Scorer
        </Button>
      </Stack>

      {activeMode === 'hiregram' ? (
        <HiregramStudio />
      ) : (
        <Box>
          <Card sx={{ mb: 3, border: '1px solid #E2E8F0', borderRadius: 3 }}>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>
                📝 Custom Question Drill & Verbal Delivery Analyzer
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Practice company-tailored technical + behavioral questions. Listen to questions spoken aloud in natural AI voice,
                record your spoken answers in real-time, and get instant feedback on verbal delivery, filler words, speech cadence (WPM),
                and STAR framework completeness.
              </Typography>
              <Stack spacing={2}>
                <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                  <CompanySelect value={company} onChange={setCompany} />
                  <TextField
                    label="Role title (optional)"
                    placeholder="e.g. Senior Backend Engineer"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    sx={{ flex: 1, minWidth: 200 }}
                  />
                  <TextField
                    label="# Questions"
                    type="number"
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(Number(e.target.value))}
                    sx={{ width: 130 }}
                    inputProps={{ min: 1, max: 10 }}
                  />
                </Stack>
                <TextField
                  label="Paste Job Description (optional)"
                  placeholder="Paste actual JD text for target-specific system design & challenge questions…"
                  multiline
                  minRows={2}
                  value={jd}
                  onChange={(e) => setJd(e.target.value)}
                />
                <Button
                  variant="contained"
                  startIcon={getQuestions.isPending ? <CircularProgress size={16} color="inherit" /> : <QuestionIcon />}
                  onClick={() => getQuestions.mutate({ company, roleTitle: role, jobDescription: jd, numQuestions })}
                  disabled={!company || getQuestions.isPending}
                  sx={{ alignSelf: 'flex-start', fontWeight: 700, borderRadius: 2 }}
                >
                  Generate Voice Interview Questions
                </Button>
              </Stack>
            </CardContent>
          </Card>

          {getQuestions.data && (
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
                Generated Questions ({getQuestions.data.data.questions.length})
              </Typography>
              {getQuestions.data.data.questions.map((q, idx) => (
                <QuestionCard key={idx} question={q} />
              ))}
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
};


export default InterviewSimulatorTab;

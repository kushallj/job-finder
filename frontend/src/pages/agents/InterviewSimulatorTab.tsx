import React from 'react';
import {
  Box, Button, Card, CardContent, Chip, CircularProgress, Divider, LinearProgress,
  Stack, TextField, Typography,
} from '@mui/material';
import { QuestionAnswer as QuestionIcon, Send as SendIcon } from '@mui/icons-material';
import CompanySelect from './CompanySelect';
import { useInterviewQuestions, useScoreAnswer } from '../../hooks/useAgents';
import type { InterviewQuestion, InterviewScore } from '../../api/types';

const typeColor: Record<InterviewQuestion['type'], 'secondary' | 'info' | 'default'> = {
  company_specific: 'secondary', technical: 'info', behavioral: 'default',
};

const STAR_LABELS: Record<keyof InterviewScore['star_scores'], string> = {
  situation: 'Situation', task: 'Task', action: 'Action', result: 'Result',
};

const QuestionCard: React.FC<{ question: InterviewQuestion }> = ({ question }) => {
  const [answer, setAnswer] = React.useState('');
  const scoreAnswer = useScoreAnswer();

  return (
    <Card variant="outlined" sx={{ mb: 2, border: '1px solid #E2E8F0' }}>
      <CardContent sx={{ p: 2.5 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
          <Typography variant="body1" sx={{ fontWeight: 600, flex: 1 }}>{question.text}</Typography>
          <Chip size="small" color={typeColor[question.type]} label={question.type.replace('_', ' ')} />
        </Stack>
        <TextField
          placeholder="Type your answer (aim for a Situation → Task → Action → Result shape)…"
          multiline
          minRows={3}
          fullWidth
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          sx={{ mb: 1.5 }}
        />
        <Button
          size="small"
          variant="contained"
          startIcon={scoreAnswer.isPending ? <CircularProgress size={14} color="inherit" /> : <SendIcon />}
          onClick={() => scoreAnswer.mutate({ question: question.text, answer, focusArea: question.focus_area })}
          disabled={!answer.trim() || scoreAnswer.isPending}
        >
          Score answer
        </Button>

        {scoreAnswer.data && (
          <Box sx={{ mt: 2, p: 2, bgcolor: '#F8FAFC', borderRadius: 2 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                Overall: {scoreAnswer.data.data.overall}/100
              </Typography>
              {scoreAnswer.data.data.used_llm && <Chip size="small" label="AI-polished feedback" />}
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

const InterviewSimulatorTab: React.FC = () => {
  const [company, setCompany] = React.useState('');
  const [role, setRole] = React.useState('');
  const [jd, setJd] = React.useState('');
  const [numQuestions, setNumQuestions] = React.useState(5);
  const getQuestions = useInterviewQuestions();

  return (
    <Box>
      <Card sx={{ mb: 3, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>Interview simulator</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Company-tailored technical + behavioral questions, plus one built from the actual job
            description's stated pain point if you paste one. Scoring is a deterministic STAR-structure
            check (Situation, Task, Action, Result) with optional AI-polished feedback — never fabricates
            facts about your answer.
          </Typography>
          <Stack spacing={2}>
            <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
              <CompanySelect value={company} onChange={setCompany} />
              <TextField
                label="Role title (optional)"
                size="small"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                sx={{ minWidth: 220 }}
              />
              <TextField
                label="# questions"
                size="small"
                type="number"
                value={numQuestions}
                onChange={(e) => setNumQuestions(Math.max(1, Math.min(10, Number(e.target.value))))}
                sx={{ width: 120 }}
              />
            </Stack>
            <TextField
              label="Job description (optional — adds a company-specific question)"
              multiline
              minRows={2}
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              fullWidth
            />
            <Box>
              <Button
                variant="contained"
                startIcon={getQuestions.isPending ? <CircularProgress size={16} color="inherit" /> : <QuestionIcon />}
                onClick={() => getQuestions.mutate({ company, roleTitle: role, jobDescription: jd, numQuestions })}
                disabled={!company.trim() || getQuestions.isPending}
              >
                Generate questions
              </Button>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {getQuestions.data && (
        <>
          <Divider sx={{ mb: 2 }} />
          {getQuestions.data.data.questions.map((q) => (
            <QuestionCard key={q.id} question={q} />
          ))}
        </>
      )}
    </Box>
  );
};

export default InterviewSimulatorTab;

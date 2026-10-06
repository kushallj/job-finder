import React from 'react';
import { Box, Tab, Tabs, Typography } from '@mui/material';
import PersonalFleetTab from './agents/PersonalFleetTab';
import CompaniesOverviewTab from './agents/CompaniesOverviewTab';
import LeadsTab from './agents/LeadsTab';
import NetworkerPitchTab from './agents/NetworkerPitchTab';
import InterviewSimulatorTab from './agents/InterviewSimulatorTab';
import NegotiatorTab from './agents/NegotiatorTab';
import { NextRaiseStudio } from '../components/nextraise/NextRaiseStudio';

const TAB_LABELS = [
  '🚀 NextRaise Auto-Apply (300/day)',
  '🤖 Personal Google AI Fleet (BYOK)',
  'Overview & Daily Run',
  'Leads (CRM)',
  'Networker & Pitcher',
  'Interview Simulator',
  'Negotiator',
];

const AgentsHub: React.FC = () => {
  const [tab, setTab] = React.useState(0);

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>
            AI Agents
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Autonomous target-company agents & personal Google Gemini fleet — signal-aware sourcing, evidenced-challenge networking, mock
            interviews, and comp negotiation.
          </Typography>
        </Box>
      </Box>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 3, borderBottom: '1px solid #E2E8F0' }}
        variant="scrollable"
        scrollButtons="auto"
      >
        {TAB_LABELS.map((label) => (
          <Tab key={label} label={label} sx={{ textTransform: 'none', fontWeight: 700 }} />
        ))}
      </Tabs>

      {tab === 0 && <NextRaiseStudio />}
      {tab === 1 && <PersonalFleetTab />}
      {tab === 2 && <CompaniesOverviewTab />}
      {tab === 3 && <LeadsTab />}
      {tab === 4 && <NetworkerPitchTab />}
      {tab === 5 && <InterviewSimulatorTab />}
      {tab === 6 && <NegotiatorTab />}
    </Box>
  );
};

export default AgentsHub;


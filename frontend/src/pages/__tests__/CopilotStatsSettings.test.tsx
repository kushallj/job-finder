import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { Copilot } from '../Copilot';
import { Stats } from '../Stats';
import { Settings } from '../Settings';
import { copilotApi, statsApi, xReferralsApi, notificationsApi } from '../../api';

describe('Copilot, Stats, and Settings Pages', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('Copilot Page', () => {
    it('renders welcome message and starters', async () => {
      vi.spyOn(copilotApi, 'getStarters').mockResolvedValue({
        starters: [{ title: 'Find Unindexed JDs', prompt: 'Write dork for unindexed JDs' }],
      });

      renderWithProviders(<Copilot />);

      expect(screen.getByText(/AI OSINT Boolean Query Copilot/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/e\.g\. Senior Distributed Systems Engineer/i)).toBeInTheDocument();
    });
  });

  describe('Stats Page', () => {
    it('renders system funnel metrics and outreach status statistics', async () => {
      vi.spyOn(statsApi, 'getStats').mockResolvedValue({
        stats: {
          total_jobs: 120,
          total_contacts: 60,
          total_applications: 30,
          total_outreach_attempts: 45,
          emails_sent: 40,
          follow_ups_sent: 5,
          success_rate: 33.3,
        },
        recent_outreach: [],
        source: 'database',
      });
      vi.spyOn(statsApi, 'getHealth').mockResolvedValue({ status: 'healthy' });

      renderWithProviders(<Stats />);

      await waitFor(() => {
        expect(screen.getByText(/Pipeline & Campaign Analytics/i)).toBeInTheDocument();
      });

      expect(screen.getByText('120')).toBeInTheDocument();
      expect(screen.getByText('33.3%')).toBeInTheDocument();
    });
  });

  describe('Settings Page', () => {
    it('renders settings dashboard, notification triggers, and health checkers', async () => {
      vi.spyOn(statsApi, 'getHealth').mockResolvedValue({ status: 'healthy' });
      vi.spyOn(xReferralsApi, 'getStatus').mockResolvedValue({ authenticated: true, user: { username: 'testuser' } } as never);
      vi.spyOn(notificationsApi, 'getConfig').mockResolvedValue({
        telegram_bot_token: '',
        telegram_chat_id: '',
        discord_webhook_url: '',
        slack_webhook_url: '',
        min_fit_score: 65,
        notify_on_tier1_only: false,
        enabled: true,
      });

      renderWithProviders(<Settings />);

      await waitFor(() => {
        expect(screen.getByText(/Settings & Subsystem Health/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Autonomous Agent Subsystems & Referral Engines/i)).toBeInTheDocument();
      expect(screen.getByText(/Multi-Channel Webhook Alerts/i)).toBeInTheDocument();
    });
  });
});

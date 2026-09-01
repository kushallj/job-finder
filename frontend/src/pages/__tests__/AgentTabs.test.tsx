import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { PersonalFleetTab } from '../agents/PersonalFleetTab';
import InterviewSimulatorTab from '../agents/InterviewSimulatorTab';
import NegotiatorTab from '../agents/NegotiatorTab';
import { agentFleetApi, agentsApi } from '../../api';

describe('Agent Hub Subtabs', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('PersonalFleetTab', () => {
    it('loads config, allows API key saving, and runs fleet cycle', async () => {
      vi.spyOn(agentFleetApi, 'getConfig').mockResolvedValue({
        data: {
          google_gemini_api_key: 'AIzaSyExistingKey',
          autonomous_mode: true,
          execution_interval_hours: 6,
          target_roles: ['Staff Backend Engineer'],
          enabled_agents: ['signal_scout'],
          target_locations: ['Remote'],
        },
      } as never);

      const updateSpy = vi.spyOn(agentFleetApi, 'updateConfig').mockResolvedValue({
        data: { status: 'success' },
      } as never);

      const runSpy = vi.spyOn(agentFleetApi, 'runCycle').mockResolvedValue({
        data: {
          status: 'success',
          cycle: {
            fleet_id: 'fleet-1',
            cycle_id: 'cycle-1',
            is_active: true,
            has_api_key: true,
            total_actions_executed: 5,
            agent_runs: [],
            execution_time_seconds: 4.2,
            completed_at: '2026-08-31T10:00:00Z',
          },
        },
      } as never);

      renderWithProviders(<PersonalFleetTab />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('AIzaSyExistingKey')).toBeInTheDocument();
      });

      const saveBtn = screen.getByRole('button', { name: /Save Fleet Config/i });
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(updateSpy).toHaveBeenCalled();
      });

      const runBtn = screen.getByRole('button', { name: /Launch Fleet Cycle Now/i });
      fireEvent.click(runBtn);

      await waitFor(() => {
        expect(runSpy).toHaveBeenCalled();
      });
    });
  });

  describe('InterviewSimulatorTab', () => {
    it('renders mode switch and defaults to Hiregram Live Studio', async () => {
      vi.spyOn(agentsApi, 'getCompanies').mockResolvedValue({
        companies: [{ name: 'Stripe', tier: 1, domain: 'stripe.com' }],
      });

      renderWithProviders(<InterviewSimulatorTab />);

      expect(screen.getByText(/Hiregram Voice AI Studio/i)).toBeInTheDocument();
      expect(screen.getByText(/Custom Question Drill & STAR Scorer/i)).toBeInTheDocument();
    });
  });

  describe('NegotiatorTab', () => {
    it('renders salary benchmark inputs and 4-year comp simulator', async () => {
      vi.spyOn(agentsApi, 'getCompanies').mockResolvedValue({
        companies: [{ name: 'Google', tier: 1, domain: 'google.com' }],
      });

      renderWithProviders(<NegotiatorTab />);

      expect(screen.getByText(/Executive Offer Negotiator & Comp Simulator/i)).toBeInTheDocument();
      expect(screen.getByText(/4-Year Total Comp & Equity Vesting Simulator/i)).toBeInTheDocument();
    });
  });
});

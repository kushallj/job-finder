import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import AgentsHub from '../AgentsHub';
import { agentFleetApi, agentsApi } from '../../api';

describe('AgentsHub Page Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders AgentsHub with all top-level agent navigation tabs', async () => {
    vi.spyOn(agentFleetApi, 'getConfig').mockResolvedValue({
      data: {
        google_gemini_api_key: 'AIzaSyFakeKey',
        autonomous_mode: true,
        execution_interval_hours: 6,
        target_roles: ['Staff AI Engineer'],
      },
    } as never);

    vi.spyOn(agentsApi, 'getCompanies').mockResolvedValue({ companies: [] });

    renderWithProviders(<AgentsHub />);

    expect(screen.getByText(/AI Agents/i)).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Personal Google AI Fleet/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Overview & Daily Run/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Leads \(CRM\)/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Interview Simulator/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Negotiator/i })).toBeInTheDocument();
  });

  it('switches tabs smoothly when user clicks tabs', async () => {
    vi.spyOn(agentFleetApi, 'getConfig').mockResolvedValue({
      data: {
        google_gemini_api_key: '',
        autonomous_mode: true,
        execution_interval_hours: 6,
      },
    } as never);
    vi.spyOn(agentsApi, 'getCompanies').mockResolvedValue({ companies: [] });
    vi.spyOn(agentsApi, 'getQueryBank').mockResolvedValue({ queries: [] });
    vi.spyOn(agentsApi, 'listLeads').mockResolvedValue({ leads: [] });

    renderWithProviders(<AgentsHub />);

    const leadsTab = screen.getByRole('tab', { name: /Leads \(CRM\)/i });
    fireEvent.click(leadsTab);

    await waitFor(() => {
      expect(screen.getByText(/X-ray \/ boolean lead sourcing/i)).toBeInTheDocument();
    });
  });
});

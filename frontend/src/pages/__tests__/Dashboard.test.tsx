import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { Dashboard } from '../Dashboard';
import { statsApi, jobsApi, providersApi, lifecycleApi } from '../../api';

describe('Dashboard Page Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders stats overview cards, search triggers, and recent outreach activity', async () => {
    const mockStats = {
      stats: {
        total_jobs: 245,
        total_contacts: 120,
        total_applications: 40,
        total_outreach_attempts: 85,
        emails_sent: 70,
        follow_ups_sent: 15,
        success_rate: 32.5,
      },
      recent_outreach: [
        {
          id: 1,
          contact_name: 'David Chen',
          company: 'Databricks',
          status: 'sent',
          sent_at: '2026-08-31T09:00:00Z',
        },
      ],
      source: 'database',
      timestamp: '2026-08-31T10:00:00Z',
    };

    const mockHealth = {
      status: 'healthy',
      database: 'connected',
      ollama: 'connected',
      email: 'ready',
    };

    vi.spyOn(statsApi, 'getStats').mockResolvedValue(mockStats);
    vi.spyOn(statsApi, 'getHealth').mockResolvedValue(mockHealth);
    vi.spyOn(jobsApi, 'getAllJobs').mockResolvedValue({
      jobs: [],
      pagination: { total: 0, pages: 0, page: 1, limit: 10 },
      total: 0,
      page: 1,
      limit: 10,
    });
    vi.spyOn(jobsApi, 'getPendingOutreach').mockResolvedValue([]);
    vi.spyOn(lifecycleApi, 'queue').mockResolvedValue({
      total: 0,
      actions: [],
    });

    renderWithProviders(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Welcome back to your Career Command Center/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('245')).toBeInTheDocument();
    });

    expect(screen.getByText(/Total Opportunities/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Decision-Makers/i).length).toBeGreaterThan(0);
    expect(screen.getByText('120')).toBeInTheDocument();
  });

  it('handles provider search query trigger', async () => {
    vi.spyOn(statsApi, 'getStats').mockResolvedValue({
      stats: { total_jobs: 10, total_contacts: 5, total_applications: 2, total_outreach_attempts: 1, emails_sent: 1, follow_ups_sent: 0, success_rate: 10 },
      recent_outreach: [],
      source: 'database',
    });
    vi.spyOn(statsApi, 'getHealth').mockResolvedValue({ status: 'healthy' });
    vi.spyOn(jobsApi, 'getAllJobs').mockResolvedValue({ jobs: [], pagination: { total: 0, pages: 0, page: 1, limit: 10 }, total: 0, page: 1, limit: 10 });
    vi.spyOn(jobsApi, 'getPendingOutreach').mockResolvedValue([]);
    vi.spyOn(lifecycleApi, 'queue').mockResolvedValue({ total: 0, actions: [] });

    const mockSyncRes = {
      status: 'success',
      total_fetched: 15,
      total_inserted: 12,
      total_updated: 3,
      sources: [
        { provider: 'JobDataAPI', fetched: 15, inserted: 12, updated: 3 },
      ],
    };
    vi.spyOn(providersApi, 'sync').mockResolvedValue(mockSyncRes as never);

    renderWithProviders(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Welcome back to your Career Command Center/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Enter role, skills, or target title\.\.\./i);
    fireEvent.change(searchInput, { target: { value: 'staff ai engineer' } });

    const syncBtn = screen.getByRole('button', { name: /Sync Boards/i });
    fireEvent.click(syncBtn);

    await waitFor(() => {
      expect(providersApi.sync).toHaveBeenCalled();
    });
  });
});

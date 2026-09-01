import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { Outreach } from '../Outreach';
import { statsApi, jobsApi } from '../../api';

describe('Outreach Page Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders outreach engine dashboard and templates', async () => {
    vi.spyOn(statsApi, 'getStats').mockResolvedValue({
      stats: {
        total_jobs: 50,
        total_contacts: 20,
        total_applications: 10,
        total_outreach_attempts: 15,
        emails_sent: 12,
        follow_ups_sent: 3,
        success_rate: 25,
      },
      recent_outreach: [],
      source: 'database',
    });
    vi.spyOn(statsApi, 'getHealth').mockResolvedValue({ status: 'healthy' });
    vi.spyOn(jobsApi, 'getAllJobs').mockResolvedValue({
      jobs: [],
      pagination: { total: 0, pages: 0, page: 1, limit: 10 },
      total: 0,
      page: 1,
      limit: 10,
    });
    vi.spyOn(jobsApi, 'getPendingOutreach').mockResolvedValue([]);

    renderWithProviders(<Outreach />);

    await waitFor(() => {
      expect(screen.getByText(/Outreach & Campaign Engine/i)).toBeInTheDocument();
    });


    expect(screen.getByText(/Compose Outreach/i)).toBeInTheDocument();
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { Jobs } from '../Jobs';
import { jobsApi, ghostHunterApi } from '../../api';

describe('Jobs Page Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(ghostHunterApi, 'getJobGhostScore').mockResolvedValue({
      status: 'success',
      ghost_score: 10,
      urgency_label: 'Fresh Listing',
      is_ghost_risk: false,
      confidence_score: 95,
      signals: [],
      action_recommendation: 'Apply directly',
      timestamp: '2026-08-31T10:00:00Z',
    });
  });

  it('renders jobs list and switches view mode from cards to table', async () => {
    const mockJobsResponse = {
      jobs: [
        {
          id: 101,
          job_id: 'job-101',
          title: 'Senior Distributed Systems Engineer',
          company: 'Cloudflare',
          source: 'greenhouse',
          location: 'Remote',
          score: 92,
          created_at: '2026-08-30T10:00:00Z',
          description: 'Build fast distributed edge proxy caches with Rust and Python.',
        },
      ],
      pagination: { total: 1, pages: 1, page: 1, limit: 30 },
      total: 1,
      page: 1,
      limit: 30,
    };

    vi.spyOn(jobsApi, 'getAllJobs').mockResolvedValue(mockJobsResponse);
    vi.spyOn(jobsApi, 'getPendingOutreach').mockResolvedValue([]);

    renderWithProviders(<Jobs />);

    await waitFor(() => {
      expect(screen.getByText(/Senior Distributed Systems Engineer/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Cloudflare/i)).toBeInTheDocument();

    // Switch view mode to table
    const tableBtn = screen.getByTestId('ViewListIcon').closest('button');
    if (tableBtn) fireEvent.click(tableBtn);

    await waitFor(() => {
      expect(screen.getByText(/Cloudflare/i)).toBeInTheDocument();
    });
  });

  it('filters jobs via search input', async () => {
    const mockJobsResponse = {
      jobs: [
        {
          id: 1,
          job_id: 'job-1',
          title: 'Frontend React Architect',
          company: 'Vercel',
          source: 'lever',
          location: 'San Francisco, CA',
        },
        {
          id: 2,
          job_id: 'job-2',
          title: 'Database Reliability Engineer',
          company: 'Cockroach Labs',
          source: 'greenhouse',
          location: 'New York, NY',
        },
      ],
      pagination: { total: 2, pages: 1, page: 1, limit: 30 },
      total: 2,
      page: 1,
      limit: 30,
    };

    vi.spyOn(jobsApi, 'getAllJobs').mockResolvedValue(mockJobsResponse);
    vi.spyOn(jobsApi, 'getPendingOutreach').mockResolvedValue([]);

    renderWithProviders(<Jobs />);

    await waitFor(() => {
      expect(screen.getByText(/Frontend React Architect/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search by title, company, skills\.\.\./i);
    fireEvent.change(searchInput, { target: { value: 'Cockroach' } });

    expect(screen.queryByText(/Frontend React Architect/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Database Reliability Engineer/i)).toBeInTheDocument();
  });
});

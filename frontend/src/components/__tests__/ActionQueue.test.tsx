import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { ActionQueue } from '../lifecycle/ActionQueue';
import { lifecycleApi } from '../../api/endpoints/lifecycle';

describe('ActionQueue Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading indicator when queue is loading', () => {
    vi.spyOn(lifecycleApi, 'queue').mockReturnValue(new Promise(() => {}));
    renderWithProviders(<ActionQueue />);
    expect(screen.getByText(/Loading priority action queue.../i)).toBeInTheDocument();
  });

  it('renders prioritized opportunity cards and executes next action', async () => {
    const queueData = {
      total: 1,
      actions: [
        {
          job_id: 88,
          title: 'Staff Backend Engineer',
          company: 'Databricks',
          stage: 'saved',
          fit_score: 96,
          action: {
            key: 'tailor_resume',
            label: 'Generate Transformer Attention Pitch & Tailor Resume',
            priority: 'high',
            reason: 'High fit score detected with decision makers indexed.',
          },
        },
      ],
    };

    vi.spyOn(lifecycleApi, 'queue').mockResolvedValue(queueData);
    const doNextSpy = vi.spyOn(lifecycleApi, 'doNext').mockResolvedValue({ status: 'success' });

    renderWithProviders(<ActionQueue />);

    await waitFor(() => {
      expect(screen.getByText(/Staff Backend Engineer/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/@ Databricks/i)).toBeInTheDocument();
    expect(screen.getByText(/96% Match/i)).toBeInTheDocument();

    const executeBtn = screen.getByRole('button', { name: /Execute Step/i });
    fireEvent.click(executeBtn);

    await waitFor(() => {
      expect(doNextSpy).toHaveBeenCalledWith(88);
    });
  });
});

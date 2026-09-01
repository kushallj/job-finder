import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { GhostBadge } from '../ghost_hunter/GhostBadge';
import { ghostHunterApi } from '../../api';

describe('GhostBadge Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders with initial default score chip', () => {
    renderWithProviders(<GhostBadge initialGhostScore={20} initialUrgencyLabel="Active Hiring ⚡" />);
    expect(screen.getByText(/Active Hiring ⚡ \(20% Ghost Risk\)/i)).toBeInTheDocument();
  });

  it('renders moderate warning chip when score is moderate', () => {
    renderWithProviders(<GhostBadge initialGhostScore={45} />);
    expect(screen.getByText(/Moderate ⚠️ \(45% Ghost Risk\)/i)).toBeInTheDocument();
  });

  it('renders ghost risk chip when score is high', () => {
    renderWithProviders(<GhostBadge initialGhostScore={75} />);
    expect(screen.getByText(/Ghost Risk 👻 \(75% Ghost Risk\)/i)).toBeInTheDocument();
  });

  it('opens popover on click and renders audit details and signals', async () => {
    const mockAudit = {
      data: {
        ghost_score: 18,
        urgency_label: 'Active Hiring ⚡',
        action_recommendation: 'Role recently opened with confirmed recruiter activity.',
        signals: [
          { severity: 'positive', description: 'Posted 2 days ago' },
          { severity: 'info', description: 'Standard hiring tempo' },
        ],
      },
    };

    vi.spyOn(ghostHunterApi, 'getJobGhostScore').mockResolvedValue(mockAudit as never);

    renderWithProviders(<GhostBadge jobId={101} initialGhostScore={18} />);

    const chip = screen.getByText(/Active Hiring ⚡/i);
    fireEvent.click(chip);

    await waitFor(() => {
      expect(screen.getByText(/Ghost Hunter Legitimacy Audit/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Role recently opened with confirmed recruiter activity./i)).toBeInTheDocument();
    expect(screen.getByText(/Posted 2 days ago/i)).toBeInTheDocument();
  });
});

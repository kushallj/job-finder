import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { SpamHeatmapSandbox } from '../deliverability/SpamHeatmapSandbox';
import { deliverabilityApi } from '../../api';

describe('SpamHeatmapSandbox Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders nothing when body is empty or whitespace', () => {
    const { container } = renderWithProviders(
      <SpamHeatmapSandbox subject="Hello" body="   " />
    );
    expect(container.firstChild).toBeNull();
  });

  it('analyzes email body and displays spam risk assessment', async () => {
    const mockAnalysis = {
      data: {
        status: 'success',
        spam_score: 15,
        deliverability_tier: 'Optimal Tier-1 Inbox',
        is_safe: true,
        flesch_kincaid_grade: 7,
        reading_time_seconds: 25,
        word_count: 55,
        char_count: 320,
        link_count: 0,
        uppercase_ratio: 0.02,
        spam_matches: [
          {
            word: 'guarantee',
            category: 'hype',
            severity: 'warning' as const,
            suggested_alternatives: ['aim for', 'target'],
            position: 1,
          },
        ],
        subject_score: 90,
        subject_advice: 'Clean concise subject line',
        deliverability_recommendations: ['Optimal word count (55 words)'],
        timestamp: '2026-08-31T10:00:00Z',
      },
    };

    vi.spyOn(deliverabilityApi, 'analyzeDraft').mockResolvedValue(mockAnalysis as never);

    const onReplace = vi.fn();
    renderWithProviders(
      <SpamHeatmapSandbox
        subject="Staff AI Role"
        body="We guarantee high performance and fast turnaround."
        onReplaceWord={onReplace}
      />
    );

    await waitFor(
      () => {
        expect(screen.getByText('15%')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(screen.getByText('"guarantee"')).toBeInTheDocument();

    const replaceBtn = screen.getByRole('button', { name: /aim for/i });
    fireEvent.click(replaceBtn);

    expect(onReplace).toHaveBeenCalledWith('guarantee', 'aim for');
  });
});

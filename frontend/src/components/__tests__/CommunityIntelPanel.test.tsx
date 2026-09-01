import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { CommunityIntelPanel } from '../community_intel/CommunityIntelPanel';
import { communityIntelApi } from '../../api';

describe('CommunityIntelPanel Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders card shell when open', () => {
    renderWithProviders(<CommunityIntelPanel company="" />);
    expect(screen.getByText(/Community Interview Debriefs & Insider Intelligence/i)).toBeInTheDocument();
  });

  it('fetches and displays community intelligence across tabs', async () => {
    const mockIntel = {
      data: {
        status: 'success',
        company: 'Stripe',
        role_category: 'Engineering',
        total_sources_scanned: 12,
        overall_sentiment: 'Positive (84% sentiment index)',
        interview_debrief: {
          rounds: [
            { round: 'Round 1', type: 'System Architecture', focus: 'Distributed Idempotency & Latency' },
          ],
          common_questions: ['How do you prevent duplicate charges at 100k TPS?'],
          system_design_topics: ['Idempotent Payment Event Stream'],
          green_flags: ['High engineering autonomy'],
          red_flags: ['Fast-paced on-call rotation'],
          negotiation_tips: ['Ask for sign-on bonus match against equity vesting cliff'],
        },
        sources: [
          {
            source: 'reddit' as const,
            title: 'Stripe Staff AI System Design Experience',
            url: 'https://reddit.com/r/cscareerquestions/123',
            author: 'engineer_anon',
            published_at: '2026-08-15',
            summary: 'Heavy focus on distributed idempotency and latency guarantees.',
            relevance_score: 95,
            tags: ['stripe', 'interview'],
          },
        ],
        last_updated: '2026-08-31T10:00:00Z',
      },
    };

    vi.spyOn(communityIntelApi, 'getCompanyIntel').mockResolvedValue(mockIntel as never);

    renderWithProviders(<CommunityIntelPanel company="Stripe" role="Staff AI Engineer" />);

    await waitFor(() => {
      expect(screen.getByText(/Positive \(84% sentiment index\)/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Round 1/i)).toBeInTheDocument();
    expect(screen.getByText(/System Architecture/i)).toBeInTheDocument();

    // Switch to Questions tab
    const qTab = screen.getByRole('tab', { name: /Leaked Questions & System Design/i });
    fireEvent.click(qTab);

    expect(screen.getByText(/How do you prevent duplicate charges at 100k TPS\?/i)).toBeInTheDocument();
    expect(screen.getByText(/Idempotent Payment Event Stream/i)).toBeInTheDocument();

    // Switch to Culture tab
    const cultureTab = screen.getByRole('tab', { name: /Culture Flags & Negotiation/i });
    fireEvent.click(cultureTab);

    expect(screen.getByText(/High engineering autonomy/i)).toBeInTheDocument();
    expect(screen.getByText(/Fast-paced on-call rotation/i)).toBeInTheDocument();

    // Switch to Source Citations tab
    const srcTab = screen.getByRole('tab', { name: /Source Citations/i });
    fireEvent.click(srcTab);

    expect(screen.getByText(/Stripe Staff AI System Design Experience/i)).toBeInTheDocument();
  });
});

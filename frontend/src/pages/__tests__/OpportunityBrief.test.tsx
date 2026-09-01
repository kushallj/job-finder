import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { renderWithProviders } from '../../test/test-utils';
import { OpportunityBrief } from '../OpportunityBrief';
import { opportunitiesApi, attentionApi, ghostHunterApi, communityIntelApi } from '../../api';

describe('OpportunityBrief Page Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders complete opportunity brief with lifecycle status and actions', async () => {
    const mockBrief = {
      status: 'success',
      job: {
        id: 77,
        job_id: 'job-77',
        title: 'Staff AI Infrastructure Engineer',
        company: 'Anthropic',
        location: 'San Francisco, CA / Remote',
        source: 'greenhouse',
        score: 95,
        description: 'Design massive GPU training clusters and low latency serving infrastructure.',
        url: 'https://anthropic.com/careers/77',
        fetched_at: '2026-08-31T10:00:00Z',
        posted_date: '2026-08-30',
      },
      fit_score: 95,
      fit_label: 'Exceptional Fit',
      fit_reasons: ['Deep distributed systems experience', 'Strong AI infrastructure background'],
      company_signals: [],
      people: [
        {
          id: 1,
          name: 'Sarah Connor',
          title: 'Director of AI Platform',
          linkedin_url: 'https://linkedin.com/in/sarahconnor',
          relevance: 'Hiring Manager',
        },
      ],
      resume: {
        headline: 'Staff AI Engineer',
        key_highlights: ['Optimized GPU cluster utilization by 40%'],
        missing_keywords: ['Ray'],
      },
      outreach: {
        total_contacts: 1,
        attempts_count: 0,
        pending: 1,
        latest_status: null,
        recommended_message: 'Hi Sarah, I would love to connect...',
      },
      next_action: {
        key: 'apply',
        label: 'Submit Application with Challenge',
        reason: 'High fit score detected with decision makers indexed.',
        priority: 'high' as const,
      },
      application_status: 'ready' as const,
    };

    const mockAttention = {
      status: 'success',
      overall_score: 95,
      fit_label: 'Strong Fit',
      heads: {
        tech_stack: { head_name: 'tech_stack', head_score: 98, top_matches: [] },
      },
      matrix: {
        query_tokens: [],
        key_tokens: [],
        weights: [],
      },
      top_attended_values: [],
      tailored_bullets: [],
      outreach_hooks: [],
      summary_insight: 'Strong cross-attention match.',
      timestamp: '2026-08-31T10:00:00Z',
    };

    vi.spyOn(opportunitiesApi, 'brief').mockResolvedValue(mockBrief as never);
    vi.spyOn(attentionApi, 'match').mockResolvedValue(mockAttention as never);
    vi.spyOn(ghostHunterApi, 'getJobGhostScore').mockResolvedValue({
      status: 'success',
      ghost_score: 15,
      urgency_label: 'Active Hiring',
      is_ghost_risk: false,
      confidence_score: 90,
      signals: [],
      action_recommendation: 'Apply',
      timestamp: '2026-08-31T10:00:00Z',
    });
    vi.spyOn(communityIntelApi, 'getCompanyIntel').mockResolvedValue({
      data: {
        status: 'success',
        company: 'Anthropic',
        role_category: 'Engineering',
        total_sources_scanned: 10,
        overall_sentiment: 'Positive',
        interview_debrief: {
          rounds: [],
          common_questions: [],
          system_design_topics: [],
          red_flags: [],
          green_flags: [],
          negotiation_tips: [],
        },
        sources: [],
        last_updated: '2026-08-31T10:00:00Z',
      },
    } as never);

    renderWithProviders(
      <Routes>
        <Route path="/opportunities/:jobId" element={<OpportunityBrief />} />
      </Routes>,
      { initialEntries: ['/opportunities/77'] }
    );

    await waitFor(() => {
      expect(screen.getByText(/Staff AI Infrastructure Engineer/i)).toBeInTheDocument();
    });

    const anthropicElements = screen.getAllByText(/Anthropic/i);
    expect(anthropicElements.length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(screen.getByText(/Submit Application with Challenge/i)).toBeInTheDocument();
    });
  });
});

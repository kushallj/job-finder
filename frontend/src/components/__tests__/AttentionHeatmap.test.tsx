import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { AttentionHeatmap } from '../attention/AttentionHeatmap';
import type { AttentionMatchResponse } from '../../api/endpoints/attention';

describe('AttentionHeatmap Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading spinner when loading is true', () => {
    renderWithProviders(<AttentionHeatmap data={null} loading={true} />);
    expect(screen.getByText(/Computing 4-Head Transformer Q,K,V Attention Matrix/i)).toBeInTheDocument();
  });

  it('renders empty fallback when data is null or empty', () => {
    const { container } = renderWithProviders(<AttentionHeatmap data={null} loading={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders full multi-head attention scores, Q,K,V table, and handles copy actions', () => {
    const mockAttentionData: AttentionMatchResponse = {
      status: 'success',
      overall_score: 91,
      fit_label: 'Exceptional Strategic & Technical Alignment',
      heads: {
        tech_stack: {
          head_name: 'tech_stack',
          head_score: 95,
          top_matches: [
            {
              query_id: 'q1',
              query_text: 'Distributed Systems & Async Python',
              key_id: 'k1',
              key_text: 'FastAPI asyncio Ray queue architecture',
              attention_weight: 0.96,
            },
          ],
        },
        scale_architecture: {
          head_name: 'scale_architecture',
          head_score: 90,
          top_matches: [],
        },
        business_impact: {
          head_name: 'business_impact',
          head_score: 88,
          top_matches: [],
        },
        leadership_domain: {
          head_name: 'leadership_domain',
          head_score: 92,
          top_matches: [],
        },
      },
      matrix: {
        query_tokens: [
          { id: 'q1', text: 'Distributed Systems', category: 'core', weight: 0.9 },
        ],
        key_tokens: [
          { id: 'k1', text: 'FastAPI asyncio', category: 'core', source: 'resume' },
        ],
        weights: [[0.95]],
      },
      top_attended_values: [
        {
          id: 'v1',
          proof_point: 'Scaled Redis + Celery distributed pipeline to 50k events/sec with zero loss',
          context: 'Previous experience leading platform scale',
          impact_metric: '50,000 evt/s',
        },
      ],
      tailored_bullets: [],
      outreach_hooks: [],
      summary_insight: 'Strong cross-attention match across system scale and asynchronous architectures.',
      timestamp: '2026-08-31T10:00:00Z',
    };

    const handleSelectProof = vi.fn();

    renderWithProviders(
      <AttentionHeatmap
        data={mockAttentionData}
        loading={false}
        onSelectProofPoint={handleSelectProof}
      />
    );

    expect(screen.getByText(/Transformer Q,K,V Attention Match/i)).toBeInTheDocument();
    expect(screen.getByText(/91% Alignment/i)).toBeInTheDocument();
    expect(screen.getByText(/Tech Stack Alignment/i)).toBeInTheDocument();
    expect(screen.getByText(/Scaled Redis \+ Celery distributed pipeline/i)).toBeInTheDocument();

    const useBulletBtn = screen.getByRole('button', { name: /Use Bullet/i });
    fireEvent.click(useBulletBtn);

    expect(handleSelectProof).toHaveBeenCalledWith(
      'Scaled Redis + Celery distributed pipeline to 50k events/sec with zero loss'
    );
  });
});

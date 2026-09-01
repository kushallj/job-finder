import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { ProofOfWorkModal } from '../skill_bridge/ProofOfWorkModal';
import { skillBridgeApi } from '../../api';

describe('ProofOfWorkModal Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading state on open and automatically fetches challenge project', async () => {
    const mockChallenge = {
      data: {
        status: 'success',
        company: 'Stripe',
        role_title: 'Staff AI Engineer',
        gap_analysis: {
          candidate_skills: ['Python', 'FastAPI'],
          required_skills: ['Python', 'FastAPI', 'Kafka'],
          gap_skills: ['Kafka'],
          match_percentage: 88,
        },
        project_spec: {
          title: 'Idempotent Payment Event Stream Engine',
          tagline: 'High-throughput Kafka payment consumer with deduplication and DLQ.',
          duration_estimate: '24 hours',
          skills_proven: ['Kafka', 'Idempotency', 'Event Sourcing'],
          architecture_overview: 'Consumer groups reading payment events with Redis idempotency keys.',
          starter_code_files: {
            'main.py': 'def process_payment(event):\n    pass\n',
            'models.py': 'class PaymentEvent:\n    id: str\n',
          },
          demonstration_prompt: 'Run test suite demonstrating 10,000 rps zero-duplication execution.',
        },
        timestamp: '2026-08-31T10:00:00Z',
      },
    };

    const generateSpy = vi.spyOn(skillBridgeApi, 'generateProject').mockResolvedValue(mockChallenge as never);

    renderWithProviders(
      <ProofOfWorkModal
        open={true}
        onClose={vi.fn()}
        company="Stripe"
        roleTitle="Staff AI Engineer"
      />
    );

    expect(screen.getByText(/24h Proof-of-Work Micro-Project Generator/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Idempotent Payment Event Stream Engine/i)).toBeInTheDocument();
    });

    expect(generateSpy).toHaveBeenCalledWith({
      company: 'Stripe',
      role_title: 'Staff AI Engineer',
      job_description: undefined,
    });
    expect(screen.getByText(/88%/i)).toBeInTheDocument();
    expect(screen.getByText(/main.py/i)).toBeInTheDocument();
  });
});

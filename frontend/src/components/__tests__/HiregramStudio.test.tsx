import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { HiregramStudio } from '../hiregram/HiregramStudio';
import { hiregramApi } from '../../api';

describe('HiregramStudio Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders interview studio configuration screen', () => {
    renderWithProviders(<HiregramStudio initialCompany="Stripe" initialRole="Staff Systems Architect" />);

    expect(screen.getByText(/Hiregram Voice AI Mock Interview Studio/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Start Simulation/i })).toBeInTheDocument();
  });

  it('starts mock interview session and initializes dialogue turn', async () => {
    const mockStartResponse = {
      data: {
        status: 'success',
        session_id: 'sess-abc-123',
        company: 'Stripe',
        role_title: 'Staff Systems Architect',
        persona: 'architect_alex',
        total_questions: 4,
        current_turn: {
          turn_index: 1,
          question: 'How do you design an idempotent payment processing engine at 10,000 TPS?',
          interviewer_persona: 'architect_alex',
          candidate_answer: '',
          duration_seconds: 0,
          wpm: 0,
          filler_words_detected: [],
          star_breakdown: {},
          turn_score: 0,
          strengths: [],
          areas_for_improvement: [],
          gold_standard_ideal_answer: '',
          completed: false,
        },
      },
    };

    const startSpy = vi.spyOn(hiregramApi, 'startSession').mockResolvedValue(mockStartResponse as never);

    renderWithProviders(<HiregramStudio initialCompany="Stripe" initialRole="Staff Systems Architect" />);

    const startBtn = screen.getByRole('button', { name: /Start Simulation/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(startSpy).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText(/How do you design an idempotent payment processing engine at 10,000 TPS\?/i)).toBeInTheDocument();
    });
  });
});

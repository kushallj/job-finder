import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../../test/test-utils';
import { JobCard } from '../JobCard';
import { JobDetailModal } from '../JobDetailModal';
import type { Job } from '../../../api/types';

const mockJob: Job = {
  id: 42,
  job_id: 'job-42',
  title: 'Lead AI Engineer - LLM & MCP Systems',
  company: 'Aarivi AI',
  location: 'Bengaluru, India',
  source: 'greenhouse',
  has_remote: true,
  work_mode: 'remote',
  match_score: 94,
  matched_skills: ['React', 'TypeScript', 'Vite', 'LLM Integration', 'Model Context Protocol (MCP)', 'RAG'],
  missing_skills: ['CSS3', 'Figma'],
  reasons: [
    'Matches 6 of your verified skills including React, TypeScript, LLM Integration +3 more',
    'Seniority: Matches your 4+ years engineering experience',
    'Location: Bengaluru / India hub match (Bengaluru, India)',
  ],
  description: 'Design and deploy production-grade multi-agent swarms with Model Context Protocol (MCP) and RAG vector search pipelines.',
  fetched_at: '2026-11-02T12:00:00Z',
  posted_date: '2026-11-01T10:00:00Z',
};

describe('JobCard Component', () => {
  it('renders job title, company, and 94% Match score badge', () => {
    const onSelectJob = vi.fn();
    renderWithProviders(<JobCard job={mockJob} onSelectJob={onSelectJob} />);

    expect(screen.getByText(/Lead AI Engineer - LLM & MCP Systems/i)).toBeInTheDocument();
    expect(screen.getByText(/Aarivi AI/i)).toBeInTheDocument();
    expect(screen.getByText(/94% Match/i)).toBeInTheDocument();
  });

  it('renders emerald matched skills and muted missing skills chips', () => {
    const onSelectJob = vi.fn();
    renderWithProviders(<JobCard job={mockJob} onSelectJob={onSelectJob} />);

    // Matched skills chips
    expect(screen.getByText('React')).toBeInTheDocument();
    expect(screen.getByText('TypeScript')).toBeInTheDocument();
    expect(screen.getByText('Vite')).toBeInTheDocument();
    expect(screen.getByText('LLM Integration')).toBeInTheDocument();
    expect(screen.getByText('Model Context Protocol (MCP)')).toBeInTheDocument();
    expect(screen.getByText('RAG')).toBeInTheDocument();

    // Missing skills chips
    expect(screen.getByText('CSS3')).toBeInTheDocument();
    expect(screen.getByText('Figma')).toBeInTheDocument();
  });

  it('renders 3-bullet natural language validation reasons', () => {
    const onSelectJob = vi.fn();
    renderWithProviders(<JobCard job={mockJob} onSelectJob={onSelectJob} />);

    expect(screen.getByText(/Matches 6 of your verified skills/i)).toBeInTheDocument();
    expect(screen.getByText(/Seniority: Matches your 4\+ years engineering experience/i)).toBeInTheDocument();
    expect(screen.getByText(/Location: Bengaluru \/ India hub match/i)).toBeInTheDocument();
  });

  it('triggers onSelectJob when clicking Evaluate button', () => {
    const onSelectJob = vi.fn();
    renderWithProviders(<JobCard job={mockJob} onSelectJob={onSelectJob} />);

    const evalBtn = screen.getByRole('button', { name: /Evaluate/i });
    fireEvent.click(evalBtn);

    expect(onSelectJob).toHaveBeenCalledWith(mockJob);
  });
});

describe('JobDetailModal Component', () => {
  it('renders detailed modal with Aarivi explainable match intelligence', () => {
    const onClose = vi.fn();
    renderWithProviders(<JobDetailModal open={true} job={mockJob} onClose={onClose} />);

    expect(screen.getByText(/Aarivi Explainable Match Intelligence/i)).toBeInTheDocument();
    expect(screen.getByText(/Exceptional Fit — 94% Alignment/i)).toBeInTheDocument();
    expect(screen.getByText(/🟢 Matched Candidate Skills \(6\):/i)).toBeInTheDocument();
    expect(screen.getByText(/⚪ Missing Job Keywords \(2\):/i)).toBeInTheDocument();
    expect(screen.getByText(/Design and deploy production-grade multi-agent swarms/i)).toBeInTheDocument();
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { MarketRadar } from '../MarketRadar';
import { marketRadarApi } from '../../api';

describe('MarketRadar Page Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders USD/EUR arbitrage contracts, PPP multiplier, and GCC tech center hubs', async () => {
    const mockRadarData = {
      status: 'success',
      usd_to_inr_rate: 86.5,
      eur_to_inr_rate: 93.2,
      remote_global_roles: [
        {
          title: 'Senior Distributed Systems Architect',
          company: 'GitLab',
          country: 'US / Worldwide Remote',
          currency: 'USD',
          base_comp_range: '$175,000 - $210,000',
          inr_equivalent_range: '₹1.51 Cr - ₹1.81 Cr',
          ppp_multiplier: 3.6,
          tz_overlap_hours: '4 hrs overlap',
          tax_advantage: '50% presumptive tax saving under Sec 44ADA',
          source_url: 'https://gitlab.com/jobs/123',
          skills_required: ['Python', 'PostgreSQL', 'Distributed'],
        },
      ],
      top_gcc_hubs: [
        {
          hub_city: 'Bangalore & Hyderabad',
          active_openings: 450,
          top_employers: ['Goldman Sachs GCC', 'JPMorgan Chase GCC'],
          median_senior_ctc: '₹55L - ₹85L',
          growth_yoy: '+34% YoY',
        },
      ],
      timestamp: '2026-08-31T10:00:00Z',
    };

    vi.spyOn(marketRadarApi, 'getOpportunities').mockResolvedValue({ data: mockRadarData } as never);

    renderWithProviders(<MarketRadar />);

    await waitFor(() => {
      expect(screen.getByText(/Global Remote Arbitrage & GCC Opportunity Radar/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Senior Distributed Systems Architect/i)).toBeInTheDocument();
    expect(screen.getByText(/GitLab/i)).toBeInTheDocument();
    expect(screen.getByText(/Bangalore & Hyderabad/i)).toBeInTheDocument();
  });
});

import { describe, it, expect, beforeEach } from 'vitest';
import { useFilterStore } from '../useFilterStore';

describe('useFilterStore', () => {
  beforeEach(() => {
    useFilterStore.getState().resetAllFilters();
  });

  it('initializes with default state values', () => {
    const state = useFilterStore.getState();
    expect(state.jobSearch).toBe('');
    expect(state.jobSourceFilter).toEqual([]);
    expect(state.jobMinScore).toBe(50);
    expect(state.contactSearch).toBe('');
    expect(state.contactCompanyFilter).toEqual([]);
    expect(state.contactsPage).toBe(1);
    expect(state.contactsLimit).toBe(50);
    expect(state.outreachStatusFilter).toEqual([]);
    expect(state.dateRange).toEqual({ start: null, end: null });
  });

  it('updates job filters correctly', () => {
    const { setJobSearch, setJobSourceFilter, setJobMinScore } = useFilterStore.getState();
    
    setJobSearch('Staff Engineer');
    setJobSourceFilter(['greenhouse', 'lever']);
    setJobMinScore(75);

    const state = useFilterStore.getState();
    expect(state.jobSearch).toBe('Staff Engineer');
    expect(state.jobSourceFilter).toEqual(['greenhouse', 'lever']);
    expect(state.jobMinScore).toBe(75);
  });

  it('resets only job filters when resetJobFilters is invoked', () => {
    const { setJobSearch, setJobMinScore, setContactSearch, resetJobFilters } = useFilterStore.getState();
    
    setJobSearch('Backend Lead');
    setJobMinScore(80);
    setContactSearch('Recruiter Name');

    resetJobFilters();

    const state = useFilterStore.getState();
    expect(state.jobSearch).toBe('');
    expect(state.jobMinScore).toBe(50);
    expect(state.contactSearch).toBe('Recruiter Name'); // Preserved
  });

  it('updates contact filters and pagination', () => {
    const { setContactSearch, setContactCompanyFilter, setContactsPage, setContactsLimit } = useFilterStore.getState();

    setContactSearch('Engineering Manager');
    setContactCompanyFilter(['Google', 'Meta']);
    setContactsPage(3);
    setContactsLimit(25);

    const state = useFilterStore.getState();
    expect(state.contactSearch).toBe('Engineering Manager');
    expect(state.contactCompanyFilter).toEqual(['Google', 'Meta']);
    expect(state.contactsPage).toBe(3);
    expect(state.contactsLimit).toBe(25);
  });

  it('resets only contact filters when resetContactFilters is invoked', () => {
    const { setContactSearch, setContactsPage, setJobSearch, resetContactFilters } = useFilterStore.getState();

    setContactSearch('VP Eng');
    setContactsPage(4);
    setJobSearch('Staff AI');

    resetContactFilters();

    const state = useFilterStore.getState();
    expect(state.contactSearch).toBe('');
    expect(state.contactsPage).toBe(1);
    expect(state.jobSearch).toBe('Staff AI'); // Preserved
  });

  it('updates outreach filters and date range', () => {
    const { setOutreachStatusFilter, setDateRange } = useFilterStore.getState();
    const start = new Date('2026-08-01');
    const end = new Date('2026-08-31');

    setOutreachStatusFilter(['sent', 'replied']);
    setDateRange({ start, end });

    const state = useFilterStore.getState();
    expect(state.outreachStatusFilter).toEqual(['sent', 'replied']);
    expect(state.dateRange).toEqual({ start, end });
  });

  it('resets all filters to initial state with resetAllFilters', () => {
    const { setJobSearch, setContactSearch, setOutreachStatusFilter, resetAllFilters } = useFilterStore.getState();

    setJobSearch('AI Architect');
    setContactSearch('CTO');
    setOutreachStatusFilter(['replied']);

    resetAllFilters();

    const state = useFilterStore.getState();
    expect(state.jobSearch).toBe('');
    expect(state.contactSearch).toBe('');
    expect(state.outreachStatusFilter).toEqual([]);
    expect(state.jobMinScore).toBe(50);
  });
});

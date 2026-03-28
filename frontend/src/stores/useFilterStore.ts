import { create } from 'zustand';

interface FilterState {
  // Job filters
  jobSearch: string;
  setJobSearch: (search: string) => void;
  jobSourceFilter: string[];
  setJobSourceFilter: (sources: string[]) => void;
  jobMinScore: number;
  setJobMinScore: (score: number) => void;
  
  // Contact filters
  contactSearch: string;
  setContactSearch: (search: string) => void;
  contactCompanyFilter: string[];
  setContactCompanyFilter: (companies: string[]) => void;
  contactsPage: number;
  setContactsPage: (page: number) => void;
  contactsLimit: number;
  setContactsLimit: (limit: number) => void;
  
  // Outreach filters
  outreachStatusFilter: string[];
  setOutreachStatusFilter: (statuses: string[]) => void;
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
  setDateRange: (range: { start: Date | null; end: Date | null }) => void;
  
  // Reset
  resetJobFilters: () => void;
  resetContactFilters: () => void;
  resetOutreachFilters: () => void;
  resetAllFilters: () => void;
}

const initialState = {
  jobSearch: '',
  jobSourceFilter: [] as string[],
  jobMinScore: 50,
  contactSearch: '',
  contactCompanyFilter: [] as string[],
  contactsPage: 1,
  contactsLimit: 50,
  outreachStatusFilter: [] as string[],
  dateRange: {
    start: null as Date | null,
    end: null as Date | null,
  },
};

export const useFilterStore = create<FilterState>((set) => ({
  // Job filters
  ...initialState,
  setJobSearch: (search) => set({ jobSearch: search }),
  setJobSourceFilter: (sources) => set({ jobSourceFilter: sources }),
  setJobMinScore: (score) => set({ jobMinScore: score }),
  
  // Contact filters
  setContactSearch: (search) => set({ contactSearch: search }),
  setContactCompanyFilter: (companies) => set({ contactCompanyFilter: companies }),
  setContactsPage: (page) => set({ contactsPage: page }),
  setContactsLimit: (limit) => set({ contactsLimit: limit }),
  
  // Outreach filters
  setOutreachStatusFilter: (statuses) => set({ outreachStatusFilter: statuses }),
  setDateRange: (range) => set({ dateRange: range }),
  
  // Reset functions
  resetJobFilters: () => set({
    jobSearch: initialState.jobSearch,
    jobSourceFilter: initialState.jobSourceFilter,
    jobMinScore: initialState.jobMinScore,
  }),

  resetContactFilters: () => set({
    contactSearch: initialState.contactSearch,
    contactCompanyFilter: initialState.contactCompanyFilter,
    contactsPage: initialState.contactsPage,
    contactsLimit: initialState.contactsLimit,
  }),
  resetOutreachFilters: () => set({
    outreachStatusFilter: initialState.outreachStatusFilter,
    dateRange: initialState.dateRange,
  }),
  resetAllFilters: () => set(initialState),
}));


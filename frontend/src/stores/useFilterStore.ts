import { create } from 'zustand';

interface FilterState {
  // Job filters
  jobSearch: string;
  setJobSearch: (search: string) => void;
  jobRegion: string;
  setJobRegion: (region: string) => void;
  jobExperienceLevel: string;
  setJobExperienceLevel: (level: string) => void;
  jobYearsOfExperience: number | null;
  setJobYearsOfExperience: (yoe: number | null) => void;
  jobDatePosted: string;
  setJobDatePosted: (date: string) => void;
  jobTechStack: string[];
  setJobTechStack: (stacks: string[]) => void;
  toggleJobTechStack: (stack: string) => void;
  jobSource: string;
  setJobSource: (source: string) => void;
  jobSourceFilter: string[];
  setJobSourceFilter: (sources: string[]) => void;
  jobMinScore: number;
  setJobMinScore: (score: number) => void;
  jobSortBy: string;
  setJobSortBy: (sortBy: string) => void;
  jobSortOrder: 'asc' | 'desc';
  setJobSortOrder: (order: 'asc' | 'desc') => void;
  jobPage: number;
  setJobPage: (page: number) => void;
  jobLimit: number;
  setJobLimit: (limit: number) => void;
  
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
  jobRegion: 'all',
  jobExperienceLevel: 'all',
  jobYearsOfExperience: null as number | null,
  jobDatePosted: 'all',
  jobTechStack: [] as string[],
  jobSource: 'all',
  jobSourceFilter: [] as string[],
  jobMinScore: 50,
  jobSortBy: 'fetched_at',
  jobSortOrder: 'desc' as 'asc' | 'desc',
  jobPage: 1,
  jobLimit: 30,

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
  ...initialState,

  // Job filter setters
  setJobSearch: (search) => set({ jobSearch: search, jobPage: 1 }),
  setJobRegion: (region) => set({ jobRegion: region, jobPage: 1 }),
  setJobExperienceLevel: (level) => set({ jobExperienceLevel: level, jobPage: 1 }),
  setJobYearsOfExperience: (yoe) => set({ jobYearsOfExperience: yoe, jobPage: 1 }),
  setJobDatePosted: (date) => set({ jobDatePosted: date, jobPage: 1 }),
  setJobTechStack: (stacks) => set({ jobTechStack: stacks, jobPage: 1 }),
  toggleJobTechStack: (stack) =>
    set((state) => {
      const exists = state.jobTechStack.includes(stack);
      return {
        jobTechStack: exists
          ? state.jobTechStack.filter((s) => s !== stack)
          : [...state.jobTechStack, stack],
        jobPage: 1,
      };
    }),
  setJobSource: (source) => set({ jobSource: source, jobPage: 1 }),
  setJobSourceFilter: (sources) => set({ jobSourceFilter: sources }),
  setJobMinScore: (score) => set({ jobMinScore: score }),
  setJobSortBy: (sortBy) => set({ jobSortBy: sortBy }),
  setJobSortOrder: (order) => set({ jobSortOrder: order }),
  setJobPage: (page) => set({ jobPage: page }),
  setJobLimit: (limit) => set({ jobLimit: limit }),
  
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
    jobRegion: initialState.jobRegion,
    jobExperienceLevel: initialState.jobExperienceLevel,
    jobYearsOfExperience: initialState.jobYearsOfExperience,
    jobDatePosted: initialState.jobDatePosted,
    jobTechStack: initialState.jobTechStack,
    jobSource: initialState.jobSource,
    jobSourceFilter: initialState.jobSourceFilter,
    jobMinScore: initialState.jobMinScore,
    jobSortBy: initialState.jobSortBy,
    jobSortOrder: initialState.jobSortOrder,
    jobPage: 1,
    jobLimit: initialState.jobLimit,
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

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentsApi } from '../api';
import type { BooleanLead } from '../api/types';

export const useCompanies = () =>
  useQuery({ queryKey: ['agents', 'companies'], queryFn: agentsApi.getCompanies, staleTime: 5 * 60 * 1000 });

export const useDailyPipeline = () =>
  useMutation({ mutationFn: (tiers?: number[]) => agentsApi.runDaily(tiers) });

export const useLeads = () => {
  const queryClient = useQueryClient();
  const runLeads = useMutation({
    mutationFn: (categories?: string[]) => agentsApi.runLeads(categories),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents', 'leads-list'] }),
  });
  const queryBank = useQuery({
    queryKey: ['agents', 'query-bank'], queryFn: agentsApi.getQueryBank, staleTime: 10 * 60 * 1000,
  });
  const updateLeadStatus = useMutation({
    mutationFn: ({ leadId, status }: { leadId: number; status: BooleanLead['status'] }) =>
      agentsApi.updateLeadStatus(leadId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents', 'leads-list'] }),
  });
  return { runLeads, queryBank, updateLeadStatus };
};

export const useLeadsList = (params?: { status?: string; category?: string }) =>
  useQuery({ queryKey: ['agents', 'leads-list', params], queryFn: () => agentsApi.listLeads(params) });

export const useNetworker = () =>
  useMutation({
    mutationFn: ({ company, jobDescription }: { company: string; jobDescription?: string }) =>
      agentsApi.runNetworker(company, jobDescription),
  });

export const usePitch = () =>
  useMutation({
    mutationFn: ({ company, jobDescription }: { company: string; jobDescription?: string }) =>
      agentsApi.runPitch(company, jobDescription),
  });

export const useInterviewQuestions = () =>
  useMutation({
    mutationFn: (
      { company, roleTitle, jobDescription, numQuestions }:
      { company: string; roleTitle?: string; jobDescription?: string; numQuestions?: number }
    ) => agentsApi.getInterviewQuestions(company, roleTitle, jobDescription, numQuestions),
  });

export const useScoreAnswer = () =>
  useMutation({
    mutationFn: ({ question, answer, focusArea }: { question: string; answer: string; focusArea?: string }) =>
      agentsApi.scoreInterviewAnswer(question, answer, focusArea),
  });

export const useNegotiationBenchmark = (company: string, enabled: boolean) =>
  useQuery({
    queryKey: ['agents', 'negotiate-benchmark', company],
    queryFn: () => agentsApi.getNegotiationBenchmark(company),
    enabled: enabled && !!company,
  });

export const useNegotiationCounter = () =>
  useMutation({
    mutationFn: ({ company, offerAmountLpa }: { company: string; offerAmountLpa: number }) =>
      agentsApi.getNegotiationCounter(company, offerAmountLpa),
  });

export const useOutreachDraft = () =>
  useMutation({
    mutationFn: (
      { company, roleTitle, jobDescription }:
      { company: string; roleTitle?: string; jobDescription?: string }
    ) => agentsApi.runOutreachDraft(company, roleTitle, jobDescription),
  });

export const useInterviewPrep = () =>
  useMutation({
    mutationFn: ({ company, roleTitle }: { company: string; roleTitle?: string }) =>
      agentsApi.runInterviewPrep(company, roleTitle),
  });

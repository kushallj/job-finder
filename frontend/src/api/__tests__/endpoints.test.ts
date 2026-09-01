import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../axios';
import {
  agentFleetApi,
  attentionApi,
  communityIntelApi,
  contactsApi,
  deliverabilityApi,
  ghostHunterApi,
  hiregramApi,
  instagramReferralsApi,
  jobsApi,
  lifecycleApi,
  marketRadarApi,
  providersApi,
  skillBridgeApi,
  xReferralsApi,
} from '../index';

describe('API Endpoints Mapping & Payload Serialization', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('agentFleetApi sends proper requests', async () => {
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: { autonomous_mode: true } });
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { status: 'success' } });

    await agentFleetApi.getConfig();
    expect(getSpy).toHaveBeenCalledWith('/api/fleet/config');

    const config = {
      google_gemini_api_key: 'AIzaSyTestKey',
      autonomous_mode: true,
      execution_interval_hours: 6,
      enabled_agents: ['signal_scout'],
      target_roles: ['Staff AI'],
      target_locations: ['Remote'],
    };
    await agentFleetApi.updateConfig(config);
    expect(postSpy).toHaveBeenCalledWith('/api/fleet/config', config);

    await agentFleetApi.runCycle({ target_roles: ['Staff AI'] });
    expect(postSpy).toHaveBeenCalledWith('/api/fleet/run-cycle', { target_roles: ['Staff AI'] });
  });

  it('attentionApi sends proper requests', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { overall_score: 92 } });

    await attentionApi.match('FastAPI expert', ['Built Python async queue']);
    expect(postSpy).toHaveBeenCalledWith('/api/attention/match', {
      job_description: 'FastAPI expert',
      custom_bullets: ['Built Python async queue'],
    });

    await attentionApi.tailor('FastAPI expert');
    expect(postSpy).toHaveBeenCalledWith('/api/attention/tailor', {
      job_description: 'FastAPI expert',
      custom_bullets: undefined,
    });
  });

  it('ghostHunterApi sends proper requests', async () => {
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: { ghost_score: 15 } });
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { ghost_score: 20 } });

    await ghostHunterApi.getJobGhostScore(42);
    expect(getSpy).toHaveBeenCalledWith('/api/jobs/42/ghost-score');

    await ghostHunterApi.analyze({ title: 'Lead Architect', company: 'Stripe', description: 'desc' });
    expect(postSpy).toHaveBeenCalledWith('/api/ghost-hunter/analyze', {
      title: 'Lead Architect',
      company: 'Stripe',
      description: 'desc',
    });
  });

  it('skillBridgeApi sends proper requests', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { project_spec: {} } });

    await skillBridgeApi.generateProject({
      company: 'Meta',
      role_title: 'Staff Eng',
      job_description: 'Distributed cache',
    });
    expect(postSpy).toHaveBeenCalledWith('/api/skill-bridge/generate-project', {
      company: 'Meta',
      role_title: 'Staff Eng',
      job_description: 'Distributed cache',
    });
  });

  it('marketRadarApi sends proper requests', async () => {
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: { remote_opportunities: [] } });

    await marketRadarApi.getOpportunities();
    expect(getSpy).toHaveBeenCalledWith('/api/market-radar/opportunities');
  });

  it('instagramReferralsApi sends proper requests', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { status: 'success' } });

    await instagramReferralsApi.search({ company: 'Meta', role_keyword: 'Staff' });
    expect(postSpy).toHaveBeenCalledWith('/api/instagram/search', {
      company: 'Meta',
      role_keyword: 'Staff',
    });

    await instagramReferralsApi.generateMessage({
      action_type: 'dm',
      target_username: 'founder_tech',
      company: 'TechCorp',
      name: 'Alex',
      role_title: 'Staff Engineer',
    });
    expect(postSpy).toHaveBeenCalledWith('/api/instagram/generate-message', {
      action_type: 'dm',
      target_username: 'founder_tech',
      company: 'TechCorp',
      name: 'Alex',
      role_title: 'Staff Engineer',
    });
  });

  it('xReferralsApi sends proper requests', async () => {
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: { authenticated: true } });
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { status: 'success' } });

    await xReferralsApi.getStatus();
    expect(getSpy).toHaveBeenCalledWith('/api/x/auth/status');

    await xReferralsApi.search('Google', 'Engineer', 5);
    expect(postSpy).toHaveBeenCalledWith('/api/x/search', { company: 'Google', role: 'Engineer', limit: 5 });
  });

  it('communityIntelApi sends proper requests', async () => {
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: { company: 'Apple' } });

    await communityIntelApi.getCompanyIntel('Apple');
    expect(getSpy).toHaveBeenCalledWith('/api/community-intel/company/Apple', {
      params: { role: undefined, force_refresh: false },
    });
  });

  it('deliverabilityApi sends proper requests', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { spam_score: 5 } });

    await deliverabilityApi.analyzeDraft({ subject: 'Quick chat', body: 'Let us connect' });
    expect(postSpy).toHaveBeenCalledWith('/api/deliverability/analyze-draft', {
      subject: 'Quick chat',
      body: 'Let us connect',
    });
  });

  it('hiregramApi sends proper requests', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { session_id: 'session-123' } });

    await hiregramApi.startSession({ company: 'Amazon', role_title: 'SDE III' });
    expect(postSpy).toHaveBeenCalledWith('/api/hiregram/start-session', {
      company: 'Amazon',
      role_title: 'SDE III',
    });
  });

  it('lifecycleApi sends proper requests', async () => {
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: { items: [] } });
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { status: 'success' } });

    await lifecycleApi.queue(10);
    expect(getSpy).toHaveBeenCalledWith('/api/action-queue', { params: { limit: 10 } });

    await lifecycleApi.doNext(105);
    expect(postSpy).toHaveBeenCalledWith('/api/opportunities/105/do-next');
  });

  it('jobsApi and contactsApi send pagination params properly', async () => {
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: { jobs: [] } });

    await jobsApi.getAllJobs(2, 25);
    expect(getSpy).toHaveBeenCalledWith('/api/jobs', { params: { page: 2, limit: 25 } });

    await contactsApi.getAll('Uber', 3, 10);
    expect(getSpy).toHaveBeenCalledWith('/api/contacts', {
      params: { company: 'Uber', page: 3, limit: 10 },
    });
  });
});

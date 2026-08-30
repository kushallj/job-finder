import api from '../axios';

export interface NotificationConfig {
  telegram_bot_token?: string | null;
  telegram_chat_id?: string | null;
  discord_webhook_url?: string | null;
  slack_webhook_url?: string | null;
  min_fit_score: number;
  notify_on_tier1_only: boolean;
  enabled: boolean;
}

export interface NotificationTestResult {
  status: string;
  channel: string;
  delivery_status: string;
  detail: string;
}

export const notificationsApi = {
  getConfig: () => api.get<NotificationConfig>('/api/notifications/config'),
  updateConfig: (config: NotificationConfig) =>
    api.post<NotificationConfig>('/api/notifications/config', config),
  testChannel: (channel: 'telegram' | 'discord' | 'slack') =>
    api.post<NotificationTestResult>('/api/notifications/test', { channel }),
};

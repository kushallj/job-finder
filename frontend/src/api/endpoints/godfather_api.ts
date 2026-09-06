import api from '../axios';

export interface RadarFinding {
  category: string;
  title: string;
  rate?: string;
  reward?: string;
  badge: string;
}

export interface InlineKeyboardButton {
  text: string;
  callback_data?: string;
  url?: string;
}

export interface BotMessageResponse {
  text: string;
  parse_mode: string;
  reply_markup?: {
    inline_keyboard?: InlineKeyboardButton[][];
  };
  action_type: string;
  agent_invoked?: string;
}

export interface BotStatusResponse {
  status: string;
  is_running: boolean;
  is_configured: boolean;
  bot_username: string;
  uptime_seconds: number;
  total_commands_executed: number;
  autopilot_enabled: boolean;
  active_monitors_count: number;
  last_active_timestamp?: string;
  daemon_running?: boolean;
  scan_interval_seconds?: number;
  last_radar_scan?: string;
  total_alerts_dispatched?: number;
  registered_subscribers_count?: number;
  latest_findings?: RadarFinding[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'godfather';
  text: string;
  agentInvoked?: string;
  timestamp: string;
  replyMarkup?: {
    inline_keyboard?: InlineKeyboardButton[][];
  };
}

export const godfatherApi = {
  getStatus: async (): Promise<BotStatusResponse> => {
    const res = await api.get<BotStatusResponse>('/godfather/status');
    return res.data;
  },

  interact: async (
    message: string,
    userName: string = 'Sovereign Engineer',
    userId: string = 'web_user',
    chatId: string = 'web_chat'
  ): Promise<BotMessageResponse> => {
    const res = await api.post<BotMessageResponse>('/godfather/interact', {
      message,
      user_name: userName,
      user_id: userId,
      chat_id: chatId,
    });
    return res.data;
  },

  broadcastAlert: async (message: string): Promise<{ status: string; dispatched_count: number }> => {
    const res = await api.post<{ status: string; dispatched_count: number }>('/godfather/broadcast', {
      message,
    });
    return res.data;
  },

  triggerRadarScan: async (): Promise<{
    timestamp: string;
    status: string;
    findings_count: number;
    findings: RadarFinding[];
  }> => {
    const res = await api.post('/godfather/radar/scan');
    return res.data;
  },

  toggleAutopilot: async (enabled: boolean): Promise<{ status: string; autopilot_enabled: boolean; message: string }> => {
    const res = await api.post('/godfather/autopilot/toggle', { enabled });
    return res.data;
  },
};

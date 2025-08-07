export interface ActionLink {
  platform: 'slack' | 'github' | 'notion';
  url: string;
  label: string;
  action_type: 'view' | 'edit' | 'comment' | 'reply';
}

export interface GeneratedAction {
  action_id: string;
  title: string;
  description: string;
  priority: 'urgent' | 'high' | 'medium' | 'low' | 'fyi';
  action_type: 'review' | 'respond' | 'update' | 'meeting' | 'follow_up' | 'create' | 'fix';
  reasoning: string;
  context_summary: string;
  estimated_time_minutes: number;
  action_links: ActionLink[];
  related_people: string[];
  user_id: string;
  correlation_id: string;
  generated_at: string;
  expires_at?: string;
  status: 'pending' | 'completed' | 'dismissed';
  completed_at?: string;
  user_feedback?: string;
  related_context?: {
    synthesized_context: string;
    key_insights: string[];
    platform_data: Record<string, any>;
  };
}

export interface ActionFilters {
  priority?: string[];
  status?: string;
  limit?: number;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  loading: boolean;
}

export interface UserPreferences {
  notifications: {
    urgent_actions: string[];
    high_actions: string[];
    medium_actions: string[];
    low_actions: string[];
    fyi_actions: string[];
    batch_frequency: 'immediate' | 'hourly' | 'daily';
    quiet_hours: {
      enabled: boolean;
      start: string;
      end: string;
      timezone: string;
    };
    max_daily_notifications: number;
  };
  dashboard: {
    default_view: 'priority' | 'timeline' | 'type';
    items_per_page: number;
    auto_refresh: boolean;
    refresh_interval_seconds: number;
  };
  integrations: {
    slack: {
      enabled: boolean;
      dm_enabled: boolean;
    };
    email: {
      enabled: boolean;
      address: string | null;
    };
    browser: {
      enabled: boolean;
    };
  };
}
export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  contextSources?: ContextSource[];
  metadata?: MessageMetadata;
}

export interface ContextSource {
  type: 'content' | 'event' | 'action';
  platform: string;
  timestamp: string;
  preview: string;
  relevance?: 'high' | 'medium' | 'low';
}

export interface ChatSession {
  id?: string; // v2 uses 'id' instead of 'sessionId'
  sessionId?: string; // v1 compatibility
  userId: string;
  status: 'active' | 'expired' | 'ended';
  createdAt: Date;
  conversationTurns?: ChatTurn[];
}

export interface ChatTurn {
  userMessage: string;
  assistantResponse: string;
  timestamp: Date;
  contextUsed: any;
  retrievalStrategy: string;
  metadata?: TurnMetadata;
}

export interface ChatResponse {
  // v1 fields
  sessionId?: string;
  message?: string;
  contextSources?: ContextSource[];
  retrievalStrategy?: string;
  timestamp?: Date;
  
  // v2 fields
  response?: string;
  context_used?: ContextSource[];
  metadata?: ResponseMetadata;
}

export interface WebSocketMessage {
  type: 'connected' | 'response' | 'message' | 'typing' | 'error';
  data?: any;
  response?: string;
  context_used?: ContextSource[];
  metadata?: ResponseMetadata;
  error?: string;
  isTyping?: boolean;
  status?: string;
  sessionId?: string;
}

// New v2 types
export interface UserFeedback {
  relevance_score?: number; // 0-1
  completeness_score?: number; // 0-1
  helpful?: boolean;
  feedback_text?: string;
}

export interface MessageMetadata {
  processing_time?: number;
  confidence_level?: 'high' | 'medium' | 'low';
  cache_hit?: boolean;
  expansion_attempts?: number;
  sufficiency_score?: number;
}

export interface ResponseMetadata extends MessageMetadata {
  analysis_timestamp?: string;
  retrieval_timestamp?: string;
  response_timestamp?: string;
  tokens_used?: number;
}

export interface TurnMetadata {
  intent?: string;
  entities?: Record<string, string[]>;
  platforms?: string[];
  time_range?: {
    start: string;
    end: string;
    reference: string;
  };
}

export interface SessionMetrics {
  session_id: string;
  turn_count: number;
  total_response_time: number;
  avg_response_time: number;
  avg_sufficiency_score: number;
  total_expansion_attempts: number;
  expansion_rate: number;
  error_rate: number;
  intents: string[];
  satisfaction_scores: number[];
}

export interface SystemMetrics {
  quality: {
    total_conversations: number;
    total_turns: number;
    avg_response_time: number;
    p95_response_time: number;
    avg_sufficiency_score: number;
    expansion_rate: number;
    error_rate: number;
    intent_distribution: Record<string, number>;
    active_users: number;
  };
  cache: {
    hits: number;
    misses: number;
    hit_rate: number;
    query_cache_size: number;
    context_cache_size: number;
  };
  learning: {
    response_time: MetricTrend;
    sufficiency?: MetricTrend;
    error_rate?: MetricTrend;
  };
  current_parameters: {
    sufficiency_threshold: number;
    retrieval_weights: Record<string, number>;
    rrf_k: number;
  };
}

export interface MetricTrend {
  current: number;
  average: number;
  trend: 'increasing' | 'decreasing' | 'stable';
  improvement: number;
}
export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  contextSources?: ContextSource[];
}

export interface ContextSource {
  type: 'content' | 'event' | 'action';
  platform: string;
  timestamp: string;
  preview: string;
}

export interface ChatSession {
  sessionId: string;
  userId: string;
  status: 'active' | 'expired' | 'ended';
  createdAt: Date;
  conversationTurns: ChatTurn[];
}

export interface ChatTurn {
  userMessage: string;
  assistantResponse: string;
  timestamp: Date;
  contextUsed: any;
  retrievalStrategy: string;
}

export interface ChatResponse {
  sessionId: string;
  message: string;
  contextSources: ContextSource[];
  retrievalStrategy: string;
  timestamp: Date;
}

export interface WebSocketMessage {
  type: 'connected' | 'response' | 'typing' | 'error';
  data?: any;
  error?: string;
  isTyping?: boolean;
  sessionId?: string;
}
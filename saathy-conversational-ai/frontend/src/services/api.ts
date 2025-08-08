import axios from 'axios';
import { ChatSession, ChatResponse, UserFeedback, SessionMetrics, SystemMetrics } from '../types/chat';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const USE_V2_API = process.env.REACT_APP_USE_V2_API !== 'false'; // Default to true

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token') || 'Bearer test_user_123';
  if (token) {
    config.headers.Authorization = token;
  }
  return config;
});

// Determine API version base path
const getApiBase = () => USE_V2_API ? '/api/v2/chat' : '/api/chat';

// Chat API endpoints
export const chatAPI = {
  // Create a new chat session
  createSession: async (metadata?: Record<string, any>): Promise<ChatSession> => {
    const response = await api.post(`${getApiBase()}/sessions`, 
      USE_V2_API ? { metadata } : {}
    );
    return response.data;
  },

  // Send a message
  sendMessage: async (sessionId: string, message: string): Promise<ChatResponse> => {
    const endpoint = `${getApiBase()}/sessions/${sessionId}/messages`;
    const payload = USE_V2_API ? { content: message } : { message };
    const response = await api.post(endpoint, payload);
    return response.data;
  },

  // Get session history
  getSessionHistory: async (sessionId: string): Promise<ChatSession> => {
    const response = await api.get(`${getApiBase()}/sessions/${sessionId}/history`);
    return response.data;
  },

  // End a session
  endSession: async (sessionId: string): Promise<void> => {
    await api.delete(`${getApiBase()}/sessions/${sessionId}`);
  },

  // Submit user feedback (v2 only)
  submitFeedback: async (sessionId: string, feedback: UserFeedback): Promise<void> => {
    if (!USE_V2_API) {
      console.warn('Feedback submission is only available in v2 API');
      return;
    }
    await api.post(`${getApiBase()}/sessions/${sessionId}/feedback`, feedback);
  },

  // Get session metrics (v2 only)
  getSessionMetrics: async (sessionId: string): Promise<SessionMetrics | null> => {
    if (!USE_V2_API) {
      console.warn('Session metrics are only available in v2 API');
      return null;
    }
    const response = await api.get(`${getApiBase()}/sessions/${sessionId}/metrics`);
    return response.data;
  },

  // Get system metrics (v2 only)
  getSystemMetrics: async (): Promise<SystemMetrics | null> => {
    if (!USE_V2_API) {
      console.warn('System metrics are only available in v2 API');
      return null;
    }
    const response = await api.get(`${getApiBase()}/metrics/system`);
    return response.data;
  },

  // Export analytics (v2 only)
  exportAnalytics: async (): Promise<any> => {
    if (!USE_V2_API) {
      console.warn('Analytics export is only available in v2 API');
      return null;
    }
    const response = await api.get(`${getApiBase()}/analytics/export`);
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string; service: string; initialized?: boolean }> => {
    const endpoint = USE_V2_API ? `${getApiBase()}/health` : '/health';
    const response = await api.get(endpoint);
    return response.data;
  },
};

// WebSocket URL for real-time chat
export const getWebSocketUrl = (sessionId: string): string => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = API_BASE_URL.replace(/^https?:\/\//, '');
  const wsPath = USE_V2_API 
    ? `/api/v2/chat/sessions/${sessionId}/ws`
    : `/api/chat/ws/${sessionId}`;
  return `${wsProtocol}//${wsHost}${wsPath}`;
};
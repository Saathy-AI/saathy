import axios from 'axios';
import { ChatSession, ChatResponse } from '../types/chat';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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

// Chat API endpoints
export const chatAPI = {
  // Create a new chat session
  createSession: async (): Promise<ChatSession> => {
    const response = await api.post('/api/chat/sessions');
    return response.data;
  },

  // Send a message
  sendMessage: async (sessionId: string, message: string): Promise<ChatResponse> => {
    const response = await api.post(`/api/chat/sessions/${sessionId}/messages`, {
      message,
    });
    return response.data;
  },

  // Get session history
  getSessionHistory: async (sessionId: string): Promise<ChatSession> => {
    const response = await api.get(`/api/chat/sessions/${sessionId}/history`);
    return response.data;
  },

  // End a session
  endSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/api/chat/sessions/${sessionId}`);
  },
};

// WebSocket URL for real-time chat
export const getWebSocketUrl = (sessionId: string): string => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = API_BASE_URL.replace(/^https?:\/\//, '');
  return `${wsProtocol}//${wsHost}/api/chat/ws/${sessionId}`;
};
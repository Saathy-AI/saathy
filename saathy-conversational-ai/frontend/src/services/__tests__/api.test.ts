import axios from 'axios';
import { chatAPI, getWebSocketUrl } from '../api';
import { UserFeedback, SessionMetrics, SystemMetrics } from '../../types/chat';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('Chat API Service', () => {
  let mockAxiosInstance: any;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Mock axios instance
    mockAxiosInstance = {
      post: jest.fn(),
      get: jest.fn(),
      delete: jest.fn(),
      interceptors: {
        request: { use: jest.fn() }
      }
    };
    
    mockedAxios.create.mockReturnValue(mockAxiosInstance);
    
    // Reset environment variables
    delete process.env.REACT_APP_USE_V2_API;
  });

  describe('v2 API Endpoints', () => {
    beforeEach(() => {
      process.env.REACT_APP_USE_V2_API = 'true';
    });

    it('should create session with v2 endpoint', async () => {
      const mockSession = { id: 'session-123', status: 'active' };
      mockAxiosInstance.post.mockResolvedValue({ data: mockSession });

      const result = await chatAPI.createSession({ client: 'web' });

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/api/v2/chat/sessions',
        { metadata: { client: 'web' } }
      );
      expect(result).toEqual(mockSession);
    });

    it('should send message with v2 format', async () => {
      const mockResponse = {
        response: 'Test response',
        context_used: [],
        metadata: { confidence_level: 'high' }
      };
      mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

      const result = await chatAPI.sendMessage('session-123', 'Test message');

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/api/v2/chat/sessions/session-123/messages',
        { content: 'Test message' }
      );
      expect(result).toEqual(mockResponse);
    });

    it('should submit feedback', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: {} });

      const feedback: UserFeedback = {
        relevance_score: 0.9,
        completeness_score: 0.8,
        helpful: true,
        feedback_text: 'Great response!'
      };

      await chatAPI.submitFeedback('session-123', feedback);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/api/v2/chat/sessions/session-123/feedback',
        feedback
      );
    });

    it('should get session metrics', async () => {
      const mockMetrics: SessionMetrics = {
        session_id: 'session-123',
        turn_count: 5,
        total_response_time: 7.5,
        avg_response_time: 1.5,
        avg_sufficiency_score: 0.82,
        total_expansion_attempts: 2,
        expansion_rate: 0.4,
        error_rate: 0.0,
        intents: ['query_events'],
        satisfaction_scores: [0.85, 0.9]
      };
      mockAxiosInstance.get.mockResolvedValue({ data: mockMetrics });

      const result = await chatAPI.getSessionMetrics('session-123');

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/api/v2/chat/sessions/session-123/metrics'
      );
      expect(result).toEqual(mockMetrics);
    });

    it('should get system metrics', async () => {
      const mockMetrics: Partial<SystemMetrics> = {
        quality: {
          total_conversations: 150,
          total_turns: 500,
          avg_response_time: 1.4,
          p95_response_time: 2.8,
          avg_sufficiency_score: 0.79,
          expansion_rate: 0.35,
          error_rate: 0.02,
          intent_distribution: { query_events: 45 },
          active_users: 42
        }
      };
      mockAxiosInstance.get.mockResolvedValue({ data: mockMetrics });

      const result = await chatAPI.getSystemMetrics();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/api/v2/chat/metrics/system'
      );
      expect(result).toEqual(mockMetrics);
    });

    it('should export analytics', async () => {
      const mockAnalytics = { export_timestamp: '2024-01-10' };
      mockAxiosInstance.get.mockResolvedValue({ data: mockAnalytics });

      const result = await chatAPI.exportAnalytics();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/api/v2/chat/analytics/export'
      );
      expect(result).toEqual(mockAnalytics);
    });

    it('should use v2 health check endpoint', async () => {
      const mockHealth = { status: 'ok', service: 'agentic', initialized: true };
      mockAxiosInstance.get.mockResolvedValue({ data: mockHealth });

      const result = await chatAPI.healthCheck();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/v2/chat/health');
      expect(result).toEqual(mockHealth);
    });
  });

  describe('v1 API Compatibility', () => {
    beforeEach(() => {
      process.env.REACT_APP_USE_V2_API = 'false';
    });

    it('should use v1 endpoints when configured', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: {} });

      await chatAPI.createSession();
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/api/chat/sessions',
        {}
      );

      await chatAPI.sendMessage('session-123', 'Test');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/api/chat/sessions/session-123/messages',
        { message: 'Test' }
      );
    });

    it('should warn when using v2-only features in v1 mode', async () => {
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

      await chatAPI.submitFeedback('session-123', { helpful: true });
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Feedback submission is only available in v2 API'
      );

      const metrics = await chatAPI.getSessionMetrics('session-123');
      expect(metrics).toBeNull();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Session metrics are only available in v2 API'
      );

      consoleWarnSpy.mockRestore();
    });
  });

  describe('WebSocket URL Generation', () => {
    it('should generate v2 WebSocket URL', () => {
      process.env.REACT_APP_USE_V2_API = 'true';
      const url = getWebSocketUrl('session-123');
      expect(url).toBe('ws://localhost:8000/api/v2/chat/sessions/session-123/ws');
    });

    it('should generate v1 WebSocket URL', () => {
      process.env.REACT_APP_USE_V2_API = 'false';
      const url = getWebSocketUrl('session-123');
      expect(url).toBe('ws://localhost:8000/api/chat/ws/session-123');
    });

    it('should use wss for https', () => {
      Object.defineProperty(window.location, 'protocol', {
        value: 'https:',
        configurable: true,
      });
      
      const url = getWebSocketUrl('session-123');
      expect(url).toStartWith('wss://');
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors', async () => {
      const error = new Error('Network error');
      mockAxiosInstance.post.mockRejectedValue(error);

      await expect(chatAPI.sendMessage('session-123', 'Test')).rejects.toThrow('Network error');
    });

    it('should add auth token to requests', () => {
      const mockToken = 'Bearer test-token-123';
      localStorage.setItem('auth_token', mockToken);

      // Trigger interceptor setup
      const interceptorFn = mockAxiosInstance.interceptors.request.use.mock.calls[0][0];
      const config = { headers: {} };
      
      const result = interceptorFn(config);
      
      expect(result.headers.Authorization).toBe(mockToken);
    });
  });
});
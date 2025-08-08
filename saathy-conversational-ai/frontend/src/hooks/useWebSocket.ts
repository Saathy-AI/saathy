import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketMessage } from '../types/chat';
import { getWebSocketUrl } from '../services/api';

interface UseWebSocketProps {
  sessionId: string | null;
  onMessage: (message: WebSocketMessage) => void;
  enabled?: boolean;
}

export const useWebSocket = ({ sessionId, onMessage, enabled = true }: UseWebSocketProps) => {
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    if (!sessionId || !enabled || ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);

    try {
      const wsUrl = getWebSocketUrl(sessionId);
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setIsConnecting(false);
        reconnectAttemptsRef.current = 0;

        // Send authentication
        const authMessage = {
          user_id: localStorage.getItem('user_id') || 'test_user_123',
        };
        ws.current?.send(JSON.stringify(authMessage));
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          onMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnecting(false);
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setIsConnecting(false);

        // Attempt to reconnect with exponential backoff
        if (enabled && reconnectAttemptsRef.current < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
          reconnectAttemptsRef.current += 1;

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setIsConnecting(false);
    }
  }, [sessionId, enabled, onMessage]);

  const sendMessage = useCallback((message: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ message }));
      return true;
    }
    return false;
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, enabled]);

  return {
    isConnected,
    isConnecting,
    sendMessage,
    disconnect,
  };
};
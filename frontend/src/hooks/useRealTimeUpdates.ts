import { useEffect, useCallback } from 'react';
import { createWebSocketConnection } from '../utils/api';

export function useRealTimeUpdates(userId: string, onNewAction: (action: any) => void) {
  const connectWebSocket = useCallback(() => {
    const ws = createWebSocketConnection(userId);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_action') {
          onNewAction(data.action);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      // Reconnect after 5 seconds
      setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return ws;
  }, [userId, onNewAction]);

  useEffect(() => {
    const ws = connectWebSocket();
    return () => ws.close();
  }, [connectWebSocket]);
}
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { FiMessageSquare, FiRefreshCw } from 'react-icons/fi';
import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { TypingIndicator } from './TypingIndicator';
import { useWebSocket } from '../hooks/useWebSocket';
import { chatAPI } from '../services/api';
import { ChatMessage, WebSocketMessage } from '../types/chat';

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'connected':
        console.log('Connected to chat session:', message.sessionId);
        break;
      
      case 'response': {
        const responseData = message.data || {};
        const content = responseData.message || responseData.response || message.response || '';
        const ts = responseData.timestamp || new Date().toISOString();
        const sources = responseData.contextSources || responseData.context_sources || message.context_used;
        const newMessage: ChatMessage = {
          id: Date.now().toString(),
          content,
          role: 'assistant',
          timestamp: new Date(ts),
          contextSources: sources,
        };
        setMessages((prev) => [...prev, newMessage]);
        setIsTyping(false);
        break;
      }
      
      case 'typing':
        setIsTyping(Boolean((message as any).isTyping) || (message as any).status === 'processing');
        break;
      
      case 'error':
        setError((message as any).error || 'An error occurred');
        setIsTyping(false);
        break;
    }
  }, []);

  const { isConnected, sendMessage: sendWebSocketMessage } = useWebSocket({
    sessionId,
    onMessage: handleWebSocketMessage,
    enabled: !!sessionId,
  });

  const initializeSession = async () => {
    setIsInitializing(true);
    setError(null);
    
    try {
      const session = await chatAPI.createSession();
      const sid = (session as any).sessionId || (session as any).id;
      if (!sid) {
        throw new Error('Failed to create session: no session ID returned');
      }
      setSessionId(sid);
      
      // Add welcome message
      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        content: "Hi! I'm Saathy, your AI work copilot. I can help you navigate your work across Slack, GitHub, Notion, and more. What would you like to know?",
        role: 'assistant',
        timestamp: new Date(),
      };
      setMessages([welcomeMessage]);
    } catch (err) {
      setError('Failed to start chat session. Please try again.');
      console.error('Failed to initialize session:', err);
    } finally {
      setIsInitializing(false);
    }
  };

  useEffect(() => {
    initializeSession();
  }, []);

  const handleSendMessage = async (messageText: string) => {
    if (!sessionId) {
      setError('No active session. Please refresh the page.');
      return;
    }

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: messageText,
      role: 'user',
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setError(null);

    // Try WebSocket first, fallback to HTTP
    if (isConnected) {
      const sent = sendWebSocketMessage(messageText);
      if (!sent) {
        // Fallback to HTTP
        await sendViaHttp(messageText);
      }
    } else {
      await sendViaHttp(messageText);
    }
  };

  const sendViaHttp = async (messageText: string) => {
    if (!sessionId) return;
    
    setIsTyping(true);
    
    try {
      const response = await chatAPI.sendMessage(sessionId, messageText);
      const content = response.message || response.response || '';
      const ts = (response as any).timestamp || new Date().toISOString();
      const sources = response.contextSources || (response as any).context_used;
      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        content: content || 'No response received',
        role: 'assistant',
        timestamp: new Date(ts),
        contextSources: sources,
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError('Failed to send message. Please try again.');
      console.error('Failed to send message:', err);
    } finally {
      setIsTyping(false);
    }
  };

  const handleNewSession = () => {
    if (sessionId) {
      chatAPI.endSession(sessionId).catch(console.error);
    }
    setMessages([]);
    setSessionId(null);
    setError(null);
    initializeSession();
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FiMessageSquare className="w-6 h-6 text-primary-600" />
            <h1 className="text-lg font-semibold text-gray-800">
              Saathy AI Chat
            </h1>
            {isConnected && (
              <span className="text-xs text-green-600 bg-green-100 px-2 py-1 rounded-full">
                Connected
              </span>
            )}
          </div>
          
          <button
            onClick={handleNewSession}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Start new session"
          >
            <FiRefreshCw className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="max-w-4xl mx-auto">
          {isInitializing ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-gray-500">Starting chat session...</div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />)
              )}
              
              {isTyping && <TypingIndicator />}
              
              {error && (
                <div className="mx-4 my-2 p-3 bg-red-100 border border-red-300 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </div>

      {/* Input */}
      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={!sessionId || isInitializing}
      />
    </div>
  );
};
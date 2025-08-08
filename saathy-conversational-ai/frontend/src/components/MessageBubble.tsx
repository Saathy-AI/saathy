import React from 'react';
import { format } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import { FiUser, FiCpu, FiExternalLink } from 'react-icons/fi';
import { ChatMessage } from '../types/chat';
import clsx from 'clsx';

interface MessageBubbleProps {
  message: ChatMessage;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={clsx(
        'flex gap-3 p-4 message-slide-in',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
            <FiCpu className="w-5 h-5 text-primary-600" />
          </div>
        </div>
      )}
      
      <div className={clsx('max-w-2xl', isUser && 'order-first')}>
        <div
          className={clsx(
            'rounded-lg px-4 py-3',
            isUser
              ? 'bg-primary-500 text-white'
              : 'bg-gray-100 text-gray-800'
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown
              className="prose prose-sm max-w-none"
              components={{
                a: ({ node, ...props }) => (
                  <a
                    {...props}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:text-primary-700 inline-flex items-center gap-1"
                  >
                    {props.children}
                    <FiExternalLink className="w-3 h-3" />
                  </a>
                ),
                code: ({ node, inline, ...props }: any) =>
                  inline ? (
                    <code
                      {...props}
                      className="bg-gray-200 px-1 py-0.5 rounded text-sm"
                    />
                  ) : (
                    <code
                      {...props}
                      className="block bg-gray-200 p-2 rounded text-sm overflow-x-auto"
                    />
                  ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>
        
        <div className="flex items-center gap-2 mt-1 px-1">
          <span className="text-xs text-gray-500">
            {format(new Date(message.timestamp), 'HH:mm')}
          </span>
          
          {!isUser && message.contextSources && message.contextSources.length > 0 && (
            <span className="text-xs text-gray-500">
              • {message.contextSources.length} sources
            </span>
          )}
        </div>

        {/* Context sources */}
        {!isUser && message.contextSources && message.contextSources.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.contextSources.slice(0, 2).map((source, index) => (
              <div
                key={index}
                className="text-xs bg-gray-50 border border-gray-200 rounded px-2 py-1"
              >
                <span className="font-medium text-gray-600">
                  {source.platform}
                </span>
                <span className="text-gray-500 mx-1">•</span>
                <span className="text-gray-600">{source.type}</span>
                <p className="text-gray-500 truncate mt-0.5">
                  {source.preview}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center">
            <FiUser className="w-5 h-5 text-gray-600" />
          </div>
        </div>
      )}
    </div>
  );
};
import React from 'react';
import { FiCpu } from 'react-icons/fi';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex gap-3 p-4">
      <div className="flex-shrink-0">
        <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
          <FiCpu className="w-5 h-5 text-primary-600" />
        </div>
      </div>
      
      <div className="bg-gray-100 rounded-lg px-4 py-3">
        <div className="flex space-x-1">
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-typing"></div>
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-typing" style={{ animationDelay: '0.2s' }}></div>
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-typing" style={{ animationDelay: '0.4s' }}></div>
        </div>
      </div>
    </div>
  );
};
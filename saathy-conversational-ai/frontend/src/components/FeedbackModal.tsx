import React, { useState } from 'react';
import { UserFeedback } from '../types/chat';
import { chatAPI } from '../services/api';

interface FeedbackModalProps {
  sessionId: string;
  messageId?: string;
  onClose: () => void;
  onSubmit?: () => void;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  sessionId,
  messageId,
  onClose,
  onSubmit,
}) => {
  const [feedback, setFeedback] = useState<UserFeedback>({
    relevance_score: 0.8,
    completeness_score: 0.8,
    helpful: true,
    feedback_text: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await chatAPI.submitFeedback(sessionId, feedback);
      onSubmit?.();
      onClose();
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-semibold mb-4">Rate this response</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Relevance Score */}
          <div>
            <label className="block text-sm font-medium mb-2">
              How relevant was the response? ({Math.round((feedback.relevance_score || 0) * 100)}%)
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={feedback.relevance_score}
              onChange={(e) => setFeedback({ ...feedback, relevance_score: parseFloat(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>Not relevant</span>
              <span>Very relevant</span>
            </div>
          </div>

          {/* Completeness Score */}
          <div>
            <label className="block text-sm font-medium mb-2">
              How complete was the response? ({Math.round((feedback.completeness_score || 0) * 100)}%)
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={feedback.completeness_score}
              onChange={(e) => setFeedback({ ...feedback, completeness_score: parseFloat(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>Incomplete</span>
              <span>Complete</span>
            </div>
          </div>

          {/* Helpful Toggle */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="helpful"
              checked={feedback.helpful}
              onChange={(e) => setFeedback({ ...feedback, helpful: e.target.checked })}
              className="h-4 w-4 text-blue-600 rounded"
            />
            <label htmlFor="helpful" className="ml-2 text-sm">
              This response was helpful
            </label>
          </div>

          {/* Feedback Text */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Additional feedback (optional)
            </label>
            <textarea
              value={feedback.feedback_text}
              onChange={(e) => setFeedback({ ...feedback, feedback_text: e.target.value })}
              className="w-full p-2 border rounded-md"
              rows={3}
              placeholder="Tell us more about your experience..."
            />
          </div>

          {/* Actions */}
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
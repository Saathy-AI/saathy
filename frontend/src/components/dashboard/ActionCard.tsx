import React from 'react';
import { GeneratedAction } from '../../types/actions';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

interface ActionCardProps {
  action: GeneratedAction;
  onStatusUpdate: (actionId: string, status: string, feedback?: string) => Promise<boolean>;
  onTrackInteraction: (actionId: string, eventType: string, metadata?: string) => void;
}

const priorityColors = {
  urgent: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
  fyi: 'bg-gray-100 text-gray-800 border-gray-200',
};

const actionTypeIcons = {
  review: '👀',
  respond: '💬',
  update: '📝',
  meeting: '📅',
  follow_up: '🔄',
  create: '✨',
  fix: '🔧',
};

export function ActionCard({ action, onStatusUpdate, onTrackInteraction }: ActionCardProps) {
  const handleComplete = async () => {
    onTrackInteraction(action.action_id, 'marked_complete');
    await onStatusUpdate(action.action_id, 'completed');
  };

  const handleDismiss = async () => {
    onTrackInteraction(action.action_id, 'dismissed');
    await onStatusUpdate(action.action_id, 'dismissed');
  };

  const handleLinkClick = (link: any) => {
    onTrackInteraction(action.action_id, 'clicked_link', `${link.platform}:${link.action_type}`);
    window.open(link.url, '_blank');
  };

  const isCompleted = action.status === 'completed';
  const isDismissed = action.status === 'dismissed';

  return (
    <div className={`relative p-4 bg-white rounded-lg shadow-sm border transition-all hover:shadow-md ${
      isCompleted || isDismissed ? 'opacity-75' : ''
    } ${priorityColors[action.priority]}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">{actionTypeIcons[action.action_type]}</span>
            <h3 className="font-semibold text-gray-900">{action.title}</h3>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={action.priority === 'urgent' ? 'danger' : 'warning'}>
              {action.priority.toUpperCase()}
            </Badge>
            <span className="text-sm text-gray-500">
              ~{action.estimated_time_minutes} min
            </span>
          </div>
        </div>
        
        {/* Status indicator */}
        {isCompleted && (
          <Badge variant="success">
            ✓ Completed
          </Badge>
        )}
        {isDismissed && (
          <Badge variant="default">
            Dismissed
          </Badge>
        )}
      </div>

      {/* Description */}
      <p className="text-gray-700 mb-3">{action.description}</p>

      {/* Context/Reasoning */}
      <div className="bg-white bg-opacity-50 rounded p-2 mb-3">
        <p className="text-sm text-gray-600">
          <strong>Why now:</strong> {action.reasoning}
        </p>
      </div>

      {/* Action Links */}
      {action.action_links.length > 0 && (
        <div className="mb-3">
          <p className="text-sm font-medium text-gray-700 mb-1">Quick Actions:</p>
          <div className="flex flex-wrap gap-2">
            {action.action_links.map((link, index) => (
              <Button
                key={index}
                variant="ghost"
                size="sm"
                onClick={() => handleLinkClick(link)}
              >
                {link.platform === 'slack' && '💬'}
                {link.platform === 'github' && '🐙'}
                {link.platform === 'notion' && '📝'}
                {' '}
                {link.label}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Related People */}
      {action.related_people.length > 0 && (
        <div className="mb-3">
          <p className="text-sm text-gray-600">
            <strong>People involved:</strong> {action.related_people.join(', ')}
          </p>
        </div>
      )}

      {/* Action Buttons */}
      {!isCompleted && !isDismissed && (
        <div className="flex gap-2 pt-3 border-t border-gray-200">
          <Button variant="primary" size="sm" onClick={handleComplete}>
            ✓ Mark Complete
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDismiss}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Timestamp */}
      <div className="text-xs text-gray-500 mt-3">
        Generated {new Date(action.generated_at).toLocaleDateString()} at{' '}
        {new Date(action.generated_at).toLocaleTimeString()}
      </div>
    </div>
  );
}
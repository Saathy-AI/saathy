import { useState, useEffect, useCallback } from 'react';
import { GeneratedAction, ActionFilters, ApiResponse } from '../types/actions';
import { apiClient } from '../utils/api';

export function useActions(userId: string, filters: ActionFilters = {}) {
  const [actions, setActions] = useState<ApiResponse<GeneratedAction[]>>({
    data: [],
    loading: true,
  });

  const fetchActions = useCallback(async () => {
    try {
      setActions(prev => ({ ...prev, loading: true }));
      
      const response = await apiClient.get('/api/actions', {
        params: {
          user_id: userId,
          priority: filters.priority?.join(','),
          status: filters.status,
          limit: filters.limit || 20,
        },
      });
      
      setActions({
        data: response.data.actions,
        loading: false,
      });
    } catch (error) {
      setActions({
        data: [],
        error: error instanceof Error ? error.message : 'Failed to fetch actions',
        loading: false,
      });
    }
  }, [userId, filters]);

  const updateActionStatus = async (
    actionId: string, 
    status: string, 
    feedback?: string
  ) => {
    try {
      await apiClient.post(`/api/actions/${actionId}/status`, null, {
        params: {
          user_id: userId,
          status,
          feedback,
        },
      });
      
      // Optimistically update local state
      setActions(prev => ({
        ...prev,
        data: prev.data?.map(action => 
          action.action_id === actionId 
            ? { ...action, status: status as any, user_feedback: feedback }
            : action
        ),
      }));
      
      return true;
    } catch (error) {
      console.error('Failed to update action status:', error);
      return false;
    }
  };

  const trackInteraction = async (actionId: string, eventType: string, metadata?: string) => {
    try {
      await apiClient.post(`/api/actions/${actionId}/track`, null, {
        params: {
          user_id: userId,
          event_type: eventType,
          metadata,
        },
      });
    } catch (error) {
      console.error('Failed to track interaction:', error);
    }
  };

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  return {
    actions: actions.data || [],
    loading: actions.loading,
    error: actions.error,
    refetch: fetchActions,
    updateActionStatus,
    trackInteraction,
  };
}
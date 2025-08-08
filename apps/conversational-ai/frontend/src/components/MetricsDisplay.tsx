import React, { useEffect, useState } from 'react';
import { SessionMetrics, SystemMetrics } from '../types/chat';
import { chatAPI } from '../services/api';

interface MetricsDisplayProps {
  sessionId?: string;
  showSystemMetrics?: boolean;
}

export const MetricsDisplay: React.FC<MetricsDisplayProps> = ({
  sessionId,
  showSystemMetrics = false,
}) => {
  const [sessionMetrics, setSessionMetrics] = useState<SessionMetrics | null>(null);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      setLoading(true);
      setError(null);

      try {
        if (sessionId) {
          const metrics = await chatAPI.getSessionMetrics(sessionId);
          setSessionMetrics(metrics);
        }

        if (showSystemMetrics) {
          const metrics = await chatAPI.getSystemMetrics();
          setSystemMetrics(metrics);
        }
      } catch (err) {
        setError('Failed to load metrics');
        console.error('Failed to fetch metrics:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [sessionId, showSystemMetrics]);

  if (loading) {
    return <div className="p-4 text-center">Loading metrics...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-600">{error}</div>;
  }

  return (
    <div className="space-y-6">
      {/* Session Metrics */}
      {sessionMetrics && (
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-3">Session Metrics</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="Messages"
              value={sessionMetrics.turn_count}
              unit=""
            />
            <MetricCard
              label="Avg Response Time"
              value={sessionMetrics.avg_response_time.toFixed(2)}
              unit="s"
            />
            <MetricCard
              label="Sufficiency Score"
              value={Math.round(sessionMetrics.avg_sufficiency_score * 100)}
              unit="%"
            />
            <MetricCard
              label="Expansion Rate"
              value={Math.round(sessionMetrics.expansion_rate * 100)}
              unit="%"
            />
          </div>

          {sessionMetrics.satisfaction_scores.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium mb-2">Satisfaction Scores</h4>
              <div className="flex gap-2">
                {sessionMetrics.satisfaction_scores.map((score, idx) => (
                  <div
                    key={idx}
                    className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm"
                  >
                    {Math.round(score * 100)}%
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* System Metrics */}
      {systemMetrics && (
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-3">System Metrics</h3>
          
          {/* Quality Metrics */}
          <div className="mb-4">
            <h4 className="text-sm font-medium mb-2">Quality</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard
                label="Active Users"
                value={systemMetrics.quality.active_users}
                unit=""
              />
              <MetricCard
                label="Avg Response"
                value={systemMetrics.quality.avg_response_time.toFixed(2)}
                unit="s"
              />
              <MetricCard
                label="P95 Response"
                value={systemMetrics.quality.p95_response_time.toFixed(2)}
                unit="s"
              />
              <MetricCard
                label="Error Rate"
                value={Math.round(systemMetrics.quality.error_rate * 100)}
                unit="%"
              />
            </div>
          </div>

          {/* Cache Metrics */}
          <div className="mb-4">
            <h4 className="text-sm font-medium mb-2">Cache Performance</h4>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <MetricCard
                label="Hit Rate"
                value={Math.round(systemMetrics.cache.hit_rate * 100)}
                unit="%"
              />
              <MetricCard
                label="Cache Size"
                value={systemMetrics.cache.query_cache_size + systemMetrics.cache.context_cache_size}
                unit=""
              />
              <MetricCard
                label="Total Hits"
                value={systemMetrics.cache.hits}
                unit=""
              />
            </div>
          </div>

          {/* Learning Metrics */}
          {systemMetrics.learning.response_time && (
            <div>
              <h4 className="text-sm font-medium mb-2">Learning Progress</h4>
              <div className="space-y-2">
                <TrendIndicator
                  label="Response Time"
                  current={systemMetrics.learning.response_time.current}
                  trend={systemMetrics.learning.response_time.trend}
                  improvement={systemMetrics.learning.response_time.improvement}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const MetricCard: React.FC<{
  label: string;
  value: string | number;
  unit: string;
}> = ({ label, value, unit }) => (
  <div className="bg-gray-50 p-3 rounded">
    <div className="text-sm text-gray-600">{label}</div>
    <div className="text-xl font-semibold">
      {value}
      {unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
    </div>
  </div>
);

const TrendIndicator: React.FC<{
  label: string;
  current: number;
  trend: 'increasing' | 'decreasing' | 'stable';
  improvement: number;
}> = ({ label, current, trend, improvement }) => {
  const trendIcon = {
    increasing: '↑',
    decreasing: '↓',
    stable: '→',
  }[trend];

  const trendColor = {
    increasing: improvement > 0 ? 'text-red-600' : 'text-green-600',
    decreasing: improvement < 0 ? 'text-green-600' : 'text-red-600',
    stable: 'text-gray-600',
  }[trend];

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm">{label}</span>
      <div className="flex items-center gap-2">
        <span className="font-medium">{current.toFixed(2)}</span>
        <span className={`${trendColor} text-sm`}>
          {trendIcon} {Math.abs(improvement).toFixed(2)}
        </span>
      </div>
    </div>
  );
};
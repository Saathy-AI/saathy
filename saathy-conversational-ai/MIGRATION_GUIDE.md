# Migration Guide: Phase 1 to Phase 2 & 3

This guide helps you migrate from the Phase 1 basic implementation to the advanced Phase 2 & 3 agentic system.

## Overview of Changes

### New Features
- **Multi-Agent System**: LangGraph-based intelligent processing
- **Advanced Retrieval**: Reciprocal Rank Fusion (RRF)
- **Context Sufficiency**: Multi-dimensional quality evaluation
- **Memory Compression**: COMEDY framework for long conversations
- **Intelligent Caching**: Multi-level cache with fuzzy matching
- **Learning System**: Continuous parameter optimization
- **Comprehensive Metrics**: Prometheus-based monitoring

### Breaking Changes
- New v2 API endpoints (v1 still supported)
- Additional dependencies required
- New configuration parameters
- Enhanced response format with metadata

## Step-by-Step Migration

### 1. Update Dependencies

Add new Python packages:
```bash
cd backend
pip install -r requirements.txt
```

New dependencies include:
- `langgraph==0.0.20` (already in requirements)
- `cachetools==5.3.2`
- Additional sub-dependencies

### 2. Update Configuration

Copy new environment variables to your `.env`:
```bash
# Phase 2 Settings
MAX_EXPANSION_ATTEMPTS=3
SUFFICIENCY_THRESHOLD=0.7
RRF_K=60

# Phase 3 Settings
COMPRESSION_THRESHOLD=5
CACHE_TTL_QUERY=300
LEARNING_RATE=0.1

# See .env.example for complete list
```

### 3. Database Migration

No database schema changes required. The new system uses the same models.

### 4. Update API Calls

#### Option A: Keep Using v1 (No Code Changes)
The v1 endpoints continue to work as before:
```python
POST /api/chat/sessions/{id}/messages
```

#### Option B: Migrate to v2 (Recommended)
Update your API calls:

```python
# Old v1
response = requests.post(
    f"{API_URL}/api/chat/sessions/{session_id}/messages",
    json={"content": "What happened yesterday?"}
)

# New v2
response = requests.post(
    f"{API_URL}/api/v2/chat/sessions/{session_id}/messages",
    json={"content": "What happened yesterday?"}
)

# Response includes additional metadata
data = response.json()
print(data["response"])  # Same as before
print(data["metadata"]["confidence_level"])  # New
print(data["metadata"]["processing_time"])  # New
```

### 5. Implement Feedback Collection

Add user feedback to improve the system:

```python
# After receiving a response
feedback_response = requests.post(
    f"{API_URL}/api/v2/chat/sessions/{session_id}/feedback",
    json={
        "relevance_score": 0.9,
        "completeness_score": 0.8,
        "helpful": True
    }
)
```

### 6. Monitor System Performance

Access new metrics endpoints:

```python
# Session metrics
metrics = requests.get(
    f"{API_URL}/api/v2/chat/sessions/{session_id}/metrics"
).json()

# System-wide metrics
system_metrics = requests.get(
    f"{API_URL}/api/v2/chat/metrics/system"
).json()
```

### 7. Frontend Updates

Update the frontend to use v2 endpoints:

```typescript
// Update API service
const API_V2_BASE = '/api/v2/chat';

// Update message sending
const sendMessage = async (sessionId: string, content: string) => {
  const response = await fetch(
    `${API_V2_BASE}/sessions/${sessionId}/messages`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    }
  );
  return response.json();
};

// Add feedback UI
const submitFeedback = async (sessionId: string, feedback: Feedback) => {
  await fetch(
    `${API_V2_BASE}/sessions/${sessionId}/feedback`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedback)
    }
  );
};
```

## Performance Tuning

### 1. Cache Configuration
Adjust cache TTLs based on your use case:
```env
CACHE_TTL_QUERY=300  # Increase for stable data
CACHE_TTL_CONTEXT=600  # Decrease for rapidly changing data
```

### 2. Sufficiency Thresholds
Fine-tune based on your quality requirements:
```env
SUFFICIENCY_THRESHOLD=0.7  # Increase for higher quality
MAX_EXPANSION_ATTEMPTS=3  # Increase for more thorough searches
```

### 3. Learning Parameters
Adjust learning aggressiveness:
```env
LEARNING_RATE=0.1  # Decrease for more stable parameters
LEARNING_BATCH_SIZE=100  # Increase for less frequent updates
```

## Monitoring Setup

### 1. Prometheus Configuration
Add to your `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'saathy-chat'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 2. Key Metrics to Watch
- `saathy_response_time_seconds` - Monitor latency
- `saathy_sufficiency_score` - Track context quality
- `saathy_cache_hit_rate` - Optimize cache performance
- `saathy_errors_total` - Identify issues

## Rollback Plan

If you need to rollback:

1. **Keep v1 endpoints active** - They remain functional
2. **Disable v2 features**:
   ```env
   ENABLE_V2_ENDPOINTS=false
   ENABLE_LEARNING=false
   ENABLE_CACHING=false
   ```
3. **Use v1 API calls** - No code changes needed

## Common Issues

### 1. Increased Memory Usage
The caching and memory systems use more RAM. Solutions:
- Reduce cache sizes in configuration
- Decrease `COMPRESSION_THRESHOLD` for earlier memory compression

### 2. Slower First Responses
Multi-agent processing takes longer initially but improves with caching:
- Warm up cache with common queries
- Adjust `SUFFICIENCY_THRESHOLD` if too strict

### 3. Learning System Instability
If parameters fluctuate too much:
- Decrease `LEARNING_RATE`
- Increase `LEARNING_BATCH_SIZE`
- Monitor optimization history via analytics export

## Best Practices

1. **Start with v2 in staging** - Test thoroughly before production
2. **Enable features gradually**:
   - Week 1: Basic v2 endpoints
   - Week 2: Enable caching
   - Week 3: Enable learning
3. **Monitor metrics closely** during migration
4. **Collect user feedback** to train the system
5. **Export analytics weekly** to track improvements

## Support

For migration support:
1. Check the [API Documentation](./API_DOCUMENTATION.md)
2. Review the [Phase 2 & 3 Summary](./PHASE2_3_SUMMARY.md)
3. Monitor system health at `/api/v2/chat/health`

The migration preserves all existing functionality while adding powerful new capabilities. The system will improve over time as it learns from usage patterns.
-- Database initialization for Saathy Conversational AI
-- This script sets up the required tables and indexes

-- Create chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    context_state JSONB DEFAULT '{}',
    session_metadata JSONB DEFAULT '{}'
);

-- Create chat turns table
CREATE TABLE IF NOT EXISTS chat_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_message TEXT NOT NULL,
    assistant_response TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    context_used JSONB DEFAULT '{}',
    retrieval_strategy VARCHAR(100),
    processing_time_ms INTEGER,
    metadata JSONB DEFAULT '{}'
);

-- Create user feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    turn_id UUID REFERENCES chat_turns(id) ON DELETE CASCADE,
    feedback_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create system metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    tags JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_status ON chat_sessions(status);

CREATE INDEX IF NOT EXISTS idx_chat_turns_session_id ON chat_turns(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_turns_timestamp ON chat_turns(timestamp);

CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at);

CREATE INDEX IF NOT EXISTS idx_system_metrics_name_timestamp ON system_metrics(metric_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger to chat_sessions table
DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON chat_sessions;
CREATE TRIGGER update_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some default system configuration
INSERT INTO system_metrics (metric_name, metric_value, tags) VALUES
('system_initialized', 1.0, '{"version": "1.0.0", "timestamp": "' || CURRENT_TIMESTAMP || '"}')
ON CONFLICT DO NOTHING;
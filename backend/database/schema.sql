-- =================================================================
-- TechCorp Customer Success Digital FTE — PostgreSQL Schema
-- =================================================================
-- Requires: PostgreSQL 16 + pgvector extension
-- Run: psql -U fte_user -d fte_db -f schema.sql

-- Enable pgvector extension for AI embeddings
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search

-- =================================================================
-- TABLE: customers
-- =================================================================
CREATE TABLE IF NOT EXISTS customers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(50),
    name            VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata        JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_metadata ON customers USING GIN(metadata);

-- =================================================================
-- TABLE: customer_identifiers
-- Cross-channel identity linking (email → same customer as WhatsApp number)
-- =================================================================
CREATE TABLE IF NOT EXISTS customer_identifiers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type     VARCHAR(20) NOT NULL CHECK (identifier_type IN ('email', 'phone', 'whatsapp')),
    identifier_value    VARCHAR(255) NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(identifier_type, identifier_value)
);

CREATE INDEX IF NOT EXISTS idx_customer_identifiers_customer_id ON customer_identifiers(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_identifiers_lookup ON customer_identifiers(identifier_type, identifier_value);

-- =================================================================
-- TABLE: conversations
-- =================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    initial_channel     VARCHAR(20) NOT NULL CHECK (initial_channel IN ('email', 'whatsapp', 'web_form')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'resolved', 'escalated')),
    sentiment_score     DECIMAL(3, 2) DEFAULT 0.5
                            CHECK (sentiment_score >= 0.0 AND sentiment_score <= 1.0),
    started_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at            TIMESTAMP WITH TIME ZONE,
    metadata            JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_initial_channel ON conversations(initial_channel);
CREATE INDEX IF NOT EXISTS idx_conversations_started_at ON conversations(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_sentiment ON conversations(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_conversations_metadata ON conversations USING GIN(metadata);

-- =================================================================
-- TABLE: messages
-- =================================================================
CREATE TABLE IF NOT EXISTS messages (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    channel             VARCHAR(20) NOT NULL CHECK (channel IN ('email', 'whatsapp', 'web_form')),
    direction           VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    role                VARCHAR(20) NOT NULL CHECK (role IN ('customer', 'agent', 'system')),
    content             TEXT NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tokens_used         INTEGER DEFAULT 0,
    latency_ms          INTEGER DEFAULT 0,
    tool_calls          JSONB DEFAULT '[]'::jsonb,
    channel_message_id  VARCHAR(255),
    delivery_status     VARCHAR(20) NOT NULL DEFAULT 'pending'
                            CHECK (delivery_status IN ('pending', 'sent', 'delivered', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel);
CREATE INDEX IF NOT EXISTS idx_messages_direction ON messages(direction);
CREATE INDEX IF NOT EXISTS idx_messages_delivery_status ON messages(delivery_status);
CREATE INDEX IF NOT EXISTS idx_messages_channel_message_id ON messages(channel_message_id) WHERE channel_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_tool_calls ON messages USING GIN(tool_calls);

-- =================================================================
-- TABLE: tickets
-- =================================================================
CREATE TABLE IF NOT EXISTS tickets (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    source_channel      VARCHAR(50) NOT NULL,
    category            VARCHAR(100) NOT NULL DEFAULT 'general',
    priority            VARCHAR(20) NOT NULL DEFAULT 'medium'
                            CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                            CHECK (status IN ('open', 'processing', 'resolved', 'escalated')),
    subject             VARCHAR(500),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at         TIMESTAMP WITH TIME ZONE,
    resolution_notes    TEXT,
    metadata            JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_tickets_conversation_id ON tickets(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);
CREATE INDEX IF NOT EXISTS idx_tickets_source_channel ON tickets(source_channel);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category);
CREATE INDEX IF NOT EXISTS idx_tickets_metadata ON tickets USING GIN(metadata);

-- =================================================================
-- TABLE: knowledge_base
-- =================================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       VARCHAR(500) NOT NULL,
    content     TEXT NOT NULL,
    category    VARCHAR(100) NOT NULL DEFAULT 'general',
    embedding   VECTOR(1536),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active   BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_is_active ON knowledge_base(is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_title ON knowledge_base USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_knowledge_base_content ON knowledge_base USING GIN(to_tsvector('english', content));
-- Vector similarity search index (IVFFlat for large datasets)
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding ON knowledge_base
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =================================================================
-- TABLE: agent_metrics
-- =================================================================
CREATE TABLE IF NOT EXISTS agent_metrics (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name     VARCHAR(100) NOT NULL,
    metric_value    DECIMAL(10, 4) NOT NULL,
    channel         VARCHAR(50),
    dimensions      JSONB DEFAULT '{}'::jsonb,
    recorded_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_metrics_metric_name ON agent_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_channel ON agent_metrics(channel);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_recorded_at ON agent_metrics(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_dimensions ON agent_metrics USING GIN(dimensions);

-- =================================================================
-- VIEWS: Useful aggregations
-- =================================================================

-- Daily ticket summary
CREATE OR REPLACE VIEW v_daily_ticket_summary AS
SELECT
    DATE_TRUNC('day', t.created_at) AS date,
    t.source_channel,
    t.status,
    t.priority,
    COUNT(*) AS ticket_count,
    AVG(EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 60) AS avg_resolution_minutes
FROM tickets t
GROUP BY DATE_TRUNC('day', t.created_at), t.source_channel, t.status, t.priority;

-- Customer conversation overview
CREATE OR REPLACE VIEW v_customer_overview AS
SELECT
    c.id,
    c.name,
    c.email,
    c.phone,
    COUNT(DISTINCT conv.id) AS total_conversations,
    COUNT(DISTINCT t.id) AS total_tickets,
    MAX(conv.started_at) AS last_contact,
    AVG(conv.sentiment_score) AS avg_sentiment
FROM customers c
LEFT JOIN conversations conv ON c.id = conv.customer_id
LEFT JOIN tickets t ON c.id = t.customer_id
GROUP BY c.id, c.name, c.email, c.phone;

-- =================================================================
-- FUNCTIONS: Triggers for updated_at
-- =================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =================================================================
-- INITIAL DATA: Admin user & system configuration
-- =================================================================
-- Placeholder for seed data (inserted via /admin/seed endpoint)

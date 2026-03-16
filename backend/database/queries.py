"""
TechCorp FTE — Database Query Layer
All SQL queries centralized here using asyncpg.
Provides typed Python functions for every DB operation.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import asyncpg

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection pool (initialized by FastAPI lifespan)
# ---------------------------------------------------------------------------
_pool: Optional[asyncpg.Pool] = None


async def init_pool(database_url: str, min_size: int = 2, max_size: int = 10) -> None:
    """Initialize the asyncpg connection pool."""
    global _pool
    try:
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=30,
            init=_init_connection,
        )
        logger.info(f"[DB] Connection pool initialized (min={min_size}, max={max_size})")
    except Exception as e:
        logger.error(f"[DB] Failed to initialize pool: {e}")
        raise


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Called on each new connection — register custom type codecs."""
    await conn.set_type_codec(
        "jsonb",
        encoder=lambda v: __import__("json").dumps(v),
        decoder=lambda v: __import__("json").loads(v),
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=lambda v: __import__("json").dumps(v),
        decoder=lambda v: __import__("json").loads(v),
        schema="pg_catalog",
    )


async def close_pool() -> None:
    """Close the connection pool gracefully."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("[DB] Connection pool closed")


def get_pool() -> asyncpg.Pool:
    """Get the connection pool — raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


# ---------------------------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------------------------
async def get_customer_by_email(email: str) -> Optional[dict]:
    """Fetch a customer by email address."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM customers WHERE email = $1", email
        )
        return dict(row) if row else None


async def get_customer_by_phone(phone: str) -> Optional[dict]:
    """Fetch a customer by phone number."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM customers WHERE phone = $1", phone
        )
        return dict(row) if row else None


async def get_customer_by_id(customer_id: str) -> Optional[dict]:
    """Fetch a customer by UUID."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM customers WHERE id = $1", uuid.UUID(customer_id)
        )
        return dict(row) if row else None


async def get_customer_by_identifier(
    identifier_type: str, identifier_value: str
) -> Optional[dict]:
    """Lookup customer via customer_identifiers table (cross-channel)."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT c.* FROM customers c
            JOIN customer_identifiers ci ON c.id = ci.customer_id
            WHERE ci.identifier_type = $1 AND ci.identifier_value = $2
            """,
            identifier_type,
            identifier_value,
        )
        return dict(row) if row else None


async def create_customer(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a new customer record."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO customers (id, name, email, phone, metadata)
            VALUES (uuid_generate_v4(), $1, $2, $3, $4)
            RETURNING *
            """,
            name,
            email,
            phone,
            metadata or {},
        )
        return dict(row)


async def upsert_customer_identifier(
    customer_id: str,
    identifier_type: str,
    identifier_value: str,
) -> None:
    """Link a channel identifier to a customer (idempotent)."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO customer_identifiers (id, customer_id, identifier_type, identifier_value)
            VALUES (uuid_generate_v4(), $1, $2, $3)
            ON CONFLICT (identifier_type, identifier_value) DO NOTHING
            """,
            uuid.UUID(customer_id),
            identifier_type,
            identifier_value,
        )


async def list_customers(limit: int = 50, offset: int = 0) -> list[dict]:
    """List all customers with pagination."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM customers ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# CONVERSATIONS
# ---------------------------------------------------------------------------
async def create_conversation(
    customer_id: str,
    initial_channel: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a new conversation."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO conversations (id, customer_id, initial_channel, status, metadata)
            VALUES (uuid_generate_v4(), $1, $2, 'active', $3)
            RETURNING *
            """,
            uuid.UUID(customer_id),
            initial_channel,
            metadata or {},
        )
        return dict(row)


async def get_conversation(conversation_id: str) -> Optional[dict]:
    """Fetch a conversation by ID."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM conversations WHERE id = $1",
            uuid.UUID(conversation_id),
        )
        return dict(row) if row else None


async def update_conversation_status(
    conversation_id: str,
    status: str,
    sentiment_score: Optional[float] = None,
) -> None:
    """Update conversation status and optionally sentiment score."""
    async with get_pool().acquire() as conn:
        if sentiment_score is not None:
            await conn.execute(
                """
                UPDATE conversations
                SET status = $1, sentiment_score = $2,
                    ended_at = CASE WHEN $1 IN ('resolved', 'escalated') THEN NOW() ELSE ended_at END
                WHERE id = $3
                """,
                status,
                sentiment_score,
                uuid.UUID(conversation_id),
            )
        else:
            await conn.execute(
                """
                UPDATE conversations
                SET status = $1,
                    ended_at = CASE WHEN $1 IN ('resolved', 'escalated') THEN NOW() ELSE ended_at END
                WHERE id = $2
                """,
                status,
                uuid.UUID(conversation_id),
            )


async def get_active_conversation(
    customer_id: str, channel: str
) -> Optional[dict]:
    """Get the most recent active conversation for a customer on a channel."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM conversations
            WHERE customer_id = $1
              AND initial_channel = $2
              AND status = 'active'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            uuid.UUID(customer_id),
            channel,
        )
        return dict(row) if row else None


async def get_customer_conversations(
    customer_id: str, limit: int = 10
) -> list[dict]:
    """Get all conversations for a customer."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.*, COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.customer_id = $1
            GROUP BY c.id
            ORDER BY c.started_at DESC
            LIMIT $2
            """,
            uuid.UUID(customer_id),
            limit,
        )
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# MESSAGES
# ---------------------------------------------------------------------------
async def store_message(
    conversation_id: str,
    channel: str,
    direction: str,
    role: str,
    content: str,
    tokens_used: int = 0,
    latency_ms: int = 0,
    tool_calls: Optional[list] = None,
    channel_message_id: Optional[str] = None,
    delivery_status: str = "pending",
) -> dict:
    """Store a message in the database."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages (
                id, conversation_id, channel, direction, role, content,
                tokens_used, latency_ms, tool_calls, channel_message_id, delivery_status
            )
            VALUES (uuid_generate_v4(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
            """,
            uuid.UUID(conversation_id),
            channel,
            direction,
            role,
            content,
            tokens_used,
            latency_ms,
            tool_calls or [],
            channel_message_id,
            delivery_status,
        )
        return dict(row)


async def get_conversation_messages(
    conversation_id: str, limit: int = 50
) -> list[dict]:
    """Get messages for a conversation, ordered chronologically."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            LIMIT $2
            """,
            uuid.UUID(conversation_id),
            limit,
        )
        return [dict(r) for r in rows]


async def update_message_delivery_status(
    message_id: str, status: str
) -> None:
    """Update delivery status of a message."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE messages SET delivery_status = $1 WHERE id = $2",
            status,
            uuid.UUID(message_id),
        )


# ---------------------------------------------------------------------------
# TICKETS
# ---------------------------------------------------------------------------
async def create_ticket(
    conversation_id: str,
    customer_id: str,
    source_channel: str,
    category: str = "general",
    priority: str = "medium",
    subject: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a new support ticket."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tickets (
                id, conversation_id, customer_id, source_channel,
                category, priority, status, subject, metadata
            )
            VALUES (uuid_generate_v4(), $1, $2, $3, $4, $5, 'open', $6, $7)
            RETURNING *
            """,
            uuid.UUID(conversation_id),
            uuid.UUID(customer_id),
            source_channel,
            category,
            priority,
            subject,
            metadata or {},
        )
        return dict(row)


async def get_ticket(ticket_id: str) -> Optional[dict]:
    """Fetch a ticket by ID."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tickets WHERE id = $1",
            uuid.UUID(ticket_id),
        )
        return dict(row) if row else None


async def get_ticket_with_messages(ticket_id: str) -> Optional[dict]:
    """Fetch a ticket with its conversation messages."""
    ticket = await get_ticket(ticket_id)
    if not ticket:
        return None
    messages = await get_conversation_messages(str(ticket["conversation_id"]))
    ticket["messages"] = messages
    return ticket


async def update_ticket_status(
    ticket_id: str,
    status: str,
    resolution_notes: Optional[str] = None,
) -> None:
    """Update ticket status."""
    async with get_pool().acquire() as conn:
        if status == "resolved":
            await conn.execute(
                """
                UPDATE tickets
                SET status = $1, resolution_notes = $2, resolved_at = NOW(), updated_at = NOW()
                WHERE id = $3
                """,
                status,
                resolution_notes,
                uuid.UUID(ticket_id),
            )
        else:
            await conn.execute(
                "UPDATE tickets SET status = $1, updated_at = NOW() WHERE id = $2",
                status,
                uuid.UUID(ticket_id),
            )


async def list_tickets(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List tickets with optional filters."""
    async with get_pool().acquire() as conn:
        conditions = []
        params: list[Any] = []
        idx = 1

        if status:
            conditions.append(f"t.status = ${idx}")
            params.append(status)
            idx += 1
        if channel:
            conditions.append(f"t.source_channel = ${idx}")
            params.append(channel)
            idx += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])

        rows = await conn.fetch(
            f"""
            SELECT t.*, c.name AS customer_name, c.email AS customer_email
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            {where_clause}
            ORDER BY t.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params,
        )
        return [dict(r) for r in rows]


async def get_escalated_tickets() -> list[dict]:
    """Get all escalated tickets that need human attention."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.*, c.name AS customer_name, c.email AS customer_email
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            WHERE t.status = 'escalated'
            ORDER BY t.created_at DESC
            """
        )
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# KNOWLEDGE BASE
# ---------------------------------------------------------------------------
async def search_knowledge_base(
    query_embedding: list[float],
    max_results: int = 5,
    category: Optional[str] = None,
    similarity_threshold: float = 0.7,
) -> list[dict]:
    """
    Vector similarity search in the knowledge base.
    Returns articles ranked by cosine similarity to query embedding.
    """
    async with get_pool().acquire() as conn:
        if category:
            rows = await conn.fetch(
                """
                SELECT id, title, content, category,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM knowledge_base
                WHERE is_active = TRUE
                  AND category = $2
                  AND 1 - (embedding <=> $1::vector) >= $3
                ORDER BY embedding <=> $1::vector
                LIMIT $4
                """,
                query_embedding,
                category,
                similarity_threshold,
                max_results,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, title, content, category,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM knowledge_base
                WHERE is_active = TRUE
                  AND 1 - (embedding <=> $1::vector) >= $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                query_embedding,
                similarity_threshold,
                max_results,
            )
        return [dict(r) for r in rows]


async def fulltext_search_knowledge_base(
    query: str, max_results: int = 5, category: Optional[str] = None
) -> list[dict]:
    """Full-text search fallback when no embedding is available."""
    async with get_pool().acquire() as conn:
        if category:
            rows = await conn.fetch(
                """
                SELECT id, title, content, category,
                       ts_rank(to_tsvector('english', title || ' ' || content),
                               plainto_tsquery('english', $1)) AS rank
                FROM knowledge_base
                WHERE is_active = TRUE
                  AND category = $2
                  AND to_tsvector('english', title || ' ' || content)
                      @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $3
                """,
                query,
                category,
                max_results,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, title, content, category,
                       ts_rank(to_tsvector('english', title || ' ' || content),
                               plainto_tsquery('english', $1)) AS rank
                FROM knowledge_base
                WHERE is_active = TRUE
                  AND to_tsvector('english', title || ' ' || content)
                      @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $2
                """,
                query,
                max_results,
            )
        return [dict(r) for r in rows]


async def insert_knowledge_base_entry(
    title: str,
    content: str,
    category: str,
    embedding: Optional[list[float]] = None,
) -> dict:
    """Insert a new knowledge base entry."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO knowledge_base (id, title, content, category, embedding)
            VALUES (uuid_generate_v4(), $1, $2, $3, $4)
            RETURNING *
            """,
            title,
            content,
            category,
            embedding,
        )
        return dict(row)


# ---------------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------------
async def record_metric(
    metric_name: str,
    metric_value: float,
    channel: Optional[str] = None,
    dimensions: Optional[dict] = None,
) -> None:
    """Record an agent performance metric."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO agent_metrics (id, metric_name, metric_value, channel, dimensions)
            VALUES (uuid_generate_v4(), $1, $2, $3, $4)
            """,
            metric_name,
            metric_value,
            channel,
            dimensions or {},
        )


async def get_channel_metrics(days: int = 7) -> list[dict]:
    """Get aggregated metrics per channel for the last N days."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                t.source_channel AS channel,
                COUNT(DISTINCT t.id) AS total_tickets,
                COUNT(DISTINCT CASE WHEN t.status = 'resolved' THEN t.id END) AS resolved,
                COUNT(DISTINCT CASE WHEN t.status = 'escalated' THEN t.id END) AS escalated,
                COUNT(DISTINCT CASE WHEN t.status = 'open' THEN t.id END) AS open,
                AVG(EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 60)
                    AS avg_resolution_minutes
            FROM tickets t
            WHERE t.created_at >= NOW() - INTERVAL '$1 days'
            GROUP BY t.source_channel
            """,
            days,
        )
        return [dict(r) for r in rows]


async def get_daily_stats() -> dict:
    """Get today's summary statistics."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(DISTINCT t.id) AS total_tickets,
                COUNT(DISTINCT CASE WHEN t.status = 'resolved' THEN t.id END) AS resolved_tickets,
                COUNT(DISTINCT CASE WHEN t.status = 'escalated' THEN t.id END) AS escalated_tickets,
                COUNT(DISTINCT CASE WHEN t.status IN ('open', 'processing') THEN t.id END) AS open_tickets,
                AVG(EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 60)
                    AS avg_resolution_minutes,
                AVG(conv.sentiment_score) AS avg_sentiment
            FROM tickets t
            JOIN conversations conv ON t.conversation_id = conv.id
            WHERE t.created_at >= NOW() - INTERVAL '24 hours'
            """
        )
        return dict(row) if row else {}


async def get_sentiment_trends(days: int = 7) -> list[dict]:
    """Get daily average sentiment scores."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                DATE_TRUNC('day', c.started_at)::DATE AS date,
                c.initial_channel AS channel,
                AVG(c.sentiment_score) AS avg_sentiment,
                COUNT(*) AS conversation_count
            FROM conversations c
            WHERE c.started_at >= NOW() - INTERVAL '$1 days'
            GROUP BY DATE_TRUNC('day', c.started_at), c.initial_channel
            ORDER BY date ASC
            """,
            days,
        )
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# DEMO DATA SEED
# ---------------------------------------------------------------------------
async def seed_demo_data() -> dict:
    """
    Seed the database with realistic demo data.
    Called by POST /admin/seed endpoint.
    """
    created = {
        "customers": [],
        "tickets": [],
        "messages": [],
        "knowledge_base": [],
    }

    # Sample customers with Pakistani names
    sample_customers = [
        {"name": "Ahmed Khan", "email": "ahmed.khan@example.com", "phone": "+92-300-1234567"},
        {"name": "Fatima Malik", "email": "fatima.malik@techstartup.pk", "phone": "+92-321-7654321"},
        {"name": "Usman Raza", "email": "usman.raza@corporation.com", "phone": "+92-333-9876543"},
        {"name": "Ayesha Siddiqui", "email": "ayesha.s@gmail.com", "phone": "+92-311-2345678"},
        {"name": "Bilal Hassan", "email": "bilal.hassan@enterprise.pk", "phone": "+92-345-8765432"},
    ]

    async with get_pool().acquire() as conn:
        for c in sample_customers:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO customers (id, name, email, phone, metadata)
                    VALUES (uuid_generate_v4(), $1, $2, $3, $4)
                    ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
                    RETURNING *
                    """,
                    c["name"],
                    c["email"],
                    c["phone"],
                    {"source": "seed"},
                )
                created["customers"].append(str(row["id"]))

                # Add identifiers
                await conn.execute(
                    """
                    INSERT INTO customer_identifiers (id, customer_id, identifier_type, identifier_value)
                    VALUES (uuid_generate_v4(), $1, 'email', $2)
                    ON CONFLICT DO NOTHING
                    """,
                    row["id"],
                    c["email"],
                )
                await conn.execute(
                    """
                    INSERT INTO customer_identifiers (id, customer_id, identifier_type, identifier_value)
                    VALUES (uuid_generate_v4(), $1, 'phone', $2)
                    ON CONFLICT DO NOTHING
                    """,
                    row["id"],
                    c["phone"],
                )
            except Exception as e:
                logger.warning(f"Seed customer error: {e}")

        # Sample tickets across channels
        channels = ["email", "whatsapp", "web_form"]
        categories = ["technical", "billing", "general", "bug_report", "feedback"]
        statuses = ["open", "processing", "resolved", "escalated"]
        priorities = ["low", "medium", "high", "urgent"]

        ticket_scenarios = [
            ("Can't reset my password", "technical", "high", "resolved"),
            ("Need help with team invitations", "general", "medium", "resolved"),
            ("Gantt chart not showing tasks", "bug_report", "high", "open"),
            ("Billing question about subscription", "billing", "medium", "escalated"),
            ("API returning 401 errors", "technical", "urgent", "processing"),
            ("How to export project data?", "general", "low", "resolved"),
            ("Mobile app sync issues", "technical", "medium", "open"),
            ("Request for discount", "billing", "medium", "escalated"),
            ("Feature request: dark mode", "feedback", "low", "resolved"),
            ("Cannot access account", "technical", "urgent", "processing"),
        ]

        for i, (subject, category, priority, status) in enumerate(ticket_scenarios):
            customer_id = uuid.UUID(created["customers"][i % len(created["customers"])])
            channel = channels[i % len(channels)]

            try:
                # Create conversation
                conv_row = await conn.fetchrow(
                    """
                    INSERT INTO conversations (id, customer_id, initial_channel, status, sentiment_score)
                    VALUES (uuid_generate_v4(), $1, $2, $3, $4)
                    RETURNING *
                    """,
                    customer_id,
                    channel,
                    "resolved" if status == "resolved" else "active",
                    0.7 if status not in ("escalated",) else 0.2,
                )

                # Create ticket
                ticket_row = await conn.fetchrow(
                    """
                    INSERT INTO tickets (
                        id, conversation_id, customer_id, source_channel,
                        category, priority, status, subject, metadata
                    )
                    VALUES (uuid_generate_v4(), $1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING *
                    """,
                    conv_row["id"],
                    customer_id,
                    channel,
                    category,
                    priority,
                    status,
                    subject,
                    {"seeded": True},
                )
                created["tickets"].append(str(ticket_row["id"]))

                # Sample messages
                sample_messages = [
                    ("inbound", "customer", f"Hi, I need help with: {subject}"),
                    ("outbound", "agent", f"Hello! I'd be happy to help you with that. I've created ticket #{str(ticket_row['id'])[:8]} for your request. Let me look into this for you."),
                    ("inbound", "customer", "Thank you, please resolve this quickly."),
                    ("outbound", "agent", "I understand the urgency. I'm working on it right now and will update you shortly." if status != "resolved" else "Great news! I've resolved this issue. Please let me know if you need anything else. — TechCorp AI Support Team"),
                ]

                for direction, role, content in sample_messages:
                    await conn.execute(
                        """
                        INSERT INTO messages (
                            id, conversation_id, channel, direction, role,
                            content, delivery_status
                        )
                        VALUES (uuid_generate_v4(), $1, $2, $3, $4, $5, 'delivered')
                        """,
                        conv_row["id"],
                        channel,
                        direction,
                        role,
                        content,
                    )
                    created["messages"].append("ok")

            except Exception as e:
                logger.warning(f"Seed ticket error: {e}")

        # Knowledge base entries
        kb_entries = [
            ("How to reset password", "Visit login page → Forgot Password → enter email → check inbox for reset link. Link valid for 1 hour.", "account"),
            ("Team member invitation", "Go to Settings → Team Members → Invite → enter email addresses → click Send Invitations.", "team"),
            ("API authentication", "Use OAuth2 bearer tokens. Include in header: Authorization: Bearer YOUR_TOKEN. Tokens expire after 1 hour.", "api"),
            ("Export project data", "Go to Project → Export → choose CSV, Excel, or PDF format. For full workspace export: Settings → Export Workspace.", "data"),
            ("Gantt chart setup", "Tasks need both start date AND due date to appear in Gantt view. Tasks with only due date appear as milestones.", "tasks"),
            ("Mobile app offline mode", "TaskFlow Pro supports offline mode. Changes sync automatically when you reconnect to internet.", "mobile"),
            ("2FA setup", "Go to Profile → Security → Enable 2FA. Supports Google Authenticator, Authy, and SMS.", "security"),
            ("SSO configuration", "SSO available on Business/Enterprise plans. Supports Google Workspace, Azure AD, Okta. Configure at Settings → Security → SSO.", "security"),
            ("Recurring tasks", "In task settings → Recurrence → choose Daily/Weekly/Monthly/Custom. Next occurrence auto-created on completion.", "tasks"),
            ("Custom fields", "Create custom fields at Project Settings → Custom Fields. Types: text, number, date, dropdown, checkbox, URL.", "tasks"),
        ]

        for title, content, category in kb_entries:
            try:
                await conn.execute(
                    """
                    INSERT INTO knowledge_base (id, title, content, category)
                    VALUES (uuid_generate_v4(), $1, $2, $3)
                    ON CONFLICT DO NOTHING
                    """,
                    title,
                    content,
                    category,
                )
                created["knowledge_base"].append(title)
            except Exception as e:
                logger.warning(f"Seed KB error: {e}")

    return created

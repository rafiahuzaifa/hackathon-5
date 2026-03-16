"""
TechCorp FTE — AI Agent Tools
All tools available to the Customer Success agent.
LIVE MODE: Real database + API calls.
DEMO MODE: Mock data returned without external dependencies.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input Models (Pydantic)
# ---------------------------------------------------------------------------

class SearchKBInput(BaseModel):
    """Input for knowledge base search."""
    query: str = Field(..., description="Search query text")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum results to return")
    category: Optional[str] = Field(default=None, description="Filter by category: account, team, api, data, tasks, mobile, security, billing")


class CreateTicketInput(BaseModel):
    """Input for creating a support ticket."""
    customer_id: str = Field(..., description="UUID of the customer")
    issue: str = Field(..., description="Description of the issue")
    priority: str = Field(default="medium", description="Priority: low, medium, high, urgent")
    channel: str = Field(..., description="Channel: email, whatsapp, web_form")
    category: str = Field(default="general", description="Category: general, technical, billing, bug_report, feedback")
    subject: Optional[str] = Field(default=None, description="Short subject line for the ticket")


class GetCustomerHistoryInput(BaseModel):
    """Input for retrieving customer conversation history."""
    customer_id: str = Field(..., description="UUID of the customer")
    limit: int = Field(default=5, ge=1, le=20, description="Number of recent conversations")


class EscalateInput(BaseModel):
    """Input for escalating to a human agent."""
    ticket_id: str = Field(..., description="UUID of the ticket to escalate")
    reason: str = Field(..., description="Reason for escalation")
    urgency: str = Field(default="medium", description="Urgency: low, medium, high, critical")


class SendResponseInput(BaseModel):
    """Input for sending a response to the customer."""
    ticket_id: str = Field(..., description="UUID of the ticket")
    message: str = Field(..., description="The message to send to the customer")
    channel: str = Field(..., description="Channel to send via: email, whatsapp, web_form")


class AnalyzeSentimentInput(BaseModel):
    """Input for sentiment analysis."""
    message_text: str = Field(..., description="Customer message text to analyze")


# ---------------------------------------------------------------------------
# DEMO MODE MOCK DATA
# ---------------------------------------------------------------------------

MOCK_KB_RESULTS = {
    "password": [
        {
            "id": str(uuid.uuid4()),
            "title": "How to Reset Your Password",
            "content": "On the login page, click 'Forgot Password.' Enter your registered email. You'll receive a reset link within 2 minutes. The link expires after 1 hour. Check spam if not received.",
            "category": "account",
            "similarity": 0.95,
        }
    ],
    "team": [
        {
            "id": str(uuid.uuid4()),
            "title": "Inviting Team Members",
            "content": "Go to Settings → Team Members → Invite. Enter email addresses (comma-separated for bulk). They'll receive an invitation link valid for 7 days. Assign roles: Admin, Manager, Member, or Viewer.",
            "category": "team",
            "similarity": 0.92,
        }
    ],
    "billing": [
        {
            "id": str(uuid.uuid4()),
            "title": "Billing and Subscription",
            "content": "For billing inquiries, contact billing@techcorp.pk with your account email and invoice number. For plan changes, contact sales@techcorp.pk. We do not discuss pricing in support channels.",
            "category": "billing",
            "similarity": 0.88,
        }
    ],
    "api": [
        {
            "id": str(uuid.uuid4()),
            "title": "API Authentication",
            "content": "Use OAuth2 bearer tokens. Include Authorization: Bearer YOUR_TOKEN in headers. Tokens expire after 1 hour — use refresh token to get new ones. Rate limits: 1,000 req/hour (Pro), 10,000 (Business).",
            "category": "api",
            "similarity": 0.91,
        }
    ],
    "login": [
        {
            "id": str(uuid.uuid4()),
            "title": "Login Issues and Account Access",
            "content": "Accounts lock after 5 failed attempts for 30 minutes. Use password reset flow, or wait 30 minutes. For SSO issues, contact your IT admin. Enable 2FA at Profile → Security.",
            "category": "account",
            "similarity": 0.89,
        }
    ],
    "default": [
        {
            "id": str(uuid.uuid4()),
            "title": "TaskFlow Pro General Help",
            "content": "TaskFlow Pro is a project management platform. Key features: Task Management, Team Collaboration, Gantt Charts, Time Tracking, Integrations (Slack, GitHub, Jira). For specific issues, please describe your problem in detail.",
            "category": "general",
            "similarity": 0.75,
        }
    ],
}

MOCK_CUSTOMER_HISTORY = {
    "conversations": [
        {
            "id": str(uuid.uuid4()),
            "channel": "email",
            "status": "resolved",
            "started_at": "2025-01-10T14:00:00Z",
            "summary": "Password reset assistance — resolved successfully",
            "sentiment_score": 0.8,
        },
        {
            "id": str(uuid.uuid4()),
            "channel": "web_form",
            "status": "resolved",
            "started_at": "2025-01-05T09:30:00Z",
            "summary": "Team member invitation help — resolved",
            "sentiment_score": 0.75,
        },
    ],
    "total_conversations": 2,
    "avg_sentiment": 0.775,
    "channels_used": ["email", "web_form"],
    "last_contact": "2025-01-10T14:00:00Z",
}


# ---------------------------------------------------------------------------
# TOOL FUNCTIONS
# ---------------------------------------------------------------------------

async def search_knowledge_base(
    query: str,
    max_results: int = 5,
    category: Optional[str] = None,
    dry_run: bool = True,
) -> dict:
    """
    Search the knowledge base for relevant documentation.
    LIVE: Vector similarity search in PostgreSQL.
    DEMO: Returns mock product documentation results.
    """
    logger.info(f"[Tool:search_kb] query='{query}', category={category}, dry_run={dry_run}")

    if dry_run:
        # Find best mock match based on keywords
        query_lower = query.lower()
        results = None
        for keyword, mock_results in MOCK_KB_RESULTS.items():
            if keyword in query_lower:
                results = mock_results
                break
        if not results:
            results = MOCK_KB_RESULTS["default"]

        return {
            "results": results[:max_results],
            "total": len(results[:max_results]),
            "query": query,
            "mode": "demo",
        }

    try:
        from backend.database.queries import (
            fulltext_search_knowledge_base,
            search_knowledge_base as db_search,
        )
        from backend.config import config

        # Try vector search first
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            # Use a simple embedding — in production use text-embedding-3-small
            # For now, fall back to full-text search
            raise NotImplementedError("Use full-text search")
        except Exception:
            # Fallback to full-text search
            results = await fulltext_search_knowledge_base(query, max_results, category)

        return {
            "results": results[:max_results],
            "total": len(results),
            "query": query,
            "mode": "live",
        }
    except Exception as e:
        logger.error(f"[Tool:search_kb] Error: {e}")
        return {
            "results": [],
            "total": 0,
            "query": query,
            "error": str(e),
            "mode": "live",
        }


async def create_ticket(
    customer_id: str,
    issue: str,
    priority: str,
    channel: str,
    category: str = "general",
    subject: Optional[str] = None,
    dry_run: bool = True,
    conversation_id: Optional[str] = None,
) -> dict:
    """
    Create a support ticket in the system.
    LIVE: Insert into PostgreSQL tickets table.
    DEMO: Return fake UUID ticket ID.
    """
    logger.info(f"[Tool:create_ticket] customer={customer_id}, channel={channel}, priority={priority}")

    if dry_run:
        fake_ticket_id = str(uuid.uuid4())
        fake_conversation_id = conversation_id or str(uuid.uuid4())
        logger.info(f"[DEMO] Created fake ticket: {fake_ticket_id}")
        return {
            "ticket_id": fake_ticket_id,
            "conversation_id": fake_conversation_id,
            "status": "open",
            "priority": priority,
            "category": category,
            "channel": channel,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": "demo",
            "message": f"[DEMO] Ticket created successfully: {fake_ticket_id[:8]}",
        }

    try:
        from backend.database import queries

        if not conversation_id:
            conv = await queries.create_conversation(customer_id, channel)
            conversation_id = str(conv["id"])

        ticket = await queries.create_ticket(
            conversation_id=conversation_id,
            customer_id=customer_id,
            source_channel=channel,
            category=category,
            priority=priority,
            subject=subject or issue[:100],
        )

        return {
            "ticket_id": str(ticket["id"]),
            "conversation_id": conversation_id,
            "status": ticket["status"],
            "priority": ticket["priority"],
            "category": ticket["category"],
            "channel": channel,
            "created_at": ticket["created_at"].isoformat(),
            "mode": "live",
        }
    except Exception as e:
        logger.error(f"[Tool:create_ticket] Error: {e}")
        return {
            "ticket_id": str(uuid.uuid4()),
            "error": str(e),
            "mode": "live_fallback",
        }


async def get_customer_history(
    customer_id: str,
    limit: int = 5,
    dry_run: bool = True,
) -> dict:
    """
    Retrieve customer's conversation history across all channels.
    LIVE: Query conversations + messages from PostgreSQL.
    DEMO: Return mock history with 2-3 fake past conversations.
    """
    logger.info(f"[Tool:get_history] customer={customer_id}, dry_run={dry_run}")

    if dry_run:
        return {
            **MOCK_CUSTOMER_HISTORY,
            "customer_id": customer_id,
            "mode": "demo",
        }

    try:
        from backend.database import queries

        customer = await queries.get_customer_by_id(customer_id)
        if not customer:
            return {
                "customer_id": customer_id,
                "conversations": [],
                "total_conversations": 0,
                "error": "Customer not found",
                "mode": "live",
            }

        conversations = await queries.get_customer_conversations(customer_id, limit)
        channels_used = list({c["initial_channel"] for c in conversations})

        sentiments = [
            float(c["sentiment_score"])
            for c in conversations
            if c.get("sentiment_score") is not None
        ]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.5

        last_contact = (
            max(c["started_at"] for c in conversations).isoformat()
            if conversations
            else None
        )

        return {
            "customer_id": customer_id,
            "customer_name": customer.get("name"),
            "conversations": [
                {
                    "id": str(c["id"]),
                    "channel": c["initial_channel"],
                    "status": c["status"],
                    "started_at": c["started_at"].isoformat(),
                    "sentiment_score": float(c["sentiment_score"] or 0.5),
                    "message_count": c.get("message_count", 0),
                }
                for c in conversations
            ],
            "total_conversations": len(conversations),
            "avg_sentiment": avg_sentiment,
            "channels_used": channels_used,
            "last_contact": last_contact,
            "mode": "live",
        }
    except Exception as e:
        logger.error(f"[Tool:get_history] Error: {e}")
        return {
            "customer_id": customer_id,
            "conversations": [],
            "total_conversations": 0,
            "error": str(e),
            "mode": "live_fallback",
        }


async def escalate_to_human(
    ticket_id: str,
    reason: str,
    urgency: str = "medium",
    dry_run: bool = True,
) -> dict:
    """
    Escalate a ticket to human agent.
    LIVE: Update ticket status, publish to Kafka escalations topic.
    DEMO: Log escalation, return mock escalation ID.
    """
    escalation_id = str(uuid.uuid4())
    sla_times = {
        "critical": "15 minutes",
        "high": "1 hour",
        "medium": "4 hours",
        "low": "24 hours",
    }
    sla_time = sla_times.get(urgency, "4 hours")

    logger.info(
        f"[Tool:escalate] ticket={ticket_id}, reason='{reason}', urgency={urgency}"
    )

    if dry_run:
        logger.warning(
            f"[DEMO ESCALATION] Ticket {ticket_id[:8]} escalated: {reason} (urgency={urgency})"
        )
        return {
            "escalation_id": escalation_id,
            "ticket_id": ticket_id,
            "reason": reason,
            "urgency": urgency,
            "sla_time": sla_time,
            "status": "escalated",
            "mode": "demo",
            "message": f"[DEMO] Escalation logged. In live mode, ticket would be escalated to human agent.",
        }

    try:
        from backend.database import queries
        from backend.kafka_client import create_producer

        # Update ticket status
        await queries.update_ticket_status(ticket_id, "escalated")

        # Publish to Kafka escalations topic
        producer = create_producer(dry_run=False)
        await producer.start()
        await producer.publish_escalation(
            ticket_id=ticket_id,
            reason=reason,
            urgency=urgency,
            context={"escalation_id": escalation_id, "sla_time": sla_time},
        )
        await producer.stop()

        return {
            "escalation_id": escalation_id,
            "ticket_id": ticket_id,
            "reason": reason,
            "urgency": urgency,
            "sla_time": sla_time,
            "status": "escalated",
            "mode": "live",
        }
    except Exception as e:
        logger.error(f"[Tool:escalate] Error: {e}")
        return {
            "escalation_id": escalation_id,
            "ticket_id": ticket_id,
            "error": str(e),
            "mode": "live_fallback",
        }


async def send_response(
    ticket_id: str,
    message: str,
    channel: str,
    dry_run: bool = True,
    customer_contact: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> dict:
    """
    Send a response to the customer via the appropriate channel.
    LIVE: Call Gmail/Twilio/store based on channel.
    DEMO: Log response to console, return mock delivery status.
    """
    message_id = str(uuid.uuid4())

    logger.info(
        f"[Tool:send_response] ticket={ticket_id[:8]}, channel={channel}, "
        f"len={len(message)}"
    )

    if dry_run:
        logger.info(f"\n{'='*60}")
        logger.info(f"[DEMO] OUTBOUND MESSAGE via {channel.upper()}")
        logger.info(f"  Ticket: {ticket_id[:8]}")
        logger.info(f"  Contact: {customer_contact or 'N/A'}")
        logger.info(f"  Message:\n{message}")
        logger.info(f"{'='*60}\n")

        return {
            "message_id": message_id,
            "ticket_id": ticket_id,
            "channel": channel,
            "delivery_status": "sent",
            "recipient": customer_contact or "demo@example.com",
            "mode": "demo",
            "message": f"[DEMO] Response logged to console. In live mode, would send via {channel}.",
        }

    try:
        from backend.database import queries
        from backend.channels.gmail_handler import GmailHandler
        from backend.channels.whatsapp_handler import WhatsAppHandler

        delivery_status = "sent"
        channel_message_id = None

        if channel == "email" and customer_contact:
            handler = GmailHandler(dry_run=False)
            result = await handler.send_reply(
                to=customer_contact,
                subject=f"Re: Your Support Ticket #{ticket_id[:8]}",
                body=message,
                thread_id=None,
            )
            channel_message_id = result.get("message_id")
            delivery_status = "delivered" if result.get("success") else "failed"

        elif channel == "whatsapp" and customer_contact:
            handler = WhatsAppHandler(dry_run=False)
            result = await handler.send_message(
                to_phone=customer_contact,
                body=message,
            )
            channel_message_id = result.get("sid")
            delivery_status = "sent" if result.get("success") else "failed"

        # Store message in DB
        if conversation_id:
            stored = await queries.store_message(
                conversation_id=conversation_id,
                channel=channel,
                direction="outbound",
                role="agent",
                content=message,
                channel_message_id=channel_message_id,
                delivery_status=delivery_status,
            )
            message_id = str(stored["id"])

        return {
            "message_id": message_id,
            "ticket_id": ticket_id,
            "channel": channel,
            "delivery_status": delivery_status,
            "channel_message_id": channel_message_id,
            "mode": "live",
        }
    except Exception as e:
        logger.error(f"[Tool:send_response] Error: {e}")
        return {
            "message_id": message_id,
            "ticket_id": ticket_id,
            "channel": channel,
            "delivery_status": "failed",
            "error": str(e),
            "mode": "live_fallback",
        }


async def analyze_sentiment(
    message_text: str,
    dry_run: bool = True,
) -> dict:
    """
    Analyze sentiment of customer message using Claude.
    Both modes call Claude for accurate sentiment analysis.
    Returns score 0.0 (very negative) to 1.0 (very positive).
    """
    logger.info(f"[Tool:sentiment] Analyzing: '{message_text[:100]}...'")

    try:
        import anthropic
        from backend.config import config
        from backend.agent.prompts import SENTIMENT_ANALYSIS_PROMPT

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": SENTIMENT_ANALYSIS_PROMPT.format(message=message_text),
                }
            ],
        )

        response_text = response.content[0].text.strip()

        # Clean up JSON if wrapped in code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)

        logger.info(
            f"[Tool:sentiment] Score={result.get('score')}, "
            f"Label={result.get('label')}, "
            f"Escalate={result.get('escalation_recommended')}"
        )

        return {
            **result,
            "mode": "demo" if dry_run else "live",
        }

    except Exception as e:
        logger.error(f"[Tool:sentiment] Error: {e}")
        # Fallback: simple keyword-based sentiment
        text_lower = message_text.lower()
        negative_words = ["angry", "frustrated", "terrible", "worst", "hate", "awful", "broken", "useless"]
        positive_words = ["thanks", "great", "excellent", "wonderful", "love", "perfect", "helpful"]

        negative_count = sum(1 for w in negative_words if w in text_lower)
        positive_count = sum(1 for w in positive_words if w in text_lower)

        if negative_count > positive_count:
            score = max(0.2, 0.4 - negative_count * 0.1)
            label = "negative"
        elif positive_count > negative_count:
            score = min(0.9, 0.6 + positive_count * 0.1)
            label = "positive"
        else:
            score = 0.5
            label = "neutral"

        return {
            "score": score,
            "label": label,
            "confidence": 0.6,
            "detected_emotions": ["unknown"],
            "escalation_recommended": score < 0.3,
            "error": str(e),
            "mode": "fallback",
        }

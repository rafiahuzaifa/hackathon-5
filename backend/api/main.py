"""
TechCorp Customer Success Digital FTE — FastAPI Backend
Complete REST API with all endpoints for support, webhooks, metrics, and admin.
"""

import logging
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from backend.config import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting (simple in-memory token bucket)
# ---------------------------------------------------------------------------
_request_counts: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(client_ip: str) -> bool:
    """Simple sliding window rate limiter."""
    now = time.time()
    window = config.RATE_LIMIT_WINDOW_SECONDS
    max_req = config.RATE_LIMIT_MAX_REQUESTS

    # Clean old entries
    _request_counts[client_ip] = [
        t for t in _request_counts[client_ip] if now - t < window
    ]

    if len(_request_counts[client_ip]) >= max_req:
        return False

    _request_counts[client_ip].append(now)
    return True


# ---------------------------------------------------------------------------
# Lifespan (startup/shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize and cleanup resources."""
    # Startup
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )
    config.log_startup()

    if config.is_live:
        try:
            from backend.database import queries
            await queries.init_pool(
                config.DATABASE_URL,
                min_size=config.DB_POOL_MIN_SIZE,
                max_size=config.DB_POOL_MAX_SIZE,
            )
            logger.info("[API] Database pool initialized")
        except Exception as e:
            logger.warning(f"[API] Database init failed (continuing): {e}")

    yield

    # Shutdown
    if config.is_live:
        try:
            from backend.database import queries
            await queries.close_pool()
        except Exception:
            pass
    logger.info("[API] Shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TechCorp Customer Success FTE API",
    description="AI-powered customer support system for TechCorp TaskFlow Pro",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({duration_ms}ms) "
        f"[{request.client.host if request.client else 'unknown'}]"
    )
    return response


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------
class SupportFormRequest(BaseModel):
    """Support form submission from web channel."""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    subject: str = Field(..., min_length=5, max_length=500)
    category: str = Field(default="general")
    priority: str = Field(default="medium")
    message: str = Field(..., min_length=10, max_length=5000)


class SupportFormResponse(BaseModel):
    """Response after support form submission."""
    ticket_id: str
    conversation_id: str
    status: str
    channel: str
    estimated_response: str
    message: str
    mode: str


class TicketStatusResponse(BaseModel):
    """Ticket status with conversation history."""
    ticket_id: str
    status: str
    priority: str
    category: str
    channel: str
    subject: Optional[str]
    created_at: str
    updated_at: Optional[str]
    customer_name: Optional[str]
    messages: list[dict]
    mode: str


class AdminModeRequest(BaseModel):
    """Request to switch between demo/live mode."""
    dry_run: bool


# ---------------------------------------------------------------------------
# DEPENDENCY: get IP for rate limiting
# ---------------------------------------------------------------------------
def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# HEALTH ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """System health status with mode indicator."""
    db_status = "unknown"
    if config.is_live:
        try:
            from backend.database import queries
            pool = queries.get_pool()
            db_status = "connected" if pool else "disconnected"
        except Exception:
            db_status = "error"
    else:
        db_status = "demo"

    return {
        "status": "healthy",
        "mode": config.mode_label,
        "dry_run": config.DRY_RUN,
        "version": config.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": db_status,
            "kafka": "demo" if config.is_demo else "live",
            "anthropic": "configured" if config.anthropic_configured else "missing",
        },
    }


@app.get("/health/channels", tags=["Health"])
async def channel_health() -> dict:
    """Status of each integration channel."""
    from backend.channels.gmail_handler import GmailHandler
    from backend.channels.whatsapp_handler import WhatsAppHandler

    gmail_status = GmailHandler(dry_run=config.is_demo).get_status()
    wa_status = WhatsAppHandler(dry_run=config.is_demo).get_status()

    return {
        "email": gmail_status,
        "whatsapp": wa_status,
        "web_form": {"status": "active", "connected": True, "mode": config.mode_label},
        "mode": config.mode_label,
    }


# ---------------------------------------------------------------------------
# SUPPORT FORM ENDPOINTS
# ---------------------------------------------------------------------------
@app.post("/support/submit", response_model=SupportFormResponse, tags=["Support"])
async def submit_support_form(
    form: SupportFormRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> SupportFormResponse:
    """
    Submit a support request via web form.
    Creates ticket, runs AI agent, returns ticket ID.
    """
    client_ip = get_client_ip(request)

    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
        )

    # Validate category and priority
    valid_categories = {"general", "technical", "billing", "bug_report", "feedback"}
    valid_priorities = {"low", "medium", "high", "urgent"}

    category = form.category if form.category in valid_categories else "general"
    priority = form.priority if form.priority in valid_priorities else "medium"

    logger.info(
        f"[API] Support form from {form.email}: '{form.subject[:50]}' "
        f"[{category}/{priority}]"
    )

    # DEMO mode: process synchronously with mock data
    if config.is_demo:
        ticket_id = str(uuid.uuid4())
        conversation_id = str(uuid.uuid4())

        # Run AI agent in background
        background_tasks.add_task(
            _process_webform_with_agent,
            form=form,
            ticket_id=ticket_id,
            conversation_id=conversation_id,
            category=category,
            priority=priority,
        )

        return SupportFormResponse(
            ticket_id=ticket_id,
            conversation_id=conversation_id,
            status="processing",
            channel="web_form",
            estimated_response="< 1 minute (AI) • 4 hours (Human)",
            message=f"Ticket #{ticket_id[:8]} created. Our AI is processing your request.",
            mode="demo",
        )

    # LIVE mode: full DB + Kafka flow
    try:
        from backend.database import queries
        from backend.kafka_client import create_producer

        # Get or create customer
        customer = await queries.get_customer_by_identifier("email", form.email)
        if not customer:
            customer = await queries.create_customer(
                name=form.name, email=form.email
            )
            await queries.upsert_customer_identifier(
                str(customer["id"]), "email", form.email
            )

        # Create conversation
        conv = await queries.create_conversation(
            customer_id=str(customer["id"]),
            initial_channel="web_form",
        )

        # Create ticket
        ticket = await queries.create_ticket(
            conversation_id=str(conv["id"]),
            customer_id=str(customer["id"]),
            source_channel="web_form",
            category=category,
            priority=priority,
            subject=form.subject,
        )

        # Store inbound message
        await queries.store_message(
            conversation_id=str(conv["id"]),
            channel="web_form",
            direction="inbound",
            role="customer",
            content=form.message,
            delivery_status="delivered",
        )

        # Publish to Kafka for processing
        producer = create_producer(dry_run=False)
        await producer.start()
        await producer.publish_channel_message(
            "web_form",
            {
                "id": str(ticket["id"]),
                "customer_id": str(customer["id"]),
                "customer_name": form.name,
                "sender_email": form.email,
                "conversation_id": str(conv["id"]),
                "body": form.message,
                "subject": form.subject,
                "category": category,
                "priority": priority,
                "channel": "web_form",
            },
        )
        await producer.stop()

        return SupportFormResponse(
            ticket_id=str(ticket["id"]),
            conversation_id=str(conv["id"]),
            status="processing",
            channel="web_form",
            estimated_response="< 1 minute (AI) • 4 hours (Human)",
            message=f"Ticket #{str(ticket['id'])[:8]} created successfully.",
            mode="live",
        )

    except Exception as e:
        logger.error(f"[API] Support form error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _process_webform_with_agent(
    form: SupportFormRequest,
    ticket_id: str,
    conversation_id: str,
    category: str,
    priority: str,
) -> None:
    """Background task to process web form with AI agent."""
    try:
        from backend.agent.customer_success_agent import (
            CustomerSuccessAgent,
            IncomingMessage,
        )

        agent = CustomerSuccessAgent()
        incoming = IncomingMessage(
            content=f"Subject: {form.subject}\n\n{form.message}",
            channel="web_form",
            customer_id=str(uuid.uuid4()),
            customer_name=form.name,
            customer_contact=form.email,
            conversation_id=conversation_id,
            ticket_id=ticket_id,
        )
        await agent.process(incoming)
    except Exception as e:
        logger.error(f"[API] Background agent processing failed: {e}")


@app.get("/support/ticket/{ticket_id}", tags=["Support"])
async def get_ticket_status(ticket_id: str) -> dict:
    """Get ticket status and conversation messages."""
    if config.is_demo:
        # Return mock ticket data
        return {
            "ticket_id": ticket_id,
            "status": "processing",
            "priority": "medium",
            "category": "technical",
            "channel": "web_form",
            "subject": "Demo Support Request",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "customer_name": "Demo User",
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "role": "customer",
                    "direction": "inbound",
                    "content": "I need help with my account.",
                    "channel": "web_form",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "delivery_status": "delivered",
                },
                {
                    "id": str(uuid.uuid4()),
                    "role": "agent",
                    "direction": "outbound",
                    "content": "Hi! I'd be happy to help. I've created ticket #{} for your request. Let me look into this for you.\n\n— TechCorp AI Support Team".format(ticket_id[:8]),
                    "channel": "web_form",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "delivery_status": "delivered",
                },
            ],
            "mode": "demo",
        }

    try:
        from backend.database import queries
        ticket = await queries.get_ticket_with_messages(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Serialize datetimes
        def serialize(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        return {
            "ticket_id": str(ticket["id"]),
            "status": ticket["status"],
            "priority": ticket["priority"],
            "category": ticket["category"],
            "channel": ticket["source_channel"],
            "subject": ticket.get("subject"),
            "created_at": serialize(ticket["created_at"]),
            "updated_at": serialize(ticket.get("updated_at")),
            "customer_name": None,
            "messages": [
                {
                    "id": str(m["id"]),
                    "role": m["role"],
                    "direction": m["direction"],
                    "content": m["content"],
                    "channel": m["channel"],
                    "created_at": serialize(m["created_at"]),
                    "delivery_status": m["delivery_status"],
                }
                for m in ticket.get("messages", [])
            ],
            "mode": "live",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Get ticket error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/support/tickets", tags=["Support"])
async def list_tickets(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List all support tickets with optional filters."""
    if config.is_demo:
        mock_tickets = [
            {
                "ticket_id": str(uuid.uuid4()),
                "subject": f"Demo Ticket {i+1}",
                "status": ["open", "processing", "resolved", "escalated"][i % 4],
                "priority": ["low", "medium", "high", "urgent"][i % 4],
                "category": ["technical", "billing", "general", "bug_report"][i % 4],
                "channel": ["email", "whatsapp", "web_form"][i % 3],
                "customer_name": ["Ahmed Khan", "Fatima Malik", "Usman Raza"][i % 3],
                "customer_email": f"customer{i+1}@example.com",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(10)
        ]
        return {
            "tickets": mock_tickets,
            "total": len(mock_tickets),
            "limit": limit,
            "offset": offset,
            "mode": "demo",
        }

    try:
        from backend.database import queries
        tickets = await queries.list_tickets(status, channel, limit, offset)
        return {
            "tickets": [
                {
                    "ticket_id": str(t["id"]),
                    "subject": t.get("subject"),
                    "status": t["status"],
                    "priority": t["priority"],
                    "category": t["category"],
                    "channel": t["source_channel"],
                    "customer_name": t.get("customer_name"),
                    "customer_email": t.get("customer_email"),
                    "created_at": t["created_at"].isoformat(),
                }
                for t in tickets
            ],
            "total": len(tickets),
            "limit": limit,
            "offset": offset,
            "mode": "live",
        }
    except Exception as e:
        logger.error(f"[API] List tickets error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# WEBHOOK ENDPOINTS
# ---------------------------------------------------------------------------
@app.post("/webhooks/gmail", tags=["Webhooks"])
async def gmail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """
    Gmail Pub/Sub push notification endpoint.
    Triggered when new emails arrive in the support inbox.
    """
    try:
        body = await request.json()
        logger.info(f"[Webhook] Gmail notification received")

        background_tasks.add_task(_process_gmail_notification, body)

        return JSONResponse({"status": "accepted"}, status_code=200)
    except Exception as e:
        logger.error(f"[Webhook] Gmail error: {e}")
        return JSONResponse({"status": "error"}, status_code=500)


async def _process_gmail_notification(notification: dict) -> None:
    """Process Gmail Pub/Sub notification in background."""
    try:
        from backend.channels.gmail_handler import GmailHandler
        from backend.kafka_client import create_producer

        handler = GmailHandler(dry_run=config.is_demo)
        emails = await handler.get_new_emails()

        producer = create_producer(dry_run=config.is_demo)
        await producer.start()

        for email in emails:
            await producer.publish_channel_message("email", {
                **email,
                "channel": "email",
            })

        await producer.stop()
    except Exception as e:
        logger.error(f"[Webhook] Gmail processing error: {e}")


@app.post("/webhooks/whatsapp", tags=["Webhooks"])
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    """
    Twilio WhatsApp incoming message webhook.
    Returns empty TwiML response (Twilio expects this).
    """
    try:
        form_data = dict(await request.form())
        logger.info(f"[Webhook] WhatsApp message received from {form_data.get('From', 'unknown')}")

        from backend.channels.whatsapp_handler import WhatsAppHandler

        handler = WhatsAppHandler(dry_run=config.is_demo)

        # Validate signature in LIVE mode
        if config.is_live:
            signature = request.headers.get("X-Twilio-Signature", "")
            is_valid = handler.validate_webhook(
                signature=signature,
                url=str(request.url),
                params=form_data,
            )
            if not is_valid:
                logger.warning("[Webhook] Invalid Twilio signature")
                return Response(status_code=403)

        message = handler.process_webhook(form_data)
        if message:
            background_tasks.add_task(_process_whatsapp_message, message)

        # Return empty TwiML
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
            status_code=200,
        )

    except Exception as e:
        logger.error(f"[Webhook] WhatsApp error: {e}")
        return Response(status_code=500)


async def _process_whatsapp_message(message: dict) -> None:
    """Process WhatsApp message in background."""
    try:
        from backend.kafka_client import create_producer

        producer = create_producer(dry_run=config.is_demo)
        await producer.start()
        await producer.publish_channel_message("whatsapp", message)
        await producer.stop()
    except Exception as e:
        logger.error(f"[Webhook] WhatsApp processing error: {e}")


@app.post("/webhooks/whatsapp/status", tags=["Webhooks"])
async def whatsapp_status_webhook(request: Request) -> JSONResponse:
    """Twilio delivery status callback."""
    try:
        form_data = dict(await request.form())
        from backend.channels.whatsapp_handler import WhatsAppHandler

        handler = WhatsAppHandler(dry_run=config.is_demo)
        status_update = handler.process_status_callback(form_data)

        if status_update and config.is_live:
            from backend.database import queries
            # Find message by channel_message_id and update status
            logger.info(
                f"[Webhook] WhatsApp delivery status: "
                f"sid={status_update.get('message_sid')}, "
                f"status={status_update.get('status')}"
            )

        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"[Webhook] Status callback error: {e}")
        return JSONResponse({"status": "error"}, status_code=500)


# ---------------------------------------------------------------------------
# CUSTOMER ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/customers/lookup", tags=["Customers"])
async def lookup_customer(
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> dict:
    """Find a customer by email or phone."""
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Provide email or phone")

    if config.is_demo:
        return {
            "customer": {
                "id": str(uuid.uuid4()),
                "name": "Demo Customer",
                "email": email or "demo@example.com",
                "phone": phone or "+92-300-0000000",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "mode": "demo",
        }

    try:
        from backend.database import queries

        customer = None
        if email:
            customer = await queries.get_customer_by_identifier("email", email)
        if not customer and phone:
            customer = await queries.get_customer_by_identifier("phone", phone)

        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        return {
            "customer": {
                "id": str(customer["id"]),
                "name": customer["name"],
                "email": customer.get("email"),
                "phone": customer.get("phone"),
                "created_at": customer["created_at"].isoformat(),
            },
            "mode": "live",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Customer lookup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/customers/{customer_id}/history", tags=["Customers"])
async def get_customer_history(customer_id: str) -> dict:
    """Get full cross-channel conversation history for a customer."""
    if config.is_demo:
        from backend.agent.tools import MOCK_CUSTOMER_HISTORY
        return {**MOCK_CUSTOMER_HISTORY, "customer_id": customer_id, "mode": "demo"}

    try:
        from backend.agent.tools import get_customer_history
        result = await get_customer_history(customer_id, limit=20, dry_run=False)
        return result
    except Exception as e:
        logger.error(f"[API] Customer history error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# METRICS & DASHBOARD ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/metrics/channels", tags=["Metrics"])
async def get_channel_metrics(days: int = 7) -> dict:
    """Per-channel statistics for the last N days."""
    if config.is_demo:
        return {
            "channels": [
                {
                    "channel": "email",
                    "total_tickets": 42,
                    "resolved": 35,
                    "escalated": 3,
                    "open": 4,
                    "avg_resolution_minutes": 8.5,
                },
                {
                    "channel": "whatsapp",
                    "total_tickets": 28,
                    "resolved": 22,
                    "escalated": 2,
                    "open": 4,
                    "avg_resolution_minutes": 3.2,
                },
                {
                    "channel": "web_form",
                    "total_tickets": 63,
                    "resolved": 55,
                    "escalated": 4,
                    "open": 4,
                    "avg_resolution_minutes": 6.7,
                },
            ],
            "days": days,
            "mode": "demo",
        }

    try:
        from backend.database import queries
        metrics = await queries.get_channel_metrics(days)
        return {"channels": metrics, "days": days, "mode": "live"}
    except Exception as e:
        logger.error(f"[API] Channel metrics error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/metrics/daily", tags=["Metrics"])
async def get_daily_stats() -> dict:
    """Today's summary statistics."""
    if config.is_demo:
        return {
            "total_tickets": 15,
            "resolved_tickets": 11,
            "escalated_tickets": 2,
            "open_tickets": 2,
            "avg_resolution_minutes": 6.2,
            "avg_sentiment": 0.72,
            "date": datetime.now(timezone.utc).date().isoformat(),
            "mode": "demo",
        }

    try:
        from backend.database import queries
        stats = await queries.get_daily_stats()
        stats["date"] = datetime.now(timezone.utc).date().isoformat()
        stats["mode"] = "live"
        return stats
    except Exception as e:
        logger.error(f"[API] Daily stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/metrics/sentiment", tags=["Metrics"])
async def get_sentiment_trends(days: int = 7) -> dict:
    """Sentiment score trends over time."""
    if config.is_demo:
        import random
        from datetime import timedelta

        today = datetime.now(timezone.utc).date()
        data = []
        for i in range(days, 0, -1):
            date = today - timedelta(days=i)
            for channel in ["email", "whatsapp", "web_form"]:
                data.append({
                    "date": date.isoformat(),
                    "channel": channel,
                    "avg_sentiment": round(0.6 + random.random() * 0.3, 3),
                    "conversation_count": random.randint(3, 15),
                })

        return {"data": data, "days": days, "mode": "demo"}

    try:
        from backend.database import queries
        data = await queries.get_sentiment_trends(days)
        return {"data": data, "days": days, "mode": "live"}
    except Exception as e:
        logger.error(f"[API] Sentiment trends error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# ADMIN ENDPOINTS
# ---------------------------------------------------------------------------
@app.post("/admin/mode", tags=["Admin"])
async def switch_mode(req: AdminModeRequest) -> dict:
    """
    Switch between DEMO and LIVE mode.
    Note: Changes only apply to the current process.
    """
    old_mode = config.mode_label
    config.DRY_RUN = req.dry_run
    new_mode = config.mode_label

    logger.warning(f"[Admin] Mode switched: {old_mode} → {new_mode}")

    return {
        "previous_mode": old_mode,
        "current_mode": new_mode,
        "dry_run": config.DRY_RUN,
        "message": f"Mode switched from {old_mode} to {new_mode}",
    }


@app.post("/admin/seed", tags=["Admin"])
async def seed_demo_data() -> dict:
    """Seed the database with demo data (customers, tickets, conversations)."""
    try:
        from backend.database import queries
        result = await queries.seed_demo_data()
        return {
            "status": "success",
            "created": result,
            "message": f"Seeded {len(result.get('customers', []))} customers, "
                       f"{len(result.get('tickets', []))} tickets",
        }
    except Exception as e:
        logger.error(f"[Admin] Seed error: {e}")
        # In demo mode with no DB, return mock success
        if config.is_demo:
            return {
                "status": "demo",
                "created": {"customers": 5, "tickets": 10, "messages": 40, "knowledge_base": 10},
                "message": "Demo mode: Data seeded (in-memory, no database required)",
            }
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/escalations", tags=["Admin"])
async def get_escalations() -> dict:
    """Get all escalated tickets pending human review."""
    if config.is_demo:
        return {
            "escalations": [
                {
                    "ticket_id": str(uuid.uuid4()),
                    "subject": "Billing dispute — needs human review",
                    "customer_name": "Ahmed Khan",
                    "customer_email": "ahmed.khan@example.com",
                    "channel": "email",
                    "priority": "high",
                    "reason": "Refund request",
                    "escalated_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "ticket_id": str(uuid.uuid4()),
                    "subject": "Legal threat in WhatsApp message",
                    "customer_name": "Usman Raza",
                    "customer_email": "usman.raza@corporation.com",
                    "channel": "whatsapp",
                    "priority": "urgent",
                    "reason": "Legal threat detected",
                    "escalated_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "total": 2,
            "mode": "demo",
        }

    try:
        from backend.database import queries
        escalations = await queries.get_escalated_tickets()
        return {
            "escalations": [
                {
                    "ticket_id": str(t["id"]),
                    "subject": t.get("subject"),
                    "customer_name": t.get("customer_name"),
                    "customer_email": t.get("customer_email"),
                    "channel": t["source_channel"],
                    "priority": t["priority"],
                    "escalated_at": t["created_at"].isoformat(),
                }
                for t in escalations
            ],
            "total": len(escalations),
            "mode": "live",
        }
    except Exception as e:
        logger.error(f"[Admin] Escalations error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# DIRECT AGENT TEST ENDPOINT (dev/demo use)
# ---------------------------------------------------------------------------
class AgentTestRequest(BaseModel):
    """Test the AI agent directly."""
    message: str
    channel: str = "web_form"
    customer_name: str = "Test User"
    customer_id: Optional[str] = None


@app.post("/agent/test", tags=["Agent"])
async def test_agent(req: AgentTestRequest) -> dict:
    """
    Directly invoke the AI agent with a test message.
    Useful for demos and testing.
    """
    try:
        from backend.agent.customer_success_agent import (
            CustomerSuccessAgent,
            IncomingMessage,
        )

        agent = CustomerSuccessAgent()
        incoming = IncomingMessage(
            content=req.message,
            channel=req.channel,
            customer_id=req.customer_id or str(uuid.uuid4()),
            customer_name=req.customer_name,
        )

        response = await agent.process(incoming)

        return {
            "response": response.message,
            "ticket_id": response.ticket_id,
            "channel": response.channel,
            "escalated": response.escalated,
            "sentiment_score": response.sentiment_score,
            "tokens_used": response.tokens_used,
            "latency_ms": response.latency_ms,
            "tool_calls_count": len(response.tool_calls),
            "mode": config.mode_label,
        }

    except Exception as e:
        logger.error(f"[Agent] Test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# App entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=config.LOG_LEVEL.lower(),
    )

"""
TechCorp FTE — Unified Message Processor
Consumes messages from all channels (Email, WhatsApp, Web Form) via Kafka,
runs the AI agent, and stores results in PostgreSQL.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.config import config
from backend.kafka_client import (
    ALL_TOPICS,
    FTEKafkaConsumer,
    FTEKafkaProducer,
    TOPIC_DLQ,
    TOPIC_METRICS,
    create_consumer,
    create_producer,
)
from backend.agent.customer_success_agent import CustomerSuccessAgent, IncomingMessage

logger = logging.getLogger(__name__)


class UnifiedMessageProcessor:
    """
    Unified processor for all incoming customer messages.
    Handles message routing, customer resolution, AI agent execution,
    and response delivery across Email, WhatsApp, and Web Form channels.
    """

    def __init__(self) -> None:
        self.agent = CustomerSuccessAgent()
        self.producer = create_producer(dry_run=config.DRY_RUN)
        self.consumer = create_consumer(
            topics=ALL_TOPICS,
            group_id=config.KAFKA_GROUP_ID,
            dry_run=config.DRY_RUN,
        )
        self._running = False
        self._processed_count = 0
        self._error_count = 0

    async def start(self) -> None:
        """Start the message processing loop."""
        logger.info(
            f"[Processor] Starting in {'DEMO' if config.is_demo else 'LIVE'} mode"
        )

        await self.producer.start()
        await self.consumer.start()

        self._running = True
        await self.consumer.consume(handler=self.process_message)

    async def stop(self) -> None:
        """Gracefully stop processing."""
        self._running = False
        await self.consumer.stop()
        await self.producer.stop()
        logger.info(
            f"[Processor] Stopped. Processed: {self._processed_count}, "
            f"Errors: {self._error_count}"
        )

    async def process_message(self, topic: str, message: dict) -> None:
        """
        Main message processing pipeline:
        1. Extract channel from message
        2. Resolve/create customer
        3. Get or create conversation
        4. Store inbound message
        5. Load conversation history
        6. Run AI agent
        7. Store agent response
        8. Publish metrics
        """
        start_time = time.time()
        message_id = message.get("event_id", str(uuid.uuid4()))

        logger.info(
            f"[Processor] Processing message from topic={topic}, id={message_id[:8]}"
        )

        try:
            # 1. Extract channel
            channel = self._extract_channel(topic, message)

            # 2. Resolve customer
            customer = await self.resolve_customer(message, channel)
            if not customer:
                logger.error(f"[Processor] Cannot resolve customer for {message_id}")
                await self._send_to_dlq(topic, message, "customer_resolution_failed")
                return

            customer_id = str(customer["id"])
            customer_name = customer.get("name", "Customer")
            customer_contact = customer.get("email") or customer.get("phone")

            # 3. Get or create conversation
            conversation_id = await self.get_or_create_conversation(
                customer_id=customer_id,
                channel=channel,
                message=message,
            )

            # 4. Store inbound message
            await self.store_message(
                conversation_id=conversation_id,
                channel=channel,
                direction="inbound",
                role="customer",
                content=message.get("body", message.get("content", "")),
                channel_message_id=message.get("id"),
            )

            # 5. Load conversation history
            history = await self.load_conversation_history(conversation_id)

            # 6. Build IncomingMessage for AI agent
            incoming = IncomingMessage(
                content=message.get("body", message.get("content", "")),
                channel=channel,
                customer_id=customer_id,
                customer_name=customer_name,
                customer_contact=customer_contact,
                conversation_id=conversation_id,
                history=history,
                metadata=message.get("metadata", {}),
            )

            # 7. Run AI agent
            agent_response = await self.agent.process(incoming)

            # 8. Store agent response
            await self.store_message(
                conversation_id=conversation_id,
                channel=channel,
                direction="outbound",
                role="agent",
                content=agent_response.message,
                tokens_used=agent_response.tokens_used,
                latency_ms=agent_response.latency_ms,
                tool_calls=agent_response.tool_calls,
            )

            # 9. Update conversation status
            if agent_response.escalated:
                await self.update_conversation_status(
                    conversation_id, "escalated", agent_response.sentiment_score
                )
            elif agent_response.sentiment_score is not None and agent_response.sentiment_score > 0.7:
                # High satisfaction — might resolve
                pass

            # 10. Publish metrics
            latency = int((time.time() - start_time) * 1000)
            await self.publish_metrics(
                channel=channel,
                latency_ms=latency,
                tokens_used=agent_response.tokens_used,
                escalated=agent_response.escalated,
                sentiment_score=agent_response.sentiment_score,
            )

            self._processed_count += 1
            logger.info(
                f"[Processor] Message processed — ticket={agent_response.ticket_id[:8]}, "
                f"latency={latency}ms"
            )

        except Exception as e:
            self._error_count += 1
            logger.error(f"[Processor] Fatal error processing {message_id}: {e}", exc_info=True)

            # Try to send apology to customer
            await self._handle_processing_error(message, topic, e)

            # Send to DLQ
            await self._send_to_dlq(topic, message, str(e))

    async def resolve_customer(self, message: dict, channel: str) -> Optional[dict]:
        """
        Find or create a customer based on message identifiers.
        Tries email first, then phone.
        Creates new customer if not found.
        """
        if config.is_demo:
            # Return mock customer for demo
            return {
                "id": message.get("customer_id", str(uuid.uuid4())),
                "name": message.get("sender_name", message.get("customer_name", "Demo Customer")),
                "email": message.get("sender_email", message.get("email", "demo@example.com")),
                "phone": message.get("from_number", message.get("phone")),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            from backend.database import queries

            # Try email lookup
            email = message.get("sender_email") or message.get("email")
            if email:
                customer = await queries.get_customer_by_identifier("email", email)
                if customer:
                    return customer

            # Try phone lookup
            phone = (
                message.get("from_number", "")
                .replace("whatsapp:", "")
                .strip()
            )
            if phone:
                customer = await queries.get_customer_by_identifier("phone", phone)
                if customer:
                    return customer

            # Create new customer
            name = (
                message.get("sender_name")
                or message.get("customer_name")
                or (email.split("@")[0] if email else "New Customer")
            )
            customer = await queries.create_customer(
                name=name,
                email=email,
                phone=phone or None,
            )

            # Store identifiers
            if email:
                await queries.upsert_customer_identifier(
                    str(customer["id"]), "email", email
                )
            if phone:
                await queries.upsert_customer_identifier(
                    str(customer["id"]), "phone", phone
                )
            if channel == "whatsapp" and message.get("from_number"):
                await queries.upsert_customer_identifier(
                    str(customer["id"]),
                    "whatsapp",
                    message["from_number"],
                )

            logger.info(f"[Processor] Created new customer: {customer['id']}")
            return customer

        except Exception as e:
            logger.error(f"[Processor] Customer resolution error: {e}")
            return None

    async def get_or_create_conversation(
        self,
        customer_id: str,
        channel: str,
        message: dict,
    ) -> str:
        """Find existing active conversation or create new one."""
        if config.is_demo:
            return message.get("conversation_id", str(uuid.uuid4()))

        try:
            from backend.database import queries

            # Check for existing active conversation
            existing = await queries.get_active_conversation(customer_id, channel)
            if existing:
                return str(existing["id"])

            # Create new conversation
            conv = await queries.create_conversation(
                customer_id=customer_id,
                initial_channel=channel,
                metadata={"source": "kafka", "message_id": message.get("id")},
            )
            return str(conv["id"])

        except Exception as e:
            logger.error(f"[Processor] Conversation error: {e}")
            return str(uuid.uuid4())

    async def store_message(
        self,
        conversation_id: str,
        channel: str,
        direction: str,
        role: str,
        content: str,
        tokens_used: int = 0,
        latency_ms: int = 0,
        tool_calls: Optional[list] = None,
        channel_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """Store a message in the database."""
        if config.is_demo:
            msg_id = str(uuid.uuid4())
            logger.debug(f"[DEMO] Stored message: {direction}/{role} ({len(content)} chars)")
            return msg_id

        try:
            from backend.database import queries

            stored = await queries.store_message(
                conversation_id=conversation_id,
                channel=channel,
                direction=direction,
                role=role,
                content=content,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                tool_calls=tool_calls,
                channel_message_id=channel_message_id,
                delivery_status="delivered" if direction == "inbound" else "sent",
            )
            return str(stored["id"])

        except Exception as e:
            logger.error(f"[Processor] Message store error: {e}")
            return None

    async def load_conversation_history(
        self, conversation_id: str, limit: int = 10
    ) -> list[dict]:
        """Load recent messages from a conversation."""
        if config.is_demo:
            return []

        try:
            from backend.database import queries
            messages = await queries.get_conversation_messages(conversation_id, limit)
            return [
                {
                    "role": m["role"],
                    "content": m["content"],
                    "direction": m["direction"],
                    "created_at": m["created_at"].isoformat(),
                }
                for m in messages
            ]
        except Exception as e:
            logger.error(f"[Processor] History load error: {e}")
            return []

    async def update_conversation_status(
        self,
        conversation_id: str,
        status: str,
        sentiment_score: Optional[float] = None,
    ) -> None:
        """Update conversation status in the database."""
        if config.is_demo:
            logger.debug(f"[DEMO] Conversation {conversation_id[:8]} → {status}")
            return

        try:
            from backend.database import queries
            await queries.update_conversation_status(
                conversation_id, status, sentiment_score
            )
        except Exception as e:
            logger.error(f"[Processor] Status update error: {e}")

    async def publish_metrics(
        self,
        channel: str,
        latency_ms: int,
        tokens_used: int,
        escalated: bool,
        sentiment_score: Optional[float],
    ) -> None:
        """Publish processing metrics to Kafka metrics topic."""
        try:
            await self.producer.publish(
                TOPIC_METRICS,
                {
                    "event_type": "message_processed",
                    "channel": channel,
                    "latency_ms": latency_ms,
                    "tokens_used": tokens_used,
                    "escalated": escalated,
                    "sentiment_score": sentiment_score,
                },
            )

            if not config.is_demo:
                from backend.database import queries
                await queries.record_metric("response_latency_ms", latency_ms, channel)
                await queries.record_metric("tokens_used", tokens_used, channel)
                if sentiment_score is not None:
                    await queries.record_metric("sentiment_score", sentiment_score, channel)

        except Exception as e:
            logger.error(f"[Processor] Metrics publish error: {e}")

    async def _handle_processing_error(
        self, message: dict, topic: str, error: Exception
    ) -> None:
        """Send an apology message when processing fails completely."""
        try:
            channel = self._extract_channel(topic, message)
            customer_contact = (
                message.get("sender_email")
                or message.get("email")
                or message.get("from_number")
            )

            if not customer_contact:
                return

            ticket_id = str(uuid.uuid4())[:8]

            if channel == "email":
                apology = (
                    f"Dear Customer,\n\n"
                    f"We sincerely apologize — we encountered a technical issue processing "
                    f"your message. Your request has been flagged for immediate human review.\n\n"
                    f"Reference: {ticket_id}\n\n"
                    f"Our team will contact you within 2 hours.\n\n"
                    f"Best regards,\nTechCorp Support Team"
                )
                from backend.channels.gmail_handler import GmailHandler
                handler = GmailHandler(dry_run=config.is_demo)
                await handler.send_reply(
                    to=customer_contact,
                    subject=f"Re: Your Support Request — {ticket_id}",
                    body=apology,
                )

            elif channel == "whatsapp":
                apology = (
                    f"We apologize for the technical issue. "
                    f"Your request has been escalated for urgent review. "
                    f"Ref: {ticket_id}"
                )
                from backend.channels.whatsapp_handler import WhatsAppHandler
                handler = WhatsAppHandler(dry_run=config.is_demo)
                await handler.send_message(to_phone=customer_contact, body=apology)

        except Exception as e:
            logger.error(f"[Processor] Failed to send apology: {e}")

    def _extract_channel(self, topic: str, message: dict) -> str:
        """Extract channel type from topic name or message."""
        if "email" in topic:
            return "email"
        elif "whatsapp" in topic:
            return "whatsapp"
        elif "webform" in topic:
            return "web_form"
        else:
            return message.get("channel", "web_form")

    async def _send_to_dlq(
        self, original_topic: str, message: dict, error: str
    ) -> None:
        """Send failed message to dead letter queue."""
        try:
            await self.producer.publish(
                TOPIC_DLQ,
                {
                    "original_topic": original_topic,
                    "error": error,
                    "message": message,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"[Processor] DLQ publish failed: {e}")


# ---------------------------------------------------------------------------
# Entry point for standalone worker process
# ---------------------------------------------------------------------------
async def run_worker() -> None:
    """Run the message processor as a standalone worker."""
    import signal

    from backend.database import queries
    from backend.config import config

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )

    config.log_startup()

    # Initialize database if in LIVE mode
    if config.is_live:
        await queries.init_pool(
            config.DATABASE_URL,
            min_size=config.DB_POOL_MIN_SIZE,
            max_size=config.DB_POOL_MAX_SIZE,
        )

    processor = UnifiedMessageProcessor()

    # Graceful shutdown
    loop = asyncio.get_event_loop()

    def handle_shutdown():
        logger.info("[Worker] Shutdown signal received")
        asyncio.create_task(processor.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_shutdown)

    try:
        await processor.start()
    finally:
        if config.is_live:
            await queries.close_pool()


if __name__ == "__main__":
    asyncio.run(run_worker())

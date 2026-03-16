"""
TechCorp FTE — Kafka Client
LIVE MODE: Uses aiokafka for real Apache Kafka connectivity.
DEMO MODE: Uses asyncio.Queue as an in-memory message bus.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Topic Definitions
# ---------------------------------------------------------------------------
TOPIC_TICKETS_INCOMING = "fte.tickets.incoming"
TOPIC_EMAIL_INBOUND = "fte.channels.email.inbound"
TOPIC_WHATSAPP_INBOUND = "fte.channels.whatsapp.inbound"
TOPIC_WEBFORM_INBOUND = "fte.channels.webform.inbound"
TOPIC_ESCALATIONS = "fte.escalations"
TOPIC_METRICS = "fte.metrics"
TOPIC_DLQ = "fte.dlq"

ALL_TOPICS = [
    TOPIC_TICKETS_INCOMING,
    TOPIC_EMAIL_INBOUND,
    TOPIC_WHATSAPP_INBOUND,
    TOPIC_WEBFORM_INBOUND,
    TOPIC_ESCALATIONS,
    TOPIC_METRICS,
    TOPIC_DLQ,
]


# ---------------------------------------------------------------------------
# DEMO MODE: In-memory message bus
# ---------------------------------------------------------------------------
class InMemoryBus:
    """
    Thread-safe in-memory pub/sub bus using asyncio.Queue.
    Replaces Kafka in DEMO mode — no external dependencies needed.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._history: list[dict] = []
        self._lock = asyncio.Lock()

    def _get_topic_queue(self, topic: str) -> asyncio.Queue:
        """Get or create a queue for the given topic."""
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue(maxsize=1000)
        return self._queues[topic]

    async def publish(self, topic: str, message: dict) -> bool:
        """Publish a message to a topic."""
        try:
            async with self._lock:
                envelope = {
                    "id": str(uuid.uuid4()),
                    "topic": topic,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._history.append(envelope)
                # Notify all subscribers
                if topic in self._subscribers:
                    for q in self._subscribers[topic]:
                        try:
                            q.put_nowait(envelope)
                        except asyncio.QueueFull:
                            logger.warning(f"[InMemoryBus] Queue full for topic {topic}")
            logger.debug(f"[InMemoryBus] Published to {topic}: {json.dumps(message)[:200]}")
            return True
        except Exception as e:
            logger.error(f"[InMemoryBus] Publish error for {topic}: {e}")
            return False

    async def subscribe(self, topics: list[str]) -> asyncio.Queue:
        """Subscribe to one or more topics, returns a queue to read from."""
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        async with self._lock:
            for topic in topics:
                if topic not in self._subscribers:
                    self._subscribers[topic] = []
                self._subscribers[topic].append(q)
        return q

    def get_history(self, topic: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Get message history, optionally filtered by topic."""
        history = self._history
        if topic:
            history = [h for h in history if h["topic"] == topic]
        return history[-limit:]


# Singleton in-memory bus instance
_in_memory_bus = InMemoryBus()


# ---------------------------------------------------------------------------
# PRODUCER
# ---------------------------------------------------------------------------
class FTEKafkaProducer:
    """
    Unified Kafka producer.
    LIVE MODE: Real aiokafka AIOKafkaProducer.
    DEMO MODE: In-memory bus.
    """

    def __init__(self, bootstrap_servers: str, dry_run: bool = True) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.dry_run = dry_run
        self._producer: Any = None
        self._started = False

    async def start(self) -> None:
        """Initialize the producer."""
        if self.dry_run:
            logger.info("[Kafka Producer] DEMO mode — using in-memory bus")
            self._started = True
            return

        try:
            from aiokafka import AIOKafkaProducer  # type: ignore
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                enable_idempotence=True,
                compression_type="gzip",
            )
            await self._producer.start()
            self._started = True
            logger.info(f"[Kafka Producer] Connected to {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"[Kafka Producer] Failed to connect: {e}")
            logger.warning("[Kafka Producer] Falling back to in-memory bus")
            self.dry_run = True
            self._started = True

    async def stop(self) -> None:
        """Gracefully stop the producer."""
        if self._producer and not self.dry_run:
            await self._producer.stop()
        self._started = False

    async def publish(
        self,
        topic: str,
        message: dict,
        key: Optional[str] = None,
    ) -> bool:
        """
        Publish a message to a Kafka topic.
        Returns True on success, False on failure.
        """
        if not self._started:
            await self.start()

        # Add standard metadata
        message.setdefault("event_id", str(uuid.uuid4()))
        message.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        if self.dry_run:
            return await _in_memory_bus.publish(topic, message)

        try:
            await self._producer.send_and_wait(topic, value=message, key=key)
            logger.debug(f"[Kafka] Published to {topic}: key={key}")
            return True
        except Exception as e:
            logger.error(f"[Kafka] Publish failed for {topic}: {e}")
            # Fallback to DLQ
            try:
                dlq_message = {"original_topic": topic, "error": str(e), "message": message}
                await self._producer.send_and_wait(TOPIC_DLQ, value=dlq_message)
            except Exception:
                pass
            return False

    async def publish_ticket_event(
        self,
        ticket_id: str,
        customer_id: str,
        channel: str,
        event_type: str,
        payload: dict,
    ) -> bool:
        """Publish a ticket lifecycle event."""
        message = {
            "event_type": event_type,
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "channel": channel,
            "payload": payload,
        }
        return await self.publish(TOPIC_TICKETS_INCOMING, message, key=ticket_id)

    async def publish_channel_message(
        self,
        channel: str,
        message: dict,
    ) -> bool:
        """Publish an incoming channel message to the appropriate topic."""
        topic_map = {
            "email": TOPIC_EMAIL_INBOUND,
            "whatsapp": TOPIC_WHATSAPP_INBOUND,
            "web_form": TOPIC_WEBFORM_INBOUND,
        }
        topic = topic_map.get(channel, TOPIC_TICKETS_INCOMING)
        return await self.publish(topic, message, key=message.get("customer_id"))

    async def publish_escalation(
        self,
        ticket_id: str,
        reason: str,
        urgency: str,
        context: dict,
    ) -> bool:
        """Publish an escalation event."""
        message = {
            "event_type": "escalation",
            "ticket_id": ticket_id,
            "reason": reason,
            "urgency": urgency,
            "context": context,
        }
        return await self.publish(TOPIC_ESCALATIONS, message, key=ticket_id)

    async def publish_metric(
        self,
        metric_name: str,
        value: float,
        channel: Optional[str] = None,
        dimensions: Optional[dict] = None,
    ) -> bool:
        """Publish a metric event."""
        message = {
            "event_type": "metric",
            "metric_name": metric_name,
            "value": value,
            "channel": channel,
            "dimensions": dimensions or {},
        }
        return await self.publish(TOPIC_METRICS, message)


# ---------------------------------------------------------------------------
# CONSUMER
# ---------------------------------------------------------------------------
class FTEKafkaConsumer:
    """
    Unified Kafka consumer.
    LIVE MODE: Real aiokafka AIOKafkaConsumer.
    DEMO MODE: Reads from in-memory bus.
    """

    def __init__(
        self,
        topics: list[str],
        group_id: str,
        bootstrap_servers: str,
        dry_run: bool = True,
    ) -> None:
        self.topics = topics
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers
        self.dry_run = dry_run
        self._consumer: Any = None
        self._queue: Optional[asyncio.Queue] = None
        self._started = False
        self._running = False

    async def start(self) -> None:
        """Initialize the consumer."""
        if self.dry_run:
            logger.info(f"[Kafka Consumer] DEMO mode — subscribing to {self.topics}")
            self._queue = await _in_memory_bus.subscribe(self.topics)
            self._started = True
            return

        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore
            self._consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
            await self._consumer.start()
            self._started = True
            logger.info(f"[Kafka Consumer] Subscribed to {self.topics}")
        except Exception as e:
            logger.error(f"[Kafka Consumer] Failed to connect: {e}")
            logger.warning("[Kafka Consumer] Falling back to in-memory bus")
            self.dry_run = True
            self._queue = await _in_memory_bus.subscribe(self.topics)
            self._started = True

    async def stop(self) -> None:
        """Gracefully stop the consumer."""
        self._running = False
        if self._consumer and not self.dry_run:
            await self._consumer.stop()
        self._started = False

    async def consume(
        self,
        handler: Callable[[str, dict], Any],
        poll_timeout_ms: int = 1000,
    ) -> None:
        """
        Start consuming messages and call handler for each.
        handler(topic, message) is called for every message.
        Runs indefinitely until stop() is called.
        """
        if not self._started:
            await self.start()

        self._running = True
        logger.info(f"[Kafka Consumer] Starting message loop for {self.topics}")

        while self._running:
            try:
                if self.dry_run:
                    # In-memory mode: poll with timeout
                    try:
                        envelope = await asyncio.wait_for(
                            self._queue.get(),  # type: ignore
                            timeout=poll_timeout_ms / 1000,
                        )
                        topic = envelope["topic"]
                        message = envelope["message"]
                        await handler(topic, message)
                    except asyncio.TimeoutError:
                        continue
                else:
                    # Real Kafka mode
                    records = await self._consumer.getmany(  # type: ignore
                        timeout_ms=poll_timeout_ms,
                        max_records=10,
                    )
                    for tp, messages in records.items():
                        for msg in messages:
                            await handler(msg.topic, msg.value)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Kafka Consumer] Error in consume loop: {e}")
                await asyncio.sleep(1)  # Back off on error

        logger.info("[Kafka Consumer] Message loop stopped")


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------
def create_producer(dry_run: bool = True) -> FTEKafkaProducer:
    """Create a Kafka producer instance."""
    from backend.config import config
    return FTEKafkaProducer(
        bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
        dry_run=dry_run,
    )


def create_consumer(
    topics: list[str],
    group_id: str = "fte-consumer-group",
    dry_run: bool = True,
) -> FTEKafkaConsumer:
    """Create a Kafka consumer instance."""
    from backend.config import config
    return FTEKafkaConsumer(
        topics=topics,
        group_id=group_id,
        bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
        dry_run=dry_run,
    )


def get_in_memory_bus() -> InMemoryBus:
    """Get the singleton in-memory bus (for testing/admin)."""
    return _in_memory_bus

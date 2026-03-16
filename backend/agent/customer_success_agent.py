"""
TechCorp FTE — Customer Success AI Agent
Main agent orchestrating all customer support interactions.
Uses Anthropic Claude with tool use for structured workflows.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import anthropic

from backend.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT
from backend.agent import tools
from backend.config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message Context Model
# ---------------------------------------------------------------------------
class IncomingMessage:
    """Represents an incoming customer message with full context."""

    def __init__(
        self,
        content: str,
        channel: str,
        customer_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_contact: Optional[str] = None,
        conversation_id: Optional[str] = None,
        ticket_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        self.content = content
        self.channel = channel
        self.customer_id = customer_id or str(uuid.uuid4())
        self.customer_name = customer_name or "Customer"
        self.customer_contact = customer_contact
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.ticket_id = ticket_id
        self.history = history or []
        self.metadata = metadata or {}


class AgentResponse:
    """Represents the agent's response to a customer message."""

    def __init__(
        self,
        message: str,
        ticket_id: str,
        channel: str,
        escalated: bool = False,
        escalation_id: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        tool_calls: Optional[list] = None,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> None:
        self.message = message
        self.ticket_id = ticket_id
        self.channel = channel
        self.escalated = escalated
        self.escalation_id = escalation_id
        self.sentiment_score = sentiment_score
        self.tool_calls = tool_calls or []
        self.tokens_used = tokens_used
        self.latency_ms = latency_ms

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "message": self.message,
            "ticket_id": self.ticket_id,
            "channel": self.channel,
            "escalated": self.escalated,
            "escalation_id": self.escalation_id,
            "sentiment_score": self.sentiment_score,
            "tool_calls_count": len(self.tool_calls),
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
        }


# ---------------------------------------------------------------------------
# Tool Definitions for Claude API
# ---------------------------------------------------------------------------
AGENT_TOOLS = [
    {
        "name": "search_knowledge_base",
        "description": "Search TechCorp's knowledge base for relevant documentation and FAQs about TaskFlow Pro. Use this to find answers to customer questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 5},
                "category": {
                    "type": "string",
                    "description": "Optional category filter: account, team, api, data, tasks, mobile, security, billing, general",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_ticket",
        "description": "Create a support ticket for the customer's issue. Call this at the START of every conversation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer UUID"},
                "issue": {"type": "string", "description": "Description of the issue"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "default": "medium",
                },
                "channel": {
                    "type": "string",
                    "enum": ["email", "whatsapp", "web_form"],
                },
                "category": {
                    "type": "string",
                    "enum": ["general", "technical", "billing", "bug_report", "feedback"],
                    "default": "general",
                },
                "subject": {"type": "string", "description": "Brief subject line"},
            },
            "required": ["customer_id", "issue", "priority", "channel"],
        },
    },
    {
        "name": "get_customer_history",
        "description": "Retrieve customer's past conversations across all channels. Use to avoid making customers repeat themselves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer UUID"},
                "limit": {"type": "integer", "default": 5, "description": "Number of recent conversations"},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate the ticket to a human agent. Use for: legal threats, refund requests, security breaches, very negative sentiment, or when KB search fails twice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Ticket UUID to escalate"},
                "reason": {"type": "string", "description": "Reason for escalation"},
                "urgency": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "default": "medium",
                },
            },
            "required": ["ticket_id", "reason"],
        },
    },
    {
        "name": "send_response",
        "description": "Send the final response to the customer via their channel. Call this ONCE with the complete, formatted message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Ticket UUID"},
                "message": {"type": "string", "description": "Complete message to send"},
                "channel": {
                    "type": "string",
                    "enum": ["email", "whatsapp", "web_form"],
                },
            },
            "required": ["ticket_id", "message", "channel"],
        },
    },
    {
        "name": "analyze_sentiment",
        "description": "Analyze the sentiment of a customer message. Returns score 0.0 (very negative) to 1.0 (very positive).",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_text": {"type": "string", "description": "Customer message to analyze"},
            },
            "required": ["message_text"],
        },
    },
]


# ---------------------------------------------------------------------------
# Main Agent Class
# ---------------------------------------------------------------------------
class CustomerSuccessAgent:
    """
    AI-powered Customer Success agent for TechCorp.
    Orchestrates tool calls to handle customer support requests
    across Email, WhatsApp, and Web Form channels.
    """

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.ANTHROPIC_MODEL
        self.max_tokens = config.ANTHROPIC_MAX_TOKENS
        self.dry_run = config.DRY_RUN
        self._tool_calls_log: list[dict] = []

    async def process(self, incoming: IncomingMessage) -> AgentResponse:
        """
        Process an incoming customer message end-to-end.
        Returns AgentResponse with message, ticket_id, and metadata.
        """
        start_time = time.time()
        self._tool_calls_log = []
        ticket_id = incoming.ticket_id or str(uuid.uuid4())
        escalated = False
        escalation_id = None
        sentiment_score = None
        total_tokens = 0

        logger.info(
            f"[Agent] Processing message — channel={incoming.channel}, "
            f"customer={incoming.customer_id[:8]}, "
            f"mode={'DEMO' if self.dry_run else 'LIVE'}"
        )

        # Build conversation history for context
        messages = self._build_messages(incoming)

        try:
            # Agentic loop — continue until no more tool calls
            response_message = None
            iteration = 0
            max_iterations = 10  # Safety limit

            while iteration < max_iterations:
                iteration += 1

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
                    tools=AGENT_TOOLS,
                    messages=messages,
                )

                total_tokens += response.usage.input_tokens + response.usage.output_tokens

                logger.debug(
                    f"[Agent] Iteration {iteration}: stop_reason={response.stop_reason}, "
                    f"blocks={len(response.content)}"
                )

                # Check for final text response
                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            response_message = block.text
                    break

                # Process tool calls
                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})

                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_result = await self._execute_tool(
                                name=block.name,
                                tool_input=block.input,
                                incoming=incoming,
                                ticket_id=ticket_id,
                            )

                            # Track important state
                            if block.name == "create_ticket":
                                if "ticket_id" in tool_result:
                                    ticket_id = tool_result["ticket_id"]

                            elif block.name == "analyze_sentiment":
                                sentiment_score = tool_result.get("score")

                            elif block.name == "escalate_to_human":
                                escalated = True
                                escalation_id = tool_result.get("escalation_id")

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(tool_result),
                            })

                            self._tool_calls_log.append({
                                "tool": block.name,
                                "input": block.input,
                                "result": tool_result,
                            })

                    messages.append({"role": "user", "content": tool_results})
                    continue

                # Unexpected stop reason
                logger.warning(f"[Agent] Unexpected stop_reason: {response.stop_reason}")
                break

            if not response_message:
                response_message = self._fallback_response(incoming.channel)

            # Enforce channel-specific length limits
            response_message = self._enforce_channel_limits(
                response_message, incoming.channel
            )

            latency_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[Agent] Completed — ticket={ticket_id[:8]}, "
                f"escalated={escalated}, tokens={total_tokens}, "
                f"latency={latency_ms}ms"
            )

            return AgentResponse(
                message=response_message,
                ticket_id=ticket_id,
                channel=incoming.channel,
                escalated=escalated,
                escalation_id=escalation_id,
                sentiment_score=sentiment_score,
                tool_calls=self._tool_calls_log,
                tokens_used=total_tokens,
                latency_ms=latency_ms,
            )

        except anthropic.APIError as e:
            logger.error(f"[Agent] Anthropic API error: {e}")
            return self._error_response(ticket_id, incoming.channel, str(e))

        except Exception as e:
            logger.error(f"[Agent] Unexpected error: {e}", exc_info=True)
            return self._error_response(ticket_id, incoming.channel, str(e))

    async def _execute_tool(
        self,
        name: str,
        tool_input: dict,
        incoming: IncomingMessage,
        ticket_id: str,
    ) -> dict:
        """Execute a tool call and return the result."""
        logger.info(f"[Agent] Executing tool: {name}")

        try:
            if name == "search_knowledge_base":
                return await tools.search_knowledge_base(
                    query=tool_input.get("query", ""),
                    max_results=tool_input.get("max_results", 5),
                    category=tool_input.get("category"),
                    dry_run=self.dry_run,
                )

            elif name == "create_ticket":
                return await tools.create_ticket(
                    customer_id=tool_input.get("customer_id", incoming.customer_id),
                    issue=tool_input.get("issue", incoming.content),
                    priority=tool_input.get("priority", "medium"),
                    channel=tool_input.get("channel", incoming.channel),
                    category=tool_input.get("category", "general"),
                    subject=tool_input.get("subject"),
                    dry_run=self.dry_run,
                    conversation_id=incoming.conversation_id,
                )

            elif name == "get_customer_history":
                return await tools.get_customer_history(
                    customer_id=tool_input.get("customer_id", incoming.customer_id),
                    limit=tool_input.get("limit", 5),
                    dry_run=self.dry_run,
                )

            elif name == "escalate_to_human":
                return await tools.escalate_to_human(
                    ticket_id=tool_input.get("ticket_id", ticket_id),
                    reason=tool_input.get("reason", "Manual escalation"),
                    urgency=tool_input.get("urgency", "medium"),
                    dry_run=self.dry_run,
                )

            elif name == "send_response":
                return await tools.send_response(
                    ticket_id=tool_input.get("ticket_id", ticket_id),
                    message=tool_input.get("message", ""),
                    channel=tool_input.get("channel", incoming.channel),
                    dry_run=self.dry_run,
                    customer_contact=incoming.customer_contact,
                    conversation_id=incoming.conversation_id,
                )

            elif name == "analyze_sentiment":
                return await tools.analyze_sentiment(
                    message_text=tool_input.get("message_text", incoming.content),
                    dry_run=self.dry_run,
                )

            else:
                logger.warning(f"[Agent] Unknown tool: {name}")
                return {"error": f"Unknown tool: {name}"}

        except Exception as e:
            logger.error(f"[Agent] Tool {name} failed: {e}")
            return {"error": str(e), "tool": name}

    def _build_messages(self, incoming: IncomingMessage) -> list[dict]:
        """Build the messages list for the Claude API call."""
        messages = []

        # Add conversation history if available
        for msg in incoming.history[-8:]:  # Last 8 messages for context
            role = "user" if msg.get("role") == "customer" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})

        # Build context-rich user message
        context_parts = [
            f"CHANNEL: {incoming.channel.upper()}",
            f"CUSTOMER_ID: {incoming.customer_id}",
            f"CUSTOMER_NAME: {incoming.customer_name}",
        ]

        if incoming.customer_contact:
            context_parts.append(f"CUSTOMER_CONTACT: {incoming.customer_contact}")

        context_header = " | ".join(context_parts)

        user_message = f"[{context_header}]\n\nCustomer message:\n{incoming.content}"

        messages.append({"role": "user", "content": user_message})
        return messages

    def _enforce_channel_limits(self, message: str, channel: str) -> str:
        """Enforce channel-specific message length limits."""
        limits = {
            "email": 2000,       # ~500 words
            "whatsapp": 1600,    # Twilio limit, ~300 chars visible
            "web_form": 1500,    # ~300 words
        }
        limit = limits.get(channel, 2000)

        if len(message) > limit:
            message = message[:limit - 50] + "\n\n[Continued in follow-up message...]"

        return message

    def _fallback_response(self, channel: str) -> str:
        """Fallback response when agent fails to generate a message."""
        if channel == "whatsapp":
            return "Hi! I received your message. A support specialist will contact you shortly. Thank you for your patience."
        elif channel == "email":
            return (
                "Dear Customer,\n\n"
                "Thank you for contacting TechCorp Support. We have received your message "
                "and a support specialist will review your case shortly.\n\n"
                "We appreciate your patience.\n\n"
                "Best regards,\nTechCorp AI Support Team"
            )
        else:
            return (
                "Thank you for contacting TechCorp Support. "
                "We've received your message and will respond shortly.\n\n"
                "— TechCorp AI Support Team"
            )

    def _error_response(
        self, ticket_id: str, channel: str, error: str
    ) -> AgentResponse:
        """Generate an error response when agent fails completely."""
        logger.error(f"[Agent] Generating error response for ticket {ticket_id}")

        if channel == "whatsapp":
            message = (
                "Sorry, I'm experiencing a technical issue. "
                "Your message has been flagged for urgent human review. "
                f"Ref: {ticket_id[:8]}"
            )
        elif channel == "email":
            message = (
                "Dear Customer,\n\n"
                "We apologize — we experienced a technical issue processing your request. "
                "Your message has been flagged for immediate human review and our team "
                f"will contact you within 2 hours.\n\n"
                f"Reference: {ticket_id}\n\n"
                "Best regards,\nTechCorp Support Team"
            )
        else:
            message = (
                "We apologize for the inconvenience. We experienced a technical issue "
                "and your request has been escalated to our support team for immediate review.\n\n"
                f"Reference: {ticket_id}\n\n"
                "— TechCorp Support Team"
            )

        return AgentResponse(
            message=message,
            ticket_id=ticket_id,
            channel=channel,
            escalated=True,
        )


# Singleton agent instance
_agent_instance: Optional[CustomerSuccessAgent] = None


def get_agent() -> CustomerSuccessAgent:
    """Get the singleton agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CustomerSuccessAgent()
    return _agent_instance

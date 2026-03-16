"""
TechCorp FTE — WhatsApp Channel Handler (via Twilio)
Handles inbound WhatsApp messages and outbound replies.
DEMO MODE: All methods return mock data, no real API calls.
LIVE MODE: Full Twilio WhatsApp Sandbox integration.
"""

import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# WhatsApp magic words that trigger human escalation
ESCALATION_KEYWORDS = {
    "human", "agent", "representative", "person",
    "real person", "speak to someone", "انسان", "اردو"  # Urdu support
}

# Mock incoming WhatsApp messages for DEMO mode
MOCK_WHATSAPP_MESSAGES = [
    {
        "id": f"WA{uuid.uuid4().hex[:8].upper()}",
        "from_number": "whatsapp:+923001234567",
        "sender_name": "Usman Raza",
        "body": "Hello I cannot login to my account. Please help.",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "profile_name": "Usman Raza",
        "num_media": "0",
    },
    {
        "id": f"WA{uuid.uuid4().hex[:8].upper()}",
        "from_number": "whatsapp:+923211234567",
        "sender_name": "Ayesha",
        "body": "My tasks are not syncing on mobile app",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "profile_name": "Ayesha",
        "num_media": "0",
    },
]


class WhatsAppHandler:
    """
    WhatsApp channel handler for TechCorp FTE using Twilio.
    Manages webhook validation, message parsing, and outbound messaging.
    """

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run
        self._client: Optional[object] = None

    def _get_client(self) -> Optional[object]:
        """Lazy-initialize Twilio client."""
        if self.dry_run:
            return None

        if self._client is None:
            try:
                from twilio.rest import Client  # type: ignore
                from backend.config import config

                if not config.twilio_configured:
                    logger.error("[WhatsApp] Twilio credentials not configured")
                    return None

                self._client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
                logger.info("[WhatsApp] Twilio client initialized")
            except Exception as e:
                logger.error(f"[WhatsApp] Client init failed: {e}")

        return self._client

    def validate_webhook(self, signature: str, url: str, params: dict) -> bool:
        """
        Verify Twilio webhook signature for security.
        DEMO: Always returns True.
        LIVE: Validates HMAC-SHA1 signature.
        """
        if self.dry_run:
            logger.debug("[WhatsApp DEMO] Webhook validation skipped")
            return True

        try:
            from backend.config import config

            if not config.TWILIO_AUTH_TOKEN:
                logger.warning("[WhatsApp] No auth token — skipping validation")
                return True

            # Build validation string: URL + sorted params
            s = url + urlencode(sorted(params.items()))
            computed_signature = base64.b64encode(
                hmac.new(
                    config.TWILIO_AUTH_TOKEN.encode("utf-8"),
                    s.encode("utf-8"),
                    hashlib.sha1,
                ).digest()
            ).decode()

            valid = hmac.compare_digest(signature, computed_signature)
            if not valid:
                logger.warning("[WhatsApp] Invalid webhook signature")
            return valid

        except Exception as e:
            logger.error(f"[WhatsApp] Signature validation error: {e}")
            return False

    def process_webhook(self, form_data: dict) -> Optional[dict]:
        """
        Parse incoming Twilio WhatsApp webhook payload.
        Returns standardized message dict or None if invalid.

        Twilio webhook fields:
        - From: whatsapp:+1234567890
        - Body: message text
        - MessageSid: unique message ID
        - ProfileName: sender's WhatsApp display name
        - NumMedia: number of media attachments
        """
        try:
            message_body = form_data.get("Body", "").strip()
            from_number = form_data.get("From", "")
            message_sid = form_data.get("MessageSid", "")
            profile_name = form_data.get("ProfileName", "")
            num_media = int(form_data.get("NumMedia", "0"))

            if not from_number or not message_sid:
                logger.warning("[WhatsApp] Invalid webhook: missing From or MessageSid")
                return None

            # Clean phone number (remove whatsapp: prefix)
            clean_number = from_number.replace("whatsapp:", "")

            # Check for escalation keywords
            is_escalation_request = message_body.lower().strip() in ESCALATION_KEYWORDS

            result = {
                "id": message_sid,
                "from_number": from_number,
                "clean_number": clean_number,
                "sender_name": profile_name or clean_number,
                "body": message_body,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "has_media": num_media > 0,
                "num_media": num_media,
                "is_escalation_request": is_escalation_request,
                "channel": "whatsapp",
            }

            logger.info(
                f"[WhatsApp] Parsed message from {clean_number}: "
                f"'{message_body[:50]}...' "
                f"(escalation={is_escalation_request})"
            )

            return result

        except Exception as e:
            logger.error(f"[WhatsApp] Webhook parse error: {e}")
            return None

    async def send_message(
        self,
        to_phone: str,
        body: str,
    ) -> dict:
        """
        Send a WhatsApp message via Twilio.
        DEMO: Logs message, no real send.
        LIVE: Sends via Twilio API.
        """
        from backend.config import config

        # Ensure WhatsApp prefix format
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"

        # Split into chunks if too long
        chunks = self.format_response(body)

        if self.dry_run:
            logger.info(f"\n[WhatsApp DEMO] Would send to: {to_phone}")
            for i, chunk in enumerate(chunks):
                logger.info(f"  Message {i+1}/{len(chunks)}:\n{chunk}")
            return {
                "success": True,
                "sid": f"demo_wa_{uuid.uuid4().hex[:8]}",
                "to": to_phone,
                "chunks": len(chunks),
                "mode": "demo",
            }

        client = self._get_client()
        if not client:
            return {"success": False, "error": "Twilio client not available"}

        try:
            last_sid = None
            for chunk in chunks:
                message = client.messages.create(  # type: ignore
                    from_=config.TWILIO_WHATSAPP_NUMBER,
                    to=to_phone,
                    body=chunk,
                )
                last_sid = message.sid
                logger.info(
                    f"[WhatsApp] Sent to {to_phone}: sid={message.sid}, "
                    f"status={message.status}"
                )

            return {
                "success": True,
                "sid": last_sid,
                "to": to_phone,
                "chunks": len(chunks),
                "mode": "live",
            }

        except Exception as e:
            logger.error(f"[WhatsApp] Send failed to {to_phone}: {e}")
            return {"success": False, "error": str(e), "to": to_phone, "mode": "live"}

    def format_response(self, text: str, max_length: int = 1600) -> list[str]:
        """
        Split a long message into Twilio-compliant chunks.
        Twilio WhatsApp max message size is 1600 characters.
        Splits on sentence boundaries where possible.
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""
        sentences = text.replace("\n\n", "\n").split("\n")

        for sentence in sentences:
            # If single sentence is longer than limit, hard split
            if len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                for i in range(0, len(sentence), max_length):
                    chunks.append(sentence[i : i + max_length])
                continue

            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += sentence + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [c for c in chunks if c]

    def process_status_callback(self, form_data: dict) -> Optional[dict]:
        """
        Parse Twilio delivery status callback.
        Returns delivery status update dict.
        """
        try:
            return {
                "message_sid": form_data.get("MessageSid", ""),
                "status": form_data.get("MessageStatus", ""),
                "to": form_data.get("To", ""),
                "from": form_data.get("From", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"[WhatsApp] Status callback parse error: {e}")
            return None

    def get_mock_messages(self) -> list[dict]:
        """Return mock messages for DEMO mode testing."""
        return MOCK_WHATSAPP_MESSAGES

    def get_status(self) -> dict:
        """Return channel health status."""
        if self.dry_run:
            return {"status": "demo", "connected": True, "mode": "demo"}

        from backend.config import config
        if not config.twilio_configured:
            return {"status": "not_configured", "connected": False, "mode": "live"}

        try:
            client = self._get_client()
            if not client:
                return {"status": "error", "connected": False, "mode": "live"}
            # Quick test — fetch account info
            account = client.api.accounts(config.TWILIO_ACCOUNT_SID).fetch()  # type: ignore
            return {
                "status": "connected",
                "connected": True,
                "account_name": account.friendly_name,
                "mode": "live",
            }
        except Exception as e:
            return {"status": "error", "connected": False, "error": str(e), "mode": "live"}


# Need to import base64 for signature validation
import base64
import hmac as hmac_module

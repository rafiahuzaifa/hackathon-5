"""
TechCorp FTE — Gmail Channel Handler
Handles inbound email via Gmail API and outbound email replies.
DEMO MODE: All methods return mock data, no real API calls.
LIVE MODE: Full Gmail OAuth2 + REST API integration.
"""

import base64
import logging
import re
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

# Mock emails for DEMO mode
MOCK_EMAILS = [
    {
        "id": str(uuid.uuid4()),
        "thread_id": "thread_" + str(uuid.uuid4())[:8],
        "sender_email": "ahmed.khan@example.com",
        "sender_name": "Ahmed Khan",
        "subject": "Cannot reset my password",
        "body": "Hi, I've been trying to reset my password for the last 30 minutes but I'm not receiving the reset email. Please help ASAP.",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "labels": ["UNREAD", "INBOX"],
    },
    {
        "id": str(uuid.uuid4()),
        "thread_id": "thread_" + str(uuid.uuid4())[:8],
        "sender_email": "fatima.malik@techstartup.pk",
        "sender_name": "Fatima Malik",
        "subject": "API returning 401 errors",
        "body": "Hello, our integration with TaskFlow API stopped working. We're getting 401 Unauthorized errors since yesterday. This is blocking our team completely.",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "labels": ["UNREAD", "INBOX"],
    },
]


class GmailHandler:
    """
    Gmail channel handler for TechCorp FTE.
    Manages OAuth2 authentication, email fetching, parsing, and sending.
    """

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run
        self._service: Optional[object] = None
        self._credentials: Optional[object] = None

    def setup_oauth2(self) -> bool:
        """
        Initialize Gmail OAuth2 credentials.
        LIVE: Load from environment variables.
        DEMO: No-op, returns True.
        """
        if self.dry_run:
            logger.info("[Gmail] DEMO mode — OAuth2 skipped")
            return True

        try:
            from google.oauth2.credentials import Credentials  # type: ignore
            from googleapiclient.discovery import build  # type: ignore
            from backend.config import config

            if not config.gmail_configured:
                logger.error("[Gmail] Gmail credentials not configured")
                return False

            self._credentials = Credentials(
                token=None,
                refresh_token=config.GMAIL_REFRESH_TOKEN,
                client_id=config.GMAIL_CLIENT_ID,
                client_secret=config.GMAIL_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=["https://www.googleapis.com/auth/gmail.modify"],
            )

            self._service = build("gmail", "v1", credentials=self._credentials)
            logger.info("[Gmail] OAuth2 initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[Gmail] OAuth2 setup failed: {e}")
            return False

    async def get_new_emails(self) -> list[dict]:
        """
        Fetch unread emails from inbox.
        DEMO: Returns mock email data.
        LIVE: Fetches from Gmail API.
        """
        if self.dry_run:
            logger.info(f"[Gmail DEMO] Returning {len(MOCK_EMAILS)} mock emails")
            return MOCK_EMAILS

        if not self._service:
            success = self.setup_oauth2()
            if not success:
                return []

        try:
            results = self._service.users().messages().list(  # type: ignore
                userId="me",
                labelIds=["UNREAD", "INBOX"],
                maxResults=10,
            ).execute()

            messages = results.get("messages", [])
            parsed = []

            for msg_ref in messages:
                try:
                    parsed_email = await self._fetch_and_parse_email(msg_ref["id"])
                    if parsed_email:
                        parsed.append(parsed_email)
                except Exception as e:
                    logger.error(f"[Gmail] Error parsing message {msg_ref['id']}: {e}")

            logger.info(f"[Gmail] Fetched {len(parsed)} new emails")
            return parsed

        except Exception as e:
            logger.error(f"[Gmail] Error fetching emails: {e}")
            return []

    async def _fetch_and_parse_email(self, message_id: str) -> Optional[dict]:
        """Fetch a single message and parse it."""
        try:
            msg = self._service.users().messages().get(  # type: ignore
                userId="me",
                id=message_id,
                format="full",
            ).execute()
            return self.parse_email(msg)
        except Exception as e:
            logger.error(f"[Gmail] Error fetching message {message_id}: {e}")
            return None

    def parse_email(self, message: dict) -> dict:
        """
        Parse a Gmail API message into a standardized format.
        Extracts sender, subject, body, and thread info.
        """
        headers = {}
        payload = message.get("payload", {})

        for header in payload.get("headers", []):
            headers[header["name"].lower()] = header["value"]

        # Extract sender info
        from_header = headers.get("from", "")
        sender_email, sender_name = self._parse_from_header(from_header)

        # Extract body
        body = self._extract_body(payload)

        return {
            "id": message["id"],
            "thread_id": message.get("threadId", ""),
            "sender_email": sender_email,
            "sender_name": sender_name,
            "subject": headers.get("subject", "(no subject)"),
            "body": body,
            "received_at": datetime.fromtimestamp(
                int(message.get("internalDate", 0)) / 1000, tz=timezone.utc
            ).isoformat(),
            "labels": message.get("labelIds", []),
        }

    def _parse_from_header(self, from_header: str) -> tuple[str, str]:
        """Parse 'From' header into (email, name) tuple."""
        # Format: "Name <email@example.com>"
        match = re.match(r'"?([^"<]+)"?\s*<([^>]+)>', from_header)
        if match:
            return match.group(2).strip(), match.group(1).strip()

        # Plain email
        if "@" in from_header:
            return from_header.strip(), from_header.split("@")[0].strip()

        return from_header, "Unknown"

    def _extract_body(self, payload: dict) -> str:
        """Recursively extract email body from MIME payload."""
        body = ""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

        elif mime_type == "text/html":
            data = payload.get("body", {}).get("data", "")
            if data:
                html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                # Basic HTML strip — production should use html2text
                body = re.sub(r"<[^>]+>", "", html)

        elif "multipart" in mime_type:
            for part in payload.get("parts", []):
                part_body = self._extract_body(part)
                if part_body and not body:
                    body = part_body

        return body.strip()

    async def send_reply(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
    ) -> dict:
        """
        Send an email reply via Gmail API.
        DEMO: Logs the email, no real send.
        LIVE: Sends via Gmail API.
        """
        if self.dry_run:
            logger.info(f"\n[Gmail DEMO] Would send email to: {to}")
            logger.info(f"  Subject: {subject}")
            logger.info(f"  Thread: {thread_id}")
            logger.info(f"  Body:\n{body[:500]}")
            return {
                "success": True,
                "message_id": f"demo_msg_{uuid.uuid4().hex[:8]}",
                "thread_id": thread_id or f"demo_thread_{uuid.uuid4().hex[:8]}",
                "mode": "demo",
            }

        if not self._service:
            self.setup_oauth2()

        try:
            msg = MIMEMultipart("alternative")
            msg["To"] = to
            msg["Subject"] = subject

            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
                msg["References"] = in_reply_to

            msg.attach(MIMEText(body, "plain"))

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            body_data: dict = {"raw": raw}

            if thread_id:
                body_data["threadId"] = thread_id

            sent = self._service.users().messages().send(  # type: ignore
                userId="me", body=body_data
            ).execute()

            logger.info(f"[Gmail] Email sent to {to}, message_id={sent['id']}")
            return {
                "success": True,
                "message_id": sent["id"],
                "thread_id": sent.get("threadId"),
                "mode": "live",
            }

        except Exception as e:
            logger.error(f"[Gmail] Send failed to {to}: {e}")
            return {"success": False, "error": str(e), "mode": "live"}

    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read after processing."""
        if self.dry_run:
            logger.debug(f"[Gmail DEMO] Would mark {message_id} as read")
            return True

        try:
            self._service.users().messages().modify(  # type: ignore
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return True
        except Exception as e:
            logger.error(f"[Gmail] Mark read failed for {message_id}: {e}")
            return False

    def get_status(self) -> dict:
        """Return channel health status."""
        if self.dry_run:
            return {"status": "demo", "connected": True, "mode": "demo"}

        from backend.config import config
        if not config.gmail_configured:
            return {"status": "not_configured", "connected": False, "mode": "live"}

        try:
            if not self._service:
                self.setup_oauth2()
            # Quick test — get profile
            self._service.users().getProfile(userId="me").execute()  # type: ignore
            return {"status": "connected", "connected": True, "mode": "live"}
        except Exception as e:
            return {"status": "error", "connected": False, "error": str(e), "mode": "live"}

"""
TechCorp Customer Success Digital FTE — Configuration
Reads all environment variables with sensible defaults.
DEMO MODE (DRY_RUN=true): No external API calls required.
LIVE MODE (DRY_RUN=false): Full production capabilities.
"""

import os
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """
    Central configuration class for the FTE system.
    Reads from environment variables with defaults.
    All external API calls are skipped in DEMO mode.
    """

    # ------------------------------------------------------------------
    # MODE SETTINGS
    # ------------------------------------------------------------------
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    BANK_CURRENCY: str = os.getenv("BANK_CURRENCY", "PKR")
    MAX_ACTIONS_PER_HOUR: int = int(os.getenv("MAX_ACTIONS_PER_HOUR", "10"))
    APP_NAME: str = os.getenv("APP_NAME", "TechCorp Customer Success FTE")
    VERSION: str = "1.0.0"

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://fte_user:password@localhost:5432/fte_db"
    )
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
    DB_COMMAND_TIMEOUT: int = int(os.getenv("DB_COMMAND_TIMEOUT", "30"))

    # ------------------------------------------------------------------
    # KAFKA
    # ------------------------------------------------------------------
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
    )
    KAFKA_GROUP_ID: str = os.getenv("KAFKA_GROUP_ID", "fte-consumer-group")
    KAFKA_AUTO_OFFSET_RESET: str = os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest")

    # ------------------------------------------------------------------
    # ANTHROPIC AI
    # ------------------------------------------------------------------
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv(
        "ANTHROPIC_MODEL", "claude-sonnet-4-20250514"
    )
    ANTHROPIC_MAX_TOKENS: int = int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048"))

    # ------------------------------------------------------------------
    # GMAIL (only needed in LIVE mode)
    # ------------------------------------------------------------------
    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    GMAIL_REFRESH_TOKEN: str = os.getenv("GMAIL_REFRESH_TOKEN", "")
    GMAIL_REDIRECT_URI: str = os.getenv(
        "GMAIL_REDIRECT_URI", "http://localhost:8000/oauth/gmail/callback"
    )
    GMAIL_SUPPORT_EMAIL: str = os.getenv(
        "GMAIL_SUPPORT_EMAIL", "support@techcorp.pk"
    )

    # ------------------------------------------------------------------
    # TWILIO WHATSAPP (only needed in LIVE mode)
    # ------------------------------------------------------------------
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv(
        "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",")

    # ------------------------------------------------------------------
    # RATE LIMITING
    # ------------------------------------------------------------------
    RATE_LIMIT_WINDOW_SECONDS: int = 3600  # 1 hour
    RATE_LIMIT_MAX_REQUESTS: int = MAX_ACTIONS_PER_HOUR

    # ------------------------------------------------------------------
    # KNOWLEDGE BASE
    # ------------------------------------------------------------------
    KB_CONTEXT_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "context"
    )
    KB_SIMILARITY_THRESHOLD: float = float(
        os.getenv("KB_SIMILARITY_THRESHOLD", "0.7")
    )
    KB_MAX_RESULTS: int = int(os.getenv("KB_MAX_RESULTS", "5"))

    # ------------------------------------------------------------------
    # PROPERTIES
    # ------------------------------------------------------------------
    @property
    def is_demo(self) -> bool:
        """Returns True when running in DEMO (dry-run) mode."""
        return self.DRY_RUN

    @property
    def is_live(self) -> bool:
        """Returns True when running in LIVE (production) mode."""
        return not self.DRY_RUN

    @property
    def mode_label(self) -> str:
        """Human-readable mode label for display."""
        return "DEMO" if self.is_demo else "LIVE"

    @property
    def gmail_configured(self) -> bool:
        """Returns True if Gmail credentials are available."""
        return bool(
            self.GMAIL_CLIENT_ID
            and self.GMAIL_CLIENT_SECRET
            and self.GMAIL_REFRESH_TOKEN
        )

    @property
    def twilio_configured(self) -> bool:
        """Returns True if Twilio credentials are available."""
        return bool(
            self.TWILIO_ACCOUNT_SID
            and self.TWILIO_AUTH_TOKEN
            and self.TWILIO_WHATSAPP_NUMBER
        )

    @property
    def anthropic_configured(self) -> bool:
        """Returns True if Anthropic API key is available."""
        return bool(self.ANTHROPIC_API_KEY)

    @property
    def kafka_enabled(self) -> bool:
        """Kafka is only used in LIVE mode."""
        return self.is_live

    def validate(self) -> list[str]:
        """
        Validate configuration and return list of warnings/errors.
        Returns empty list if everything is fine.
        """
        issues: list[str] = []

        if not self.anthropic_configured:
            issues.append("ANTHROPIC_API_KEY is not set — AI agent will not function")

        if self.is_live:
            if not self.gmail_configured:
                issues.append(
                    "LIVE mode: Gmail credentials not configured — email channel disabled"
                )
            if not self.twilio_configured:
                issues.append(
                    "LIVE mode: Twilio credentials not configured — WhatsApp channel disabled"
                )

        return issues

    def log_startup(self) -> None:
        """Log configuration summary at startup."""
        mode_emoji = "🟡" if self.is_demo else "🟢"
        logger.info(f"{mode_emoji} TechCorp FTE starting in {self.mode_label} mode")
        logger.info(f"  Anthropic: {'✅ configured' if self.anthropic_configured else '❌ missing'}")
        logger.info(f"  Gmail: {'✅ configured' if self.gmail_configured else '⚠️  not configured'}")
        logger.info(f"  Twilio: {'✅ configured' if self.twilio_configured else '⚠️  not configured'}")
        logger.info(f"  Kafka: {'enabled' if self.kafka_enabled else 'disabled (in-memory queue)'}")
        logger.info(f"  Database: {self.DATABASE_URL.split('@')[-1]}")  # Hide credentials

        for issue in self.validate():
            logger.warning(f"  ⚠️  {issue}")


# Singleton instance
config = Config()


@lru_cache(maxsize=1)
def get_config() -> Config:
    """
    Returns the global Config singleton.
    Use this for dependency injection in FastAPI.
    """
    return config

"""
Vercel serverless entry point for TechCorp FTE FastAPI backend.
Wraps the FastAPI app for Vercel's Python runtime.
"""
import sys
import os

# Add parent directory to path so backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force DEMO mode on Vercel (no Kafka/Gmail/Twilio setup required)
os.environ.setdefault("DRY_RUN", "true")
os.environ.setdefault("LOG_LEVEL", "INFO")

from backend.api.main import app  # noqa: F401 — Vercel uses `app`

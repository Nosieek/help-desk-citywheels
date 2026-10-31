import os
from datetime import datetime, timezone

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
MAX_ITERATIONS = 10
MAX_TOKENS = 1024

# 2026-06-10 09:00 Europe/Warsaw (fixed "current date" from README.md)
REFERENCE_NOW = datetime(2026, 6, 10, 7, 0, 0, tzinfo=timezone.utc)

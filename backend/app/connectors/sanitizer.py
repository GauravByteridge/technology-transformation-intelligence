"""
Message sanitizer for connector exception messages.

WARNING: This module is a DEFENSE LAYER, not the sole security boundary.
It strips credential-bearing patterns from exception messages before they are
propagated to callers, logged, or returned in API responses. However, the
primary security controls are:
  1. Never passing credentials into error-raising code paths where possible.
  2. Database-level credential isolation (least-privilege roles).
  3. Structured logging with credential filtering (app.config.logging).

This sanitizer acts as a safety net — if an underlying driver (asyncpg, Motor)
embeds credentials in its exception text, this layer redacts them before the
message leaves the connector boundary.

Patterns are adapted from _LOG_SENSITIVE_PATTERNS in app/config/logging.py
but tuned for the structure of database driver exception messages.
"""

import re

# Patterns that identify credential-like values in exception messages.
# Each pattern is compiled once at module load for performance.
_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    # password/pwd/passwd assignments (e.g., password=secret123, pwd: mysecret)
    re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+"),
    # api_key/secret_key/apikey assignments
    re.compile(r"(?i)(api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*\S+"),
    # token/bearer assignments
    re.compile(r"(?i)(token|bearer)\s*[:=]\s*\S+"),
    # private_key assignments
    re.compile(r"(?i)(private[_-]?key)\s*[:=]\s*\S+"),
    # PostgreSQL connection URIs with embedded credentials
    re.compile(r"postgresql(\+\w+)?://\S+:\S+@"),
    # MongoDB connection URIs with embedded credentials
    re.compile(r"mongodb(\+srv)?://\S+:\S+@"),
]

_REDACTED = "[REDACTED]"


def sanitize_message(message: str) -> str:
    """Strip credential-bearing patterns from an exception message.

    Scans the input for known credential patterns (passwords, API keys,
    tokens, private keys, and database connection URIs with embedded
    credentials) and replaces matches with '[REDACTED]'.

    Non-credential portions of the message are preserved intact.

    Args:
        message: The raw exception or error message to sanitize.

    Returns:
        The sanitized message with all credential patterns replaced.
    """
    sanitized = message
    for pattern in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(_REDACTED, sanitized)
    return sanitized

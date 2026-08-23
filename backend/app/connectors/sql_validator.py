"""Application-level read-only SQL validation for PostgreSQL queries.

This module provides EARLY REJECTION of obviously prohibited SQL as the first
layer (Layer 1) of defense-in-depth. It is NOT a complete SQL parser and does
NOT guarantee catching all write operations.

The safety guarantee comes from the combination of:
  1. This validator — catches common prohibited patterns early with clear errors
  2. SET TRANSACTION READ ONLY at the session level (Layer 2) — enforced by
     PostgreSQL, which rejects ANY write attempt including data-modifying CTEs
  3. Read-only database credentials (Layer 3) — SELECT-only grants as baseline

Data-modifying CTEs (e.g., ``WITH deleted AS (DELETE FROM users RETURNING *)
SELECT * FROM deleted``) start with WITH — not a prohibited keyword — so they
pass this validator's token inspection. They are BLOCKED by PostgreSQL's
SET TRANSACTION READ ONLY enforcement (Layer 2), which raises:
``ERROR: cannot execute DELETE in a read-only transaction``
"""

import re

from app.errors.datasource_errors import QueryValidationError

PROHIBITED_STATEMENTS: frozenset[str] = frozenset({
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
})

_COMMENT_PATTERN: re.Pattern[str] = re.compile(
    r"(--[^\n]*)|(/\*[\s\S]*?\*/)",
    re.MULTILINE,
)


def validate_read_only_sql(sql: str, source_type: str = "postgresql") -> None:
    """Validate that SQL is safe for read-only execution.

    Performs three sequential checks:
      1. Non-empty/whitespace
      2. No multi-statement (semicolons outside single-quoted string literals)
      3. First token not in PROHIBITED_STATEMENTS

    NOTE: This is an early-rejection layer only. Data-modifying CTEs and other
    advanced write patterns are caught by SET TRANSACTION READ ONLY at the
    PostgreSQL session level.

    Args:
        sql: Raw SQL string to validate.
        source_type: Source type label for error context (default "postgresql").

    Raises:
        QueryValidationError: If SQL is empty, multi-statement, or starts with
            a prohibited keyword.
    """
    if not sql or not sql.strip():
        raise QueryValidationError(
            source_type=source_type,
            message="Query must not be empty",
        )

    if _is_multi_statement(sql):
        raise QueryValidationError(
            source_type=source_type,
            message="Multi-statement queries are not permitted",
        )

    cleaned = _strip_comments(sql)
    token = _get_first_token(cleaned)

    if token.upper() in PROHIBITED_STATEMENTS:
        raise QueryValidationError(
            source_type=source_type,
            message=f"Only read-only (SELECT) queries are permitted. Prohibited: {token.upper()}",
        )


def _strip_comments(sql: str) -> str:
    """Remove SQL comments (-- line comments and /* block comments */)."""
    return _COMMENT_PATTERN.sub("", sql)


def _is_multi_statement(sql: str) -> bool:
    """Detect semicolons that indicate multiple statements.

    Ignores semicolons inside single-quoted string literals. Walks the string
    character-by-character to track whether we are inside a literal.
    """
    in_single_quote = False
    i = 0
    length = len(sql)

    while i < length:
        char = sql[i]

        if char == "'" and not in_single_quote:
            in_single_quote = True
        elif char == "'" and in_single_quote:
            # Handle escaped single quotes ('')
            if i + 1 < length and sql[i + 1] == "'":
                i += 1  # skip the escaped quote
            else:
                in_single_quote = False
        elif char == ";" and not in_single_quote:
            # Found a semicolon outside a string literal
            # Check if there's any meaningful content after it
            remaining = sql[i + 1:].strip()
            if remaining:
                return True
        i += 1

    return False


def _get_first_token(sql: str) -> str:
    """Extract the first significant word from cleaned SQL.

    Strips leading whitespace and returns the first contiguous word.
    """
    stripped = sql.strip()
    if not stripped:
        return ""
    # Split on any whitespace and take the first token
    return stripped.split()[0]

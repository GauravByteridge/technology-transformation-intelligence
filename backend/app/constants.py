"""
Application-wide constants.

SYSTEM_USER_ID is the single source of truth for the temporary stub
user identity used until authentication is implemented.
"""

from uuid import UUID

# TODO(AUTH): Replace with authenticated user resolution once identity
# provider integration is complete. Until then, all created_by and
# user_id fields use this constant.
SYSTEM_USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")

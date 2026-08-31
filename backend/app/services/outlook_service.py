"""Outlook service — delegated OAuth 2.0 (authorization-code) + Microsoft Graph.

Lightweight sibling of GmailService. Uses an EXISTING Microsoft Entra App
Registration (delegated Microsoft Graph permission: Mail.Read) to authenticate
a user via the authorization-code flow and call Microsoft Graph on their behalf.

This is a connectivity POC only:
- No application/client-credentials flow.
- No Power Automate.
- No RAG ingestion / attachments (added later).

Token storage mirrors the Gmail integration's lightweight approach: tokens are
persisted to a local JSON file (outlook_token.json) and auto-refreshed via the
stored refresh token. The client secret is only ever used server-side and is
never logged or returned to the frontend.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# Delegated scopes: Mail.Read (Graph) + standard OpenID Connect / refresh scopes.
OUTLOOK_SCOPES = "openid profile email offline_access https://graph.microsoft.com/Mail.Read"


class OutlookAuthError(Exception):
    """Raised when Outlook/Graph authentication fails.

    The `message` is safe to surface to the user (never contains the client
    secret). Optional `status` carries an upstream HTTP status when relevant.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class OutlookService:
    """Delegated OAuth + Microsoft Graph client for Outlook mail (Mail.Read)."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        token_file: str = "./outlook_token.json",
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._token_path = Path(token_file)

    # --- OAuth endpoints (tenant-scoped) ---

    @property
    def _authorize_url(self) -> str:
        return f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/authorize"

    @property
    def _token_url(self) -> str:
        return f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"

    # --- Authorization-code flow ---

    def get_auth_url(self, state: str = "") -> str:
        """Build the Microsoft OAuth authorization URL for the delegated flow."""
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "response_mode": "query",
            "scope": OUTLOOK_SCOPES,
            "state": state,
            "prompt": "select_account",
        }
        return f"{self._authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange an authorization code for tokens (server-side).

        Raises:
            OutlookAuthError: With a user-safe message on any failure. The
                Microsoft error `description` is surfaced (it never contains
                the client secret) to make redirect-URI / consent / tenant
                misconfiguration obvious.
        """
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
            "scope": OUTLOOK_SCOPES,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._token_url, data=payload, timeout=15.0)

        if response.status_code != 200:
            raise OutlookAuthError(self._describe_token_error(response), status=response.status_code)

        self._save_tokens(self._tokens_from_response(response.json()))
        return self._load_tokens() or {}

    async def refresh_access_token(self) -> str:
        """Use the stored refresh token to obtain a new access token."""
        tokens = self._load_tokens()
        if not tokens or not tokens.get("refresh_token"):
            raise OutlookAuthError("Not authenticated — no refresh token available.")

        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": tokens["refresh_token"],
            "grant_type": "refresh_token",
            "scope": OUTLOOK_SCOPES,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._token_url, data=payload, timeout=15.0)

        if response.status_code != 200:
            # Refresh failed — clear tokens so the user is prompted to re-auth.
            self._clear_tokens()
            raise OutlookAuthError(self._describe_token_error(response), status=response.status_code)

        new_tokens = self._tokens_from_response(response.json())
        # Preserve the previous refresh_token if the response omits one.
        if not new_tokens.get("refresh_token"):
            new_tokens["refresh_token"] = tokens.get("refresh_token", "")
        self._save_tokens(new_tokens)
        return new_tokens["access_token"]

    async def get_valid_access_token(self) -> str:
        """Return a valid access token, refreshing if it is expired/near expiry."""
        tokens = self._load_tokens()
        if not tokens or not tokens.get("access_token"):
            raise OutlookAuthError("Not authenticated — no tokens stored. Connect Outlook first.")

        if time.time() >= tokens.get("expires_at", 0) - 120:
            return await self.refresh_access_token()
        return tokens["access_token"]

    def is_connected(self) -> bool:
        """True if an access token is stored (does not validate it against Graph)."""
        tokens = self._load_tokens()
        return bool(tokens and tokens.get("access_token"))

    # --- Microsoft Graph calls ---

    async def get_me(self) -> dict:
        """GET /me — the authenticated user's profile."""
        return await self._graph_get("/me")

    async def get_messages(self, top: int = 5) -> list[dict]:
        """GET /me/messages?$top=N — lightweight recent message metadata."""
        params = {
            "$top": str(top),
            "$select": "id,subject,from,receivedDateTime",
            "$orderby": "receivedDateTime desc",
        }
        data = await self._graph_get("/me/messages", params=params)
        return data.get("value", []) if isinstance(data, dict) else []

    async def fetch_emails(self, keywords: str = "", max_results: int = 10) -> list[dict]:
        """Fetch Outlook emails, optionally filtered by a keyword search.

        Mirrors GmailService.fetch_emails: returns parsed email dicts with
        subject, sender, date, body_preview, and supported attachment metadata.

        Args:
            keywords: Free-text search. Uses Microsoft Graph $search (KQL-like);
                the frontend passes project name/code (joined with OR) or manual
                keywords, same as Gmail.
            max_results: Maximum number of emails to fetch (capped by Graph).

        Returns:
            List of email dicts with the same shape the frontend expects.
        """
        params: dict = {
            "$top": str(max_results),
            "$select": "id,subject,from,receivedDateTime,bodyPreview,hasAttachments",
        }
        headers_extra: dict = {}

        if keywords and keywords.strip():
            # $search cannot be combined with $orderby on messages.
            params["$search"] = f'"{keywords.strip()}"'
            # $search on messages requires the ConsistencyLevel header.
            headers_extra["ConsistencyLevel"] = "eventual"
        else:
            params["$orderby"] = "receivedDateTime desc"

        data = await self._graph_get("/me/messages", params=params, extra_headers=headers_extra)
        messages = data.get("value", []) if isinstance(data, dict) else []

        emails: list[dict] = []
        for msg in messages:
            message_id = msg.get("id", "")
            attachments: list[dict] = []
            if msg.get("hasAttachments"):
                attachments = await self._fetch_attachment_metadata(message_id)

            sender = ""
            from_field = msg.get("from") or {}
            if isinstance(from_field, dict):
                sender = (from_field.get("emailAddress") or {}).get("address", "")

            emails.append({
                "message_id": message_id,
                "subject": msg.get("subject", "(No Subject)"),
                "sender": sender,
                "date": msg.get("receivedDateTime", ""),
                "body_preview": msg.get("bodyPreview", "") or "",
                "attachments": attachments,
                "has_attachments": len(attachments) > 0,
            })

        return emails

    async def _fetch_attachment_metadata(self, message_id: str) -> list[dict]:
        """List supported attachments for a message (metadata only, no bytes)."""
        params = {"$select": "id,name,contentType,size"}
        try:
            data = await self._graph_get(
                f"/me/messages/{message_id}/attachments", params=params
            )
        except OutlookAuthError:
            return []

        attachments: list[dict] = []
        for att in data.get("value", []) if isinstance(data, dict) else []:
            filename = att.get("name", "") or ""
            if not filename or "." not in filename:
                continue
            ext = "." + filename.rsplit(".", 1)[-1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            attachments.append({
                "attachment_id": att.get("id", ""),
                "filename": filename,
                "mime_type": att.get("contentType", ""),
                "size": att.get("size", 0),
            })
        return attachments

    async def get_full_body(self, message_id: str) -> str:
        """Fetch the full plain-text body for a message (falls back to HTML→text)."""
        params = {"$select": "body,bodyPreview"}
        try:
            msg = await self._graph_get(f"/me/messages/{message_id}", params=params)
        except OutlookAuthError:
            return ""
        body = msg.get("body") or {}
        content = body.get("content", "") if isinstance(body, dict) else ""
        content_type = body.get("contentType", "") if isinstance(body, dict) else ""
        if content_type.lower() == "html":
            content = self.html_to_text(content)
        return content or msg.get("bodyPreview", "") or ""

    async def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download a file attachment's bytes via Graph (Base64 contentBytes)."""
        data = await self._graph_get(
            f"/me/messages/{message_id}/attachments/{attachment_id}"
        )
        content_bytes = data.get("contentBytes", "") if isinstance(data, dict) else ""
        if not content_bytes:
            raise OutlookAuthError("Attachment has no downloadable content.")
        return base64.b64decode(content_bytes)

    @staticmethod
    def html_to_text(content: str) -> str:
        """Convert HTML email content to clean plain text (lightweight, no deps)."""
        import re

        if not content:
            return ""
        if "<" not in content:
            return content.strip()
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", content)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</(p|div|li)>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        for entity, char in {
            "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
            "&quot;": '"', "&#39;": "'", "&apos;": "'",
        }.items():
            text = text.replace(entity, char)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return text.strip()

    async def _graph_get(
        self, path: str, params: dict | None = None, extra_headers: dict | None = None
    ) -> dict:
        """Perform an authenticated Graph GET, refreshing the token on a 401 once.

        Raises:
            OutlookAuthError: With clear messages for 401 (expired/invalid token)
                and 403 (insufficient permissions / consent) and other statuses.
        """
        access_token = await self.get_valid_access_token()

        async def _do(token: str) -> httpx.Response:
            headers = {"Authorization": f"Bearer {token}"}
            if extra_headers:
                headers.update(extra_headers)
            async with httpx.AsyncClient() as client:
                return await client.get(
                    f"{GRAPH_API_BASE}{path}",
                    headers=headers,
                    params=params,
                    timeout=30.0,
                )

        response = await _do(access_token)

        if response.status_code == 401:
            # Token may have just expired — refresh once and retry.
            try:
                access_token = await self.refresh_access_token()
            except OutlookAuthError:
                raise OutlookAuthError(
                    "Microsoft Graph returned 401 (token expired or invalid). Please reconnect Outlook.",
                    status=401,
                )
            response = await _do(access_token)

        if response.status_code == 401:
            raise OutlookAuthError(
                "Microsoft Graph returned 401 (token expired or invalid). Please reconnect Outlook.",
                status=401,
            )
        if response.status_code == 403:
            raise OutlookAuthError(
                "Microsoft Graph returned 403 (insufficient permissions). Ensure delegated "
                "Mail.Read is consented for this account.",
                status=403,
            )
        if response.status_code != 200:
            raise OutlookAuthError(
                f"Microsoft Graph request failed ({response.status_code}).",
                status=response.status_code,
            )

        return response.json()

    # --- Token persistence (lightweight, mirrors Gmail) ---

    def _tokens_from_response(self, data: dict) -> dict:
        return {
            "access_token": data.get("access_token", ""),
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": int(time.time()) + int(data.get("expires_in", 3600)),
            "scope": data.get("scope", ""),
        }

    def _save_tokens(self, tokens: dict) -> None:
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(json.dumps(tokens), encoding="utf-8")

    def _load_tokens(self) -> dict | None:
        if not self._token_path.exists():
            return None
        try:
            return json.loads(self._token_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _clear_tokens(self) -> None:
        if self._token_path.exists():
            self._token_path.unlink()

    # --- Error helpers (never leak the client secret) ---

    @staticmethod
    def _describe_token_error(response: httpx.Response) -> str:
        """Build a user-safe message from a Microsoft token error response.

        Microsoft returns {"error": ..., "error_description": ...}. The
        description explains redirect-URI mismatch, invalid client, invalid
        tenant, consent problems, etc. It never contains the client secret.
        """
        try:
            body = response.json()
        except (json.JSONDecodeError, ValueError):
            return f"Token request failed (HTTP {response.status_code})."

        error = str(body.get("error", "invalid_request"))
        description = str(body.get("error_description", "")).splitlines()
        first_line = description[0] if description else ""

        hints = {
            "invalid_client": "Invalid client ID or client secret.",
            "unauthorized_client": "The app is not authorized for this flow. Check the App Registration.",
            "invalid_grant": "Authorization code invalid/expired or redirect URI mismatch.",
            "invalid_request": "Invalid request — often a redirect URI mismatch.",
            "consent_required": "Admin/user consent required for the requested scopes (Mail.Read).",
            "access_denied": "User or admin denied consent.",
            "invalid_scope": "Requested scope is invalid or not permitted for this app.",
        }
        hint = hints.get(error, "")
        parts = [p for p in [f"[{error}]", hint, first_line] if p]
        return " ".join(parts) or f"Token request failed (HTTP {response.status_code})."

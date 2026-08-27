"""Gmail service for OAuth 2.0 and Gmail API interactions.

Adapted from the email-rag POC for integration into the main platform.
Handles token management, email fetching by keyword, and attachment downloading.
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

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

SUPPORTED_ATTACHMENT_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "text/plain",
    "application/octet-stream",
}
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"}


class GmailAuthError(Exception):
    """Raised when Gmail authentication fails."""
    pass


class GmailService:
    """Handles OAuth flow and Gmail API interactions."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        token_file: str = "./gmail_token.json",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._token_path = Path(token_file)

    def get_auth_url(self, state: str = "") -> str:
        """Generate Google OAuth consent URL."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": GMAIL_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for tokens."""
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload, timeout=10.0)

        if response.status_code != 200:
            raise GmailAuthError("Authorization code exchange failed")

        data = response.json()
        tokens = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": int(time.time()) + data.get("expires_in", 3600),
        }
        self._save_tokens(tokens)
        return tokens

    async def refresh_access_token(self) -> str:
        """Use stored refresh token to get a new access token."""
        tokens = self._load_tokens()
        if not tokens or not tokens.get("refresh_token"):
            raise GmailAuthError("No refresh token available")

        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": tokens["refresh_token"],
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload, timeout=10.0)

        if response.status_code != 200:
            self._clear_tokens()
            raise GmailAuthError("Token refresh failed")

        data = response.json()
        tokens["access_token"] = data["access_token"]
        tokens["expires_at"] = int(time.time()) + data.get("expires_in", 3600)
        self._save_tokens(tokens)
        return tokens["access_token"]

    async def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if expired."""
        tokens = self._load_tokens()
        if not tokens:
            raise GmailAuthError("Not authenticated — no tokens stored")

        if time.time() >= tokens.get("expires_at", 0) - 100:
            return await self.refresh_access_token()
        return tokens["access_token"]

    def is_connected(self) -> bool:
        """Check if tokens exist."""
        tokens = self._load_tokens()
        return tokens is not None and "access_token" in tokens

    async def get_user_email(self) -> str:
        """Fetch authenticated user's email address."""
        access_token = await self.get_valid_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GMAIL_API_BASE}/users/me/profile",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
        if response.status_code != 200:
            raise GmailAuthError("Failed to fetch user email")
        return response.json().get("emailAddress", "")

    async def fetch_emails(self, keywords: str = "", max_results: int = 10) -> list[dict]:
        """Fetch emails from Gmail with optional keyword search.

        Args:
            keywords: Gmail search query (same syntax as Gmail search bar).
            max_results: Maximum number of emails to fetch.

        Returns:
            List of email dicts with subject, sender, date, body, attachments.
        """
        access_token = await self.get_valid_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            params: dict = {"maxResults": max_results}
            if keywords:
                params["q"] = keywords

            list_response = await client.get(
                f"{GMAIL_API_BASE}/users/me/messages",
                headers=headers,
                params=params,
                timeout=15.0,
            )

            if list_response.status_code == 401:
                access_token = await self.refresh_access_token()
                headers = {"Authorization": f"Bearer {access_token}"}
                list_response = await client.get(
                    f"{GMAIL_API_BASE}/users/me/messages",
                    headers=headers,
                    params=params,
                    timeout=15.0,
                )

            if list_response.status_code != 200:
                raise GmailAuthError(f"Failed to list emails: {list_response.status_code}")

            messages_list = list_response.json().get("messages", [])
            emails = []

            for msg_info in messages_list:
                msg_response = await client.get(
                    f"{GMAIL_API_BASE}/users/me/messages/{msg_info['id']}",
                    headers=headers,
                    params={"format": "full"},
                    timeout=15.0,
                )
                if msg_response.status_code != 200:
                    continue

                msg_data = msg_response.json()
                email = self._parse_message(msg_data)
                emails.append(email)

        return emails

    async def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download an attachment by message_id and attachment_id."""
        access_token = await self.get_valid_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GMAIL_API_BASE}/users/me/messages/{message_id}/attachments/{attachment_id}",
                headers=headers,
                timeout=30.0,
            )

        if response.status_code == 401:
            access_token = await self.refresh_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{GMAIL_API_BASE}/users/me/messages/{message_id}/attachments/{attachment_id}",
                    headers=headers,
                    timeout=30.0,
                )

        if response.status_code != 200:
            raise GmailAuthError(f"Failed to download attachment: {response.status_code}")

        data = response.json().get("data", "")
        return base64.urlsafe_b64decode(data + "==")

    # --- Private helpers ---

    def _parse_message(self, msg_data: dict) -> dict:
        """Parse a raw Gmail API message into a structured dict."""
        headers = msg_data.get("payload", {}).get("headers", [])
        header_map = {h["name"].lower(): h["value"] for h in headers}

        body = self._extract_body(msg_data.get("payload", {}))
        attachments = self._extract_attachments(msg_data.get("payload", {}))

        return {
            "message_id": msg_data.get("id", ""),
            "thread_id": msg_data.get("threadId", ""),
            "subject": header_map.get("subject", "(No Subject)"),
            "sender": header_map.get("from", ""),
            "date": header_map.get("date", ""),
            "body_preview": body[:300] if body else "",
            "attachments": attachments,
            "has_attachments": len(attachments) > 0,
        }

    def _extract_attachments(self, payload: dict) -> list[dict]:
        """Extract supported attachment metadata from message parts."""
        attachments: list[dict] = []
        self._collect_attachments(payload.get("parts", []), attachments)
        return attachments

    def _collect_attachments(self, parts: list[dict], attachments: list[dict]) -> None:
        """Recursively collect attachment info."""
        for part in parts:
            filename = part.get("filename", "")
            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            attachment_id = body.get("attachmentId", "")

            if filename and attachment_id:
                ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
                if mime_type in SUPPORTED_ATTACHMENT_MIMES or ext in SUPPORTED_EXTENSIONS:
                    attachments.append({
                        "filename": filename,
                        "mime_type": mime_type,
                        "size": body.get("size", 0),
                        "attachment_id": attachment_id,
                    })

            nested = part.get("parts", [])
            if nested:
                self._collect_attachments(nested, attachments)

    def _extract_body(self, payload: dict) -> str:
        """Extract body text preferring text/plain over text/html."""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain":
            return self._decode_body(payload.get("body", {}))

        parts = payload.get("parts", [])
        if not parts:
            return self._decode_body(payload.get("body", {}))

        for part in parts:
            if part.get("mimeType") == "text/plain":
                return self._decode_body(part.get("body", {}))

        for part in parts:
            if part.get("mimeType") == "text/html":
                return self._decode_body(part.get("body", {}))

        for part in parts:
            if part.get("mimeType", "").startswith("multipart/"):
                result = self._extract_body(part)
                if result:
                    return result

        return ""

    def _decode_body(self, body: dict) -> str:
        """Decode base64url-encoded body data."""
        data = body.get("data", "")
        if not data:
            return ""
        try:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        except Exception:
            return ""

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

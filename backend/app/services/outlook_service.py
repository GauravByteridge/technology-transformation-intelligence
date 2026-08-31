"""Outlook service for OAuth 2.0 and Microsoft Graph API interactions.

Mirrors the GmailService pattern but targets Microsoft Graph so users can
fetch mail from a personal or organizational Outlook / Microsoft 365 account.
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

# Azure AD (Microsoft identity platform) v2.0 endpoints.
# `{tenant}` is substituted at runtime — "common" supports both personal and
# work/school accounts, "organizations" restricts to work/school only.
MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# `offline_access` is required to receive a refresh token.
OUTLOOK_SCOPE = "offline_access User.Read Mail.Read"

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

# Graph attachment type discriminator for a regular file attachment.
FILE_ATTACHMENT_TYPE = "#microsoft.graph.fileAttachment"


class OutlookAuthError(Exception):
    """Raised when Outlook authentication fails."""

    pass


class OutlookService:
    """Handles OAuth flow and Microsoft Graph mail API interactions."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        tenant: str = "common",
        token_file: str = "./outlook_token.json",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._tenant = tenant or "common"
        self._token_path = Path(token_file)

    @property
    def _auth_url(self) -> str:
        return MICROSOFT_AUTH_URL.format(tenant=self._tenant)

    @property
    def _token_url(self) -> str:
        return MICROSOFT_TOKEN_URL.format(tenant=self._tenant)

    def get_auth_url(self, state: str = "") -> str:
        """Generate Microsoft OAuth consent URL."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": OUTLOOK_SCOPE,
            "response_mode": "query",
            "prompt": "consent",
            "state": state,
        }
        return f"{self._auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for tokens."""
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
            "scope": OUTLOOK_SCOPE,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._token_url, data=payload, timeout=10.0)

        if response.status_code != 200:
            raise OutlookAuthError("Authorization code exchange failed")

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
            raise OutlookAuthError("No refresh token available")

        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": tokens["refresh_token"],
            "grant_type": "refresh_token",
            "scope": OUTLOOK_SCOPE,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self._token_url, data=payload, timeout=10.0)

        if response.status_code != 200:
            self._clear_tokens()
            raise OutlookAuthError("Token refresh failed")

        data = response.json()
        tokens["access_token"] = data["access_token"]
        tokens["expires_at"] = int(time.time()) + data.get("expires_in", 3600)
        # Microsoft may rotate the refresh token — persist the new one if present.
        if data.get("refresh_token"):
            tokens["refresh_token"] = data["refresh_token"]
        self._save_tokens(tokens)
        return tokens["access_token"]

    async def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if expired."""
        tokens = self._load_tokens()
        if not tokens:
            raise OutlookAuthError("Not authenticated — no tokens stored")

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
                f"{GRAPH_API_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
        if response.status_code != 200:
            raise OutlookAuthError("Failed to fetch user email")
        data = response.json()
        # Personal accounts may not populate `mail`; fall back to UPN.
        return data.get("mail") or data.get("userPrincipalName", "")

    async def fetch_emails(self, keywords: str = "", max_results: int = 10) -> list[dict]:
        """Fetch emails from Outlook with optional keyword search.

        Args:
            keywords: Free-text search applied via Graph `$search`.
            max_results: Maximum number of emails to fetch.

        Returns:
            List of email dicts with subject, sender, date, body, attachments.
        """
        access_token = await self.get_valid_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        params: dict = {
            "$top": max_results,
            "$select": "id,conversationId,subject,from,receivedDateTime,bodyPreview,body,hasAttachments",
        }
        if keywords:
            # Graph requires the $search value to be a quoted string.
            params["$search"] = f'"{keywords}"'
        else:
            # $orderby is not allowed together with $search, so only sort when
            # there is no search term.
            params["$orderby"] = "receivedDateTime desc"

        async with httpx.AsyncClient() as client:
            list_response = await client.get(
                f"{GRAPH_API_BASE}/me/messages",
                headers=headers,
                params=params,
                timeout=15.0,
            )

            if list_response.status_code == 401:
                access_token = await self.refresh_access_token()
                headers = {"Authorization": f"Bearer {access_token}"}
                list_response = await client.get(
                    f"{GRAPH_API_BASE}/me/messages",
                    headers=headers,
                    params=params,
                    timeout=15.0,
                )

            if list_response.status_code != 200:
                raise OutlookAuthError(f"Failed to list emails: {list_response.status_code}")

            messages_list = list_response.json().get("value", [])
            emails = []

            for msg_data in messages_list:
                email = self._parse_message(msg_data)
                # Graph does not return attachment metadata inline; fetch it
                # when the message flags that attachments are present.
                if email["has_attachments"]:
                    email["attachments"] = await self._list_attachments(
                        client, headers, email["message_id"]
                    )
                emails.append(email)

        return emails

    async def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download an attachment by message_id and attachment_id."""
        access_token = await self.get_valid_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{GRAPH_API_BASE}/me/messages/{message_id}/attachments/{attachment_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0)

            if response.status_code == 401:
                access_token = await self.refresh_access_token()
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(url, headers=headers, timeout=30.0)

        if response.status_code != 200:
            raise OutlookAuthError(f"Failed to download attachment: {response.status_code}")

        content_bytes = response.json().get("contentBytes", "")
        return base64.b64decode(content_bytes)

    # --- Private helpers ---

    async def _list_attachments(
        self, client: httpx.AsyncClient, headers: dict, message_id: str
    ) -> list[dict]:
        """List supported file-attachment metadata for a message."""
        response = await client.get(
            f"{GRAPH_API_BASE}/me/messages/{message_id}/attachments",
            headers=headers,
            params={"$select": "id,name,contentType,size,@odata.type"},
            timeout=15.0,
        )
        if response.status_code != 200:
            return []

        attachments: list[dict] = []
        for att in response.json().get("value", []):
            if att.get("@odata.type") != FILE_ATTACHMENT_TYPE:
                continue

            filename = att.get("name", "")
            mime_type = att.get("contentType", "")
            ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
            if mime_type in SUPPORTED_ATTACHMENT_MIMES or ext in SUPPORTED_EXTENSIONS:
                attachments.append({
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": att.get("size", 0),
                    "attachment_id": att.get("id", ""),
                })
        return attachments

    def _parse_message(self, msg_data: dict) -> dict:
        """Parse a raw Graph message resource into a structured dict."""
        sender = msg_data.get("from", {}).get("emailAddress", {})
        sender_str = sender.get("address", "")
        if sender.get("name"):
            sender_str = f"{sender['name']} <{sender_str}>"

        body_preview = msg_data.get("bodyPreview", "")
        if not body_preview:
            body_preview = self._extract_body(msg_data)

        return {
            "message_id": msg_data.get("id", ""),
            "thread_id": msg_data.get("conversationId", ""),
            "subject": msg_data.get("subject") or "(No Subject)",
            "sender": sender_str,
            "date": msg_data.get("receivedDateTime", ""),
            "body_preview": body_preview[:300] if body_preview else "",
            "attachments": [],
            "has_attachments": bool(msg_data.get("hasAttachments", False)),
        }

    def _extract_body(self, msg_data: dict) -> str:
        """Extract the message body content from a Graph message resource."""
        body = msg_data.get("body", {})
        return body.get("content", "") or ""

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

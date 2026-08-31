"""Lightweight unit tests for the Outlook delegated-OAuth service.

These tests cover the pure, dependency-free logic of OutlookService: building
the Microsoft authorization URL with the correct delegated scopes, token
persistence/refresh bookkeeping, connection state, and user-safe error
messages (which must never contain the client secret). Network calls to
Microsoft Graph / the token endpoint are not made here.

Run:
    cd backend
    .venv\\Scripts\\python -m pytest tests/test_outlook_service.py -v
"""

import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.services.outlook_service import (
    OUTLOOK_SCOPES,
    OutlookAuthError,
    OutlookService,
)


@pytest.fixture()
def service(tmp_path) -> OutlookService:
    return OutlookService(
        tenant_id="tenant-123",
        client_id="client-abc",
        client_secret="super-secret-value",
        redirect_uri="http://localhost:8000/api/v1/outlook/auth/callback",
        token_file=str(tmp_path / "outlook_token.json"),
    )


# --- Authorization URL ---

def test_auth_url_targets_tenant_authorize_endpoint(service: OutlookService):
    url = service.get_auth_url(state="xyz")
    parsed = urlparse(url)
    assert parsed.netloc == "login.microsoftonline.com"
    assert parsed.path == "/tenant-123/oauth2/v2.0/authorize"


def test_auth_url_requests_delegated_scopes(service: OutlookService):
    url = service.get_auth_url(state="xyz")
    qs = parse_qs(urlparse(url).query)
    assert qs["client_id"] == ["client-abc"]
    assert qs["response_type"] == ["code"]
    assert qs["redirect_uri"] == ["http://localhost:8000/api/v1/outlook/auth/callback"]
    assert qs["state"] == ["xyz"]
    scope = qs["scope"][0]
    for required in ["openid", "profile", "email", "offline_access", "Mail.Read"]:
        assert required in scope
    assert scope == OUTLOOK_SCOPES


def test_auth_url_never_contains_client_secret(service: OutlookService):
    assert "super-secret-value" not in service.get_auth_url(state="xyz")


# --- Connection state / token persistence ---

def test_not_connected_when_no_token_file(service: OutlookService):
    assert service.is_connected() is False


def test_connected_after_saving_tokens(service: OutlookService):
    service._save_tokens({
        "access_token": "abc",
        "refresh_token": "ref",
        "expires_at": int(time.time()) + 3600,
    })
    assert service.is_connected() is True


def test_tokens_from_response_sets_expiry(service: OutlookService):
    before = int(time.time())
    tokens = service._tokens_from_response({
        "access_token": "at",
        "refresh_token": "rt",
        "expires_in": 3600,
        "scope": OUTLOOK_SCOPES,
    })
    assert tokens["access_token"] == "at"
    assert tokens["refresh_token"] == "rt"
    assert tokens["expires_at"] >= before + 3500


@pytest.mark.asyncio
async def test_get_valid_access_token_requires_auth(service: OutlookService):
    with pytest.raises(OutlookAuthError):
        await service.get_valid_access_token()


# --- Error message safety (never leak the client secret) ---

def _resp(status_code: int, json_body: dict) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_body)


def test_describe_token_error_invalid_client(service: OutlookService):
    msg = OutlookService._describe_token_error(
        _resp(401, {"error": "invalid_client", "error_description": "AADSTS7000215: bad secret"})
    )
    assert "invalid_client" in msg
    assert "Invalid client ID or client secret" in msg
    assert "super-secret-value" not in msg


def test_describe_token_error_redirect_mismatch(service: OutlookService):
    msg = OutlookService._describe_token_error(
        _resp(400, {"error": "invalid_grant", "error_description": "AADSTS50011: redirect URI mismatch"})
    )
    assert "invalid_grant" in msg
    assert "redirect uri" in msg.lower()


def test_describe_token_error_consent(service: OutlookService):
    msg = OutlookService._describe_token_error(
        _resp(400, {"error": "consent_required", "error_description": "AADSTS65001: consent needed"})
    )
    assert "consent" in msg.lower()


def test_auth_error_carries_status():
    err = OutlookAuthError("boom", status=403)
    assert err.status == 403
    assert err.message == "boom"


# --- HTML → text (email bodies from Graph may be HTML) ---

def test_html_to_text_strips_tags_and_scripts():
    html = "<style>.x{}</style><p>Hello <b>World</b></p><script>bad()</script>"
    text = OutlookService.html_to_text(html)
    assert "Hello" in text and "World" in text
    assert "bad()" not in text
    assert "<" not in text


def test_html_to_text_passthrough_plain():
    assert OutlookService.html_to_text("just text") == "just text"


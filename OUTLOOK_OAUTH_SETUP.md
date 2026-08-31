# Outlook Integration — Delegated OAuth Connectivity POC

Outlook connects using an **existing Microsoft Entra App Registration** with the
delegated Microsoft Graph permission **`Mail.Read`**, via the OAuth
**authorization-code** flow. No Power Automate, no application/client-credentials
flow, no new App Registration.

```
Browser → Microsoft login → delegated Mail.Read consent → OAuth callback
        → backend exchanges code for tokens → Microsoft Graph /me + /me/messages
```

This stage is connectivity-only: no RAG ingestion, attachments, or filtering yet.

---

## Backend endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/outlook/status` | Whether Outlook is connected (tokens present) |
| `GET` | `/api/v1/outlook/auth/login` | Redirects the browser to Microsoft consent |
| `GET` | `/api/v1/outlook/auth/callback` | Exchanges the code for tokens (server-side) |
| `GET` | `/api/v1/outlook/test` | Calls Graph `/me` and `/me/messages?$top=5` |

Tokens are stored locally in `backend/outlook_token.json` (mirrors the Gmail
integration's lightweight token file) and auto-refreshed via the refresh token.
The client secret is used server-side only and is never logged or returned.

---

## 1. Environment variables (`backend/.env`)

```
MICROSOFT_TENANT_ID=<your tenant / directory ID>
MICROSOFT_CLIENT_ID=<application (client) ID>
MICROSOFT_CLIENT_SECRET=<client secret VALUE — not the secret ID>
MICROSOFT_REDIRECT_URI=http://localhost:8000/api/v1/outlook/auth/callback
```

`MICROSOFT_REDIRECT_URI` has a sensible default (the callback above) so it's
optional if you use the default; the other three are required. Never put real
values in `.env.example`.

## 2. Redirect URI to register in the App Registration

In the Entra App Registration → **Authentication** → **Web** → **Redirect URIs**,
add EXACTLY:

```
http://localhost:8000/api/v1/outlook/auth/callback
```

(Must match `MICROSOFT_REDIRECT_URI` character-for-character, including scheme,
host, port, and path.)

## 3. URL to open in the browser to start authentication

```
http://localhost:8000/api/v1/outlook/auth/login
```

This redirects to Microsoft, prompts for sign-in + consent (`Mail.Read`), then
returns to the backend callback, which stores tokens and redirects to
`http://localhost:5173/sources?outlook=connected`.

You can also start it from the UI: **Data Sources → Outlook → Connect Outlook**.

## 4. Verifying `/me/messages` returned your emails

After connecting, call:

```
http://localhost:8000/api/v1/outlook/test
```

Expected JSON (bodies are intentionally NOT returned):

```json
{
  "connected": true,
  "display_name": "Your Name",
  "email": "you@yourtenant.com",
  "message_count": 5,
  "messages": [
    { "message_id": "AAMk...", "subject": "...", "sender": "...", "received_at": "2026-08-30T10:00:00Z" }
  ]
}
```

- `message_count` > 0 and populated `messages` → `/me/messages` succeeded.
- In the UI, the **Test Connection** button shows the same summary.

---

## Error handling (surfaced clearly)

| Situation | Where it appears | Message |
|-----------|------------------|---------|
| Invalid client ID/secret | callback | `[invalid_client] Invalid client ID or client secret.` |
| Redirect URI mismatch | callback | `[invalid_grant] ... redirect URI ...` |
| Invalid tenant | login/callback | Microsoft error surfaced |
| Consent/permission denied | callback | `[access_denied]` / `[consent_required]` |
| Expired/invalid token (Graph 401) | `/test` | 401 — "reconnect Outlook" |
| Insufficient permission (Graph 403) | `/test` | 403 — "ensure delegated Mail.Read is consented" |

The client secret never appears in any response or log.

---

## Notes

- `outlook_token.json` is git-ignored (added under `*_token.json`).
- Gmail integration is unchanged and continues to use its own token file.

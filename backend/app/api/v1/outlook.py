"""Microsoft Outlook integration API routes — delegated OAuth connectivity POC.

Uses an EXISTING Microsoft Entra App Registration (delegated Microsoft Graph
permission: Mail.Read) with the authorization-code flow. Mirrors the Gmail
integration's structure and lightweight token-file storage.

This stage is a connectivity POC only:
- No Power Automate, no application/client-credentials flow.
- No RAG ingestion / attachment processing yet.

Endpoints:
- GET /api/v1/outlook/status         — is Outlook connected?
- GET /api/v1/outlook/auth/login     — redirect to Microsoft OAuth consent
- GET /api/v1/outlook/auth/callback  — exchange code → tokens (server-side)
- GET /api/v1/outlook/test           — call Graph /me and /me/messages?$top=5
"""

import logging
import secrets
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import SYSTEM_USER_ID
from app.dependencies import get_app_db_session, get_ingestion_orchestrator, get_settings
from app.documents.orchestrator import IngestionOrchestrator
from app.services.outlook_service import OutlookAuthError, OutlookService

logger = logging.getLogger(__name__)

router = APIRouter()

# Frontend location to return to after the OAuth callback (mirrors Gmail).
_FRONTEND_SOURCES_URL = "http://localhost:5173/sources"


# --- Schemas ---

class OutlookStatusResponse(BaseModel):
    connected: bool
    mode: str = "delegated_oauth"


class OutlookMessageSummary(BaseModel):
    message_id: str
    subject: str
    sender: str
    received_at: str


class OutlookTestResponse(BaseModel):
    connected: bool
    display_name: str | None = None
    email: str | None = None
    message_count: int = 0
    messages: list[OutlookMessageSummary] = []


# --- Fetch / RAG schemas (mirror Gmail) ---

class OutlookFetchRequest(BaseModel):
    keywords: str = ""
    max_results: int = 10


class OutlookEmailSummary(BaseModel):
    message_id: str
    subject: str
    sender: str
    date: str
    body_preview: str
    has_attachments: bool
    attachments: list[dict] = []


class OutlookFetchResponse(BaseModel):
    emails: list[OutlookEmailSummary]
    total: int


class OutlookAddToRagRequest(BaseModel):
    message_id: str
    subject: str = "(No Subject)"
    body: str = ""
    project_id: str | None = None
    attachments: list[dict] = []


class OutlookAddAllToRagRequest(BaseModel):
    emails: list[OutlookAddToRagRequest]
    project_id: str | None = None


class OutlookAddToRagResponse(BaseModel):
    success: bool
    documents_indexed: int
    message: str


# --- Helpers ---

def _get_outlook_service() -> OutlookService:
    """Build an OutlookService from settings.

    Raises 503 if the App Registration environment variables are not configured.
    The client secret never leaves the backend and is never logged.
    """
    settings = get_settings()
    tenant_id = getattr(settings, "microsoft_tenant_id", None) or ""
    client_id = getattr(settings, "microsoft_client_id", None) or ""
    client_secret = getattr(settings, "microsoft_client_secret", None) or ""
    redirect_uri = getattr(settings, "microsoft_redirect_uri", None) or ""

    missing = [
        name for name, value in [
            ("MICROSOFT_TENANT_ID", tenant_id),
            ("MICROSOFT_CLIENT_ID", client_id),
            ("MICROSOFT_CLIENT_SECRET", client_secret),
            ("MICROSOFT_REDIRECT_URI", redirect_uri),
        ] if not value
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Outlook integration not configured. Set: " + ", ".join(missing)
            ),
        )

    return OutlookService(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        token_file="./outlook_token.json",
    )


# --- Routes ---

@router.get("/status", response_model=OutlookStatusResponse)
async def outlook_status():
    """Report whether Outlook is connected (tokens present)."""
    try:
        outlook = _get_outlook_service()
    except HTTPException:
        return OutlookStatusResponse(connected=False)
    return OutlookStatusResponse(connected=outlook.is_connected())


@router.get("/auth/login")
async def outlook_auth_login():
    """Redirect the browser to Microsoft's OAuth authorization endpoint.

    Requests delegated scopes: openid profile email offline_access Mail.Read.
    """
    outlook = _get_outlook_service()
    state = secrets.token_urlsafe(16)
    auth_url = outlook.get_auth_url(state=state)
    logger.info("OUTLOOK AUTH LOGIN redirecting to Microsoft consent")
    return RedirectResponse(url=auth_url)


@router.get("/auth/callback")
async def outlook_auth_callback(
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    state: str | None = Query(default=None),  # noqa: ARG001 — reserved for CSRF check
):
    """Handle the Microsoft OAuth callback and exchange the code for tokens."""
    if error:
        # Consent denied / redirect issues arrive here as query params.
        safe_desc = (error_description or "").splitlines()[0] if error_description else ""
        logger.warning("OUTLOOK AUTH CALLBACK error=%s", error)
        raise HTTPException(
            status_code=400,
            detail=f"Authorization failed [{error}] {safe_desc}".strip(),
        )
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    outlook = _get_outlook_service()
    try:
        await outlook.exchange_code(code)
    except OutlookAuthError as exc:
        logger.warning("OUTLOOK AUTH CALLBACK token exchange failed: %s", exc.message)
        raise HTTPException(status_code=400, detail=exc.message)

    logger.info("OUTLOOK AUTH CALLBACK success — tokens stored")
    # Return to the frontend Data Sources page (mirrors Gmail behavior).
    return RedirectResponse(url=f"{_FRONTEND_SOURCES_URL}?outlook=connected")


@router.get("/test", response_model=OutlookTestResponse)
async def outlook_test():
    """Verify delegated connectivity: call Graph /me and /me/messages?$top=5.

    Returns a lightweight summary (no email bodies). Surfaces clear errors for
    unauthenticated/expired tokens (401) and permission/consent issues (403).
    """
    outlook = _get_outlook_service()

    if not outlook.is_connected():
        raise HTTPException(
            status_code=401,
            detail="Not connected to Outlook. Start authentication at /api/v1/outlook/auth/login.",
        )

    try:
        me = await outlook.get_me()
        messages = await outlook.get_messages(top=5)
    except OutlookAuthError as exc:
        logger.warning("OUTLOOK TEST failed: %s", exc.message)
        raise HTTPException(status_code=exc.status or 400, detail=exc.message)

    summaries: list[OutlookMessageSummary] = []
    for msg in messages:
        sender = ""
        from_field = msg.get("from") or {}
        if isinstance(from_field, dict):
            sender = (from_field.get("emailAddress") or {}).get("address", "")
        summaries.append(
            OutlookMessageSummary(
                message_id=msg.get("id", ""),
                subject=msg.get("subject", "(No Subject)"),
                sender=sender,
                received_at=msg.get("receivedDateTime", ""),
            )
        )

    logger.info("OUTLOOK TEST ok — messages=%d", len(summaries))

    return OutlookTestResponse(
        connected=True,
        display_name=me.get("displayName"),
        email=me.get("mail") or me.get("userPrincipalName"),
        message_count=len(summaries),
        messages=summaries,
    )


@router.post("/fetch", response_model=OutlookFetchResponse)
async def fetch_outlook_emails(request: OutlookFetchRequest):
    """Fetch Outlook emails by keyword/project search (mirrors /gmail/fetch).

    The frontend passes either project name+code (joined with OR) or manual
    keywords. Returns email previews without adding to RAG.
    """
    outlook = _get_outlook_service()

    if not outlook.is_connected():
        raise HTTPException(
            status_code=401,
            detail="Not connected to Outlook. Start authentication at /api/v1/outlook/auth/login.",
        )

    try:
        emails = await outlook.fetch_emails(
            keywords=request.keywords,
            max_results=request.max_results,
        )
    except OutlookAuthError as exc:
        logger.warning("OUTLOOK FETCH failed: %s", exc.message)
        raise HTTPException(status_code=exc.status or 502, detail=exc.message)

    summaries = [
        OutlookEmailSummary(
            message_id=e["message_id"],
            subject=e["subject"],
            sender=e["sender"],
            date=e["date"],
            body_preview=e["body_preview"],
            has_attachments=e["has_attachments"],
            attachments=e["attachments"],
        )
        for e in emails
    ]
    return OutlookFetchResponse(emails=summaries, total=len(summaries))


@router.post("/add-to-rag", response_model=OutlookAddToRagResponse)
async def add_outlook_email_to_rag(
    request: OutlookAddToRagRequest,
    orchestrator: IngestionOrchestrator = Depends(get_ingestion_orchestrator),
    session: AsyncSession = Depends(get_app_db_session),
):
    """Add an Outlook email and its attachments to RAG.

    Mirrors /gmail/add-to-rag exactly: the email body is chunked + embedded
    directly (bypasses the content classifier, source_type="email"), and
    attachments go through the content-aware IngestionOrchestrator. Everything
    is associated with the selected project_id.
    """
    from app.documents.chunker import FixedSizeChunker
    from app.documents.embedder import DeterministicEmbeddingGenerator
    from app.models.document import Document, DocumentChunk, Embedding
    from app.models.uploaded_file import UploadedFile
    from app.repositories.document_repository import DocumentRepository

    outlook = _get_outlook_service()
    documents_indexed = 0
    project_id: UUID | None = None
    if request.project_id:
        try:
            project_id = UUID(request.project_id)
        except ValueError:
            pass

    # 1. Fetch the FULL email body from Graph (not just the preview)
    full_body = request.body
    if request.message_id:
        try:
            extracted = await outlook.get_full_body(request.message_id)
            if extracted and len(extracted) > len(full_body):
                full_body = extracted
        except Exception as e:
            logger.warning("OUTLOOK could not fetch full body, using preview: %s", e)

    # 2. Index email body DIRECTLY into RAG (bypass content classifier)
    email_text = f"Subject: {request.subject}\n\n{full_body}"
    if email_text.strip() and len(email_text.strip()) > 10:
        file_record = UploadedFile(
            id=uuid4(),
            file_name=f"outlook_{request.message_id[:8]}_{request.subject[:30]}.txt",
            file_type="txt",
            file_size=len(email_text.encode()),
            project_id=project_id,
            uploaded_by=SYSTEM_USER_ID,
            processing_status="processing",
        )
        session.add(file_record)
        await session.flush()

        chunker = FixedSizeChunker()
        chunks = [c for c in chunker.chunk(email_text) if c.text and c.text.strip()]

        if chunks:
            try:
                try:
                    from app.dependencies import get_embedding_provider
                    from app.documents.embedder import ProductionEmbeddingGenerator
                    embedding_provider = get_embedding_provider()
                    embedding_gen = ProductionEmbeddingGenerator(embedding_provider)
                except (RuntimeError, Exception):
                    embedding_gen = DeterministicEmbeddingGenerator()

                chunk_texts = [c.text for c in chunks]
                embeddings = await embedding_gen.generate(chunk_texts)

                doc_repo = DocumentRepository(session)
                document = Document(
                    project_id=str(project_id) if project_id else str(SYSTEM_USER_ID),
                    file_name=file_record.file_name,
                    file_type="txt",
                    file_size=len(email_text.encode()),
                    source_type="email",
                    uploaded_by=str(SYSTEM_USER_ID),
                    processing_status="completed",
                )
                document = await doc_repo.create_document(document)

                for chunk_result, embedding_vector in zip(chunks, embeddings):
                    chunk_record = DocumentChunk(
                        document_id=str(document.id),
                        chunk_index=chunk_result.chunk_index,
                        content=chunk_result.text,
                        page_number=chunk_result.page_number,
                        section=chunk_result.section,
                    )
                    chunk_record = await doc_repo.create_chunk(chunk_record)

                    embedding_record = Embedding(
                        chunk_id=str(chunk_record.id),
                        embedding=embedding_vector,
                        model_name="all-MiniLM-L6-v2",
                        dimension=len(embedding_vector),
                    )
                    await doc_repo.create_embedding(embedding_record)

                documents_indexed += len(chunks)
                file_record.processing_status = "READY"
                logger.info(
                    "OUTLOOK EMAIL INGESTED message_id=%s chunks=%d project_id=%s",
                    request.message_id, len(chunks), project_id,
                )
            except Exception as e:
                logger.error("OUTLOOK failed to index email body: %s", e)
                file_record.processing_status = "FAILED"

        await session.flush()

    # 3. Download and index attachments (through the normal pipeline)
    for attachment in request.attachments:
        attachment_id = attachment.get("attachment_id", "")
        filename = attachment.get("filename", "attachment")
        if not attachment_id:
            continue

        try:
            file_bytes = await outlook.download_attachment(request.message_id, attachment_id)
        except Exception as e:
            logger.warning("OUTLOOK ATTACHMENT SKIPPED file=%s (download failed: %s)", filename, e)
            continue

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        supported_exts = {"pdf", "docx", "doc", "xlsx", "xls", "csv", "txt"}
        if ext not in supported_exts:
            logger.info("OUTLOOK ATTACHMENT SKIPPED file=%s (unsupported)", filename)
            continue

        file_record = UploadedFile(
            id=uuid4(),
            file_name=filename,
            file_type=ext,
            file_size=len(file_bytes),
            project_id=project_id,
            uploaded_by=SYSTEM_USER_ID,
            processing_status="processing",
        )
        session.add(file_record)
        await session.flush()

        temp_dir = tempfile.mkdtemp(prefix="outlook_att_")
        temp_path = Path(temp_dir) / f"attachment.{ext}"
        temp_path.write_bytes(file_bytes)

        try:
            result = await orchestrator.process_file(
                file_id=file_record.id,
                file_path=str(temp_path),
                file_name=filename,
                file_type=ext,
                file_size=len(file_bytes),
                project_id=project_id,
                uploaded_by=SYSTEM_USER_ID,
            )
            documents_indexed += result.get("documents_indexed", 0)
            file_record.processing_status = result.get("status", "READY")
            await session.flush()
            logger.info("OUTLOOK ATTACHMENT INGESTED file=%s project_id=%s", filename, project_id)
        except Exception as e:
            logger.warning("OUTLOOK ATTACHMENT SKIPPED file=%s (processing failed: %s)", filename, e)
            file_record.processing_status = "FAILED"
            await session.flush()
        finally:
            temp_path.unlink(missing_ok=True)
            Path(temp_dir).rmdir()

    return OutlookAddToRagResponse(
        success=True,
        documents_indexed=documents_indexed,
        message=f"Email indexed. {documents_indexed} document(s) added to RAG.",
    )


@router.post("/add-all-to-rag", response_model=OutlookAddToRagResponse)
async def add_all_outlook_emails_to_rag(
    request: OutlookAddAllToRagRequest,
    orchestrator: IngestionOrchestrator = Depends(get_ingestion_orchestrator),
    session: AsyncSession = Depends(get_app_db_session),
):
    """Add all fetched Outlook emails + attachments to RAG (mirrors Gmail)."""
    total_indexed = 0
    for email_req in request.emails:
        email_req.project_id = request.project_id
        try:
            result = await add_outlook_email_to_rag(email_req, orchestrator, session)
            total_indexed += result.documents_indexed
        except Exception as e:
            logger.warning("OUTLOOK failed to add email %s to RAG: %s", email_req.message_id, e)

    return OutlookAddToRagResponse(
        success=True,
        documents_indexed=total_indexed,
        message=f"All emails indexed. {total_indexed} document(s) added to RAG.",
    )

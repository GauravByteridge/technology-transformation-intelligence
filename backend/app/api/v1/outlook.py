"""Outlook (Microsoft Graph) integration API routes.

Mirrors the Gmail routes. Provides endpoints for:
- OAuth status check and authorization
- Fetching emails by keyword search
- Adding email content and attachments to RAG
"""

import logging
import secrets
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import SYSTEM_USER_ID
from app.dependencies import get_app_db_session, get_ingestion_orchestrator
from app.documents.orchestrator import IngestionOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Schemas ---

class OutlookStatusResponse(BaseModel):
    connected: bool
    email: str | None = None


class OutlookFetchRequest(BaseModel):
    keywords: str = ""
    max_results: int = 10


class EmailSummary(BaseModel):
    message_id: str
    subject: str
    sender: str
    date: str
    body_preview: str
    has_attachments: bool
    attachments: list[dict] = []


class OutlookFetchResponse(BaseModel):
    emails: list[EmailSummary]
    total: int


class AddToRagRequest(BaseModel):
    message_id: str
    subject: str
    body: str
    project_id: str | None = None
    attachments: list[dict] = []


class AddAllToRagRequest(BaseModel):
    emails: list[AddToRagRequest]
    project_id: str | None = None


class AddToRagResponse(BaseModel):
    success: bool
    documents_indexed: int
    message: str


# --- Helper to get OutlookService ---

def _get_outlook_service():
    """Create an OutlookService instance from settings."""
    from app.dependencies import get_settings
    from app.services.outlook_service import OutlookService

    settings = get_settings()
    client_id = getattr(settings, 'microsoft_client_id', '') or ''
    client_secret = getattr(settings, 'microsoft_client_secret', '') or ''
    tenant = getattr(settings, 'microsoft_tenant', 'common') or 'common'
    redirect_uri = getattr(
        settings, 'microsoft_redirect_uri',
        'http://localhost:8000/api/v1/outlook/auth/callback',
    )

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Outlook integration not configured. Set MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET.",
        )

    return OutlookService(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        tenant=tenant,
        token_file="./outlook_token.json",
    )


# --- Routes ---

@router.get("/status", response_model=OutlookStatusResponse)
async def outlook_status():
    """Check Outlook connection status."""
    try:
        outlook = _get_outlook_service()
    except HTTPException:
        return OutlookStatusResponse(connected=False)

    if not outlook.is_connected():
        return OutlookStatusResponse(connected=False)

    try:
        email = await outlook.get_user_email()
        return OutlookStatusResponse(connected=True, email=email)
    except Exception:
        return OutlookStatusResponse(connected=False)


@router.get("/auth/url")
async def get_auth_url():
    """Get Microsoft OAuth authorization URL."""
    outlook = _get_outlook_service()
    state = secrets.token_urlsafe(16)
    url = outlook.get_auth_url(state=state)
    return {"auth_url": url}


@router.get("/auth/callback")
async def auth_callback(
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    """Handle Microsoft OAuth callback."""
    if error:
        raise HTTPException(status_code=400, detail=f"Authorization failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    outlook = _get_outlook_service()
    try:
        await outlook.exchange_code(code)
        # Redirect back to the frontend data sources page
        return RedirectResponse(url="http://localhost:5173/sources?outlook=connected")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/fetch", response_model=OutlookFetchResponse)
async def fetch_emails(request: OutlookFetchRequest):
    """Fetch emails by keyword search.

    Uses Microsoft Graph `$search` free-text search over the mailbox.
    Returns email previews without adding to RAG.
    """
    outlook = _get_outlook_service()

    try:
        emails = await outlook.fetch_emails(
            keywords=request.keywords,
            max_results=request.max_results,
        )
    except Exception as e:
        logger.error("Outlook fetch failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch emails: {str(e)}")

    summaries = [
        EmailSummary(
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


@router.post("/add-to-rag", response_model=AddToRagResponse)
async def add_email_to_rag(
    request: AddToRagRequest,
    orchestrator: IngestionOrchestrator = Depends(get_ingestion_orchestrator),
    session: AsyncSession = Depends(get_app_db_session),
):
    """Add an email and its attachments to RAG.

    Email body is directly chunked and embedded (bypasses content classifier).
    Attachments go through the normal content-aware pipeline.
    """
    from app.documents.chunker import FixedSizeChunker
    from app.documents.embedder import DeterministicEmbeddingGenerator
    from app.models.document import Document, DocumentChunk, Embedding
    from app.models.uploaded_file import UploadedFile
    from app.repositories.document_repository import DocumentRepository

    outlook = _get_outlook_service()
    documents_indexed = 0
    project_id = None

    if request.project_id:
        from uuid import UUID
        try:
            project_id = UUID(request.project_id)
        except ValueError:
            pass

    # 1. Fetch the FULL email body from Graph (fetch preview may be truncated).
    full_body = request.body
    if request.message_id:
        try:
            access_token = await outlook.get_valid_access_token()
            import httpx
            async with httpx.AsyncClient() as client:
                msg_response = await client.get(
                    f"https://graph.microsoft.com/v1.0/me/messages/{request.message_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"$select": "subject,body,bodyPreview"},
                    timeout=15.0,
                )
                if msg_response.status_code == 200:
                    msg_data = msg_response.json()
                    extracted_body = outlook._extract_body(msg_data)
                    if extracted_body and len(extracted_body) > len(full_body):
                        full_body = extracted_body
        except Exception as e:
            logger.warning("Could not fetch full email body, using provided body: %s", e)

    # 2. Index email body DIRECTLY into RAG (bypass content classifier)
    email_text = f"Subject: {request.subject}\n\n{full_body}"
    if email_text.strip() and len(email_text.strip()) > 10:
        # Create uploaded_file record for tracking
        file_record = UploadedFile(
            id=uuid4(),
            file_name=f"email_{request.message_id[:8]}_{request.subject[:30]}.txt",
            file_type="txt",
            file_size=len(email_text.encode()),
            project_id=project_id,
            uploaded_by=SYSTEM_USER_ID,
            processing_status="processing",
        )
        session.add(file_record)
        await session.flush()

        # Directly chunk and embed (no classifier)
        chunker = FixedSizeChunker()
        chunks = chunker.chunk(email_text)

        if chunks:
            # Filter empty chunks
            chunks = [c for c in chunks if c.text and c.text.strip()]
            if not chunks:
                pass  # no non-empty chunks to embed
            else:
                try:
                    # Use production embedding generator if available
                    try:
                        from app.dependencies import get_embedding_provider
                        from app.documents.embedder import ProductionEmbeddingGenerator
                        embedding_provider = get_embedding_provider()
                        embedding_gen = ProductionEmbeddingGenerator(embedding_provider)
                    except (RuntimeError, Exception):
                        embedding_gen = DeterministicEmbeddingGenerator()

                    chunk_texts = [c.text for c in chunks]
                    embeddings = await embedding_gen.generate(chunk_texts)

                    # Store directly via DocumentRepository
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
                except Exception as e:
                    logger.error("Failed to index email body: %s", e)
                    file_record.processing_status = "FAILED"

            await session.flush()

    # 3. Download and index attachments (through normal pipeline)
    for attachment in request.attachments:
        attachment_id = attachment.get("attachment_id", "")
        filename = attachment.get("filename", "attachment")

        if not attachment_id:
            continue

        try:
            file_bytes = await outlook.download_attachment(request.message_id, attachment_id)
        except Exception as e:
            logger.warning("Failed to download attachment %s: %s", filename, e)
            continue

        # Determine file type
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        supported_exts = {"pdf", "docx", "doc", "xlsx", "xls", "csv", "txt"}
        if ext not in supported_exts:
            continue

        # Create file record
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

        # Write to temp file and process through orchestrator
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
        except Exception as e:
            logger.warning("Failed to process attachment %s: %s", filename, e)
            file_record.processing_status = "FAILED"
            await session.flush()
        finally:
            temp_path.unlink(missing_ok=True)
            Path(temp_dir).rmdir()

    return AddToRagResponse(
        success=True,
        documents_indexed=documents_indexed,
        message=f"Email indexed. {documents_indexed} document(s) added to RAG.",
    )


@router.post("/add-all-to-rag", response_model=AddToRagResponse)
async def add_all_emails_to_rag(
    request: AddAllToRagRequest,
    orchestrator: IngestionOrchestrator = Depends(get_ingestion_orchestrator),
    session: AsyncSession = Depends(get_app_db_session),
):
    """Add all fetched emails and their attachments to RAG in batch.

    Iterates over all emails in the request and indexes each one.
    """
    total_indexed = 0

    for email_req in request.emails:
        # Override project_id from the batch-level value
        email_req.project_id = request.project_id

        try:
            result = await add_email_to_rag(email_req, orchestrator, session)
            total_indexed += result.documents_indexed
        except Exception as e:
            logger.warning("Failed to add email %s to RAG: %s", email_req.message_id, e)

    return AddToRagResponse(
        success=True,
        documents_indexed=total_indexed,
        message=f"All emails indexed. {total_indexed} document(s) added to RAG.",
    )

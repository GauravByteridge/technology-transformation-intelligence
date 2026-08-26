"""
File upload and inspection API route handlers.

Provides the unified file upload entry point for content-aware ingestion,
plus endpoints for inspecting file structure, regions, and datasets.

Architecture note:
  Excel files (.xlsx / .xls) are processed asynchronously via BackgroundTasks.
  The upload endpoint returns 202 Accepted immediately so the client is never
  blocked waiting for openpyxl to finish (the original source of timeouts).
  Clients poll GET /{file_id}/status to track progress.

  All other file types (CSV, PDF, DOCX, TXT, JSON) are small enough to be
  processed inline and continue to return 201 Created synchronously.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import SYSTEM_USER_ID
from app.dependencies import (
    get_app_db_session,
    get_dataset_service,
    get_ingestion_orchestrator,
    get_settings,
)
from app.documents.orchestrator import IngestionOrchestrator
from app.models.uploaded_file import UploadedFile
from app.schemas.dataset import (
    DataRegionResponse,
    DatasetResponse,
    FileUploadResponse,
)
from app.services.dataset_service import DatasetService

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload constraints
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
SUPPORTED_EXTENSIONS = {"xlsx", "xls", "csv", "json", "pdf", "docx", "txt"}

# File types that use the async background pipeline (large / slow to process)
ASYNC_PROCESSING_EXTENSIONS = {"xlsx", "xls"}


# =============================================================================
# Background task: run the Excel pipeline and write status back to DB
# =============================================================================


async def _run_excel_pipeline_background(
    file_id: UUID,
    file_path: str,
    file_name: str,
    file_type: str,
    file_size: int,
    project_id: UUID | None,
    uploaded_by: UUID,
    session_factory: object,  # async_sessionmaker
) -> None:
    """Background task: run the ExcelPipelineGraph and update file status in DB.

    This function is scheduled via FastAPI BackgroundTasks so the upload
    HTTP response is returned to the client before any processing starts.
    It opens its own database session from the session factory.
    """
    from app.dependencies import create_ingestion_orchestrator
    from app.processors.content_classifier import ContentClassifier
    from app.processors.excel_pipeline import ExcelPipelineGraph
    from app.processors.excel_state import ExcelProcessingState

    state = ExcelProcessingState(
        file_id=file_id,
        file_path=file_path,
        file_name=file_name,
        file_size=file_size,
        file_type=file_type,
        project_id=project_id,
        uploaded_by=uploaded_by,
    )

    final_status = "failed"
    try:
        async with session_factory() as session:
            orchestrator = create_ingestion_orchestrator(session)
            pipeline = ExcelPipelineGraph(
                classifier=ContentClassifier(),
                dataset_service=orchestrator._dataset_service,
                orchestrator=orchestrator,
            )

            state = await pipeline.run(state)
            final_status = "ready" if state.status == "done" else state.status

            # Write final status back to the DB within the active session
            result = await session.execute(
                select(UploadedFile).where(UploadedFile.id == file_id)
            )
            file_record = result.scalar_one_or_none()
            if file_record:
                file_record.processing_status = final_status
                if state.errors:
                    file_record.processing_error = "; ".join(state.errors[:3])
            await session.commit()
    except Exception as exc:
        logger.error(
            "excel_background_pipeline_failed",
            extra={"file_id": str(file_id), "error": str(exc)},
        )
        final_status = "failed"

    # Clean up temp file
    try:
        Path(file_path).unlink(missing_ok=True)
        Path(file_path).parent.rmdir()
    except OSError:
        pass

    logger.info(
        "excel_background_pipeline_completed",
        extra={
            "file_id": str(file_id),
            "status": final_status,
            "datasets": len(state.datasets_created),
            "chunks": state.documents_indexed,
        },
    )


# =============================================================================
# Upload endpoint
# =============================================================================


@router.post(
    "/upload",
    summary="Upload a file for content-aware ingestion",
    responses={
        201: {"description": "Non-Excel file processed synchronously and ready"},
        202: {"description": "Excel file accepted; poll /{file_id}/status for progress"},
        422: {"description": "Invalid file, empty file, or unsupported type"},
    },
)
async def upload_file(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    project_id: UUID | None = Form(None),
    service: IngestionOrchestrator = Depends(get_ingestion_orchestrator),
    session: AsyncSession = Depends(get_app_db_session),
) -> dict:
    """Upload a file for content-aware ingestion processing.

    For Excel files (.xlsx / .xls):
        Returns 202 Accepted immediately. Processing continues in the background
        via the ExcelPipelineGraph (pandas-based, non-blocking). Poll
        GET /{file_id}/status until status is 'ready' or 'failed'.

    For all other file types:
        Returns 201 Created after synchronous processing (fast for small files).
    """
    # ── Validation ────────────────────────────────────────────────────────────
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is required",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is empty",
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
        )

    file_extension = _extract_extension(file.filename)
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported file type: {file_extension}. "
                f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    # ── Create DB record ──────────────────────────────────────────────────────
    is_excel = file_extension in ASYNC_PROCESSING_EXTENSIONS
    initial_status = "processing" if is_excel else "processing"

    file_record = UploadedFile(
        id=uuid4(),
        file_name=file.filename,
        file_type=file_extension,
        file_size=len(content),
        project_id=project_id,
        uploaded_by=SYSTEM_USER_ID,
        processing_status=initial_status,
    )
    session.add(file_record)
    await session.flush()
    real_file_id = file_record.id

    # ── Write temp file ───────────────────────────────────────────────────────
    suffix = f".{file_extension}" if file_extension else ""
    temp_dir = tempfile.mkdtemp(prefix="ingestion_")
    temp_path = Path(temp_dir) / f"upload{suffix}"
    # Write bytes in a thread so we don't block the event loop for large files
    await asyncio.to_thread(temp_path.write_bytes, content)

    # ── Route: Excel → async background, others → sync inline ─────────────────
    if is_excel:
        # Get the session factory from the dependency so the background task
        # can open its own session (request session will be closed by then).
        from app.dependencies import _get_app_session_factory  # noqa: PLC0415
        session_factory = _get_app_session_factory()

        background_tasks.add_task(
            _run_excel_pipeline_background,
            file_id=real_file_id,
            file_path=str(temp_path),
            file_name=file.filename,
            file_type=file_extension,
            file_size=len(content),
            project_id=project_id,
            uploaded_by=SYSTEM_USER_ID,
            session_factory=session_factory,
        )

        logger.info(
            "file_upload_accepted_async",
            extra={
                "file_name": file.filename,
                "file_type": file_extension,
                "file_size": len(content),
                "file_id": str(real_file_id),
            },
        )

        from fastapi.responses import JSONResponse  # noqa: PLC0415
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "file_id": str(real_file_id),
                "file_name": file.filename,
                "file_type": file_extension,
                "processing_status": "processing",
                "status_url": f"/api/v1/files/{real_file_id}/status",
                "datasets_created": [],
                "documents_indexed": 0,
                "message": (
                    "Excel file accepted. Processing in background. "
                    f"Poll /api/v1/files/{real_file_id}/status for progress."
                ),
            },
        )

    else:
        # Non-Excel: process synchronously (fast path)
        try:
            result = await service.process_file(
                file_id=real_file_id,
                file_path=str(temp_path),
                file_name=file.filename,
                file_type=file_extension,
                file_size=len(content),
                project_id=project_id,
                uploaded_by=SYSTEM_USER_ID,
            )

            file_record.processing_status = result.get("status", "ready")
            await session.flush()

            logger.info(
                "file_upload_processed",
                extra={
                    "file_name": file.filename,
                    "file_type": file_extension,
                    "file_size": len(content),
                    "status": result.get("status", "unknown"),
                    "file_id": str(real_file_id),
                },
            )

            from fastapi.responses import JSONResponse  # noqa: PLC0415
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "file_id": str(real_file_id),
                    "file_name": file.filename,
                    "file_type": file_extension,
                    "processing_status": result.get("status", "ready"),
                    "datasets_created": result.get("datasets_created", []),
                    "documents_indexed": result.get("documents_indexed", 0),
                },
            )
        finally:
            try:
                temp_path.unlink(missing_ok=True)
                Path(temp_dir).rmdir()
            except OSError:
                pass


# =============================================================================
# Status polling endpoint
# =============================================================================


@router.get(
    "/{file_id}/status",
    summary="Get processing status for an uploaded file",
    responses={
        200: {"description": "File status returned"},
        404: {"description": "File not found"},
    },
)
async def get_file_status(
    file_id: UUID,
    session: AsyncSession = Depends(get_app_db_session),
) -> dict:
    """Poll the processing status of an uploaded file.

    Useful for tracking Excel files that are processed in the background.
    Returns status values: 'processing', 'reading', 'inspecting',
    'classifying', 'extracting', 'indexing', 'ready', 'failed'.
    """
    result = await session.execute(
        select(UploadedFile).where(UploadedFile.id == file_id)
    )
    file_record = result.scalar_one_or_none()

    if file_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found",
        )

    return {
        "file_id": str(file_record.id),
        "file_name": file_record.file_name,
        "file_type": file_record.file_type,
        "processing_status": file_record.processing_status,
        "processing_error": file_record.processing_error,
        "uploaded_at": file_record.uploaded_at.isoformat() if file_record.uploaded_at else None,
    }


# =============================================================================
# Existing read endpoints (unchanged)
# =============================================================================


@router.get(
    "/{file_id}/structure",
    summary="Get file inspection structure",
    responses={
        404: {"description": "File not found"},
    },
)
async def get_file_structure(
    file_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> dict:
    """Return the file's inspection structure result including datasets and regions."""
    try:
        return await service.get_file_structure(file_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{file_id}/regions",
    response_model=list[DataRegionResponse],
    summary="Get detected regions for a file",
    responses={
        404: {"description": "File not found"},
    },
)
async def get_file_regions(
    file_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> list[dict]:
    """Return all detected regions with classifications for a file."""
    return await service.get_file_regions(file_id)


@router.get(
    "/{file_id}/datasets",
    response_model=list[DatasetResponse],
    summary="Get datasets extracted from a file",
)
async def get_file_datasets(
    file_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> list[dict]:
    """Return all detected datasets for a file."""
    return await service.list_datasets(file_id=file_id)


# =============================================================================
# Helpers
# =============================================================================


def _extract_extension(filename: str) -> str:
    """Extract and normalize the file extension from a filename."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()




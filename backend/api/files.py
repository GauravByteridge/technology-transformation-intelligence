"""
File API endpoints for the Project Intelligence Hub.

Handles file upload (with processing pipeline), listing, downloading, and deletion.
Requirements: 3.1-3.5, 5.2-5.7, 10.4, 10.5, 10.6, 10.7
"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile, Query, status
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.orm import Session

from db.chroma_client import add_embeddings, delete_embeddings_by_file
from db.database import get_db
from models.database_models import File, Project
from models.schemas import FileCategory, FileResponse
from services.chunker import Chunker
from services.embeddings import EmbeddingGenerator
from services.file_processor import FileProcessor

router = APIRouter()

# Supported file extensions
SUPPORTED_FILE_TYPES = {"pdf", "xlsx", "xls", "csv", "json"}

# File storage directory
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


def _get_project_or_404(db: Session) -> Project:
    """Helper to get the current project or raise 404."""
    project = db.query(Project).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No project exists. Create a project first.",
        )
    return project


@router.post("/files/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = FastAPIFile(...),
    category: FileCategory = Query(...),
    db: Session = Depends(get_db),
):
    """
    Upload a file with category metadata.

    - Validates file type is in {pdf, xlsx, xls, csv, json}
    - Saves original file to uploads/ directory
    - Processes file: extract text → chunk → generate embeddings → store in ChromaDB
    - Saves file metadata to PostgreSQL
    - Returns FileResponse on success
    """
    project = _get_project_or_404(db)

    # Extract file extension and validate
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename.",
        )

    file_extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_extension not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: '{file_extension}'. Supported types: {', '.join(sorted(SUPPORTED_FILE_TYPES))}",
        )

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Generate a unique filename to prevent collisions
    unique_prefix = uuid.uuid4().hex[:8]
    safe_filename = f"{unique_prefix}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # Save the uploaded file to disk
    try:
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # Process file: extract text → chunk → generate embeddings
    try:
        file_processor = FileProcessor()
        chunker = Chunker()
        embedding_generator = EmbeddingGenerator()

        # Extract text
        text = file_processor.process(file_path, file_extension)

        # Chunk text
        chunks = chunker.chunk(text)

        # Generate embeddings (only if there are chunks)
        if chunks:
            embeddings = embedding_generator.generate(chunks)
        else:
            embeddings = []

    except Exception as e:
        # Clean up the saved file if processing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Text extraction failed for file '{file.filename}'. {str(e)}",
        )

    # Save file metadata to PostgreSQL first to get the file ID
    db_file = File(
        file_name=file.filename,
        file_type=file_extension,
        category=category.value,
        file_path=file_path,
        chunk_count=len(chunks),
        project_id=project.id,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # Store embeddings in ChromaDB with IDs like "{file_id}_{chunk_index}"
    if chunks and embeddings:
        chunk_ids = [f"{db_file.id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "file_id": db_file.id,
                "file_name": file.filename,
                "category": category.value,
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]
        try:
            add_embeddings(
                ids=chunk_ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as e:
            # If ChromaDB storage fails, remove the DB record and file
            db.delete(db_file)
            db.commit()
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store embeddings: {str(e)}",
            )

    return FileResponse(
        id=db_file.id,
        file_name=db_file.file_name,
        file_type=db_file.file_type,
        category=category,
        uploaded_at=db_file.uploaded_at,
        chunk_count=db_file.chunk_count,
    )


@router.get("/files", response_model=list[FileResponse])
def list_files(db: Session = Depends(get_db)):
    """
    List all uploaded files for the current project.

    Returns a list of FileResponse objects.
    """
    project = _get_project_or_404(db)

    files = db.query(File).filter(File.project_id == project.id).all()

    return [
        FileResponse(
            id=f.id,
            file_name=f.file_name,
            file_type=f.file_type,
            category=f.category,
            uploaded_at=f.uploaded_at,
            chunk_count=f.chunk_count,
        )
        for f in files
    ]


@router.get("/files/{file_id}")
def download_file(file_id: int, db: Session = Depends(get_db)):
    """
    Download a specific file by its ID.

    Returns the original file as a download attachment.
    Returns 404 if file not found.
    """
    project = _get_project_or_404(db)

    db_file = db.query(File).filter(File.id == file_id, File.project_id == project.id).first()
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id {file_id} not found.",
        )

    # Verify file exists on disk
    if not os.path.exists(db_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{db_file.file_name}' not found on disk.",
        )

    return FastAPIFileResponse(
        path=db_file.file_path,
        filename=db_file.file_name,
        media_type="application/octet-stream",
    )


@router.delete("/files/{file_id}", status_code=status.HTTP_200_OK)
def delete_file(file_id: int, db: Session = Depends(get_db)):
    """
    Delete a specific file by its ID.

    - Deletes the original file from disk
    - Deletes all associated embeddings from ChromaDB
    - Deletes file metadata from PostgreSQL
    - Returns 404 if file not found
    """
    project = _get_project_or_404(db)

    db_file = db.query(File).filter(File.id == file_id, File.project_id == project.id).first()
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id {file_id} not found.",
        )

    # 1. Delete original file from disk
    if os.path.exists(db_file.file_path):
        os.remove(db_file.file_path)

    # 2. Delete all associated embeddings from ChromaDB
    delete_embeddings_by_file(db_file.id)

    # 3. Delete file metadata from PostgreSQL
    db.delete(db_file)
    db.commit()

    return {"detail": f"File '{db_file.file_name}' deleted successfully."}

"""
File API endpoints for the Project Intelligence Hub.

Handles file upload with dual pipeline processing:
- Structured data (Excel tables, CSV) -> Relational database
- Unstructured data (PDF, text, unstructured sheets) -> ChromaDB vectors

Requirements: 3.1-3.5, 5.2-5.7, 10.4, 10.5, 10.6, 10.7
"""

import os
import uuid
import logging
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

# New ingestion services
from services.ingestion.file_classifier import FileClassifier, DataType
from services.ingestion.structured_ingestion_service import StructuredIngestionService
from services.ingestion.unstructured_ingestion_service import UnstructuredIngestionService

logger = logging.getLogger(__name__)

router = APIRouter()

# Supported file extensions
SUPPORTED_FILE_TYPES = {"pdf", "xlsx", "xls", "csv", "json"}

# Maximum file size: 50 MB
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

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
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    category: FileCategory = Query(...),
    db: Session = Depends(get_db),
):
    """
    Upload a file with category metadata.

    Processing pipeline:
    1. Validates file type is in {pdf, xlsx, xls, csv, json}
    2. Validates file size is under 50 MB
    3. Saves original file to uploads/ directory
    4. Classifies file content (structured vs unstructured)
    5. For structured data (Excel tables, CSV):
       - Extracts typed data with schema detection
       - Stores in relational database tables
    6. For unstructured data (PDF, text sheets):
       - Semantic chunking with structure preservation
       - Generates embeddings
       - Stores in ChromaDB
    7. Returns FileResponse on success
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
        total_size = 0
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)  # Read 1 MB at a time
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE_MB} MB.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # Create file record first (we'll update chunk_count later)
    db_file = File(
        file_name=file.filename,
        file_type=file_extension,
        category=category.value,
        file_path=file_path,
        chunk_count=0,
        project_id=project.id,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # Process file through dual pipeline
    try:
        total_chunks = 0
        
        # Initialize services
        structured_service = StructuredIngestionService()
        unstructured_service = UnstructuredIngestionService()
        classifier = FileClassifier()
        
        # Classify the file
        classification = classifier.classify(file_path, file_extension)
        
        logger.info(
            f"File classification: {file.filename} -> {classification.primary_data_type.value} "
            f"(confidence: {classification.confidence:.2f})"
        )
        
        # Process based on file type and classification
        if file_extension in ("xlsx", "xls"):
            # Excel: Process each sheet appropriately
            
            # 1. Ingest structured sheets into database
            datasets_created, struct_rows = structured_service.ingest_file(
                db, db_file, file_path, file_extension
            )
            logger.info(f"Structured ingestion: {datasets_created} datasets, {struct_rows} rows")
            
            # 2. Ingest unstructured sheets into ChromaDB
            unstructured_sheets = structured_service.get_unstructured_sheets(file_path, file_extension)
            for sheet_name in unstructured_sheets:
                chunks = unstructured_service.ingest_excel_sheet_as_text(
                    db_file.id, file_path, file.filename, sheet_name, category.value
                )
                total_chunks += chunks
                logger.info(f"Unstructured sheet '{sheet_name}': {chunks} chunks")
            
            # Also create semantic text for structured sheets (for hybrid queries)
            # This allows finding structured data via semantic search too
            for sc in classification.sheet_classifications:
                if sc.data_type in (DataType.STRUCTURED, DataType.SEMI_STRUCTURED):
                    # Create a summary text chunk for the structured sheet
                    chunks = _create_structured_sheet_summary(
                        db_file.id, file_path, file.filename, sc.sheet_name, category.value
                    )
                    total_chunks += chunks
            
        elif file_extension == "csv":
            # CSV: Ingest as structured data
            datasets_created, struct_rows = structured_service.ingest_file(
                db, db_file, file_path, file_extension
            )
            logger.info(f"CSV structured ingestion: {datasets_created} datasets, {struct_rows} rows")
            
            # Also create text chunks for semantic search
            chunks = _process_csv_for_vectors(db_file.id, file_path, file.filename, category.value)
            total_chunks += chunks
            
        elif file_extension == "json":
            # JSON: Check if structured (array of records) or unstructured
            if classification.primary_data_type == DataType.STRUCTURED:
                datasets_created, struct_rows = structured_service.ingest_file(
                    db, db_file, file_path, file_extension
                )
                logger.info(f"JSON structured ingestion: {datasets_created} datasets, {struct_rows} rows")
            
            # Also create text chunks
            chunks = _process_json_for_vectors(db_file.id, file_path, file.filename, category.value)
            total_chunks += chunks
            
        elif file_extension == "pdf":
            # PDF: Fully unstructured - use semantic chunking
            total_chunks = unstructured_service.ingest_pdf(
                db_file.id, file_path, file.filename, category.value
            )
            logger.info(f"PDF ingestion: {total_chunks} chunks")
        
        else:
            # Other: Use legacy chunking
            total_chunks = _legacy_process_file(db_file.id, file_path, file_extension, file.filename, category.value)
        
        # Update chunk count
        db_file.chunk_count = total_chunks
        db.commit()
        
        logger.info(f"File processing complete: {file.filename} -> {total_chunks} total chunks")
        
    except Exception as e:
        # Clean up on failure
        logger.error(f"File processing failed: {e}")
        db.delete(db_file)
        db.commit()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File processing failed for '{file.filename}'. {str(e)}",
        )

    return FileResponse(
        id=db_file.id,
        file_name=db_file.file_name,
        file_type=db_file.file_type,
        category=category,
        uploaded_at=db_file.uploaded_at,
        chunk_count=db_file.chunk_count,
    )


def _create_structured_sheet_summary(file_id: int, file_path: str, 
                                     file_name: str, sheet_name: str,
                                     category: str) -> int:
    """Create a semantic summary chunk for a structured sheet."""
    import pandas as pd
    
    try:
        excel_file = pd.ExcelFile(file_path)
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        excel_file.close()
        
        # Create a summary description
        columns = df.columns.tolist()
        row_count = len(df)
        
        # Sample first few rows for context
        sample = df.head(3).to_string(index=False)
        
        summary_text = (
            f"Sheet: {sheet_name}\n"
            f"This is a structured data table from {file_name}.\n"
            f"Columns: {', '.join(str(c) for c in columns)}\n"
            f"Total rows: {row_count}\n\n"
            f"Sample data:\n{sample}\n\n"
            f"For exact numerical queries on this data, use the structured query tools."
        )
        
        # Store as single chunk
        embedding_gen = EmbeddingGenerator()
        embedding = embedding_gen.generate([summary_text])[0]
        
        add_embeddings(
            ids=[f"{file_id}_struct_{sheet_name}_summary"],
            documents=[summary_text],
            embeddings=[embedding],
            metadatas=[{
                "file_id": file_id,
                "file_name": file_name,
                "sheet_name": sheet_name,
                "category": category,
                "chunk_index": 0,
                "data_type": "structured_summary"
            }]
        )
        
        return 1
    except Exception as e:
        logger.warning(f"Failed to create structured sheet summary: {e}")
        return 0


def _process_csv_for_vectors(file_id: int, file_path: str, 
                             file_name: str, category: str) -> int:
    """Process CSV file for vector storage (semantic search fallback)."""
    import pandas as pd
    
    try:
        df = pd.read_csv(file_path)
        
        # Create summary + sample text
        columns = df.columns.tolist()
        sample = df.head(5).to_string(index=False)
        
        text = (
            f"CSV File: {file_name}\n"
            f"Columns: {', '.join(str(c) for c in columns)}\n"
            f"Rows: {len(df)}\n\n"
            f"Sample:\n{sample}"
        )
        
        # Use semantic chunker
        from services.ingestion.unstructured_ingestion_service import UnstructuredIngestionService
        service = UnstructuredIngestionService()
        return service.ingest_text(file_id, text, file_name, "csv", category)
        
    except Exception as e:
        logger.warning(f"Failed to process CSV for vectors: {e}")
        return 0


def _process_json_for_vectors(file_id: int, file_path: str,
                              file_name: str, category: str) -> int:
    """Process JSON file for vector storage."""
    import json
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        text = f"JSON File: {file_name}\n\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        
        from services.ingestion.unstructured_ingestion_service import UnstructuredIngestionService
        service = UnstructuredIngestionService()
        return service.ingest_text(file_id, text, file_name, "json", category)
        
    except Exception as e:
        logger.warning(f"Failed to process JSON for vectors: {e}")
        return 0


def _legacy_process_file(file_id: int, file_path: str, file_type: str,
                         file_name: str, category: str) -> int:
    """Legacy processing for backward compatibility."""
    try:
        file_processor = FileProcessor()
        chunker = Chunker()
        embedding_generator = EmbeddingGenerator()

        text = file_processor.process(file_path, file_type)
        chunks = chunker.chunk(text)

        if not chunks:
            return 0

        embeddings = embedding_generator.generate(chunks)
        
        chunk_ids = [f"{file_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "file_id": file_id,
                "file_name": file_name,
                "category": category,
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]
        
        add_embeddings(
            ids=chunk_ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        
        return len(chunks)
        
    except Exception as e:
        logger.error(f"Legacy processing failed: {e}")
        return 0


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
    - Deletes all structured data from database
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

    # 3. Delete structured data
    structured_service = StructuredIngestionService()
    structured_service.delete_file_data(db, db_file.id)

    # 4. Delete file metadata from PostgreSQL
    db.delete(db_file)
    db.commit()

    return {"detail": f"File '{db_file.file_name}' deleted successfully."}

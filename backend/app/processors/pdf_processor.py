"""
PDFProcessor — FileProcessor implementation for PDF files.

For POC, classifies all content as UNSTRUCTURED → RAG.
Architecture supports future extension to detect tables within PDFs
and route them to DATASET_QUERY.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

import fitz  # PyMuPDF

from app.errors.document_errors import ContentExtractionError
from app.errors.ingestion_errors import FileProcessingError
from app.processors.protocol import (
    DetectedRegion,
    InspectionResult,
    NormalizedDataset,
    ValidationWarning,
)

logger = logging.getLogger(__name__)

# Page delimiter inserted between extracted pages
_PAGE_BREAK_DELIMITER = "\n---PAGE_BREAK---\n"

# Maximum paragraphs to include in content_sample
_MAX_SAMPLE_PARAGRAPHS = 20


class PDFProcessor:
    """FileProcessor for PDF files.

    For POC, classifies all content as UNSTRUCTURED → RAG.
    Architecture supports future extension to detect tables within PDFs.
    """

    def can_process(self, file_type: str) -> bool:
        """Return True if this processor handles the given file type.

        Args:
            file_type: File extension or type identifier.

        Returns:
            True for "pdf".
        """
        return file_type.lower() == "pdf"

    async def inspect(self, file_path: str) -> InspectionResult:
        """Inspect PDF and produce a single UNSTRUCTURED region for the full document.

        Extracts text from all pages using PyMuPDF with page delimiters
        between pages. Returns an InspectionResult with a single DetectedRegion
        covering the entire document.

        Args:
            file_path: Path to the PDF file on disk.

        Returns:
            InspectionResult with a single region representing the full document.

        Raises:
            FileProcessingError: If the file is corrupted, unreadable, or password-protected.
            ContentExtractionError: If no extractable text is found (image-only PDF).
        """
        path = Path(file_path)
        file_name = path.name

        if not path.exists():
            raise FileProcessingError(
                file_name=file_name,
                message=f"PDF file not found: {file_path}",
            )

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            raise FileProcessingError(
                file_name=file_name,
                message=f"Failed to open PDF file: {file_name}",
                detail=str(exc),
            ) from exc

        try:
            # Check for password protection
            if doc.is_encrypted:
                doc.close()
                raise FileProcessingError(
                    file_name=file_name,
                    message=f"PDF file is password-protected: {file_name}",
                )

            page_count = len(doc)
            if page_count == 0:
                doc.close()
                raise FileProcessingError(
                    file_name=file_name,
                    message=f"PDF file has no pages: {file_name}",
                )

            # Extract text from all pages
            page_texts: list[str] = []
            for page in doc:
                try:
                    text = page.get_text("text")
                    page_texts.append(text.strip())
                except Exception as exc:
                    logger.warning(
                        "Failed to extract text from page",
                        extra={
                            "file_name": file_name,
                            "page_number": page.number + 1,
                            "error": str(exc),
                        },
                    )
                    page_texts.append("")

            # Build metadata
            metadata: dict[str, str] = {}
            doc_metadata = doc.metadata
            if doc_metadata:
                if doc_metadata.get("title"):
                    metadata["title"] = doc_metadata["title"]
                if doc_metadata.get("author"):
                    metadata["author"] = doc_metadata["author"]
                if doc_metadata.get("creationDate"):
                    metadata["creation_date"] = doc_metadata["creationDate"]

            metadata["page_count"] = str(page_count)

            doc.close()
        except FileProcessingError:
            raise
        except Exception as exc:
            doc.close()
            raise FileProcessingError(
                file_name=file_name,
                message=f"Error processing PDF file: {file_name}",
                detail=str(exc),
            ) from exc

        # Join pages with delimiter
        raw_text = _PAGE_BREAK_DELIMITER.join(page_texts)

        # Check for image-only PDF (no extractable text)
        if not raw_text.strip():
            raise ContentExtractionError(
                file_name=file_name,
                message=f"No extractable text found in PDF (image-only): {file_name}",
            )

        # Build content_sample from first paragraphs
        paragraphs = [p for p in raw_text.split("\n") if p.strip()]
        content_sample: list[list[str]] = [
            [p] for p in paragraphs[:_MAX_SAMPLE_PARAGRAPHS]
        ]

        region = DetectedRegion(
            region_id=str(uuid4()),
            sheet_name="document",
            start_row=1,
            end_row=page_count,
            start_column=0,
            end_column=0,
            header_row=None,
            content_sample=content_sample,
            row_count=page_count,
            column_count=1,
            raw_text=raw_text,
        )

        return InspectionResult(
            file_name=file_name,
            file_type="pdf",
            regions=[region],
            metadata=metadata,
        )

    async def extract(
        self, file_path: str, region: DetectedRegion | None = None
    ) -> NormalizedDataset:
        """Not applicable for unstructured PDF content.

        PDF content is routed to RAG pipeline, not structured extraction.

        Raises:
            NotImplementedError: Always — unstructured content is not applicable
                for structured extraction.
        """
        raise NotImplementedError(
            "PDFProcessor does not support structured extraction. "
            "PDF content is processed through the RAG pipeline."
        )

    def validate(self, normalized: NormalizedDataset) -> list[ValidationWarning]:
        """Validate a normalized dataset. Returns empty list for PDF content.

        Args:
            normalized: The normalized dataset to validate.

        Returns:
            Empty list — PDF content is unstructured and not validated this way.
        """
        return []

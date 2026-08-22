"""
Content extractor implementations for the document ingestion pipeline.

- TxtContentExtractor: Reads plain text files directly.
- PdfContentExtractor: Placeholder — raises NotImplementedError (Phase 1).
- DocxContentExtractor: Placeholder — raises NotImplementedError (Phase 1).

The architecture accommodates future image formats (PNG, JPEG) by adding
new extractor classes without modifying existing ones or the pipeline flow.
"""

from pathlib import Path

from app.errors.document_errors import ContentExtractionError


class TxtContentExtractor:
    """Extracts content from plain-text (.txt) files.

    Satisfies the ContentExtractor protocol via structural subtyping.
    """

    async def extract(self, file_path: str, file_type: str) -> str:
        """Read the file at *file_path* and return its text content.

        Args:
            file_path: Absolute or relative path to the .txt file.
            file_type: MIME type or extension identifier (expected: "txt" or "text/plain").

        Returns:
            The full text content of the file.

        Raises:
            ContentExtractionError: If reading the file fails.
        """
        path = Path(file_path)
        if not path.exists():
            raise ContentExtractionError(
                file_name=path.name,
                message=f"File not found: {file_path}",
            )
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ContentExtractionError(
                file_name=path.name,
                message=f"Failed to read text file: {path.name}",
                detail=str(exc),
            ) from exc


class PdfContentExtractor:
    """Placeholder extractor for PDF files.

    Full PDF parsing will be implemented in Phase 1 using a dedicated
    PDF library (e.g., PyMuPDF or pdfplumber).
    """

    async def extract(self, file_path: str, file_type: str) -> str:
        """Not implemented — PDF extraction deferred to Phase 1.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "PDF content extraction is not yet implemented. "
            "Full PDF parsing will be available in Phase 1."
        )


class DocxContentExtractor:
    """Placeholder extractor for DOCX files.

    Full DOCX parsing will be implemented in Phase 1 using python-docx
    or an equivalent library.
    """

    async def extract(self, file_path: str, file_type: str) -> str:
        """Not implemented — DOCX extraction deferred to Phase 1.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "DOCX content extraction is not yet implemented. "
            "Full DOCX parsing will be available in Phase 1."
        )

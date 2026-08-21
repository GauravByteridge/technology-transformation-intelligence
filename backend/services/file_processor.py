"""
File Processor Service

Extracts and normalizes text from various file types:
- PDF: PyMuPDF (fitz)
- Excel (.xlsx, .xls): pandas
- CSV: pandas
- JSON: Python json module

Requirements: 4.1, 4.2
"""

import json
import re
from pathlib import Path

import pymupdf
import pandas as pd


class FileProcessor:
    """Extracts text content from supported file types and normalizes to plain text."""

    SUPPORTED_TYPES = {"pdf", "xlsx", "xls", "csv", "json"}

    def process(self, file_path: str, file_type: str) -> str:
        """
        Extract and normalize text from a file.

        Args:
            file_path: Path to the file on disk.
            file_type: File extension (e.g., 'pdf', 'xlsx', 'csv', 'json').

        Returns:
            Normalized plain text content extracted from the file.

        Raises:
            ValueError: If the file type is not supported.
            FileNotFoundError: If the file does not exist.
            RuntimeError: If text extraction fails.
        """
        file_type = file_type.lower().strip(".")

        if file_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported file type: '{file_type}'. "
                f"Supported types: {', '.join(sorted(self.SUPPORTED_TYPES))}"
            )

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            if file_type == "pdf":
                raw_text = self._process_pdf(file_path)
            elif file_type in ("xlsx", "xls"):
                raw_text = self._process_excel(file_path)
            elif file_type == "csv":
                raw_text = self._process_csv(file_path)
            elif file_type == "json":
                raw_text = self._process_json(file_path)
            else:
                raise ValueError(f"Unsupported file type: '{file_type}'")
        except (ValueError, FileNotFoundError):
            raise
        except Exception as e:
            raise RuntimeError(
                f"Text extraction failed for file '{Path(file_path).name}'. Error: {str(e)}"
            ) from e

        return self._normalize_text(raw_text)

    def _process_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF file using PyMuPDF.

        Iterates through all pages and concatenates the extracted text.
        """
        text_parts = []
        with pymupdf.open(file_path) as doc:
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def _process_excel(self, file_path: str) -> str:
        """
        Extract text from an Excel file (.xlsx or .xls) using pandas.

        Reads all sheets and converts each to a string representation
        including column headers and row data.
        """
        text_parts = []
        excel_file = pd.ExcelFile(file_path)

        try:
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                if not df.empty:
                    text_parts.append(f"Sheet: {sheet_name}")
                    text_parts.append(df.to_string(index=False))
        finally:
            excel_file.close()

        return "\n\n".join(text_parts)

    def _process_csv(self, file_path: str) -> str:
        """
        Extract text from a CSV file using pandas.

        Reads the CSV and converts it to a string representation
        including column headers and row data.
        """
        df = pd.read_csv(file_path)
        return df.to_string(index=False)

    def _process_json(self, file_path: str) -> str:
        """
        Extract text from a JSON file using the Python json module.

        Reads the JSON content and converts it to a formatted string
        representation for readability.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _normalize_text(self, text: str) -> str:
        """
        Normalize extracted text to clean plain text format.

        - Removes binary/control characters (except newlines and tabs)
        - Collapses multiple blank lines into single blank lines
        - Strips leading/trailing whitespace
        - Removes null bytes and other encoding artifacts

        Requirements: 4.2
        """
        if not text:
            return ""

        # Remove null bytes and other problematic characters
        text = text.replace("\x00", "")

        # Remove control characters except newline (\n), carriage return (\r), and tab (\t)
        text = re.sub(r"[^\x09\x0a\x0d\x20-\x7e\x80-\uffff]", "", text)

        # Normalize line endings to \n
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse multiple consecutive blank lines into a single blank line
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip leading/trailing whitespace from entire text
        text = text.strip()

        return text

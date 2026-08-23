"""
File processor protocol, registry, and supporting types.

This package defines the contracts and infrastructure for format-specific
file processing. Each file type (xlsx, csv, json, pdf, docx, txt) has a
dedicated processor that implements the FileProcessor protocol.
"""

from app.processors.content_classifier import ContentClassifier
from app.processors.csv_processor import CSVProcessor
from app.processors.docx_processor import DOCXProcessor
from app.processors.excel_processor import ExcelProcessor
from app.processors.file_type_detector import FileTypeDetector
from app.processors.json_processor import JSONProcessor
from app.processors.pdf_processor import PDFProcessor
from app.processors.protocol import (
    ClassificationResult,
    ColumnSchema,
    DetectedRegion,
    FileProcessor,
    FileTypeResult,
    HeaderDetectionResult,
    InspectionResult,
    NormalizedDataset,
    SheetInfo,
    ValidationWarning,
)
from app.processors.registry import FileProcessorRegistry
from app.processors.text_processor import TextProcessor

__all__ = [
    # Protocol
    "FileProcessor",
    # Data classes
    "ClassificationResult",
    "ColumnSchema",
    "DetectedRegion",
    "FileTypeResult",
    "HeaderDetectionResult",
    "InspectionResult",
    "NormalizedDataset",
    "SheetInfo",
    "ValidationWarning",
    # Classifier
    "ContentClassifier",
    # Processors
    "CSVProcessor",
    "DOCXProcessor",
    "ExcelProcessor",
    "JSONProcessor",
    "PDFProcessor",
    "TextProcessor",
    # Registry
    "FileProcessorRegistry",
    # Detector
    "FileTypeDetector",
]

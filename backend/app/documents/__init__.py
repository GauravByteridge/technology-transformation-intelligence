"""
Document ingestion pipeline module.

Exports pipeline stage protocols, result dataclasses, concrete orchestrator,
and implementations used by the document processing subsystem.
"""

from app.documents.chunker import FixedSizeChunker
from app.documents.embedder import DeterministicEmbeddingGenerator
from app.documents.extractors import (
    DocxContentExtractor,
    PdfContentExtractor,
    PptxContentExtractor,
    TxtContentExtractor,
)
from app.documents.orchestrator import IngestionOrchestrator
from app.documents.pipeline import (
    ChunkResult,
    ContentExtractor,
    DocumentResult,
    EmbeddingGenerator,
    FileValidator,
    IngestionPipeline,
    MetadataExtractor,
    TextChunker,
)
from app.documents.validator import SimpleFileValidator

__all__ = [
    # Dataclasses
    "ChunkResult",
    "DocumentResult",
    # Stage protocols
    "FileValidator",
    "ContentExtractor",
    "MetadataExtractor",
    "TextChunker",
    "EmbeddingGenerator",
    # Orchestrator protocol
    "IngestionPipeline",
    # Concrete orchestrator
    "IngestionOrchestrator",
    # Implementations
    "TxtContentExtractor",
    "PdfContentExtractor",
    "PptxContentExtractor",
    "DocxContentExtractor",
    "FixedSizeChunker",
    "DeterministicEmbeddingGenerator",
    "SimpleFileValidator",
]

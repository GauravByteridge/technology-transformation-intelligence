"""Domain enums for the document ingestion pipeline.

These enums define the allowed states for file processing status,
content classification, and downstream processing strategy routing.
"""

from enum import Enum


class ProcessingStatus(str, Enum):
    """Processing lifecycle status for uploaded files and datasets."""

    UPLOADED = "UPLOADED"
    INSPECTING = "INSPECTING"
    CLASSIFYING = "CLASSIFYING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NORMALIZING = "NORMALIZING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"


class ContentClassification(str, Enum):
    """Classification of content structure within a detected region."""

    STRUCTURED = "STRUCTURED"
    SEMI_STRUCTURED = "SEMI_STRUCTURED"
    UNSTRUCTURED = "UNSTRUCTURED"
    IGNORE = "IGNORE"


class ProcessingStrategy(str, Enum):
    """Downstream processing strategy assigned to a classified region.

    Determined by content classification and confidence level:
    - DATASET_QUERY: Structured content → dataset → query interface
    - RAG: Unstructured content → chunks → embeddings → semantic search
    - HYBRID: Both dataset AND RAG representations
    - IGNORE: Skip this region (empty/decorative content)
    - REVIEW_REQUIRED: Low confidence — user must decide
    """

    DATASET_QUERY = "DATASET_QUERY"
    RAG = "RAG"
    HYBRID = "HYBRID"
    IGNORE = "IGNORE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

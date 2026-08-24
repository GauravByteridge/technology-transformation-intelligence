"""Domain enums for the Enterprise Intelligence Platform.

These enums define the allowed values for critical domain fields,
ensuring consistency between the database, services, and API layers.
"""

from enum import Enum


# --- Catalog & Discovery Enums ---


class CatalogVersionStatus(str, Enum):
    """Status lifecycle for catalog version snapshots."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class SourceType(str, Enum):
    """Supported external data source types."""

    POSTGRESQL = "POSTGRESQL"
    MONGODB = "MONGODB"
    FILE = "FILE"
    RAG = "RAG"


class EntryType(str, Enum):
    """Catalog entry types representing discovered data objects."""

    DATABASE = "DATABASE"
    SCHEMA = "SCHEMA"
    TABLE = "TABLE"
    VIEW = "VIEW"
    COLLECTION = "COLLECTION"
    DATASET = "DATASET"
    DOCUMENT = "DOCUMENT"
    SHEET = "SHEET"


class LineageNodeType(str, Enum):
    """Node types in the query lineage DAG."""

    QUESTION = "QUESTION"
    CATALOG = "CATALOG"
    TOOL = "TOOL"
    DATA_SOURCE = "DATA_SOURCE"
    DATASET = "DATASET"
    DOCUMENT = "DOCUMENT"
    EVIDENCE = "EVIDENCE"
    SYNTHESIS = "SYNTHESIS"
    ANSWER = "ANSWER"


# --- Document Processing Enums ---


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


# --- Query & Conversation Enums ---


class QueryStatus(str, Enum):
    """Status lifecycle for AI query execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ConversationMode(str, Enum):
    """Operating mode for conversations and queries."""

    DEMO = "DEMO"
    REAL = "REAL"


class MessageRole(str, Enum):
    """Roles for conversation messages."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


# --- Discovery Enums ---


class DiscoveryRunStatus(str, Enum):
    """Status lifecycle for discovery runs."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# --- Project & User Enums ---


class ProjectStatus(str, Enum):
    """Project status indicators."""

    ACTIVE = "ACTIVE"
    AT_RISK = "AT_RISK"
    ON_TRACK = "ON_TRACK"
    ATTENTION = "ATTENTION"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class UserRole(str, Enum):
    """Platform user roles."""

    ADMIN = "ADMIN"
    USER = "USER"


class UserStatus(str, Enum):
    """Platform user account status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


# --- Executive Brief Enums ---


class BriefStatus(str, Enum):
    """Status for executive briefs."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

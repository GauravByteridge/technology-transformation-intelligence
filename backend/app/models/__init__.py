"""
ORM models for the Enterprise Intelligence Platform.

Models are organized by database:
- AppBase subclasses → App_DB (application state)
- RAGBase subclasses → RAG_DB (documents, embeddings)

Import all models here so Alembic autogenerate can detect them.
"""

from app.models.base import AppBase, RAGBase

# App_DB models — Identity & Access
from app.models.user import User
from app.models.project import Project, ProjectMember

# App_DB models — Data Sources
from app.models.data_source import DataSource, SourceConnection
from app.models.data_source_credential import DataSourceCredential
from app.models.discovery_run import DataSourceDiscoveryRun

# App_DB models — Enterprise Data Catalog
from app.models.catalog_version import CatalogVersion
from app.models.catalog_entry import CatalogEntry
from app.models.catalog_field import CatalogField
from app.models.catalog_relationship import CatalogRelationship
from app.models.catalog_project_mapping import CatalogProjectMapping
from app.models.project_source_mapping import ProjectSourceMapping

# App_DB models — Documents / RAG (control-plane metadata)
from app.models.app_document import AppDocument
from app.models.document_version import DocumentVersion
from app.models.document_processing_run import DocumentProcessingRun

# App_DB models — AI / Conversations
from app.models.conversation import Conversation, Message
from app.models.query import Query, QueryHistory, SavedQuery
from app.models.query_source_usage import QuerySourceUsage

# App_DB models — Evidence / Lineage
from app.models.evidence import Evidence
from app.models.lineage import LineageRun, LineageNode

# App_DB models — Executive Intelligence
from app.models.executive_brief import ExecutiveBrief, BriefSource

# App_DB models — Supporting domain models
from app.models.uploaded_file import UploadedFile
from app.models.audit import AuditLog
from app.models.audit_finding import AuditFinding
from app.models.remediation import RemediationItem
from app.models.risk import ProjectRisk
from app.models.sdlc import SdlcPhase, SdlcMilestone, SdlcDeliverable
from app.models.jira import Sprint, JiraIssue
from app.models.resource import (
    TeamMember,
    ResourceAllocation,
    ResourceUtilization,
    ResourceForecast,
)
from app.models.it_control import ItControl, ControlAssessment
from app.models.dataset import (
    Dataset,
    DataRegion,
    DatasetColumn,
    DatasetRecord,
    DatasetRelationship,
)
from app.models.finance import (
    ProjectBudget,
    CostCategory,
    BudgetLineItem,
    ActualCost,
    MonthlyCostTrend,
)
from app.models.progress import ProjectProgressSnapshot
from app.models.health_kpi import ProjectHealthKpi

# RAG_DB models
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentMetadata,
    Embedding,
    EMBEDDING_DIMENSION,
)

# Enums
from app.models.enums import (
    CatalogVersionStatus,
    SourceType,
    EntryType,
    LineageNodeType,
    ProcessingStatus,
    ContentClassification,
    ProcessingStrategy,
    QueryStatus,
    ConversationMode,
    MessageRole,
    DiscoveryRunStatus,
    ProjectStatus,
    UserRole,
    UserStatus,
    BriefStatus,
)

__all__ = [
    "AppBase",
    "RAGBase",
    # Identity & Access
    "User",
    "Project",
    "ProjectMember",
    # Data Sources
    "DataSource",
    "SourceConnection",
    "DataSourceCredential",
    "DataSourceDiscoveryRun",
    # Enterprise Data Catalog
    "CatalogVersion",
    "CatalogEntry",
    "CatalogField",
    "CatalogRelationship",
    "CatalogProjectMapping",
    "ProjectSourceMapping",
    # Documents (App_DB control-plane)
    "AppDocument",
    "DocumentVersion",
    "DocumentProcessingRun",
    # AI / Conversations
    "Conversation",
    "Message",
    "Query",
    "QueryHistory",  # Backward-compatible alias for Query
    "SavedQuery",
    "QuerySourceUsage",
    # Evidence / Lineage
    "Evidence",
    "LineageRun",
    "LineageNode",
    # Executive Intelligence
    "ExecutiveBrief",
    "BriefSource",
    # Supporting domain models
    "UploadedFile",
    "AuditLog",
    "AuditFinding",
    "RemediationItem",
    "ProjectRisk",
    "SdlcPhase",
    "SdlcMilestone",
    "SdlcDeliverable",
    "Sprint",
    "JiraIssue",
    "TeamMember",
    "ResourceAllocation",
    "ResourceUtilization",
    "ResourceForecast",
    "ItControl",
    "ControlAssessment",
    "Dataset",
    "DataRegion",
    "DatasetColumn",
    "DatasetRecord",
    "DatasetRelationship",
    "ProjectBudget",
    "CostCategory",
    "BudgetLineItem",
    "ActualCost",
    "MonthlyCostTrend",
    "ProjectProgressSnapshot",
    "ProjectHealthKpi",
    # RAG_DB models
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    "Embedding",
    "EMBEDDING_DIMENSION",
    # Enums
    "CatalogVersionStatus",
    "SourceType",
    "EntryType",
    "LineageNodeType",
    "ProcessingStatus",
    "ContentClassification",
    "ProcessingStrategy",
    "QueryStatus",
    "ConversationMode",
    "MessageRole",
    "DiscoveryRunStatus",
    "ProjectStatus",
    "UserRole",
    "UserStatus",
    "BriefStatus",
]

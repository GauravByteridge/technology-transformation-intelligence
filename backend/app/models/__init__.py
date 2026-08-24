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

# App_DB models — Enterprise Data Catalog
from app.models.catalog_entry import CatalogEntry
from app.models.project_source_mapping import ProjectSourceMapping

# App_DB models — AI / Conversations
from app.models.conversation import Conversation, Message
from app.models.query import Query, QueryHistory, SavedQuery

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
    # Enterprise Data Catalog
    "CatalogEntry",
    "ProjectSourceMapping",
    # AI / Conversations
    "Conversation",
    "Message",
    "Query",
    "QueryHistory",
    "SavedQuery",
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
]

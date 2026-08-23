"""
ORM models for the Technology Transformation Intelligence platform.

Models are organized by database:
- AppBase subclasses → App_DB (application state)
- RAGBase subclasses → RAG_DB (documents, embeddings)

Import all models here so Alembic autogenerate can detect them.
"""

from app.models.base import AppBase, RAGBase

# App_DB models
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.data_source import DataSource, SourceConnection
from app.models.conversation import Conversation, Message
from app.models.query import QueryHistory, SavedQuery
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

__all__ = [
    "AppBase",
    "RAGBase",
    # App_DB models
    "User",
    "Project",
    "ProjectMember",
    "DataSource",
    "SourceConnection",
    "Conversation",
    "Message",
    "QueryHistory",
    "SavedQuery",
    "UploadedFile",
    "AuditLog",
    "AuditFinding",
    "RemediationItem",
    # Finance models
    "ProjectBudget",
    "CostCategory",
    "BudgetLineItem",
    "ActualCost",
    "MonthlyCostTrend",
    # Risk models
    "ProjectRisk",
    # SDLC models
    "SdlcPhase",
    "SdlcMilestone",
    "SdlcDeliverable",
    # Jira models
    "Sprint",
    "JiraIssue",
    # Resource models
    "TeamMember",
    "ResourceAllocation",
    "ResourceUtilization",
    "ResourceForecast",
    # IT Control models
    "ItControl",
    "ControlAssessment",
    # Dataset models
    "Dataset",
    "DataRegion",
    "DatasetColumn",
    "DatasetRecord",
    "DatasetRelationship",
    # Progress models
    "ProjectProgressSnapshot",
    # Health KPI models
    "ProjectHealthKpi",
    # RAG_DB models
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    "Embedding",
    "EMBEDDING_DIMENSION",
]

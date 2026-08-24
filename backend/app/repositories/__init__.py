"""
Repository layer — database access for internal databases (App_DB, RAG_DB).

All repositories inherit from BaseRepository which enforces parameterized queries.
See base.py for security invariants and usage patterns.
"""

from app.repositories.audit_finding_repository import AuditFindingRepository
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.base import BaseRepository
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.control_repository import ControlRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.finance_repository import FinanceRepository
from app.repositories.health_kpi_repository import HealthKpiRepository
from app.repositories.jira_repository import JiraRepository
from app.repositories.progress_repository import ProgressRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.project_source_mapping_repository import (
    ProjectSourceMappingRepository,
)
from app.repositories.query_history_repository import QueryHistoryRepository
from app.repositories.remediation_repository import RemediationRepository
from app.repositories.resource_repository import ResourceRepository
from app.repositories.risk_repository import RiskRepository
from app.repositories.sdlc_repository import SdlcRepository
from app.repositories.source_connection_repository import SourceConnectionRepository

__all__ = [
    "AuditFindingRepository",
    "AuditLogRepository",
    "BaseRepository",
    "CatalogRepository",
    "ControlRepository",
    "ConversationRepository",
    "DataSourceRepository",
    "FinanceRepository",
    "HealthKpiRepository",
    "JiraRepository",
    "ProgressRepository",
    "ProjectRepository",
    "ProjectSourceMappingRepository",
    "QueryHistoryRepository",
    "RemediationRepository",
    "ResourceRepository",
    "RiskRepository",
    "SdlcRepository",
    "SourceConnectionRepository",
]

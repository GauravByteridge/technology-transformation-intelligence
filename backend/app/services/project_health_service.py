"""
Project Health Service — aggregate cross-domain health calculation service.

This service computes DERIVED health KPIs from authoritative domain data
(finance, JIRA, resources, audit findings, IT controls, remediation, risks,
progress) and writes the cached result to the project_health_kpis table via
HealthKpiRepository.

It does NOT simply read existing KPI records. Each call to recalculate_and_cache
fetches live data from all domain repositories, applies the same pure calculation
formulas used by individual domain services, and upserts the aggregated result.

The project_health_kpis table is a performance cache for dashboard queries
and AI retrieval — this service is the single writer to that cache.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import structlog

from app.models.audit_finding import AuditFinding
from app.models.health_kpi import ProjectHealthKpi
from app.models.it_control import ControlAssessment
from app.models.jira import JiraIssue
from app.models.progress import ProjectProgressSnapshot
from app.models.remediation import RemediationItem
from app.models.risk import ProjectRisk
from app.repositories.audit_finding_repository import AuditFindingRepository
from app.repositories.control_repository import ControlRepository
from app.repositories.finance_repository import FinanceRepository
from app.repositories.health_kpi_repository import HealthKpiRepository
from app.repositories.jira_repository import JiraRepository
from app.repositories.progress_repository import ProgressRepository
from app.repositories.remediation_repository import RemediationRepository
from app.repositories.resource_repository import ResourceRepository
from app.repositories.risk_repository import RiskRepository

logger = structlog.get_logger(__name__)

# Statuses considered "open" for JIRA issues
_JIRA_OPEN_STATUSES = frozenset({"To Do", "In Progress", "Blocked"})

# Statuses considered "open" for audit findings
_AUDIT_OPEN_STATUSES = frozenset({"Open", "In Progress"})

# Statuses considered "open" for remediation items
_REMEDIATION_OPEN_STATUSES = frozenset({"Open", "In Progress"})


class ProjectHealthService:
    """
    Aggregate cross-domain health calculation service.

    Queries ALL domain repositories, computes derived metrics using the same
    formulas as individual domain services, and writes the aggregated cache
    to HealthKpiRepository. This is the single source of truth for how
    project_health_kpis records are calculated and persisted.

    Dependencies are injected via constructor to support testing and
    dependency inversion.
    """

    def __init__(
        self,
        finance_repository: FinanceRepository,
        jira_repository: JiraRepository,
        resource_repository: ResourceRepository,
        audit_finding_repository: AuditFindingRepository,
        control_repository: ControlRepository,
        remediation_repository: RemediationRepository,
        risk_repository: RiskRepository,
        progress_repository: ProgressRepository,
        health_kpi_repository: HealthKpiRepository,
    ) -> None:
        """
        Initialize with all domain repositories.

        Args:
            finance_repository: Access to budget and cost data.
            jira_repository: Access to JIRA issues and sprints.
            resource_repository: Access to resource allocations and utilization.
            audit_finding_repository: Access to audit findings.
            control_repository: Access to IT controls and assessments.
            remediation_repository: Access to remediation items.
            risk_repository: Access to project risks.
            progress_repository: Access to progress snapshots.
            health_kpi_repository: Access to the cached KPI table (read/write).
        """
        self._finance_repository = finance_repository
        self._jira_repository = jira_repository
        self._resource_repository = resource_repository
        self._audit_finding_repository = audit_finding_repository
        self._control_repository = control_repository
        self._remediation_repository = remediation_repository
        self._risk_repository = risk_repository
        self._progress_repository = progress_repository
        self._health_kpi_repository = health_kpi_repository

    async def get_project_health(self, project_id: UUID) -> dict:
        """
        Compute health KPIs from domain data for a single project.

        Fetches live data from all domain repositories and returns computed
        metrics as a dictionary. Does not persist the result — use
        recalculate_and_cache for persistence.

        Args:
            project_id: UUID of the project to compute health for.

        Returns:
            Dictionary of computed health metrics.
        """
        kpi = await self.recalculate_and_cache(project_id)

        logger.debug(
            "project_health_computed",
            project_id=str(project_id),
            overall_status=kpi.overall_status,
            progress_percentage=kpi.progress_percentage,
        )

        return {
            "project_id": kpi.project_id,
            "overall_status": kpi.overall_status,
            "schedule_status": kpi.schedule_status,
            "budget_total": kpi.budget_total,
            "budget_spent": kpi.budget_spent,
            "budget_variance": kpi.budget_variance,
            "budget_variance_percentage": kpi.budget_variance_percentage,
            "progress_percentage": kpi.progress_percentage,
            "resource_utilization_percentage": kpi.resource_utilization_percentage,
            "open_issues_count": kpi.open_issues_count,
            "open_risks_count": kpi.open_risks_count,
            "open_audit_findings_count": kpi.open_audit_findings_count,
            "open_remediation_items_count": kpi.open_remediation_items_count,
            "it_control_compliance_percentage": kpi.it_control_compliance_percentage,
            "last_calculated_at": kpi.last_calculated_at,
        }

    async def get_portfolio_summary(self) -> dict:
        """
        List all cached health KPIs for the portfolio dashboard.

        Returns the most recent cached KPI records for all projects. Does not
        trigger recalculation — call recalculate_and_cache per project to refresh.

        Returns:
            Dictionary with a list of all health KPI records.
        """
        kpis = await self._health_kpi_repository.list_all()

        logger.debug(
            "portfolio_summary_retrieved",
            project_count=len(kpis),
        )

        return {
            "projects": [
                {
                    "project_id": kpi.project_id,
                    "overall_status": kpi.overall_status,
                    "schedule_status": kpi.schedule_status,
                    "budget_total": kpi.budget_total,
                    "budget_spent": kpi.budget_spent,
                    "budget_variance": kpi.budget_variance,
                    "budget_variance_percentage": kpi.budget_variance_percentage,
                    "progress_percentage": kpi.progress_percentage,
                    "resource_utilization_percentage": kpi.resource_utilization_percentage,
                    "open_issues_count": kpi.open_issues_count,
                    "open_risks_count": kpi.open_risks_count,
                    "open_audit_findings_count": kpi.open_audit_findings_count,
                    "open_remediation_items_count": kpi.open_remediation_items_count,
                    "it_control_compliance_percentage": kpi.it_control_compliance_percentage,
                    "last_calculated_at": kpi.last_calculated_at,
                }
                for kpi in kpis
            ],
        }

    async def recalculate_and_cache(self, project_id: UUID) -> ProjectHealthKpi:
        """
        Compute all health KPIs from authoritative domain data and upsert the cache.

        Steps:
        1. Fetch budget → compute total_budget, total_spent, variance, variance_pct
        2. Fetch issues → calculate open_issues_count
        3. Fetch resource data → calculate utilization percentage
        4. Fetch audit findings → calculate open_audit_findings_count
        5. Fetch control assessments → calculate compliance_percentage
        6. Fetch remediation items → calculate open_remediation_items_count
        7. Fetch risks → calculate open_risks_count
        8. Fetch progress snapshots → derive progress_percentage
        9. Determine overall_status and schedule_status
        10. Upsert ProjectHealthKpi via repository

        Args:
            project_id: UUID of the project to recalculate.

        Returns:
            The persisted ProjectHealthKpi model instance.
        """
        # 1. Budget and variance
        budget = await self._finance_repository.get_budget_by_project(project_id)
        total_budget = budget.total_budget if budget else Decimal("0")
        total_spent = await self._finance_repository.get_total_spent(project_id)
        budget_variance = self._calculate_budget_variance(total_budget, total_spent)
        budget_variance_percentage = self._calculate_variance_percentage(
            total_budget, total_spent
        )

        # 2. Open issues
        issues = await self._jira_repository.list_issues_by_project(project_id)
        open_issues_count = self.calculate_open_issues_count(issues)

        # 3. Resource utilization
        resource_utilization_percentage = await self._compute_resource_utilization(
            project_id
        )

        # 4. Open audit findings
        findings = await self._audit_finding_repository.list_findings_by_project(
            project_id
        )
        open_audit_findings_count = self.calculate_open_audit_findings_count(findings)

        # 5. Compliance percentage
        assessments = await self._control_repository.list_assessments_by_project(
            project_id
        )
        compliance_percentage = self.calculate_compliance_percentage(assessments)

        # 6. Open remediation items
        items = await self._remediation_repository.list_items_by_project(project_id)
        open_remediation_items_count = self.calculate_open_remediation_items_count(
            items
        )

        # 7. Open risks
        risks = await self._risk_repository.list_risks_by_project(project_id)
        open_risks_count = self.calculate_open_risks_count(risks)

        # 8. Progress percentage
        snapshots = await self._progress_repository.list_snapshots_by_project(
            project_id
        )
        progress_percentage = self.derive_progress_percentage(snapshots)

        # 9. Overall and schedule status — read existing KPI if available, else derive
        existing_kpi = await self._health_kpi_repository.get_by_project(project_id)
        overall_status = self._determine_overall_status(
            existing_kpi, budget_variance, open_risks_count, progress_percentage
        )
        schedule_status = self._determine_schedule_status(
            existing_kpi, progress_percentage
        )

        # 10. Build and upsert the KPI model
        kpi = ProjectHealthKpi(
            project_id=project_id,
            overall_status=overall_status,
            schedule_status=schedule_status,
            budget_total=total_budget,
            budget_spent=total_spent,
            budget_variance=budget_variance,
            budget_variance_percentage=budget_variance_percentage,
            progress_percentage=progress_percentage,
            resource_utilization_percentage=resource_utilization_percentage,
            open_issues_count=open_issues_count,
            open_risks_count=open_risks_count,
            open_audit_findings_count=open_audit_findings_count,
            open_remediation_items_count=open_remediation_items_count,
            it_control_compliance_percentage=compliance_percentage,
            last_calculated_at=datetime.now(timezone.utc),
        )

        # Preserve existing ID if updating
        if existing_kpi:
            kpi.id = existing_kpi.id

        persisted = await self._health_kpi_repository.upsert(kpi)

        logger.info(
            "health_kpi_recalculated",
            project_id=str(project_id),
            overall_status=overall_status,
            schedule_status=schedule_status,
            budget_variance=str(budget_variance),
            open_issues_count=open_issues_count,
            open_risks_count=open_risks_count,
            progress_percentage=progress_percentage,
        )

        return persisted

    # ------------------------------------------------------------------
    # Pure calculation methods
    # ------------------------------------------------------------------

    def calculate_open_issues_count(self, issues: list[JiraIssue]) -> int:
        """
        Count issues with status IN ("To Do", "In Progress", "Blocked").

        Reuses the same formula as JiraService.calculate_open_issues_count.

        Args:
            issues: List of JiraIssue instances.

        Returns:
            Number of open issues.
        """
        return sum(1 for issue in issues if issue.status in _JIRA_OPEN_STATUSES)

    def calculate_open_risks_count(self, risks: list[ProjectRisk]) -> int:
        """
        Count risks with status == "Open".

        Args:
            risks: List of ProjectRisk instances.

        Returns:
            Number of open risks.
        """
        return sum(1 for risk in risks if risk.status == "Open")

    def calculate_open_audit_findings_count(
        self, findings: list[AuditFinding]
    ) -> int:
        """
        Count audit findings with status IN ("Open", "In Progress").

        Args:
            findings: List of AuditFinding instances.

        Returns:
            Number of open audit findings.
        """
        return sum(
            1 for finding in findings if finding.status in _AUDIT_OPEN_STATUSES
        )

    def calculate_open_remediation_items_count(
        self, items: list[RemediationItem]
    ) -> int:
        """
        Count remediation items with status IN ("Open", "In Progress").

        Args:
            items: List of RemediationItem instances.

        Returns:
            Number of open remediation items.
        """
        return sum(
            1 for item in items if item.status in _REMEDIATION_OPEN_STATUSES
        )

    def calculate_compliance_percentage(
        self, assessments: list[ControlAssessment]
    ) -> int:
        """
        Calculate IT control compliance as int((compliant / total) * 100).

        An assessment is "Compliant" when compliance_status == "Compliant".
        Returns 0 when the assessment list is empty (avoids division by zero).

        Args:
            assessments: List of ControlAssessment instances.

        Returns:
            Integer compliance percentage (0–100).
        """
        if not assessments:
            return 0

        compliant_count = sum(
            1
            for assessment in assessments
            if assessment.compliance_status == "Compliant"
        )
        return int((compliant_count / len(assessments)) * 100)

    def derive_progress_percentage(
        self, snapshots: list[ProjectProgressSnapshot]
    ) -> int:
        """
        Derive progress from the most recent snapshot's actual_progress_percentage.

        Returns 0 when no snapshots exist.

        Args:
            snapshots: List of ProjectProgressSnapshot instances.

        Returns:
            Integer progress percentage (0–100), or 0 if empty.
        """
        if not snapshots:
            return 0

        most_recent = max(snapshots, key=lambda s: s.snapshot_date)
        return most_recent.actual_progress_percentage

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_budget_variance(
        budget_total: Decimal, budget_spent: Decimal
    ) -> Decimal:
        """Positive = under budget, negative = over budget."""
        return budget_total - budget_spent

    @staticmethod
    def _calculate_variance_percentage(
        budget_total: Decimal, budget_spent: Decimal
    ) -> Decimal:
        """Variance as a percentage of total budget. Zero-safe."""
        if budget_total == 0:
            return Decimal("0")
        return ((budget_total - budget_spent) / budget_total) * 100

    async def _compute_resource_utilization(self, project_id: UUID) -> Decimal:
        """
        Compute project-level resource utilization percentage.

        Follows the same algorithm as ResourceService: average utilization of
        actively allocated team members during the most recent month.
        Falls back to Decimal("0") if no data is available.
        """
        allocations = await self._resource_repository.list_allocations_by_project(
            project_id
        )
        if not allocations:
            return Decimal("0")

        most_recent_month = (
            await self._resource_repository.get_most_recent_utilization_month()
        )
        if not most_recent_month:
            return Decimal("0")

        member_ids = [a.team_member_id for a in allocations]
        utilization_records = (
            await self._resource_repository.list_utilization_by_members(
                member_ids, most_recent_month
            )
        )

        if not utilization_records:
            return Decimal("0")

        total = sum(record.utilization_percentage for record in utilization_records)
        return Decimal(str(total)) / Decimal(len(utilization_records))

    @staticmethod
    def _determine_overall_status(
        existing_kpi: ProjectHealthKpi | None,
        budget_variance: Decimal,
        open_risks_count: int,
        progress_percentage: int,
    ) -> str:
        """
        Determine overall project status.

        If an existing KPI record exists, preserve its overall_status (may have
        been set by manual override or previous evaluation). Otherwise, derive
        based on heuristics:
        - Completed if progress is 100%
        - Delayed if budget is over by >10% or progress < 30%
        - At Risk if there are critical open risks (>= 3) or budget over
        - On Track otherwise
        """
        if existing_kpi:
            return existing_kpi.overall_status

        if progress_percentage >= 100:
            return "Completed"
        if budget_variance < Decimal("0") and progress_percentage < 30:
            return "Delayed"
        if open_risks_count >= 3 or budget_variance < Decimal("0"):
            return "At Risk"
        return "On Track"

    @staticmethod
    def _determine_schedule_status(
        existing_kpi: ProjectHealthKpi | None,
        progress_percentage: int,
    ) -> str:
        """
        Determine schedule status.

        If an existing KPI record exists, preserve its schedule_status.
        Otherwise, derive: Ahead if progress > 80%, Delayed if < 30%, else On Time.
        """
        if existing_kpi:
            return existing_kpi.schedule_status

        if progress_percentage > 80:
            return "Ahead"
        if progress_percentage < 30:
            return "Delayed"
        return "On Time"

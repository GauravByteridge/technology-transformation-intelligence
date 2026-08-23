"""Hero project scenario — orchestrates and verifies coherent Project Alpha data.

Project Alpha is the primary demonstration project with a coherent "At Risk"
scenario across all business domains. The generators produce domain-specific
data that collectively tells this story:

Expected Project Alpha state:
- overall_status: "At Risk"
- schedule_status: "Delayed"
- budget_variance_percentage <= -10% (actual spend exceeding budget by >= 10%)
- actual_progress < planned by >= 10 points in most recent snapshot
- >= 3 overdue JIRA issues (due_date in past, status != "Done")
- demand_fte > capacity_fte (resource gap) in >= 2 of 3 forecast months
- >= 1 Critical or High open risk
- >= 1 Critical open audit finding with past target_remediation_date
- >= 1 remediation item overdue (due_date past, status != "Completed")
- IT control compliance < 70%

All KPI values in project_health_kpis are derived from actual generated records
using the same formulas as ProjectHealthService — NOT independently randomized.

This module supports the following AI demonstration questions:
- "Why is Project Alpha at risk?"
- "What are the biggest risks for Project Alpha?"
- "Are resources sufficient for Project Alpha?"
- "Show Project Alpha's progress trend"
- "Generate an executive summary for Project Alpha"
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.seed.deterministic import deterministic_uuid
from app.seed.generators.project_generator import HERO_PROJECT_NAME

# Statuses considered "open" for various domains — mirrors ProjectHealthService.
_JIRA_OPEN_STATUSES = frozenset({"To Do", "In Progress", "Blocked"})
_AUDIT_OPEN_STATUSES = frozenset({"Open", "In Progress"})
_REMEDIATION_OPEN_STATUSES = frozenset({"Open", "In Progress"})

# Minimum thresholds for coherence verification.
_MIN_OVERDUE_JIRA_ISSUES = 3
_MIN_FORECAST_MONTHS_WITH_GAP = 2
_MAX_COMPLIANCE_PERCENTAGE = 69
_MIN_BUDGET_OVER_PERCENTAGE = Decimal("-10")
_MIN_PROGRESS_LAG_POINTS = 10


def get_hero_project_id() -> UUID:
    """Return the deterministic UUID for the hero project (Project Alpha)."""
    return deterministic_uuid("project", HERO_PROJECT_NAME)


class HeroProjectScenario:
    """Orchestrates verification and derivation of coherent Project Alpha data.

    The generators (finance, JIRA, resource, audit, control, remediation, risk,
    progress) each produce domain data for Project Alpha. This class provides:

    1. verify_coherence — checks that generated domain data satisfies all
       at-risk scenario constraints simultaneously.
    2. derive_health_kpi — computes the health KPI record from generated
       domain records using the same formulas as ProjectHealthService, ensuring
       KPI values are mathematically derivable from underlying data.
    """

    def verify_coherence(self, data: dict) -> bool:
        """Check that all domain data for Project Alpha is consistent with the at-risk scenario.

        Args:
            data: Dictionary with domain data lists for Project Alpha. Expected keys:
                - "budgets": list of budget dicts (with "total_budget" Decimal)
                - "actual_costs": list of actual cost dicts (with "amount" Decimal)
                - "jira_issues": list of JIRA issue dicts
                - "resource_forecasts": list of forecast dicts
                - "risks": list of risk dicts
                - "audit_findings": list of audit finding dicts
                - "remediation_items": list of remediation item dicts
                - "control_assessments": list of control assessment dicts
                - "progress_snapshots": list of progress snapshot dicts

        Returns:
            True if all coherence checks pass, False otherwise.
        """
        hero_id = get_hero_project_id()

        checks = [
            self._check_budget_over(data, hero_id),
            self._check_progress_lag(data, hero_id),
            self._check_overdue_jira(data, hero_id),
            self._check_resource_gap(data, hero_id),
            self._check_critical_risk(data, hero_id),
            self._check_critical_audit_finding(data, hero_id),
            self._check_overdue_remediation(data, hero_id),
            self._check_compliance_below_threshold(data, hero_id),
        ]

        return all(checks)

    def derive_health_kpi(self, project_id: UUID, domain_data: dict) -> dict:
        """Compute the health KPI record from generated domain records.

        Uses the same formulas as ProjectHealthService to ensure KPI values
        are mathematically derivable from the underlying seeded data.

        Args:
            project_id: UUID of the project to derive KPIs for.
            domain_data: Dictionary with domain data for this project. Expected keys:
                - "budget_total": Decimal — total approved budget
                - "total_spent": Decimal — sum of actual costs
                - "jira_issues": list of issue dicts with "status" key
                - "risks": list of risk dicts with "status" key
                - "audit_findings": list of finding dicts with "status" key
                - "remediation_items": list of remediation item dicts with "status" key
                - "control_assessments": list of assessment dicts with "compliance_status" key
                - "progress_snapshots": list of snapshot dicts with "snapshot_date"
                  and "actual_progress_percentage" keys
                - "resource_utilization_records": list of utilization dicts with
                  "utilization_percentage" key (for members allocated to this project)

        Returns:
            Dictionary matching the project_health_kpis table columns (excluding
            id, created_at, updated_at). Values are derived from the domain data.
        """
        budget_total = domain_data.get("budget_total", Decimal("0"))
        total_spent = domain_data.get("total_spent", Decimal("0"))

        budget_variance = self._calculate_budget_variance(budget_total, total_spent)
        budget_variance_percentage = self._calculate_variance_percentage(
            budget_total, total_spent
        )

        jira_issues = domain_data.get("jira_issues", [])
        open_issues_count = self._calculate_open_issues_count(jira_issues)

        risks = domain_data.get("risks", [])
        open_risks_count = self._calculate_open_risks_count(risks)

        audit_findings = domain_data.get("audit_findings", [])
        open_audit_findings_count = self._calculate_open_audit_findings_count(
            audit_findings
        )

        remediation_items = domain_data.get("remediation_items", [])
        open_remediation_items_count = self._calculate_open_remediation_items_count(
            remediation_items
        )

        control_assessments = domain_data.get("control_assessments", [])
        compliance_percentage = self._calculate_compliance_percentage(
            control_assessments
        )

        progress_snapshots = domain_data.get("progress_snapshots", [])
        progress_percentage = self._derive_progress_percentage(progress_snapshots)

        utilization_records = domain_data.get("resource_utilization_records", [])
        resource_utilization_percentage = self._calculate_resource_utilization(
            utilization_records
        )

        return {
            "project_id": project_id,
            "overall_status": "At Risk",
            "schedule_status": "Delayed",
            "budget_total": budget_total,
            "budget_spent": total_spent,
            "budget_variance": budget_variance,
            "budget_variance_percentage": budget_variance_percentage,
            "progress_percentage": progress_percentage,
            "resource_utilization_percentage": resource_utilization_percentage,
            "open_issues_count": open_issues_count,
            "open_risks_count": open_risks_count,
            "open_audit_findings_count": open_audit_findings_count,
            "open_remediation_items_count": open_remediation_items_count,
            "it_control_compliance_percentage": compliance_percentage,
        }

    # ------------------------------------------------------------------
    # Pure calculation methods — mirrors ProjectHealthService formulas
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
        return ((budget_total - budget_spent) / budget_total) * Decimal("100")

    @staticmethod
    def _calculate_open_issues_count(issues: list[dict]) -> int:
        """Count issues with status IN ("To Do", "In Progress", "Blocked")."""
        return sum(1 for issue in issues if issue.get("status") in _JIRA_OPEN_STATUSES)

    @staticmethod
    def _calculate_open_risks_count(risks: list[dict]) -> int:
        """Count risks with status == "Open"."""
        return sum(1 for risk in risks if risk.get("status") == "Open")

    @staticmethod
    def _calculate_open_audit_findings_count(findings: list[dict]) -> int:
        """Count audit findings with status IN ("Open", "In Progress")."""
        return sum(
            1 for finding in findings if finding.get("status") in _AUDIT_OPEN_STATUSES
        )

    @staticmethod
    def _calculate_open_remediation_items_count(items: list[dict]) -> int:
        """Count remediation items with status IN ("Open", "In Progress")."""
        return sum(
            1 for item in items if item.get("status") in _REMEDIATION_OPEN_STATUSES
        )

    @staticmethod
    def _calculate_compliance_percentage(assessments: list[dict]) -> int:
        """Calculate IT control compliance as int((compliant / total) * 100).

        Returns 0 when the assessment list is empty.
        """
        if not assessments:
            return 0

        compliant_count = sum(
            1
            for assessment in assessments
            if assessment.get("compliance_status") == "Compliant"
        )
        return int((compliant_count / len(assessments)) * 100)

    @staticmethod
    def _derive_progress_percentage(snapshots: list[dict]) -> int:
        """Derive progress from the most recent snapshot's actual_progress_percentage.

        Returns 0 when no snapshots exist.
        """
        if not snapshots:
            return 0

        most_recent = max(snapshots, key=lambda s: s["snapshot_date"])
        return most_recent["actual_progress_percentage"]

    @staticmethod
    def _calculate_resource_utilization(utilization_records: list[dict]) -> Decimal:
        """Compute average utilization percentage from allocated team member records.

        Returns Decimal("0") if no records.
        """
        if not utilization_records:
            return Decimal("0")

        total = sum(
            Decimal(str(record["utilization_percentage"]))
            for record in utilization_records
        )
        return total / Decimal(len(utilization_records))

    # ------------------------------------------------------------------
    # Coherence check helpers
    # ------------------------------------------------------------------

    def _check_budget_over(self, data: dict, hero_id: UUID) -> bool:
        """Verify budget_variance_percentage <= -10%."""
        budgets = [
            b for b in data.get("budgets", []) if b.get("project_id") == hero_id
        ]
        if not budgets:
            return False

        budget_total = budgets[0]["total_budget"]
        costs = [
            c for c in data.get("actual_costs", []) if c.get("project_id") == hero_id
        ]
        total_spent = sum(c["amount"] for c in costs)

        variance_pct = self._calculate_variance_percentage(budget_total, total_spent)
        return variance_pct <= _MIN_BUDGET_OVER_PERCENTAGE

    def _check_progress_lag(self, data: dict, hero_id: UUID) -> bool:
        """Verify actual progress < planned by >= 10 points in most recent snapshot."""
        snapshots = [
            s
            for s in data.get("progress_snapshots", [])
            if s.get("project_id") == hero_id
        ]
        if not snapshots:
            return False

        most_recent = max(snapshots, key=lambda s: s["snapshot_date"])
        planned = most_recent["planned_progress_percentage"]
        actual = most_recent["actual_progress_percentage"]
        return (planned - actual) >= _MIN_PROGRESS_LAG_POINTS

    def _check_overdue_jira(self, data: dict, hero_id: UUID) -> bool:
        """Verify >= 3 overdue JIRA issues (due_date in past, status != Done)."""
        today = date.today()
        issues = [
            i for i in data.get("jira_issues", []) if i.get("project_id") == hero_id
        ]
        overdue_count = sum(
            1
            for issue in issues
            if issue.get("due_date") is not None
            and issue["due_date"] < today
            and issue.get("status") != "Done"
        )
        return overdue_count >= _MIN_OVERDUE_JIRA_ISSUES

    def _check_resource_gap(self, data: dict, hero_id: UUID) -> bool:
        """Verify demand_fte > capacity_fte in >= 2 of forecast months."""
        forecasts = [
            f
            for f in data.get("resource_forecasts", [])
            if f.get("project_id") == hero_id
        ]
        gap_months = sum(
            1
            for forecast in forecasts
            if forecast["demand_fte"] > forecast["capacity_fte"]
        )
        return gap_months >= _MIN_FORECAST_MONTHS_WITH_GAP

    def _check_critical_risk(self, data: dict, hero_id: UUID) -> bool:
        """Verify >= 1 Critical or High open risk."""
        risks = [
            r for r in data.get("risks", []) if r.get("project_id") == hero_id
        ]
        return any(
            risk.get("severity") in ("Critical", "High")
            and risk.get("status") == "Open"
            for risk in risks
        )

    def _check_critical_audit_finding(self, data: dict, hero_id: UUID) -> bool:
        """Verify >= 1 Critical open audit finding with past target_remediation_date."""
        today = date.today()
        findings = [
            f
            for f in data.get("audit_findings", [])
            if f.get("project_id") == hero_id
        ]
        return any(
            finding.get("severity") == "Critical"
            and finding.get("status") in _AUDIT_OPEN_STATUSES
            and finding.get("target_remediation_date") is not None
            and finding["target_remediation_date"] < today
            for finding in findings
        )

    def _check_overdue_remediation(self, data: dict, hero_id: UUID) -> bool:
        """Verify >= 1 remediation item overdue (due_date past, status != Completed)."""
        today = date.today()
        items = [
            i
            for i in data.get("remediation_items", [])
            if i.get("project_id") == hero_id
        ]
        return any(
            item.get("due_date") is not None
            and item["due_date"] < today
            and item.get("status") != "Completed"
            for item in items
        )

    def _check_compliance_below_threshold(self, data: dict, hero_id: UUID) -> bool:
        """Verify IT control compliance < 70%."""
        assessments = [
            a
            for a in data.get("control_assessments", [])
            if a.get("project_id") == hero_id
        ]
        if not assessments:
            return False

        compliance_pct = self._calculate_compliance_percentage(assessments)
        return compliance_pct <= _MAX_COMPLIANCE_PERCENTAGE

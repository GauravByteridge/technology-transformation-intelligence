"""Health KPI derivation for seed data.

Computes project_health_kpis per project from seeded domain data using
the same formulas as ProjectHealthService. This module operates on raw
dictionaries (seed generator output) rather than ORM model instances,
allowing KPI computation without a database session.

All KPI values are mathematically derived from underlying records —
no independently randomized values.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.seed.deterministic import deterministic_uuid

# Statuses considered "open" for JIRA issues (same as ProjectHealthService)
_JIRA_OPEN_STATUSES = frozenset({"To Do", "In Progress", "Blocked"})

# Statuses considered "open" for audit findings (same as ProjectHealthService)
_AUDIT_OPEN_STATUSES = frozenset({"Open", "In Progress"})

# Statuses considered "open" for remediation items (same as ProjectHealthService)
_REMEDIATION_OPEN_STATUSES = frozenset({"Open", "In Progress"})

# Default resource utilization for seed data.
# The full algorithm requires active allocation filtering which is simplified
# for the seed script.
_DEFAULT_RESOURCE_UTILIZATION_PCT = Decimal("85.0")


def derive_project_health_kpis(
    project_id: UUID,
    project_status: str,
    finance_data: dict,
    jira_data: dict,
    risk_data: list,
    audit_data: list,
    control_data: list,
    remediation_data: list,
    progress_data: list,
    resource_utilization_pct: Decimal = _DEFAULT_RESOURCE_UTILIZATION_PCT,
) -> dict:
    """Compute health KPI values from seeded domain data for a single project.

    Applies the same formulas as ProjectHealthService to produce a dictionary
    matching the ProjectHealthKpi model columns.

    Args:
        project_id: UUID of the project.
        project_status: Project overall status (e.g., "On Track", "At Risk").
        finance_data: Dictionary from FinanceSeedGenerator.generate() containing
            "budgets" and "actual_costs" lists.
        jira_data: Dictionary from JiraSeedGenerator.generate() containing
            "jira_issues" list.
        risk_data: List of risk dictionaries for this project.
        audit_data: List of audit finding dictionaries for this project.
        control_data: List of control assessment dictionaries for this project.
        remediation_data: List of remediation item dictionaries for this project.
        progress_data: List of progress snapshot dictionaries for this project.
        resource_utilization_pct: Pre-computed resource utilization percentage.
            Defaults to 85.0% for seed simplification.

    Returns:
        Dictionary matching ProjectHealthKpi columns, ready for DB insertion.
    """
    # Budget metrics
    budget_total = _get_budget_total(project_id, finance_data)
    budget_spent = _get_budget_spent(project_id, finance_data)
    budget_variance = _calculate_budget_variance(budget_total, budget_spent)
    budget_variance_percentage = _calculate_variance_percentage(
        budget_total, budget_spent
    )

    # Issue counts
    project_issues = _filter_by_project(jira_data.get("jira_issues", []), project_id)
    open_issues_count = _calculate_open_issues_count(project_issues)

    # Risk counts
    open_risks_count = _calculate_open_risks_count(risk_data)

    # Audit finding counts
    open_audit_findings_count = _calculate_open_audit_findings_count(audit_data)

    # Remediation item counts
    open_remediation_items_count = _calculate_open_remediation_items_count(
        remediation_data
    )

    # IT control compliance
    it_control_compliance_percentage = _calculate_compliance_percentage(control_data)

    # Progress percentage from most recent snapshot
    progress_percentage = _derive_progress_percentage(progress_data)

    # Schedule status derivation
    schedule_status = _determine_schedule_status(progress_percentage, project_status)

    # Generate deterministic UUID for the KPI record
    kpi_id = deterministic_uuid("project_health_kpi", str(project_id))

    return {
        "id": kpi_id,
        "project_id": project_id,
        "overall_status": project_status,
        "schedule_status": schedule_status,
        "budget_total": budget_total,
        "budget_spent": budget_spent,
        "budget_variance": budget_variance,
        "budget_variance_percentage": budget_variance_percentage,
        "progress_percentage": progress_percentage,
        "resource_utilization_percentage": resource_utilization_pct,
        "open_issues_count": open_issues_count,
        "open_risks_count": open_risks_count,
        "open_audit_findings_count": open_audit_findings_count,
        "open_remediation_items_count": open_remediation_items_count,
        "it_control_compliance_percentage": it_control_compliance_percentage,
        "last_calculated_at": datetime.now(timezone.utc),
    }


def _get_budget_total(project_id: UUID, finance_data: dict) -> Decimal:
    """Extract total budget for a project from finance data."""
    budgets = finance_data.get("budgets", [])
    for budget in budgets:
        if budget["project_id"] == project_id:
            return budget["total_budget"]
    return Decimal("0")


def _get_budget_spent(project_id: UUID, finance_data: dict) -> Decimal:
    """Sum actual costs for a project from finance data."""
    actual_costs = finance_data.get("actual_costs", [])
    total = Decimal("0")
    for cost in actual_costs:
        if cost["project_id"] == project_id:
            total += cost["amount"]
    return total


def _calculate_budget_variance(
    budget_total: Decimal, budget_spent: Decimal
) -> Decimal:
    """Positive = under budget, negative = over budget."""
    return budget_total - budget_spent


def _calculate_variance_percentage(
    budget_total: Decimal, budget_spent: Decimal
) -> Decimal:
    """Variance as a percentage of total budget. Returns 0 when budget_total is 0."""
    if budget_total == 0:
        return Decimal("0")
    return ((budget_total - budget_spent) / budget_total) * 100


def _calculate_open_issues_count(issues: list[dict]) -> int:
    """Count issues with status IN ("To Do", "In Progress", "Blocked")."""
    return sum(1 for issue in issues if issue["status"] in _JIRA_OPEN_STATUSES)


def _calculate_open_risks_count(risks: list[dict]) -> int:
    """Count risks with status == "Open"."""
    return sum(1 for risk in risks if risk["status"] == "Open")


def _calculate_open_audit_findings_count(findings: list[dict]) -> int:
    """Count audit findings with status IN ("Open", "In Progress")."""
    return sum(
        1 for finding in findings if finding["status"] in _AUDIT_OPEN_STATUSES
    )


def _calculate_open_remediation_items_count(items: list[dict]) -> int:
    """Count remediation items with status IN ("Open", "In Progress")."""
    return sum(
        1 for item in items if item["status"] in _REMEDIATION_OPEN_STATUSES
    )


def _calculate_compliance_percentage(assessments: list[dict]) -> int:
    """Calculate IT control compliance: int((compliant / total) * 100).

    Returns 0 for empty assessment lists.
    """
    if not assessments:
        return 0
    compliant_count = sum(
        1
        for assessment in assessments
        if assessment["compliance_status"] == "Compliant"
    )
    return int((compliant_count / len(assessments)) * 100)


def _derive_progress_percentage(snapshots: list[dict]) -> int:
    """Return actual_progress_percentage of the most recent snapshot.

    Returns 0 when no snapshots exist.
    """
    if not snapshots:
        return 0
    most_recent = max(snapshots, key=lambda s: s["snapshot_date"])
    return most_recent["actual_progress_percentage"]


def _filter_by_project(items: list[dict], project_id: UUID) -> list[dict]:
    """Filter a list of dicts to those matching a project_id."""
    return [item for item in items if item["project_id"] == project_id]


def _determine_schedule_status(progress_percentage: int, overall_status: str) -> str:
    """Determine schedule status from progress and overall project status.

    Allowed values per CHECK constraint: "On Time", "Delayed", "Ahead".

    Uses the same heuristic logic as ProjectHealthService:
    - Progress > 80% or Completed: "Ahead"
    - Progress < 30% or overall_status is "Delayed": "Delayed"
    - Otherwise: "On Time"
    """
    if overall_status == "Completed" or progress_percentage > 80:
        return "Ahead"
    if overall_status == "Delayed" or progress_percentage < 30:
        return "Delayed"
    return "On Time"

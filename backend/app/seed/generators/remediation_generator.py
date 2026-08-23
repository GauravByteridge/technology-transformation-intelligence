"""Remediation item seed generator.

Generates at least 2 remediation items per project linked to existing
audit findings. At-risk projects have at least 1 item with due_date
in the past and status not "Completed" — representing the derived
overdue condition.

Statuses: Open, In Progress, Completed, Cancelled
Priorities: Critical, High, Medium, Low

The generator receives audit findings as input (list of finding dicts
with "id" and "project_id" keys) to establish proper foreign key links.
"""

from datetime import date, timedelta
from uuid import UUID

from app.seed.deterministic import deterministic_uuid

# Project names classified as "At Risk" — these must have at least 1 overdue item.
AT_RISK_PROJECTS: set[str] = {
    "Project Alpha",
    "Security Operations Center",
    "Mobile Banking Platform",
}

# Mapping of project names to short codes (consistent with audit generator).
PROJECT_SHORT_CODES: dict[str, str] = {
    "Project Alpha": "ALPHA",
    "Cloud Migration Platform": "CLOUD",
    "Data Platform Modernization": "DATAP",
    "API Gateway Implementation": "APIGW",
    "Legacy System Decommission": "LEGCY",
    "Security Operations Center": "SECOP",
    "DevOps Pipeline Automation": "DEVOP",
    "Customer Portal Redesign": "CUSTM",
    "Enterprise Data Lake": "DLAKE",
    "Mobile Banking Platform": "MOBIL",
    "Identity Access Management": "IDMGT",
    "Regulatory Reporting Engine": "REGRP",
}

# Remediation item templates with realistic action descriptions.
REMEDIATION_TEMPLATES: list[dict[str, str]] = [
    {
        "title": "Implement multi-factor authentication for privileged accounts",
        "description": (
            "Deploy MFA solution for all privileged accounts identified in the audit. "
            "Includes configuration, testing, and user enrollment across all environments."
        ),
        "priority": "Critical",
        "owner": "Identity & Access Management Lead",
    },
    {
        "title": "Update change management documentation procedures",
        "description": (
            "Revise change management templates to include mandatory impact assessments "
            "and rollback procedures. Train change advisory board on new requirements."
        ),
        "priority": "High",
        "owner": "Change Management Lead",
    },
    {
        "title": "Establish automated backup verification schedule",
        "description": (
            "Implement automated monthly backup restoration tests with documented results. "
            "Configure alerting for failed verification jobs."
        ),
        "priority": "High",
        "owner": "Infrastructure Operations Manager",
    },
    {
        "title": "Complete vendor security assessment cycle",
        "description": (
            "Conduct overdue security assessments for all Tier-1 vendors with data access. "
            "Document findings and remediation requirements in vendor risk register."
        ),
        "priority": "Medium",
        "owner": "Vendor Risk Manager",
    },
    {
        "title": "Update security awareness training program",
        "description": (
            "Refresh training materials, re-enroll non-compliant staff, and implement "
            "quarterly completion tracking with automated reminders."
        ),
        "priority": "Medium",
        "owner": "Security Awareness Coordinator",
    },
    {
        "title": "Revise incident response playbooks",
        "description": (
            "Update all incident response playbooks with current contact information, "
            "escalation paths, and integration with new monitoring tools."
        ),
        "priority": "Low",
        "owner": "Incident Response Team Lead",
    },
    {
        "title": "Accelerate non-critical patch deployment",
        "description": (
            "Review and streamline patch deployment pipeline for non-production systems "
            "to meet 30-day SLA. Implement automated patch scheduling."
        ),
        "priority": "Low",
        "owner": "Patch Management Specialist",
    },
]

# Status rotation for non-at-risk projects ensures variety.
STATUS_ROTATION: list[list[str]] = [
    ["Completed", "In Progress"],
    ["In Progress", "Completed"],
    ["Completed", "Cancelled"],
    ["In Progress", "Open"],
]


class RemediationSeedGenerator:
    """Generates remediation item seed data linked to existing audit findings.

    Produces at least 2 remediation items per project. At-risk projects
    receive at least 1 item with due_date in the past and status not
    "Completed", satisfying the derived overdue condition requirement.
    """

    def generate(
        self,
        findings: list[dict],
        project_ids_with_names: list[tuple[UUID, str]],
    ) -> list[dict]:
        """Generate remediation item records for all projects.

        Args:
            findings: List of audit finding dicts from AuditSeedGenerator output.
                Each dict must contain "id" (UUID) and "project_id" (UUID) keys.
            project_ids_with_names: List of (project_id, project_name) tuples.

        Returns:
            List of remediation item dictionaries matching the RemediationItem
            model columns.
        """
        today = date.today()
        items: list[dict] = []

        # Group findings by project_id for easy lookup.
        findings_by_project: dict[UUID, list[dict]] = {}
        for finding in findings:
            pid = finding["project_id"]
            findings_by_project.setdefault(pid, []).append(finding)

        for project_idx, (project_id, project_name) in enumerate(project_ids_with_names):
            project_findings = findings_by_project.get(project_id, [])
            if not project_findings:
                continue

            short_code = PROJECT_SHORT_CODES.get(project_name, f"P{project_idx:02d}")
            is_at_risk = project_name in AT_RISK_PROJECTS

            project_items = self._generate_project_items(
                project_id=project_id,
                project_findings=project_findings,
                short_code=short_code,
                is_at_risk=is_at_risk,
                project_idx=project_idx,
                today=today,
            )
            items.extend(project_items)

        return items

    def _generate_project_items(
        self,
        project_id: UUID,
        project_findings: list[dict],
        short_code: str,
        is_at_risk: bool,
        project_idx: int,
        today: date,
    ) -> list[dict]:
        """Generate remediation items for a single project.

        At-risk projects get at least 1 overdue item (due_date in past, status
        not "Completed"). All projects get at least 2 items.
        """
        items: list[dict] = []
        seq = 1

        if is_at_risk:
            # First item: overdue — due_date in the past, status "Open" or "In Progress"
            finding = project_findings[0]
            items.append(
                self._build_item(
                    project_id=project_id,
                    finding_id=finding["id"],
                    short_code=short_code,
                    seq=seq,
                    title=f"Urgent remediation for: {finding.get('title', 'critical finding')}",
                    description=(
                        "Immediate action required to address audit finding. "
                        "Remediation plan approved but execution delayed due to "
                        "resource constraints and competing priorities."
                    ),
                    priority="Critical",
                    status="Open",
                    due_date=today - timedelta(days=10),
                    completion_date=None,
                    owner="Remediation Program Manager",
                )
            )
            seq += 1

            # Second item: in progress, future due date
            finding_idx = min(1, len(project_findings) - 1)
            finding = project_findings[finding_idx]
            items.append(
                self._build_item(
                    project_id=project_id,
                    finding_id=finding["id"],
                    short_code=short_code,
                    seq=seq,
                    title=f"Remediation plan for: {finding.get('title', 'finding')}",
                    description=(
                        "Structured remediation plan in execution. Progress tracked "
                        "weekly with stakeholder updates."
                    ),
                    priority="High",
                    status="In Progress",
                    due_date=today + timedelta(days=20),
                    completion_date=None,
                    owner="Security Operations Lead",
                )
            )
            seq += 1

            # Third item (if enough findings): completed
            if len(project_findings) >= 3:
                finding = project_findings[2]
                completion = today - timedelta(days=5)
                items.append(
                    self._build_item(
                        project_id=project_id,
                        finding_id=finding["id"],
                        short_code=short_code,
                        seq=seq,
                        title=f"Completed remediation for: {finding.get('title', 'finding')}",
                        description=(
                            "Remediation actions completed and verified. "
                            "Control effectiveness confirmed through testing."
                        ),
                        priority="Medium",
                        status="Completed",
                        due_date=today - timedelta(days=15),
                        completion_date=completion,
                        owner="Compliance Analyst",
                    )
                )
        else:
            # Non-at-risk projects: 2 items with varied statuses
            statuses = STATUS_ROTATION[project_idx % len(STATUS_ROTATION)]
            templates = self._select_templates(project_idx)

            for i in range(2):
                finding_idx = min(i, len(project_findings) - 1)
                finding = project_findings[finding_idx]
                template = templates[i]
                status = statuses[i]

                due_date: date
                completion_date: date | None = None

                if status == "Completed":
                    due_date = today - timedelta(days=20 + (i * 10))
                    completion_date = due_date - timedelta(days=3)
                elif status == "Cancelled":
                    due_date = today + timedelta(days=10 + (i * 10))
                else:
                    # Open or In Progress with future due date (not overdue)
                    due_date = today + timedelta(days=15 + (i * 10) + (project_idx * 3))

                items.append(
                    self._build_item(
                        project_id=project_id,
                        finding_id=finding["id"],
                        short_code=short_code,
                        seq=seq,
                        title=template["title"],
                        description=template["description"],
                        priority=template["priority"],
                        status=status,
                        due_date=due_date,
                        completion_date=completion_date,
                        owner=template["owner"],
                    )
                )
                seq += 1

        return items

    def _build_item(
        self,
        project_id: UUID,
        finding_id: UUID,
        short_code: str,
        seq: int,
        title: str,
        description: str,
        priority: str,
        status: str,
        due_date: date,
        completion_date: date | None,
        owner: str,
    ) -> dict:
        """Build a single remediation item dictionary."""
        item_id = deterministic_uuid("remediation_item", short_code, str(seq))

        return {
            "id": item_id,
            "finding_id": finding_id,
            "project_id": project_id,
            "title": title,
            "description": description,
            "owner": owner,
            "status": status,
            "priority": priority,
            "due_date": due_date,
            "completion_date": completion_date,
        }

    def _select_templates(self, project_idx: int) -> list[dict[str, str]]:
        """Select 2 remediation templates for a non-at-risk project.

        Rotates through available templates to ensure variety across projects.
        """
        start = (project_idx * 2) % len(REMEDIATION_TEMPLATES)
        selected: list[dict[str, str]] = []
        for i in range(2):
            idx = (start + i) % len(REMEDIATION_TEMPLATES)
            selected.append(REMEDIATION_TEMPLATES[idx])
        return selected

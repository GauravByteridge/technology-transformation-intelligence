"""Audit finding seed generator.

Generates at least 3 audit findings per project with mixed severities
(Critical, High, Medium, Low) and statuses (Open, In Progress, Closed).

Project Alpha has at least 1 Critical finding with status "Open" and
target_remediation_date in the past — representing the derived overdue condition.

Uses finding_reference pattern: AF-{PROJECT_SHORT}-{SEQ} (e.g., AF-ALPHA-001).
"""

from datetime import date, timedelta
from uuid import UUID

from app.seed.deterministic import deterministic_uuid

# Mapping of project names to short codes for finding_reference generation.
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

# Realistic audit finding templates per severity.
FINDING_TEMPLATES: list[dict[str, str]] = [
    {
        "title": "Insufficient access control on privileged accounts",
        "description": "Privileged accounts lack multi-factor authentication and periodic access reviews, increasing risk of unauthorized access to critical systems.",
        "severity": "Critical",
        "auditor": "Internal Audit - Compliance Division",
    },
    {
        "title": "Inadequate change management documentation",
        "description": "Change requests lack complete impact assessments and rollback procedures, creating risk of uncontrolled system modifications.",
        "severity": "High",
        "auditor": "External Auditor - Deloitte",
    },
    {
        "title": "Data backup verification gaps",
        "description": "Backup restoration tests have not been performed in the last 6 months, leaving data recovery capability unverified.",
        "severity": "High",
        "auditor": "Internal Audit - IT Risk",
    },
    {
        "title": "Incomplete vendor risk assessments",
        "description": "Third-party vendors with access to sensitive data have not undergone annual security assessments as required by policy.",
        "severity": "Medium",
        "auditor": "Internal Audit - Vendor Management",
    },
    {
        "title": "Outdated security awareness training records",
        "description": "Security awareness training completion records show 15% of staff have not completed mandatory annual training within the required timeframe.",
        "severity": "Medium",
        "auditor": "Internal Audit - Compliance Division",
    },
    {
        "title": "Minor documentation gaps in incident response playbooks",
        "description": "Some incident response playbooks reference deprecated contact information and outdated escalation procedures.",
        "severity": "Low",
        "auditor": "Internal Audit - IT Risk",
    },
    {
        "title": "Non-critical patch management delays",
        "description": "Low-severity patches for non-production systems are applied outside the 30-day SLA window, though no exploitation evidence exists.",
        "severity": "Low",
        "auditor": "External Auditor - PwC",
    },
]

# Status distributions for non-hero projects.
# Ensures mix of Open, In Progress, Closed per project.
STATUS_ROTATION: list[list[str]] = [
    ["Open", "In Progress", "Closed"],
    ["Closed", "Open", "In Progress"],
    ["In Progress", "Closed", "Open"],
    ["Open", "Closed", "In Progress"],
]


class AuditSeedGenerator:
    """Generates audit finding seed data for all projects.

    Produces at least 3 findings per project with mixed severities and statuses.
    Project Alpha receives a Critical/Open finding with a past target_remediation_date
    to represent the derived overdue condition.
    """

    def generate(self, project_ids_with_names: list[tuple[UUID, str]]) -> list[dict]:
        """Generate audit finding records for all projects.

        Args:
            project_ids_with_names: List of (project_id, project_name) tuples.

        Returns:
            List of audit finding dictionaries matching the AuditFinding model columns.
        """
        today = date.today()
        findings: list[dict] = []

        for project_idx, (project_id, project_name) in enumerate(project_ids_with_names):
            short_code = PROJECT_SHORT_CODES.get(project_name, f"P{project_idx:02d}")
            is_hero = project_name == "Project Alpha"

            project_findings = self._generate_project_findings(
                project_id=project_id,
                short_code=short_code,
                is_hero=is_hero,
                project_idx=project_idx,
                today=today,
            )
            findings.extend(project_findings)

        return findings

    def _generate_project_findings(
        self,
        project_id: UUID,
        short_code: str,
        is_hero: bool,
        project_idx: int,
        today: date,
    ) -> list[dict]:
        """Generate findings for a single project.

        Hero project (Project Alpha) gets a specific Critical/Open/overdue finding.
        All projects get at least 3 findings with mixed severities and statuses.
        """
        findings: list[dict] = []
        seq = 1

        if is_hero:
            # Critical finding: Open status with past target_remediation_date (overdue)
            findings.append(
                self._build_finding(
                    project_id=project_id,
                    short_code=short_code,
                    seq=seq,
                    title="Critical security vulnerability in authentication service",
                    description=(
                        "A critical authentication bypass vulnerability has been identified "
                        "in the core banking authentication service. Exploitation could allow "
                        "unauthorized access to customer accounts and financial transactions. "
                        "Immediate remediation required per security policy SOP-SEC-001."
                    ),
                    severity="Critical",
                    status="Open",
                    identified_date=today - timedelta(days=45),
                    target_remediation_date=today - timedelta(days=15),
                    actual_remediation_date=None,
                    auditor="Internal Audit - Compliance Division",
                )
            )
            seq += 1

            # High finding: In Progress
            findings.append(
                self._build_finding(
                    project_id=project_id,
                    short_code=short_code,
                    seq=seq,
                    title="Incomplete encryption implementation for data at rest",
                    description=(
                        "Several database tables containing PII lack encryption at rest. "
                        "Migration to encrypted storage is in progress but behind schedule."
                    ),
                    severity="High",
                    status="In Progress",
                    identified_date=today - timedelta(days=60),
                    target_remediation_date=today + timedelta(days=10),
                    actual_remediation_date=None,
                    auditor="External Auditor - Deloitte",
                )
            )
            seq += 1

            # Medium finding: Closed
            findings.append(
                self._build_finding(
                    project_id=project_id,
                    short_code=short_code,
                    seq=seq,
                    title="Logging configuration missing for audit trail",
                    description=(
                        "Application logging was not configured to capture all required "
                        "audit trail events. Configuration has been updated and verified."
                    ),
                    severity="Medium",
                    status="Closed",
                    identified_date=today - timedelta(days=90),
                    target_remediation_date=today - timedelta(days=60),
                    actual_remediation_date=today - timedelta(days=65),
                    auditor="Internal Audit - IT Risk",
                )
            )
            seq += 1

            # Low finding: Closed
            findings.append(
                self._build_finding(
                    project_id=project_id,
                    short_code=short_code,
                    seq=seq,
                    title="Outdated system documentation in knowledge base",
                    description=(
                        "Several architecture documents in the knowledge base reference "
                        "deprecated components. Documents have been updated."
                    ),
                    severity="Low",
                    status="Closed",
                    identified_date=today - timedelta(days=120),
                    target_remediation_date=today - timedelta(days=90),
                    actual_remediation_date=today - timedelta(days=95),
                    auditor="Internal Audit - Compliance Division",
                )
            )
        else:
            # Non-hero projects: generate 3 findings with mixed severities and statuses
            statuses = STATUS_ROTATION[project_idx % len(STATUS_ROTATION)]
            templates = self._select_templates(project_idx)

            for i, (template, status) in enumerate(zip(templates, statuses)):
                # Determine dates based on status
                identified_date = today - timedelta(days=30 + (i * 20) + (project_idx * 5))
                target_date = today + timedelta(days=15 + (i * 10)) if status != "Closed" else today - timedelta(days=10 + i * 5)
                actual_date = target_date - timedelta(days=3) if status == "Closed" else None

                findings.append(
                    self._build_finding(
                        project_id=project_id,
                        short_code=short_code,
                        seq=seq,
                        title=template["title"],
                        description=template["description"],
                        severity=template["severity"],
                        status=status,
                        identified_date=identified_date,
                        target_remediation_date=target_date,
                        actual_remediation_date=actual_date,
                        auditor=template["auditor"],
                    )
                )
                seq += 1

        return findings

    def _build_finding(
        self,
        project_id: UUID,
        short_code: str,
        seq: int,
        title: str,
        description: str,
        severity: str,
        status: str,
        identified_date: date,
        target_remediation_date: date | None,
        actual_remediation_date: date | None,
        auditor: str,
    ) -> dict:
        """Build a single audit finding dictionary."""
        finding_reference = f"AF-{short_code}-{seq:03d}"
        finding_id = deterministic_uuid("audit_finding", short_code, finding_reference)

        return {
            "id": finding_id,
            "project_id": project_id,
            "finding_reference": finding_reference,
            "title": title,
            "description": description,
            "severity": severity,
            "status": status,
            "identified_date": identified_date,
            "target_remediation_date": target_remediation_date,
            "actual_remediation_date": actual_remediation_date,
            "auditor": auditor,
        }

    def _select_templates(self, project_idx: int) -> list[dict[str, str]]:
        """Select 3 finding templates for a non-hero project.

        Rotates through available templates to ensure variety across projects.
        """
        start = (project_idx * 3) % len(FINDING_TEMPLATES)
        selected: list[dict[str, str]] = []
        for i in range(3):
            idx = (start + i) % len(FINDING_TEMPLATES)
            selected.append(FINDING_TEMPLATES[idx])
        return selected

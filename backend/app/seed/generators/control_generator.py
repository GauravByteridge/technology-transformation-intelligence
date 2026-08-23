"""IT control and control assessment seed generator.

Generates at least 10 IT control definitions across categories:
Access Control, Change Management, Data Protection, Incident Response,
and Business Continuity.

Generates assessment records linking each project to at least 5 controls
with mixed compliance statuses (Compliant, Non-Compliant, Partially Compliant,
Not Assessed).

Project Alpha: compliance < 70% (e.g., 3 Compliant out of 5 assessed = 60%).

Uses control_reference pattern: CTRL-{CATEGORY_SHORT}-{SEQ}
(e.g., CTRL-AC-001, CTRL-CM-002).
"""

from datetime import date, timedelta
from uuid import UUID

from app.seed.deterministic import deterministic_uuid

# Category short codes for control_reference generation.
CATEGORY_SHORT_CODES: dict[str, str] = {
    "Access Control": "AC",
    "Change Management": "CM",
    "Data Protection": "DP",
    "Incident Response": "IR",
    "Business Continuity": "BC",
}

# IT control definitions — at least 10 across all 5 categories.
CONTROL_DEFINITIONS: list[dict[str, str]] = [
    # Access Control (AC)
    {
        "name": "Privileged Access Management",
        "description": (
            "Privileged accounts must be managed through a dedicated PAM solution "
            "with session recording, just-in-time elevation, and periodic access certification."
        ),
        "category": "Access Control",
        "framework": "ISO 27001 - A.9.2",
    },
    {
        "name": "Multi-Factor Authentication",
        "description": (
            "All remote access and administrative interfaces must enforce multi-factor "
            "authentication using hardware tokens or authenticator applications."
        ),
        "category": "Access Control",
        "framework": "NIST 800-53 - IA-2",
    },
    {
        "name": "Periodic Access Review",
        "description": (
            "User access rights must be reviewed quarterly by system owners to ensure "
            "least-privilege principle and remove stale accounts."
        ),
        "category": "Access Control",
        "framework": "SOX ITGC - Access Management",
    },
    # Change Management (CM)
    {
        "name": "Change Advisory Board Approval",
        "description": (
            "All changes to production systems must be reviewed and approved by the "
            "Change Advisory Board prior to implementation, with documented risk assessment."
        ),
        "category": "Change Management",
        "framework": "ITIL v4 - Change Enablement",
    },
    {
        "name": "Segregation of Duties in Deployments",
        "description": (
            "The individual who develops a change must not be the same individual "
            "who approves or deploys it to production environments."
        ),
        "category": "Change Management",
        "framework": "SOX ITGC - Change Management",
    },
    # Data Protection (DP)
    {
        "name": "Encryption at Rest",
        "description": (
            "All data classified as Confidential or above must be encrypted at rest "
            "using AES-256 or equivalent, with encryption keys managed centrally."
        ),
        "category": "Data Protection",
        "framework": "ISO 27001 - A.10.1",
    },
    {
        "name": "Data Loss Prevention Monitoring",
        "description": (
            "DLP controls must monitor and prevent unauthorized transfer of sensitive "
            "data through email, removable media, and cloud storage services."
        ),
        "category": "Data Protection",
        "framework": "NIST 800-53 - SC-7",
    },
    # Incident Response (IR)
    {
        "name": "Incident Detection and Alerting",
        "description": (
            "Security information and event management (SIEM) must detect and alert "
            "on anomalous activity within 15 minutes of occurrence."
        ),
        "category": "Incident Response",
        "framework": "NIST CSF - DE.AE",
    },
    {
        "name": "Incident Escalation Procedures",
        "description": (
            "Documented escalation procedures must exist for all severity levels, "
            "with defined response times and communication templates."
        ),
        "category": "Incident Response",
        "framework": "ISO 27001 - A.16.1",
    },
    # Business Continuity (BC)
    {
        "name": "Disaster Recovery Testing",
        "description": (
            "Disaster recovery plans must be tested annually with documented results, "
            "including recovery time objectives (RTO) and recovery point objectives (RPO) validation."
        ),
        "category": "Business Continuity",
        "framework": "ISO 22301 - 8.5",
    },
    {
        "name": "Business Impact Analysis",
        "description": (
            "Business impact analyses must be reviewed annually to identify critical "
            "processes and their maximum tolerable downtime thresholds."
        ),
        "category": "Business Continuity",
        "framework": "NIST 800-34 - BIA",
    },
    {
        "name": "Backup and Recovery Verification",
        "description": (
            "Automated backup jobs must be monitored for success and backup "
            "restoration must be tested quarterly for critical systems."
        ),
        "category": "Business Continuity",
        "framework": "ISO 27001 - A.12.3",
    },
]

# Compliance status distributions for non-hero projects.
# Each project gets at least 5 assessed controls. These patterns ensure a mix.
COMPLIANCE_PATTERNS: list[list[str]] = [
    ["Compliant", "Compliant", "Compliant", "Partially Compliant", "Not Assessed"],
    ["Compliant", "Compliant", "Partially Compliant", "Non-Compliant", "Compliant"],
    ["Compliant", "Compliant", "Compliant", "Compliant", "Partially Compliant"],
    ["Compliant", "Non-Compliant", "Compliant", "Compliant", "Partially Compliant"],
    ["Compliant", "Compliant", "Compliant", "Compliant", "Compliant"],
    ["Compliant", "Compliant", "Partially Compliant", "Partially Compliant", "Compliant"],
]

# Project Alpha compliance pattern: < 70%.
# 2 Compliant out of 5 assessed = 40% (below 70% threshold).
HERO_COMPLIANCE_PATTERN: list[str] = [
    "Non-Compliant",
    "Non-Compliant",
    "Compliant",
    "Partially Compliant",
    "Non-Compliant",
]

# Assessor names for realistic data.
ASSESSORS: list[str] = [
    "GRC Team - Annual Review",
    "Internal Audit - IT Controls",
    "External Auditor - KPMG",
    "Compliance Office - Quarterly",
    "Security Team - Continuous Monitoring",
]


class ControlSeedGenerator:
    """Generates IT control definitions and control assessment seed data.

    Produces at least 10 IT control definitions across 5 categories and
    assessment records linking each project to at least 5 controls with
    mixed compliance statuses.

    Project Alpha receives a compliance-deficient scenario (< 70%).
    """

    def generate_controls(self) -> list[dict]:
        """Generate IT control definition records.

        Returns:
            List of control dictionaries matching the ItControl model columns.
        """
        controls: list[dict] = []
        # Track sequence per category for control_reference generation.
        category_seq: dict[str, int] = {}

        for control_def in CONTROL_DEFINITIONS:
            category = control_def["category"]
            short_code = CATEGORY_SHORT_CODES[category]

            seq = category_seq.get(category, 0) + 1
            category_seq[category] = seq

            control_reference = f"CTRL-{short_code}-{seq:03d}"
            control_id = deterministic_uuid("it_control", control_reference)

            controls.append(
                {
                    "id": control_id,
                    "control_reference": control_reference,
                    "name": control_def["name"],
                    "description": control_def["description"],
                    "category": category,
                    "framework": control_def["framework"],
                }
            )

        return controls

    def generate_assessments(
        self,
        project_ids_with_names: list[tuple[UUID, str]],
        controls: list[dict],
    ) -> list[dict]:
        """Generate control assessment records linking projects to controls.

        Each project is assessed against at least 5 controls with mixed
        compliance statuses. Project Alpha has compliance < 70%.

        Args:
            project_ids_with_names: List of (project_id, project_name) tuples.
            controls: List of control dictionaries (output of generate_controls).

        Returns:
            List of assessment dictionaries matching the ControlAssessment model columns.
        """
        today = date.today()
        assessments: list[dict] = []

        for project_idx, (project_id, project_name) in enumerate(project_ids_with_names):
            is_hero = project_name == "Project Alpha"

            # Select which controls to assess for this project (at least 5).
            assessed_controls = self._select_controls_for_project(
                controls, project_idx
            )

            # Determine compliance pattern.
            if is_hero:
                compliance_statuses = HERO_COMPLIANCE_PATTERN
            else:
                pattern_idx = project_idx % len(COMPLIANCE_PATTERNS)
                compliance_statuses = COMPLIANCE_PATTERNS[pattern_idx]

            for i, control in enumerate(assessed_controls):
                status = compliance_statuses[i]
                assessor = ASSESSORS[i % len(ASSESSORS)]

                assessed_date = today - timedelta(days=30 + (project_idx * 7) + (i * 5))
                next_assessment_date = assessed_date + timedelta(days=90)

                notes = self._generate_notes(status, control["name"])

                assessment_id = deterministic_uuid(
                    "control_assessment",
                    str(control["id"]),
                    str(project_id),
                )

                assessments.append(
                    {
                        "id": assessment_id,
                        "control_id": control["id"],
                        "project_id": project_id,
                        "compliance_status": status,
                        "assessed_date": assessed_date,
                        "assessor": assessor,
                        "notes": notes,
                        "next_assessment_date": next_assessment_date,
                    }
                )

        return assessments

    def _select_controls_for_project(
        self, controls: list[dict], project_idx: int
    ) -> list[dict]:
        """Select at least 5 controls to assess for a project.

        Rotates through available controls to ensure variety across projects.
        """
        num_controls = len(controls)
        start = (project_idx * 2) % num_controls
        selected: list[dict] = []

        for i in range(5):
            idx = (start + i) % num_controls
            selected.append(controls[idx])

        return selected

    def _generate_notes(self, compliance_status: str, control_name: str) -> str | None:
        """Generate assessment notes based on compliance status."""
        if compliance_status == "Compliant":
            return f"{control_name} - all requirements met. No exceptions noted."
        elif compliance_status == "Non-Compliant":
            return (
                f"{control_name} - significant gaps identified. "
                "Remediation plan required within 30 days."
            )
        elif compliance_status == "Partially Compliant":
            return (
                f"{control_name} - partial implementation observed. "
                "Minor gaps require attention within 60 days."
            )
        elif compliance_status == "Not Assessed":
            return None
        return None

    def get_control_id_by_reference(self, control_reference: str) -> UUID:
        """Return the deterministic UUID for a control by its reference."""
        return deterministic_uuid("it_control", control_reference)

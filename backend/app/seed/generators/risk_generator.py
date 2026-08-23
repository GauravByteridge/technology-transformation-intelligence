"""Project risk seed generator.

Generates at least 3 risks per project with mixed severities
(Critical, High, Medium, Low) and statuses (Open, Mitigated, Closed).

Project Alpha has at least 1 High or Critical open risk to support
the coherent at-risk scenario.

Uses risk_reference pattern: RISK-{PROJECT_SHORT_NAME}-{SEQ}
(e.g., RISK-ALPHA-001, RISK-CLOUD-001).
"""

from datetime import date, timedelta
from uuid import UUID

from app.seed.deterministic import deterministic_uuid

# Mapping of project names to short codes for risk_reference generation.
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

# Realistic risk templates with mixed severities.
RISK_TEMPLATES: list[dict[str, str]] = [
    {
        "title": "Key personnel departure risk",
        "description": (
            "Critical technical leads may leave the project due to market demand "
            "for their specialized skills, causing knowledge loss and delivery delays."
        ),
        "severity": "High",
        "owner": "Project Manager",
    },
    {
        "title": "Third-party vendor delivery delay",
        "description": (
            "External vendor responsible for critical integration components has "
            "signaled potential delivery delays due to internal restructuring."
        ),
        "severity": "Medium",
        "owner": "Vendor Manager",
    },
    {
        "title": "Regulatory compliance requirement change",
        "description": (
            "Upcoming regulatory changes may require additional compliance features "
            "not currently in scope, potentially impacting timeline and budget."
        ),
        "severity": "Medium",
        "owner": "Compliance Officer",
    },
    {
        "title": "Infrastructure capacity constraints",
        "description": (
            "Current infrastructure provisioning may not support projected load "
            "during peak periods, risking performance degradation in production."
        ),
        "severity": "High",
        "owner": "Infrastructure Lead",
    },
    {
        "title": "Data migration integrity risk",
        "description": (
            "Complex data transformations during migration may introduce data "
            "quality issues that are difficult to detect post-migration."
        ),
        "severity": "Critical",
        "owner": "Data Architect",
    },
    {
        "title": "Security vulnerability in legacy dependencies",
        "description": (
            "Legacy system dependencies contain known security vulnerabilities "
            "that may be exploited before migration is complete."
        ),
        "severity": "Critical",
        "owner": "Security Lead",
    },
    {
        "title": "Budget overrun due to scope creep",
        "description": (
            "Uncontrolled scope additions from stakeholders may exhaust remaining "
            "budget reserves before critical deliverables are completed."
        ),
        "severity": "High",
        "owner": "Program Director",
    },
    {
        "title": "Integration testing environment unavailability",
        "description": (
            "Shared integration testing environment has competing demand from "
            "multiple projects, risking testing schedule delays."
        ),
        "severity": "Low",
        "owner": "QA Manager",
    },
    {
        "title": "Documentation debt impacting knowledge transfer",
        "description": (
            "Insufficient documentation may slow onboarding of new team members "
            "and complicate future maintenance activities."
        ),
        "severity": "Low",
        "owner": "Technical Writer",
    },
]

# Status distributions for non-hero projects.
# Ensures mix of Open, Mitigated, Closed per project.
STATUS_ROTATION: list[list[str]] = [
    ["Open", "Mitigated", "Closed"],
    ["Closed", "Open", "Mitigated"],
    ["Mitigated", "Closed", "Open"],
    ["Open", "Closed", "Mitigated"],
]


class RiskSeedGenerator:
    """Generates project risk seed data for all projects.

    Produces at least 3 risks per project with mixed severities and statuses.
    Project Alpha receives at least one High or Critical open risk to support
    the coherent at-risk hero scenario.
    """

    def generate(self, project_ids_with_names: list[tuple[UUID, str]]) -> list[dict]:
        """Generate project risk records for all projects.

        Args:
            project_ids_with_names: List of (project_id, project_name) tuples.

        Returns:
            List of risk dictionaries matching the ProjectRisk model columns.
        """
        today = date.today()
        risks: list[dict] = []

        for project_idx, (project_id, project_name) in enumerate(project_ids_with_names):
            short_code = PROJECT_SHORT_CODES.get(project_name, f"P{project_idx:02d}")
            is_hero = project_name == "Project Alpha"

            project_risks = self._generate_project_risks(
                project_id=project_id,
                short_code=short_code,
                is_hero=is_hero,
                project_idx=project_idx,
                today=today,
            )
            risks.extend(project_risks)

        return risks

    def _generate_project_risks(
        self,
        project_id: UUID,
        short_code: str,
        is_hero: bool,
        project_idx: int,
        today: date,
    ) -> list[dict]:
        """Generate risks for a single project.

        Hero project (Project Alpha) gets specific High/Critical open risks.
        All projects get at least 3 risks with mixed severities and statuses.
        """
        risks: list[dict] = []
        seq = 1

        if is_hero:
            # Critical risk: Open — key risk driving the at-risk status
            risks.append(
                self._build_risk(
                    project_id=project_id,
                    short_code=short_code,
                    seq=seq,
                    title="Critical resource gap in platform engineering team",
                    description=(
                        "The platform engineering team is understaffed by 3 senior engineers. "
                        "Current team cannot deliver core infrastructure components on schedule. "
                        "Recruitment pipeline shows no viable candidates for 6-8 weeks."
                    ),
                    severity="Critical",
                    status="Open",
                    owner="Engineering Director",
                    identified_date=today - timedelta(days=30),
                    target_date=today + timedelta(days=30),
                )
            )
            seq += 1

            # High risk: Open — budget pressure
            risks.append(
                self._build_risk(
                    project_id=project_id,
                    short_code=short_code,
                    seq=seq,
                    title="Budget exhaustion before Q4 deliverables",
                    description=(
                        "Current burn rate exceeds planned expenditure by 12%. Without "
                        "additional funding approval, remaining budget will be depleted "
                        "before critical Q4 milestones are reached."
                    ),
                    severity="High",
                    status="Open",
                    owner="Program Director",
                    identified_date=today - timedelta(days=20),
                    target_date=today + timedelta(days=45),
                )
            )
            seq += 1

            # Medium risk: Mitigated
            risks.append(
                self._build_risk(
                    project_id=project_id,
                    short_code=short_code,
                    seq=seq,
                    title="Vendor API deprecation affecting integration timeline",
                    description=(
                        "Key vendor has announced API v2 deprecation in 90 days. "
                        "Migration to v3 has been planned and is underway."
                    ),
                    severity="Medium",
                    status="Mitigated",
                    owner="Integration Lead",
                    identified_date=today - timedelta(days=60),
                    target_date=today - timedelta(days=5),
                )
            )
            seq += 1

            # Low risk: Closed
            risks.append(
                self._build_risk(
                    project_id=project_id,
                    short_code=short_code,
                    seq=seq,
                    title="Development environment instability",
                    description=(
                        "Shared development environment experienced frequent outages. "
                        "Issue resolved by provisioning dedicated project environments."
                    ),
                    severity="Low",
                    status="Closed",
                    owner="DevOps Lead",
                    identified_date=today - timedelta(days=90),
                    target_date=today - timedelta(days=60),
                )
            )
        else:
            # Non-hero projects: generate 3 risks with mixed severities and statuses
            statuses = STATUS_ROTATION[project_idx % len(STATUS_ROTATION)]
            templates = self._select_templates(project_idx)

            for i, (template, status) in enumerate(zip(templates, statuses)):
                identified_date = today - timedelta(days=25 + (i * 15) + (project_idx * 7))
                target_date: date | None
                if status == "Closed":
                    target_date = today - timedelta(days=10 + i * 5)
                else:
                    target_date = today + timedelta(days=20 + (i * 15))

                risks.append(
                    self._build_risk(
                        project_id=project_id,
                        short_code=short_code,
                        seq=seq,
                        title=template["title"],
                        description=template["description"],
                        severity=template["severity"],
                        status=status,
                        owner=template["owner"],
                        identified_date=identified_date,
                        target_date=target_date,
                    )
                )
                seq += 1

        return risks

    def _build_risk(
        self,
        project_id: UUID,
        short_code: str,
        seq: int,
        title: str,
        description: str,
        severity: str,
        status: str,
        owner: str,
        identified_date: date,
        target_date: date | None,
    ) -> dict:
        """Build a single project risk dictionary."""
        risk_reference = f"RISK-{short_code}-{seq:03d}"
        risk_id = deterministic_uuid("project_risk", short_code, risk_reference)

        return {
            "id": risk_id,
            "project_id": project_id,
            "risk_reference": risk_reference,
            "title": title,
            "description": description,
            "severity": severity,
            "status": status,
            "owner": owner,
            "identified_date": identified_date,
            "target_date": target_date,
        }

    def _select_templates(self, project_idx: int) -> list[dict[str, str]]:
        """Select 3 risk templates for a non-hero project.

        Rotates through available templates to ensure variety across projects.
        """
        start = (project_idx * 3) % len(RISK_TEMPLATES)
        selected: list[dict[str, str]] = []
        for i in range(3):
            idx = (start + i) % len(RISK_TEMPLATES)
            selected.append(RISK_TEMPLATES[idx])
        return selected

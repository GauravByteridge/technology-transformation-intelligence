"""Project seed generator.

Generates a portfolio of 8-12 projects representing realistic
technology transformation initiatives. Project Alpha is designated
as the primary hero project with "At Risk" status.
"""

from uuid import UUID

from app.seed.deterministic import deterministic_uuid

# Realistic enterprise transformation initiative names.
# Order matters: index 0 is always the hero project (Project Alpha).
PROJECT_DEFINITIONS: list[dict[str, str]] = [
    {
        "name": "Project Alpha",
        "description": "Enterprise-wide digital transformation initiative focused on modernizing core banking infrastructure and customer-facing applications.",
        "status": "At Risk",
    },
    {
        "name": "Cloud Migration Platform",
        "description": "Migration of on-premises workloads to cloud-native architecture with containerization and orchestration.",
        "status": "On Track",
    },
    {
        "name": "Data Platform Modernization",
        "description": "Consolidation and modernization of data warehouses into a unified analytics platform with real-time streaming.",
        "status": "On Track",
    },
    {
        "name": "API Gateway Implementation",
        "description": "Enterprise API management layer enabling secure, standardized service integration across business units.",
        "status": "On Track",
    },
    {
        "name": "Legacy System Decommission",
        "description": "Phased retirement of legacy mainframe applications with data migration to modern platforms.",
        "status": "Delayed",
    },
    {
        "name": "Security Operations Center",
        "description": "Establishment of a 24/7 security operations center with automated threat detection and response capabilities.",
        "status": "At Risk",
    },
    {
        "name": "DevOps Pipeline Automation",
        "description": "End-to-end CI/CD pipeline automation with infrastructure-as-code and automated quality gates.",
        "status": "On Track",
    },
    {
        "name": "Customer Portal Redesign",
        "description": "Complete redesign of customer-facing portal with improved UX, accessibility, and mobile-first responsive design.",
        "status": "Completed",
    },
    {
        "name": "Enterprise Data Lake",
        "description": "Centralized data lake implementation for cross-functional analytics, machine learning, and regulatory reporting.",
        "status": "On Track",
    },
    {
        "name": "Mobile Banking Platform",
        "description": "Next-generation mobile banking application with biometric authentication and real-time transaction processing.",
        "status": "At Risk",
    },
    {
        "name": "Identity Access Management",
        "description": "Centralized identity and access management platform with single sign-on, MFA, and role-based access controls.",
        "status": "On Track",
    },
    {
        "name": "Regulatory Reporting Engine",
        "description": "Automated regulatory reporting system for real-time compliance monitoring and submission across jurisdictions.",
        "status": "On Track",
    },
]

# The hero project name — used by other generators to identify the primary scenario.
HERO_PROJECT_NAME = "Project Alpha"


class ProjectSeedGenerator:
    """Generates project seed data for the technology transformation portfolio.

    Produces a list of project dictionaries ready for database insertion.
    Uses deterministic UUIDs so repeated executions produce identical results.
    """

    def generate(self, project_count: int, created_by_user_id: UUID) -> list[dict]:
        """Generate project records for the seed portfolio.

        Args:
            project_count: Number of projects to generate (8-12).
            created_by_user_id: UUID of the user who "created" these projects
                (FK to users.id required by the projects table).

        Returns:
            List of project dictionaries with keys matching the Project model columns.
        """
        selected_projects = PROJECT_DEFINITIONS[:project_count]
        projects: list[dict] = []

        for project_def in selected_projects:
            project_id = deterministic_uuid("project", project_def["name"])
            projects.append(
                {
                    "id": project_id,
                    "name": project_def["name"],
                    "description": project_def["description"],
                    "status": project_def["status"],
                    "created_by": created_by_user_id,
                }
            )

        return projects

    def get_hero_project_id(self) -> UUID:
        """Return the deterministic UUID for the hero project (Project Alpha)."""
        return deterministic_uuid("project", HERO_PROJECT_NAME)

    def get_project_id_by_name(self, name: str) -> UUID:
        """Return the deterministic UUID for a project by name."""
        return deterministic_uuid("project", name)

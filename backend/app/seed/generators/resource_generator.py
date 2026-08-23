"""Resource seed generator.

Generates team members, resource allocations, utilization records,
and resource forecasts for the technology transformation portfolio.

Constraints:
- At least 15 team members with distinct names, emails, roles, departments
- At least 3 team members allocated per project
- Allocation percentages sum to ≤ 100% per team member across concurrent projects
- Utilization records for 6+ months per active team member (60%–110%)
- Resource forecasts for 3+ future months per project
- Project Alpha has demand_fte > capacity_fte (capacity gap)
"""

import random
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.seed.deterministic import deterministic_uuid
from app.seed.generators.project_generator import HERO_PROJECT_NAME

# Roles available for team members.
TEAM_MEMBER_ROLES: list[str] = [
    "Developer",
    "QA Engineer",
    "Project Manager",
    "Business Analyst",
    "Architect",
    "DevOps Engineer",
]

# Departments in the organization.
DEPARTMENTS: list[str] = [
    "Engineering",
    "Quality Assurance",
    "Program Management",
    "Business Analysis",
    "Architecture",
    "Platform Operations",
]

# Realistic team member definitions (at least 15).
TEAM_MEMBER_DEFINITIONS: list[dict[str, str]] = [
    {"name": "Sarah Chen", "role": "Developer", "department": "Engineering"},
    {"name": "Michael O'Brien", "role": "Developer", "department": "Engineering"},
    {"name": "Priya Patel", "role": "QA Engineer", "department": "Quality Assurance"},
    {"name": "James Nakamura", "role": "Architect", "department": "Architecture"},
    {"name": "Elena Rodriguez", "role": "Project Manager", "department": "Program Management"},
    {"name": "David Kim", "role": "DevOps Engineer", "department": "Platform Operations"},
    {"name": "Olivia Thompson", "role": "Business Analyst", "department": "Business Analysis"},
    {"name": "Raj Krishnamurthy", "role": "Developer", "department": "Engineering"},
    {"name": "Anna Johansson", "role": "QA Engineer", "department": "Quality Assurance"},
    {"name": "Marcus Williams", "role": "Developer", "department": "Engineering"},
    {"name": "Fatima Al-Hassan", "role": "Project Manager", "department": "Program Management"},
    {"name": "Thomas Mueller", "role": "Architect", "department": "Architecture"},
    {"name": "Jessica Park", "role": "Business Analyst", "department": "Business Analysis"},
    {"name": "Carlos Mendez", "role": "DevOps Engineer", "department": "Platform Operations"},
    {"name": "Natasha Volkov", "role": "Developer", "department": "Engineering"},
    {"name": "Benjamin Okafor", "role": "QA Engineer", "department": "Quality Assurance"},
    {"name": "Aisha Nguyen", "role": "Developer", "department": "Engineering"},
    {"name": "Daniel Costa", "role": "Project Manager", "department": "Program Management"},
]

# Role-on-project mappings for allocations.
ROLE_ON_PROJECT_OPTIONS: list[str] = [
    "Lead Developer",
    "Backend Developer",
    "Frontend Developer",
    "QA Lead",
    "Test Engineer",
    "Technical Project Manager",
    "Scrum Master",
    "Requirements Analyst",
    "Solution Architect",
    "Infrastructure Engineer",
    "Release Engineer",
]

# Hourly rates by role (reasonable enterprise consulting ranges).
HOURLY_RATES_BY_ROLE: dict[str, tuple[int, int]] = {
    "Developer": (85, 150),
    "QA Engineer": (75, 120),
    "Project Manager": (100, 175),
    "Business Analyst": (90, 140),
    "Architect": (130, 200),
    "DevOps Engineer": (95, 160),
}


def _generate_email(name: str) -> str:
    """Generate a realistic corporate email from a team member name."""
    parts = name.lower().replace("'", "").split()
    return f"{parts[0]}.{parts[-1]}@enterprise-corp.com"


def _role_on_project_for_role(role: str) -> str:
    """Map a team member's role to a suitable project role."""
    mapping = {
        "Developer": "Backend Developer",
        "QA Engineer": "Test Engineer",
        "Project Manager": "Technical Project Manager",
        "Business Analyst": "Requirements Analyst",
        "Architect": "Solution Architect",
        "DevOps Engineer": "Infrastructure Engineer",
    }
    return mapping.get(role, "Team Member")


class ResourceSeedGenerator:
    """Generates resource management seed data.

    Produces team members, allocations, utilization records, and forecasts.
    Uses deterministic UUIDs so repeated executions produce identical results.
    """

    def generate_team_members(self) -> list[dict]:
        """Generate at least 15 team members with distinct names, emails, roles, and departments."""
        members: list[dict] = []

        for member_def in TEAM_MEMBER_DEFINITIONS:
            name = member_def["name"]
            role = member_def["role"]
            department = member_def["department"]
            email = _generate_email(name)
            member_id = deterministic_uuid("team_member", email)

            rate_range = HOURLY_RATES_BY_ROLE[role]
            # Deterministic rate based on name hash position
            rate_index = hash(name) % (rate_range[1] - rate_range[0])
            hourly_rate = Decimal(str(rate_range[0] + rate_index))

            members.append(
                {
                    "id": member_id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "department": department,
                    "hourly_rate": hourly_rate,
                    "is_active": True,
                }
            )

        return members

    def generate_allocations(
        self,
        projects: list[dict],
        team_members: list[dict],
    ) -> list[dict]:
        """Generate resource allocations assigning at least 3 members per project.

        Ensures allocation_percentage sums to ≤ 100% per team member
        across concurrent projects.
        """
        allocations: list[dict] = []
        # Track total allocation per team member to enforce the ≤ 100% constraint.
        member_total_allocation: dict[UUID, int] = {
            m["id"]: 0 for m in team_members
        }

        # Base allocation start date — 6 months ago.
        base_start_date = date.today() - timedelta(days=180)

        num_members = len(team_members)

        for proj_idx, project in enumerate(projects):
            project_id = project["id"]
            project_name = project["name"]

            # Assign at least 3 members per project using round-robin with offset.
            members_per_project = max(3, min(5, num_members // len(projects) + 1))
            start_idx = (proj_idx * 3) % num_members

            assigned_count = 0
            candidate_idx = start_idx

            while assigned_count < members_per_project:
                member = team_members[candidate_idx % num_members]
                member_id = member["id"]

                # Determine allocation percentage (20–40%) ensuring sum ≤ 100%.
                remaining_capacity = 100 - member_total_allocation[member_id]
                if remaining_capacity < 20:
                    # This member is fully allocated; skip to next candidate.
                    candidate_idx += 1
                    # Safety: avoid infinite loop if all members exhausted.
                    if candidate_idx - start_idx >= num_members:
                        break
                    continue

                allocation_pct = min(
                    random.randint(20, 40),
                    remaining_capacity,
                )

                allocation_id = deterministic_uuid(
                    "resource_allocation",
                    project_name,
                    member["email"],
                )

                role_on_project = _role_on_project_for_role(member["role"])

                allocations.append(
                    {
                        "id": allocation_id,
                        "project_id": project_id,
                        "team_member_id": member_id,
                        "allocation_percentage": allocation_pct,
                        "start_date": base_start_date,
                        "end_date": None,
                        "role_on_project": role_on_project,
                    }
                )

                member_total_allocation[member_id] += allocation_pct
                assigned_count += 1
                candidate_idx += 1

        return allocations

    def generate_utilization(
        self,
        team_members: list[dict],
        months: int = 7,
    ) -> list[dict]:
        """Generate utilization records for 6+ months per active team member.

        Utilization percentages range from 60% to 110% where values above 100%
        represent over-utilization (overtime/weekend work).
        """
        records: list[dict] = []
        today = date.today()

        # Generate records for the past N months (covering 6+ months).
        for member in team_members:
            if not member.get("is_active", True):
                continue

            member_id = member["id"]
            email = member["email"]

            for month_offset in range(months):
                # Go backwards from current month.
                record_date = today.replace(day=1) - timedelta(days=30 * month_offset)
                year_month = record_date.strftime("%Y-%m")

                record_id = deterministic_uuid(
                    "resource_utilization",
                    email,
                    year_month,
                )

                # Standard available hours per month (accounting for working days).
                available_hours = Decimal("168")

                # Generate utilization between 60% and 110%.
                utilization_pct = Decimal(
                    str(random.randint(60, 110))
                ) + Decimal(str(random.randint(0, 9))) / Decimal("10")

                billed_hours = (available_hours * utilization_pct / Decimal("100")).quantize(
                    Decimal("0.1")
                )

                records.append(
                    {
                        "id": record_id,
                        "team_member_id": member_id,
                        "year_month": year_month,
                        "available_hours": available_hours,
                        "billed_hours": billed_hours,
                        "utilization_percentage": utilization_pct,
                    }
                )

        return records

    def generate_forecasts(
        self,
        projects: list[dict],
        forecast_months: int = 4,
    ) -> list[dict]:
        """Generate resource forecasts for 3+ future months per project.

        Project Alpha exhibits a capacity gap (demand_fte > capacity_fte).
        Other projects have balanced or surplus capacity.
        """
        forecasts: list[dict] = []
        today = date.today()

        for project in projects:
            project_id = project["id"]
            project_name = project["name"]
            is_hero = project_name == HERO_PROJECT_NAME

            for month_offset in range(1, forecast_months + 1):
                forecast_date = (
                    today.replace(day=1) + timedelta(days=30 * month_offset)
                )
                year_month = forecast_date.strftime("%Y-%m")

                forecast_id = deterministic_uuid(
                    "resource_forecast",
                    project_name,
                    year_month,
                )

                if is_hero:
                    # Project Alpha: demand exceeds capacity (resource gap).
                    demand_fte = Decimal(str(random.randint(80, 100))) / Decimal("10")
                    capacity_fte = Decimal(str(random.randint(50, 65))) / Decimal("10")
                else:
                    # Other projects: balanced or slight surplus.
                    capacity_fte = Decimal(str(random.randint(40, 70))) / Decimal("10")
                    demand_fte = capacity_fte - Decimal(
                        str(random.randint(0, 15))
                    ) / Decimal("10")

                gap_fte = demand_fte - capacity_fte

                forecasts.append(
                    {
                        "id": forecast_id,
                        "project_id": project_id,
                        "year_month": year_month,
                        "demand_fte": demand_fte,
                        "capacity_fte": capacity_fte,
                        "gap_fte": gap_fte,
                    }
                )

        return forecasts

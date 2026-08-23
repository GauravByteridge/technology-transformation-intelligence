"""JIRA seed generator.

Generates sprints and JIRA issues for each project. Each project gets
at least 2 sprints with 5-15 issues per sprint, representing realistic
agile development activity.

Project Alpha is guaranteed to have at least 3 overdue issues
(due_date in past AND status != "Done") to support the derived overdue
condition scenario.
"""

import random
from datetime import date, timedelta
from uuid import UUID

from app.seed.deterministic import deterministic_uuid

# Short names for issue key prefixes, mapped from project names.
# Used to generate keys like ALPHA-001, CLOUD-001, etc.
PROJECT_SHORT_NAMES: dict[str, str] = {
    "Project Alpha": "ALPHA",
    "Cloud Migration Platform": "CLOUD",
    "Data Platform Modernization": "DATA",
    "API Gateway Implementation": "APIGW",
    "Legacy System Decommission": "LEGACY",
    "Security Operations Center": "SECOPS",
    "DevOps Pipeline Automation": "DEVOPS",
    "Customer Portal Redesign": "PORTAL",
    "Enterprise Data Lake": "DATALAKE",
    "Mobile Banking Platform": "MOBILE",
    "Identity Access Management": "IAM",
    "Regulatory Reporting Engine": "REGENG",
}

# Issue types used in generation (excludes Epic and Sub-task for sprint-level issues)
ISSUE_TYPES: list[str] = ["Story", "Task", "Bug"]

# Statuses for JIRA issues
ISSUE_STATUSES: list[str] = ["To Do", "In Progress", "Done", "Blocked"]

# Priority values with realistic distribution weights (mostly Medium/High)
PRIORITY_VALUES: list[str] = ["Critical", "High", "Medium", "Low"]
PRIORITY_WEIGHTS: list[int] = [5, 30, 45, 20]

# Sprint statuses
SPRINT_STATUSES: list[str] = ["Completed", "Active", "Future"]

# Realistic summary templates per issue type
STORY_SUMMARIES: list[str] = [
    "Implement user authentication flow",
    "Create dashboard visualization component",
    "Design data export functionality",
    "Build notification system",
    "Develop search and filter capability",
    "Implement role-based access controls",
    "Create reporting module",
    "Design onboarding workflow",
    "Build integration with external API",
    "Implement data validation rules",
    "Create audit trail logging",
    "Design configuration management interface",
    "Build batch processing pipeline",
    "Implement caching layer",
    "Create health monitoring dashboard",
]

TASK_SUMMARIES: list[str] = [
    "Set up CI/CD pipeline configuration",
    "Configure monitoring and alerting",
    "Write unit tests for service layer",
    "Update API documentation",
    "Perform database schema migration",
    "Configure load balancer settings",
    "Review and update security policies",
    "Set up staging environment",
    "Implement logging infrastructure",
    "Create deployment runbook",
    "Update dependency versions",
    "Configure backup and recovery",
    "Set up performance benchmarks",
    "Create data migration scripts",
    "Update infrastructure as code templates",
]

BUG_SUMMARIES: list[str] = [
    "Fix timeout on large data queries",
    "Resolve memory leak in worker process",
    "Fix incorrect date formatting in reports",
    "Resolve race condition in concurrent writes",
    "Fix broken pagination on search results",
    "Resolve authentication token expiry issue",
    "Fix data truncation on import",
    "Resolve UI rendering issue on mobile",
    "Fix incorrect calculation in summary view",
    "Resolve connection pool exhaustion",
    "Fix missing validation on form submission",
    "Resolve incorrect error handling in API",
    "Fix stale cache invalidation",
    "Resolve timezone conversion errors",
    "Fix broken file upload for large files",
]

# Realistic reporter/assignee names
TEAM_NAMES: list[str] = [
    "Sarah Chen",
    "James Wilson",
    "Priya Sharma",
    "Michael Brown",
    "Emma Davis",
    "Raj Patel",
    "Lisa Thompson",
    "David Kim",
    "Maria Garcia",
    "Alex Johnson",
    "Yuki Tanaka",
    "Omar Hassan",
]


class JiraSeedGenerator:
    """Generates sprint and JIRA issue seed data for all projects.

    Produces deterministic sprint and issue records with:
    - At least 2 sprints per project (typically 3)
    - 5-15 issues per sprint with mixed types and statuses
    - Unique issue keys using project short names
    - Realistic priority distribution (mostly Medium/High)
    - Project Alpha guaranteed to have >= 3 overdue issues
    """

    def generate(
        self,
        projects: list[dict],
    ) -> dict[str, list[dict]]:
        """Generate all sprint and issue records for the given projects.

        Args:
            projects: List of project dictionaries (must include 'id' and 'name').

        Returns:
            Dictionary with 'sprints' and 'jira_issues' keys, each containing
            a list of record dictionaries ready for database insertion.
        """
        all_sprints: list[dict] = []
        all_issues: list[dict] = []

        for project in projects:
            project_id = project["id"]
            project_name = project["name"]
            short_name = PROJECT_SHORT_NAMES.get(project_name, project_name[:6].upper())

            sprints, issues = self._generate_project_jira(
                project_id=project_id,
                project_name=project_name,
                short_name=short_name,
            )
            all_sprints.extend(sprints)
            all_issues.extend(issues)

        return {
            "sprints": all_sprints,
            "jira_issues": all_issues,
        }

    def _generate_project_jira(
        self,
        project_id: UUID,
        project_name: str,
        short_name: str,
    ) -> tuple[list[dict], list[dict]]:
        """Generate sprints and issues for a single project.

        Returns:
            Tuple of (sprints_list, issues_list).
        """
        sprint_count = 3
        sprints: list[dict] = []
        issues: list[dict] = []
        issue_sequence = 1

        # Base date for sprint scheduling — sprints are 2-week intervals
        base_start = date(2024, 7, 1)

        for sprint_idx in range(sprint_count):
            sprint_number = sprint_idx + 1
            sprint_name = f"Sprint {sprint_number}"
            sprint_id = deterministic_uuid("sprint", project_name, sprint_name)

            sprint_start = base_start + timedelta(weeks=sprint_idx * 2)
            sprint_end = sprint_start + timedelta(days=13)

            # Determine sprint status based on position
            if sprint_idx < sprint_count - 2:
                sprint_status = "Completed"
            elif sprint_idx == sprint_count - 2:
                sprint_status = "Active"
            else:
                sprint_status = "Future"

            velocity = random.randint(20, 40) if sprint_status == "Completed" else None

            sprint_goal = self._generate_sprint_goal(sprint_number, project_name)

            sprints.append({
                "id": sprint_id,
                "project_id": project_id,
                "name": sprint_name,
                "sprint_number": sprint_number,
                "start_date": sprint_start,
                "end_date": sprint_end,
                "status": sprint_status,
                "goal": sprint_goal,
                "velocity": velocity,
            })

            # Generate 5-15 issues per sprint
            issue_count = random.randint(5, 15)

            for issue_idx in range(issue_count):
                issue_key = f"{short_name}-{issue_sequence:03d}"
                issue_sequence += 1

                issue_type = random.choices(ISSUE_TYPES, weights=[40, 35, 25])[0]
                status = self._pick_status_for_sprint(sprint_status)
                priority = random.choices(PRIORITY_VALUES, weights=PRIORITY_WEIGHTS)[0]
                summary = self._pick_summary(issue_type, issue_idx)
                story_points = random.choice([1, 2, 3, 5, 8, 13]) if issue_type != "Bug" else random.choice([1, 2, 3, 5])

                assignee = random.choice(TEAM_NAMES)
                reporter = random.choice(TEAM_NAMES)

                # Due date: set for ~70% of issues
                due_date = None
                if random.random() < 0.7:
                    due_date = sprint_end + timedelta(days=random.randint(-7, 7))

                # Resolved date for Done issues
                resolved_date = None
                if status == "Done":
                    resolved_date = sprint_start + timedelta(days=random.randint(1, 13))

                issue_id = deterministic_uuid("jira_issue", short_name, issue_key)

                issues.append({
                    "id": issue_id,
                    "project_id": project_id,
                    "sprint_id": sprint_id,
                    "issue_key": issue_key,
                    "issue_type": issue_type,
                    "summary": summary,
                    "description": None,
                    "status": status,
                    "priority": priority,
                    "assignee": assignee,
                    "reporter": reporter,
                    "story_points": story_points,
                    "due_date": due_date,
                    "resolved_date": resolved_date,
                })

        # Ensure Project Alpha has at least 3 overdue issues
        if project_name == "Project Alpha":
            self._ensure_overdue_issues(issues, short_name, project_id, sprints)

        return sprints, issues

    def _ensure_overdue_issues(
        self,
        issues: list[dict],
        short_name: str,
        project_id: UUID,
        sprints: list[dict],
    ) -> None:
        """Ensure at least 3 issues have due_date in the past and status != Done.

        Modifies existing issues in-place to guarantee the overdue condition.
        """
        today = date.today()
        overdue_count = sum(
            1 for issue in issues
            if issue["due_date"] is not None
            and issue["due_date"] < today
            and issue["status"] != "Done"
        )

        # Modify existing non-Done issues to have past due dates if needed
        needed = 3 - overdue_count
        if needed <= 0:
            return

        candidates = [
            issue for issue in issues
            if issue["status"] != "Done"
        ]

        for candidate in candidates[:needed]:
            # Set due date to 2-4 weeks in the past
            candidate["due_date"] = today - timedelta(days=random.randint(14, 28))
            # Ensure status is not Done
            if candidate["status"] == "Done":
                candidate["status"] = "In Progress"

    def _pick_status_for_sprint(self, sprint_status: str) -> str:
        """Pick an issue status appropriate for the sprint's status."""
        if sprint_status == "Completed":
            # Completed sprints: mostly Done, some leftover
            return random.choices(
                ISSUE_STATUSES,
                weights=[5, 10, 75, 10],
            )[0]
        elif sprint_status == "Active":
            # Active sprints: mix of all statuses
            return random.choices(
                ISSUE_STATUSES,
                weights=[20, 40, 25, 15],
            )[0]
        else:
            # Future sprints: mostly To Do
            return random.choices(
                ISSUE_STATUSES,
                weights=[70, 15, 5, 10],
            )[0]

    def _pick_summary(self, issue_type: str, index: int) -> str:
        """Pick a summary string based on issue type, cycling through templates."""
        if issue_type == "Story":
            return STORY_SUMMARIES[index % len(STORY_SUMMARIES)]
        elif issue_type == "Task":
            return TASK_SUMMARIES[index % len(TASK_SUMMARIES)]
        else:
            return BUG_SUMMARIES[index % len(BUG_SUMMARIES)]

    def _generate_sprint_goal(self, sprint_number: int, project_name: str) -> str:
        """Generate a realistic sprint goal."""
        goals = [
            "Complete core infrastructure setup and initial integrations",
            "Deliver MVP features and resolve critical defects",
            "Finalize testing, documentation, and deployment readiness",
        ]
        return goals[(sprint_number - 1) % len(goals)]

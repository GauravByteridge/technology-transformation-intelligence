"""SDLC seed generator.

Generates SDLC phases, milestones, and deliverables for each project.
Each project receives 4–6 phases in sequential order, with at least 2
milestones per phase and at least 1 deliverable per milestone.

Phase statuses reflect project progress: completed projects have all phases
completed, in-progress projects have a mix, and not-started projects remain
in "Not Started" status.
"""

import random
from datetime import date, timedelta
from uuid import UUID

from app.seed.deterministic import deterministic_uuid

# Canonical SDLC phase definitions — order matters.
# Each project selects 4–6 of these in order.
SDLC_PHASE_NAMES: list[str] = [
    "Requirements",
    "Design",
    "Development",
    "Testing",
    "Deployment",
    "Operations",
]

# Milestone templates per phase (name, description).
# Each phase has a pool of milestones; at least 2 are selected per phase.
MILESTONE_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "Requirements": [
        ("Business Requirements Document", "Complete BRD with stakeholder sign-off"),
        ("Stakeholder Analysis", "Identify and categorize all project stakeholders"),
        ("Requirements Review", "Formal review and approval of all requirements"),
        ("Scope Baseline", "Approved scope statement and work breakdown structure"),
    ],
    "Design": [
        ("Architecture Review", "Technical architecture review and approval"),
        ("High-Level Design", "System architecture and component design document"),
        ("Detailed Design", "Module-level design specifications"),
        ("Design Sign-off", "Formal design approval from technical leads"),
    ],
    "Development": [
        ("Sprint 1 Completion", "First development sprint deliverables"),
        ("Core Module Complete", "Core business logic implementation finished"),
        ("Integration Ready", "All modules integrated and ready for testing"),
        ("Code Freeze", "Feature-complete codebase with no new changes"),
    ],
    "Testing": [
        ("Test Plan Approved", "Complete test strategy and plan approved"),
        ("UAT Sign-off", "User acceptance testing completed with sign-off"),
        ("Performance Validation", "Load and performance testing passed thresholds"),
        ("Security Assessment", "Security testing and vulnerability scan completed"),
    ],
    "Deployment": [
        ("Deployment Plan Approved", "Deployment runbook reviewed and approved"),
        ("Staging Deployment", "Successful deployment to staging environment"),
        ("Production Deployment", "Go-live deployment to production completed"),
        ("Post-Deployment Verification", "Smoke tests and monitoring confirmed"),
    ],
    "Operations": [
        ("Runbook Finalized", "Operations runbook documented and reviewed"),
        ("Monitoring Setup", "Alerting and monitoring dashboards configured"),
        ("Knowledge Transfer", "Handover to operations team completed"),
        ("Steady State Achieved", "System operating within normal parameters"),
    ],
}

# Deliverable templates per milestone phase (name, owner role).
DELIVERABLE_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "Requirements": [
        ("Business Requirements Document", "Business Analyst"),
        ("User Story Map", "Product Owner"),
        ("Requirements Traceability Matrix", "Business Analyst"),
        ("Stakeholder Register", "Project Manager"),
    ],
    "Design": [
        ("Architecture Decision Record", "Architect"),
        ("System Design Document", "Architect"),
        ("API Specification", "Developer"),
        ("Data Model Document", "Architect"),
    ],
    "Development": [
        ("Source Code Package", "Developer"),
        ("Unit Test Suite", "Developer"),
        ("Technical Documentation", "Developer"),
        ("Code Review Report", "Developer"),
    ],
    "Testing": [
        ("Test Plan Document", "QA Engineer"),
        ("Test Results Report", "QA Engineer"),
        ("Defect Summary Report", "QA Engineer"),
        ("Performance Test Report", "QA Engineer"),
    ],
    "Deployment": [
        ("Deployment Runbook", "DevOps Engineer"),
        ("Release Notes", "Project Manager"),
        ("Rollback Plan", "DevOps Engineer"),
        ("Configuration Guide", "DevOps Engineer"),
    ],
    "Operations": [
        ("Operations Runbook", "DevOps Engineer"),
        ("Monitoring Dashboard Spec", "DevOps Engineer"),
        ("Incident Response Plan", "DevOps Engineer"),
        ("SLA Agreement", "Project Manager"),
    ],
}


def _determine_phase_statuses(project_status: str, phase_count: int) -> list[str]:
    """Determine phase statuses based on project progress.

    Completed projects: all phases completed.
    On Track projects: earlier phases completed, current in progress, later not started.
    At Risk / Delayed projects: earlier completed, middle in progress, later not started.
    """
    if project_status == "Completed":
        return ["Completed"] * phase_count

    # Determine how many phases are completed based on status
    if project_status == "On Track":
        completed_count = max(2, phase_count - 2)
    elif project_status in ("At Risk", "Delayed"):
        completed_count = max(1, phase_count - 3)
    else:
        completed_count = max(1, phase_count // 2)

    statuses: list[str] = []
    for i in range(phase_count):
        if i < completed_count:
            statuses.append("Completed")
        elif i == completed_count:
            statuses.append("In Progress")
        else:
            statuses.append("Not Started")

    return statuses


class SdlcSeedGenerator:
    """Generates SDLC phase, milestone, and deliverable seed data.

    Produces lists of dictionaries ready for database insertion.
    Uses deterministic UUIDs so repeated executions produce identical results.
    """

    def generate(
        self,
        projects: list[dict],
    ) -> dict[str, list[dict]]:
        """Generate SDLC records for all projects.

        Args:
            projects: List of project dicts (must include 'id', 'name', 'status').

        Returns:
            Dictionary with keys 'phases', 'milestones', 'deliverables',
            each containing a list of record dictionaries.
        """
        all_phases: list[dict] = []
        all_milestones: list[dict] = []
        all_deliverables: list[dict] = []

        for project in projects:
            project_phases, project_milestones, project_deliverables = (
                self._generate_for_project(
                    project_id=project["id"],
                    project_name=project["name"],
                    project_status=project["status"],
                )
            )
            all_phases.extend(project_phases)
            all_milestones.extend(project_milestones)
            all_deliverables.extend(project_deliverables)

        return {
            "phases": all_phases,
            "milestones": all_milestones,
            "deliverables": all_deliverables,
        }

    def _generate_for_project(
        self,
        project_id: UUID,
        project_name: str,
        project_status: str,
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Generate SDLC data for a single project.

        Returns:
            Tuple of (phases, milestones, deliverables) lists.
        """
        # Select 4–6 phases for this project
        phase_count = random.randint(4, 6)
        selected_phases = SDLC_PHASE_NAMES[:phase_count]
        phase_statuses = _determine_phase_statuses(project_status, phase_count)

        # Spread phases across a ~12-month project timeline
        project_start = date(2024, 1, 15)
        total_days = 365
        phase_duration = total_days // phase_count

        phases: list[dict] = []
        milestones: list[dict] = []
        deliverables: list[dict] = []

        for seq_idx, phase_name in enumerate(selected_phases):
            sequence_order = seq_idx + 1
            phase_id = deterministic_uuid(
                "sdlc_phase", project_name, phase_name
            )

            # Calculate planned dates
            planned_start = project_start + timedelta(days=seq_idx * phase_duration)
            planned_end = planned_start + timedelta(days=phase_duration - 1)

            # Determine actual dates based on phase status
            actual_start: date | None = None
            actual_end: date | None = None
            if phase_statuses[seq_idx] == "Completed":
                actual_start = planned_start + timedelta(days=random.randint(0, 3))
                actual_end = planned_end + timedelta(days=random.randint(-5, 5))
            elif phase_statuses[seq_idx] == "In Progress":
                actual_start = planned_start + timedelta(days=random.randint(0, 5))
                # No actual_end for in-progress phases

            phases.append(
                {
                    "id": phase_id,
                    "project_id": project_id,
                    "phase_name": phase_name,
                    "sequence_order": sequence_order,
                    "status": phase_statuses[seq_idx],
                    "planned_start_date": planned_start,
                    "planned_end_date": planned_end,
                    "actual_start_date": actual_start,
                    "actual_end_date": actual_end,
                }
            )

            # Generate milestones for this phase (at least 2)
            phase_milestones = self._generate_milestones(
                phase_id=phase_id,
                phase_name=phase_name,
                phase_status=phase_statuses[seq_idx],
                project_name=project_name,
                planned_start=planned_start,
                planned_end=planned_end,
            )
            milestones.extend(phase_milestones)

            # Generate deliverables for each milestone (at least 1 per milestone)
            for milestone in phase_milestones:
                milestone_deliverables = self._generate_deliverables(
                    milestone_id=milestone["id"],
                    milestone_name=milestone["name"],
                    milestone_status=milestone["status"],
                    phase_name=phase_name,
                    project_name=project_name,
                    due_date=milestone["planned_date"],
                )
                deliverables.extend(milestone_deliverables)

        return phases, milestones, deliverables

    def _generate_milestones(
        self,
        phase_id: UUID,
        phase_name: str,
        phase_status: str,
        project_name: str,
        planned_start: date,
        planned_end: date,
    ) -> list[dict]:
        """Generate milestones for a single phase (at least 2)."""
        templates = MILESTONE_TEMPLATES.get(phase_name, MILESTONE_TEMPLATES["Development"])
        # Select 2–3 milestones from templates
        milestone_count = random.randint(2, min(3, len(templates)))
        selected_templates = templates[:milestone_count]

        phase_days = (planned_end - planned_start).days
        milestone_interval = max(1, phase_days // (milestone_count + 1))

        milestones: list[dict] = []
        for ms_idx, (ms_name, ms_description) in enumerate(selected_templates):
            milestone_id = deterministic_uuid(
                "sdlc_milestone", project_name, phase_name, ms_name
            )
            planned_date = planned_start + timedelta(
                days=(ms_idx + 1) * milestone_interval
            )

            # Milestone status reflects phase status
            if phase_status == "Completed":
                ms_status = "Completed"
                actual_date = planned_date + timedelta(days=random.randint(-3, 5))
            elif phase_status == "In Progress":
                # First milestone(s) completed, last one in progress
                if ms_idx < milestone_count - 1:
                    ms_status = "Completed"
                    actual_date = planned_date + timedelta(days=random.randint(-2, 3))
                else:
                    ms_status = "In Progress"
                    actual_date = None
            else:
                ms_status = "Not Started"
                actual_date = None

            milestones.append(
                {
                    "id": milestone_id,
                    "phase_id": phase_id,
                    "name": ms_name,
                    "description": ms_description,
                    "planned_date": planned_date,
                    "actual_date": actual_date,
                    "status": ms_status,
                }
            )

        return milestones

    def _generate_deliverables(
        self,
        milestone_id: UUID,
        milestone_name: str,
        milestone_status: str,
        phase_name: str,
        project_name: str,
        due_date: date,
    ) -> list[dict]:
        """Generate deliverables for a single milestone (at least 1)."""
        templates = DELIVERABLE_TEMPLATES.get(
            phase_name, DELIVERABLE_TEMPLATES["Development"]
        )
        # Select 1–2 deliverables per milestone
        deliverable_count = random.randint(1, min(2, len(templates)))
        # Use a deterministic slice based on milestone name hash
        start_idx = hash(milestone_name) % max(1, len(templates) - deliverable_count + 1)
        start_idx = abs(start_idx) % max(1, len(templates) - deliverable_count + 1)
        selected_templates = templates[start_idx : start_idx + deliverable_count]

        deliverables_list: list[dict] = []
        for dl_idx, (dl_name, dl_owner) in enumerate(selected_templates):
            deliverable_id = deterministic_uuid(
                "sdlc_deliverable", project_name, phase_name, milestone_name, dl_name
            )

            # Deliverable status mirrors milestone status
            if milestone_status == "Completed":
                dl_status = "Completed"
                completion_date = due_date + timedelta(days=random.randint(-3, 2))
            elif milestone_status == "In Progress":
                dl_status = "In Progress"
                completion_date = None
            else:
                dl_status = "Not Started"
                completion_date = None

            deliverables_list.append(
                {
                    "id": deliverable_id,
                    "milestone_id": milestone_id,
                    "name": dl_name,
                    "description": f"{dl_name} for {phase_name} phase",
                    "status": dl_status,
                    "owner": dl_owner,
                    "due_date": due_date + timedelta(days=dl_idx * 3),
                    "completion_date": completion_date,
                }
            )

        return deliverables_list

"""Business domain data models — all Phase 3 tables.

Revision ID: 002_business_data_models
Revises: 001_initial
Create Date: 2025-01-15 00:00:00.000000

Creates tables:
- cost_categories
- team_members
- it_controls
- project_budgets
- actual_costs
- monthly_cost_trends
- budget_line_items
- sdlc_phases
- sdlc_milestones
- sdlc_deliverables
- sprints
- jira_issues
- resource_allocations
- resource_utilization
- resource_forecasts
- audit_findings
- control_assessments
- remediation_items
- project_risks
- project_progress_snapshots
- project_health_kpis

All tables use UUID primary keys and include created_at/updated_at timestamps.
References existing projects.id FK from Phase 1 — does NOT create or modify
the projects table.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers used by Alembic.
revision = "002_business_data_models"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all Phase 3 business domain tables in dependency-safe order."""

    # --- cost_categories (no FK deps) ---
    op.create_table(
        "cost_categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cost_categories"),
        sa.UniqueConstraint("name", name="uq_cost_categories_name"),
    )

    # --- team_members (no FK deps) ---
    op.create_table(
        "team_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(15, 2), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_team_members"),
        sa.UniqueConstraint("email", name="uq_team_members_email"),
    )

    # --- it_controls (no FK deps) ---
    op.create_table(
        "it_controls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("control_reference", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("framework", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_it_controls"),
        sa.UniqueConstraint("control_reference", name="uq_it_controls_control_reference"),
    )

    # --- project_budgets (FK → projects) ---
    op.create_table(
        "project_budgets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("total_budget", sa.Numeric(15, 2), nullable=False),
        sa.Column("approved_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_budgets"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_project_budgets_project_id_projects",
        ),
    )

    # --- actual_costs (FK → projects, cost_categories) ---
    op.create_table(
        "actual_costs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("cost_category_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("incurred_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_actual_costs"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_actual_costs_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["cost_category_id"], ["cost_categories.id"],
            name="fk_actual_costs_cost_category_id_cost_categories",
        ),
    )

    # --- monthly_cost_trends (FK → projects) ---
    op.create_table(
        "monthly_cost_trends",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("year_month", sa.String(7), nullable=False),
        sa.Column("planned_spend", sa.Numeric(15, 2), nullable=False),
        sa.Column("actual_spend", sa.Numeric(15, 2), nullable=False),
        sa.Column("cumulative_planned", sa.Numeric(15, 2), nullable=False),
        sa.Column("cumulative_actual", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_monthly_cost_trends"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_monthly_cost_trends_project_id_projects",
        ),
        sa.UniqueConstraint(
            "project_id", "year_month",
            name="uq_monthly_cost_trends_project_id_year_month",
        ),
    )
    op.create_index(
        "ix_monthly_cost_trends_project_id_year_month",
        "monthly_cost_trends",
        ["project_id", "year_month"],
    )

    # --- budget_line_items (FK → project_budgets, cost_categories) ---
    op.create_table(
        "budget_line_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("budget_id", sa.UUID(), nullable=False),
        sa.Column("cost_category_id", sa.UUID(), nullable=False),
        sa.Column("planned_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_budget_line_items"),
        sa.ForeignKeyConstraint(
            ["budget_id"], ["project_budgets.id"],
            name="fk_budget_line_items_budget_id_project_budgets",
        ),
        sa.ForeignKeyConstraint(
            ["cost_category_id"], ["cost_categories.id"],
            name="fk_budget_line_items_cost_category_id_cost_categories",
        ),
    )

    # --- sdlc_phases (FK → projects) ---
    op.create_table(
        "sdlc_phases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("phase_name", sa.String(255), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("planned_start_date", sa.Date(), nullable=False),
        sa.Column("planned_end_date", sa.Date(), nullable=False),
        sa.Column("actual_start_date", sa.Date(), nullable=True),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sdlc_phases"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_sdlc_phases_project_id_projects",
        ),
        sa.CheckConstraint(
            "status IN ('Not Started', 'In Progress', 'Completed', 'Blocked')",
            name="ck_sdlc_phases_status",
        ),
    )
    op.create_index(
        "ix_sdlc_phases_project_id_sequence_order",
        "sdlc_phases",
        ["project_id", "sequence_order"],
    )

    # --- sdlc_milestones (FK → sdlc_phases) ---
    op.create_table(
        "sdlc_milestones",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("phase_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sdlc_milestones"),
        sa.ForeignKeyConstraint(
            ["phase_id"], ["sdlc_phases.id"],
            name="fk_sdlc_milestones_phase_id_sdlc_phases",
        ),
    )

    # --- sdlc_deliverables (FK → sdlc_milestones) ---
    op.create_table(
        "sdlc_deliverables",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("milestone_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sdlc_deliverables"),
        sa.ForeignKeyConstraint(
            ["milestone_id"], ["sdlc_milestones.id"],
            name="fk_sdlc_deliverables_milestone_id_sdlc_milestones",
        ),
    )

    # --- sprints (FK → projects) ---
    op.create_table(
        "sprints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sprint_number", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("velocity", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sprints"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_sprints_project_id_projects",
        ),
    )

    # --- jira_issues (FK → projects, sprints) ---
    op.create_table(
        "jira_issues",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("sprint_id", sa.UUID(), nullable=True),
        sa.Column("issue_key", sa.String(50), nullable=False),
        sa.Column("issue_type", sa.String(50), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(50), nullable=False),
        sa.Column("assignee", sa.String(255), nullable=True),
        sa.Column("reporter", sa.String(255), nullable=False),
        sa.Column("story_points", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("resolved_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jira_issues"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_jira_issues_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["sprint_id"], ["sprints.id"],
            name="fk_jira_issues_sprint_id_sprints",
        ),
        sa.UniqueConstraint("issue_key", name="uq_jira_issues_issue_key"),
        sa.CheckConstraint(
            "priority IN ('Critical', 'High', 'Medium', 'Low')",
            name="ck_jira_issues_priority",
        ),
        sa.CheckConstraint(
            "issue_type IN ('Epic', 'Story', 'Task', 'Bug', 'Sub-task')",
            name="ck_jira_issues_issue_type",
        ),
        sa.CheckConstraint(
            "status IN ('To Do', 'In Progress', 'Done', 'Blocked')",
            name="ck_jira_issues_status",
        ),
    )
    op.create_index(
        "ix_jira_issues_project_id_status",
        "jira_issues",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_jira_issues_sprint_id",
        "jira_issues",
        ["sprint_id"],
    )

    # --- resource_allocations (FK → projects, team_members) ---
    op.create_table(
        "resource_allocations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("team_member_id", sa.UUID(), nullable=False),
        sa.Column("allocation_percentage", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("role_on_project", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resource_allocations"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_resource_allocations_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["team_member_id"], ["team_members.id"],
            name="fk_resource_allocations_team_member_id_team_members",
        ),
        sa.CheckConstraint(
            "allocation_percentage >= 0 AND allocation_percentage <= 100",
            name="ck_resource_allocations_allocation_percentage",
        ),
    )
    op.create_index(
        "ix_resource_allocations_project_id_team_member_id",
        "resource_allocations",
        ["project_id", "team_member_id"],
    )

    # --- resource_utilization (FK → team_members) ---
    op.create_table(
        "resource_utilization",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("team_member_id", sa.UUID(), nullable=False),
        sa.Column("year_month", sa.String(7), nullable=False),
        sa.Column("available_hours", sa.Numeric(), nullable=False),
        sa.Column("billed_hours", sa.Numeric(), nullable=False),
        sa.Column("utilization_percentage", sa.Numeric(5, 1), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resource_utilization"),
        sa.ForeignKeyConstraint(
            ["team_member_id"], ["team_members.id"],
            name="fk_resource_utilization_team_member_id_team_members",
        ),
        sa.UniqueConstraint(
            "team_member_id", "year_month",
            name="uq_resource_utilization_team_member_id_year_month",
        ),
    )

    # --- resource_forecasts (FK → projects) ---
    op.create_table(
        "resource_forecasts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("year_month", sa.String(7), nullable=False),
        sa.Column("demand_fte", sa.Numeric(10, 2), nullable=False),
        sa.Column("capacity_fte", sa.Numeric(10, 2), nullable=False),
        sa.Column("gap_fte", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resource_forecasts"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_resource_forecasts_project_id_projects",
        ),
        sa.UniqueConstraint(
            "project_id", "year_month",
            name="uq_resource_forecasts_project_id_year_month",
        ),
    )
    op.create_index(
        "ix_resource_forecasts_project_id_year_month",
        "resource_forecasts",
        ["project_id", "year_month"],
    )

    # --- audit_findings (FK → projects) ---
    op.create_table(
        "audit_findings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("finding_reference", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("identified_date", sa.Date(), nullable=False),
        sa.Column("target_remediation_date", sa.Date(), nullable=True),
        sa.Column("actual_remediation_date", sa.Date(), nullable=True),
        sa.Column("auditor", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_findings"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_audit_findings_project_id_projects",
        ),
        sa.UniqueConstraint("finding_reference", name="uq_audit_findings_finding_reference"),
        sa.CheckConstraint(
            "severity IN ('Critical', 'High', 'Medium', 'Low')",
            name="ck_audit_findings_severity",
        ),
        sa.CheckConstraint(
            "status IN ('Open', 'In Progress', 'Closed')",
            name="ck_audit_findings_status",
        ),
    )
    op.create_index(
        "ix_audit_findings_project_id_severity",
        "audit_findings",
        ["project_id", "severity"],
    )
    op.create_index(
        "ix_audit_findings_project_id_status",
        "audit_findings",
        ["project_id", "status"],
    )

    # --- control_assessments (FK → it_controls, projects) ---
    op.create_table(
        "control_assessments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("control_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("compliance_status", sa.String(50), nullable=False),
        sa.Column("assessed_date", sa.Date(), nullable=False),
        sa.Column("assessor", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("next_assessment_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_control_assessments"),
        sa.ForeignKeyConstraint(
            ["control_id"], ["it_controls.id"],
            name="fk_control_assessments_control_id_it_controls",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_control_assessments_project_id_projects",
        ),
        sa.CheckConstraint(
            "compliance_status IN ('Compliant', 'Non-Compliant', 'Partially Compliant', 'Not Assessed')",
            name="ck_control_assessments_compliance_status",
        ),
    )
    op.create_index(
        "ix_control_assessments_project_id_control_id",
        "control_assessments",
        ["project_id", "control_id"],
    )
    op.create_index(
        "ix_control_assessments_compliance_status",
        "control_assessments",
        ["compliance_status"],
    )

    # --- remediation_items (FK → audit_findings, projects) ---
    op.create_table(
        "remediation_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(50), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_remediation_items"),
        sa.ForeignKeyConstraint(
            ["finding_id"], ["audit_findings.id"],
            name="fk_remediation_items_finding_id_audit_findings",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_remediation_items_project_id_projects",
        ),
        sa.CheckConstraint(
            "status IN ('Open', 'In Progress', 'Completed', 'Cancelled')",
            name="ck_remediation_items_status",
        ),
        sa.CheckConstraint(
            "priority IN ('Critical', 'High', 'Medium', 'Low')",
            name="ck_remediation_items_priority",
        ),
    )
    op.create_index(
        "ix_remediation_items_project_id_status",
        "remediation_items",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_remediation_items_finding_id",
        "remediation_items",
        ["finding_id"],
    )

    # --- project_risks (FK → projects) ---
    op.create_table(
        "project_risks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("risk_reference", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("identified_date", sa.Date(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_risks"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_project_risks_project_id_projects",
        ),
        sa.UniqueConstraint("risk_reference", name="uq_project_risks_risk_reference"),
        sa.CheckConstraint(
            "severity IN ('Critical', 'High', 'Medium', 'Low')",
            name="ck_project_risks_severity",
        ),
        sa.CheckConstraint(
            "status IN ('Open', 'Mitigated', 'Closed')",
            name="ck_project_risks_status",
        ),
    )
    op.create_index(
        "ix_project_risks_project_id_severity",
        "project_risks",
        ["project_id", "severity"],
    )
    op.create_index(
        "ix_project_risks_project_id_status",
        "project_risks",
        ["project_id", "status"],
    )

    # --- project_progress_snapshots (FK → projects) ---
    op.create_table(
        "project_progress_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("planned_progress_percentage", sa.Integer(), nullable=False),
        sa.Column("actual_progress_percentage", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_progress_snapshots"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_project_progress_snapshots_project_id_projects",
        ),
        sa.UniqueConstraint(
            "project_id", "snapshot_date",
            name="uq_project_progress_snapshots_project_id_snapshot_date",
        ),
        sa.CheckConstraint(
            "planned_progress_percentage >= 0 AND planned_progress_percentage <= 100",
            name="ck_project_progress_snapshots_planned_progress_percentage",
        ),
        sa.CheckConstraint(
            "actual_progress_percentage >= 0 AND actual_progress_percentage <= 100",
            name="ck_project_progress_snapshots_actual_progress_percentage",
        ),
    )
    op.create_index(
        "ix_project_progress_snapshots_project_id_snapshot_date",
        "project_progress_snapshots",
        ["project_id", "snapshot_date"],
    )

    # --- project_health_kpis (FK → projects) ---
    op.create_table(
        "project_health_kpis",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("overall_status", sa.String(50), nullable=False),
        sa.Column("schedule_status", sa.String(50), nullable=False),
        sa.Column("budget_total", sa.Numeric(15, 2), nullable=False),
        sa.Column("budget_spent", sa.Numeric(15, 2), nullable=False),
        sa.Column("budget_variance", sa.Numeric(15, 2), nullable=False),
        sa.Column("budget_variance_percentage", sa.Numeric(15, 2), nullable=False),
        sa.Column("progress_percentage", sa.Integer(), nullable=False),
        sa.Column("resource_utilization_percentage", sa.Numeric(5, 1), nullable=False),
        sa.Column("open_issues_count", sa.Integer(), nullable=False),
        sa.Column("open_risks_count", sa.Integer(), nullable=False),
        sa.Column("open_audit_findings_count", sa.Integer(), nullable=False),
        sa.Column("open_remediation_items_count", sa.Integer(), nullable=False),
        sa.Column("it_control_compliance_percentage", sa.Integer(), nullable=False),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_health_kpis"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_project_health_kpis_project_id_projects",
        ),
        sa.UniqueConstraint("project_id", name="uq_project_health_kpis_project_id"),
        sa.CheckConstraint(
            "overall_status IN ('On Track', 'At Risk', 'Delayed', 'Completed')",
            name="ck_project_health_kpis_overall_status",
        ),
        sa.CheckConstraint(
            "schedule_status IN ('On Time', 'Delayed', 'Ahead')",
            name="ck_project_health_kpis_schedule_status",
        ),
        sa.CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="ck_project_health_kpis_progress_percentage",
        ),
        sa.CheckConstraint(
            "resource_utilization_percentage >= 0",
            name="ck_project_health_kpis_resource_utilization_percentage",
        ),
        sa.CheckConstraint(
            "it_control_compliance_percentage >= 0 AND it_control_compliance_percentage <= 100",
            name="ck_project_health_kpis_it_control_compliance_percentage",
        ),
    )


def downgrade() -> None:
    """Drop all Phase 3 business domain tables in reverse dependency order."""
    op.drop_table("project_health_kpis")
    op.drop_index(
        "ix_project_progress_snapshots_project_id_snapshot_date",
        table_name="project_progress_snapshots",
    )
    op.drop_table("project_progress_snapshots")
    op.drop_index("ix_project_risks_project_id_status", table_name="project_risks")
    op.drop_index("ix_project_risks_project_id_severity", table_name="project_risks")
    op.drop_table("project_risks")
    op.drop_index("ix_remediation_items_finding_id", table_name="remediation_items")
    op.drop_index("ix_remediation_items_project_id_status", table_name="remediation_items")
    op.drop_table("remediation_items")
    op.drop_index(
        "ix_control_assessments_compliance_status",
        table_name="control_assessments",
    )
    op.drop_index(
        "ix_control_assessments_project_id_control_id",
        table_name="control_assessments",
    )
    op.drop_table("control_assessments")
    op.drop_index("ix_audit_findings_project_id_status", table_name="audit_findings")
    op.drop_index("ix_audit_findings_project_id_severity", table_name="audit_findings")
    op.drop_table("audit_findings")
    op.drop_index(
        "ix_resource_forecasts_project_id_year_month",
        table_name="resource_forecasts",
    )
    op.drop_table("resource_forecasts")
    op.drop_table("resource_utilization")
    op.drop_index(
        "ix_resource_allocations_project_id_team_member_id",
        table_name="resource_allocations",
    )
    op.drop_table("resource_allocations")
    op.drop_index("ix_jira_issues_sprint_id", table_name="jira_issues")
    op.drop_index("ix_jira_issues_project_id_status", table_name="jira_issues")
    op.drop_table("jira_issues")
    op.drop_table("sprints")
    op.drop_table("sdlc_deliverables")
    op.drop_table("sdlc_milestones")
    op.drop_index(
        "ix_sdlc_phases_project_id_sequence_order",
        table_name="sdlc_phases",
    )
    op.drop_table("sdlc_phases")
    op.drop_table("budget_line_items")
    op.drop_index(
        "ix_monthly_cost_trends_project_id_year_month",
        table_name="monthly_cost_trends",
    )
    op.drop_table("monthly_cost_trends")
    op.drop_table("actual_costs")
    op.drop_table("project_budgets")
    op.drop_table("it_controls")
    op.drop_table("team_members")
    op.drop_table("cost_categories")

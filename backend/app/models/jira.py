"""
JIRA domain ORM models for App_DB.

Models represent sprints and issues tracked in JIRA for each project.
Sprint contains a collection of JiraIssue records with typed priorities,
issue types, and statuses enforced via CHECK constraints.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class Sprint(AppBase):
    """A sprint belonging to a project, containing JIRA issues."""

    __tablename__ = "sprints"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    sprint_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    end_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    goal: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    velocity: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    # Relationships
    issues: Mapped[list["JiraIssue"]] = relationship(
        "JiraIssue", back_populates="sprint", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Sprint id={self.id} name={self.name}>"


class JiraIssue(AppBase):
    """A JIRA issue belonging to a project, optionally assigned to a sprint."""

    __tablename__ = "jira_issues"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    sprint_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("sprints.id"), nullable=True
    )
    issue_key: Mapped[str] = mapped_column(
        sa.String(50), unique=True, nullable=False
    )
    issue_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    summary: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    priority: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    assignee: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    reporter: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    story_points: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    due_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    resolved_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    # Relationships
    sprint: Mapped["Sprint | None"] = relationship(
        "Sprint", back_populates="issues"
    )

    __table_args__ = (
        # CHECK constraints
        sa.CheckConstraint(
            "priority IN ('Critical', 'High', 'Medium', 'Low')",
            name="priority",
        ),
        sa.CheckConstraint(
            "issue_type IN ('Epic', 'Story', 'Task', 'Bug', 'Sub-task')",
            name="issue_type",
        ),
        sa.CheckConstraint(
            "status IN ('To Do', 'In Progress', 'Done', 'Blocked')",
            name="status",
        ),
        # Indexes for query optimization
        sa.Index("ix_jira_issues_project_id_status", "project_id", "status"),
        sa.Index("ix_jira_issues_sprint_id", "sprint_id"),
    )

    def __repr__(self) -> str:
        return f"<JiraIssue id={self.id} key={self.issue_key}>"

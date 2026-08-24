"""
Project and ProjectMember ORM models for App_DB.

Projects are the primary business context. All business information
(finance, SDLC, resources, audit, documents) connects to a project.
ProjectMembers represent the many-to-many relationship between users and projects.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class Project(AppBase):
    """Primary business context entity."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_code: Mapped[str | None] = mapped_column(
        sa.String(50), unique=True, nullable=True
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="active"
    )
    created_by: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False
    )
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
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", lazy="selectin"
    )
    source_connections: Mapped[list["SourceConnection"]] = relationship(
        "SourceConnection", back_populates="project", lazy="selectin"
    )
    source_mappings: Mapped[list["ProjectSourceMapping"]] = relationship(
        "ProjectSourceMapping", back_populates="project", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name}>"


class ProjectMember(AppBase):
    """Many-to-many relationship between users and projects with role."""

    __tablename__ = "project_members"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="members"
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="project_memberships"
    )

    # Unique constraint: a user can only have one role per project
    __table_args__ = (
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )

    def __repr__(self) -> str:
        return f"<ProjectMember project_id={self.project_id} user_id={self.user_id}>"

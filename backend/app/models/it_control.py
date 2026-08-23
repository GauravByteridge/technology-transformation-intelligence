"""
IT Control and Control Assessment ORM models for App_DB.

IT Controls represent defined control objectives with compliance assessment status.
Control Assessments record periodic evaluations of IT controls, producing a
compliance determination per project.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class ItControl(AppBase):
    """A defined IT control objective within a governance framework."""

    __tablename__ = "it_controls"

    id: Mapped[UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid4)
    control_reference: Mapped[str] = mapped_column(
        sa.String(100), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    category: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    framework: Mapped[str] = mapped_column(sa.String(100), nullable=False)
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
    assessments: Mapped[list["ControlAssessment"]] = relationship(
        "ControlAssessment", back_populates="control", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<ItControl id={self.id} "
            f"control_reference={self.control_reference} "
            f"category={self.category}>"
        )


class ControlAssessment(AppBase):
    """A periodic compliance evaluation of an IT control for a specific project."""

    __tablename__ = "control_assessments"

    id: Mapped[UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid4)
    control_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("it_controls.id"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    compliance_status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    assessed_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    assessor: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    next_assessment_date: Mapped[date | None] = mapped_column(
        sa.Date, nullable=True
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
    control: Mapped["ItControl"] = relationship(
        "ItControl", back_populates="assessments", lazy="selectin"
    )
    project: Mapped["Project"] = relationship("Project", lazy="selectin")

    __table_args__ = (
        sa.CheckConstraint(
            "compliance_status IN ('Compliant', 'Non-Compliant', 'Partially Compliant', 'Not Assessed')",
            name="compliance_status",
        ),
        sa.Index(
            "ix_control_assessments_project_id_control_id",
            "project_id",
            "control_id",
        ),
        sa.Index(
            "ix_control_assessments_compliance_status",
            "compliance_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ControlAssessment id={self.id} "
            f"control_id={self.control_id} "
            f"project_id={self.project_id} "
            f"compliance_status={self.compliance_status}>"
        )

"""
Financial data ORM models for App_DB.

Stores project budgets, cost categories, budget line items, actual costs,
and monthly cost trends. These tables are the authoritative source for
financial data used by FinanceService and ProjectHealthService.

Variance semantics: positive variance = under budget, negative = over budget.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class ProjectBudget(AppBase):
    """Annual budget record for a project."""

    __tablename__ = "project_budgets"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    fiscal_year: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    total_budget: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
    )
    approved_date: Mapped[date | None] = mapped_column(
        sa.Date, nullable=True
    )
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
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
    line_items: Mapped[list["BudgetLineItem"]] = relationship(
        "BudgetLineItem", back_populates="budget", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ProjectBudget id={self.id} project_id={self.project_id} fiscal_year={self.fiscal_year}>"


class CostCategory(AppBase):
    """Classification of project expenditure (e.g., Personnel, Infrastructure)."""

    __tablename__ = "cost_categories"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(
        sa.String(100), unique=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        sa.String(500), nullable=True
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

    def __repr__(self) -> str:
        return f"<CostCategory id={self.id} name={self.name}>"


class BudgetLineItem(AppBase):
    """Planned allocation of budget to a specific cost category."""

    __tablename__ = "budget_line_items"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    budget_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("project_budgets.id"), nullable=False
    )
    cost_category_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("cost_categories.id"), nullable=False
    )
    planned_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
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
    budget: Mapped["ProjectBudget"] = relationship(
        "ProjectBudget", back_populates="line_items"
    )
    cost_category: Mapped["CostCategory"] = relationship(
        "CostCategory", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<BudgetLineItem id={self.id} budget_id={self.budget_id}>"


class ActualCost(AppBase):
    """Recorded expenditure against a project and cost category."""

    __tablename__ = "actual_costs"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    cost_category_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("cost_categories.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
    )
    incurred_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    description: Mapped[str | None] = mapped_column(
        sa.String(500), nullable=True
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

    def __repr__(self) -> str:
        return f"<ActualCost id={self.id} project_id={self.project_id} amount={self.amount}>"


class MonthlyCostTrend(AppBase):
    """Time-series record of planned vs actual spend per project per month."""

    __tablename__ = "monthly_cost_trends"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    year_month: Mapped[str] = mapped_column(
        sa.String(7), nullable=False
    )
    planned_spend: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
    )
    actual_spend: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
    )
    cumulative_planned: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
    )
    cumulative_actual: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
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

    __table_args__ = (
        sa.Index(
            "ix_monthly_cost_trends_project_id_year_month",
            "project_id",
            "year_month",
        ),
        sa.UniqueConstraint(
            "project_id",
            "year_month",
            name="uq_monthly_cost_trends_project_id_year_month",
        ),
    )

    def __repr__(self) -> str:
        return f"<MonthlyCostTrend id={self.id} project_id={self.project_id} year_month={self.year_month}>"

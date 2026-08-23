"""
Finance repository — database access layer for financial domain entities.

Provides typed, parameterized access to project_budgets, actual_costs, and
monthly_cost_trends tables in App_DB. All queries use SQLAlchemy ORM with
bound parameters (inherited from BaseRepository).
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import ActualCost, MonthlyCostTrend, ProjectBudget
from app.repositories.base import BaseRepository


class FinanceRepository(BaseRepository[ProjectBudget]):
    """
    Encapsulates all database access for financial domain entities.

    Manages queries against project_budgets, actual_costs, and
    monthly_cost_trends tables. Inherits parameterized query patterns
    from BaseRepository. Services call this repository — it contains
    no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, ProjectBudget)

    async def get_budget_by_project(self, project_id: UUID) -> ProjectBudget | None:
        """
        Retrieve the project budget for a given project.

        Args:
            project_id: UUID of the project to look up the budget for.

        Returns:
            ProjectBudget model instance, or None if no budget exists.
        """
        statement = select(ProjectBudget).where(
            ProjectBudget.project_id == project_id
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def list_actual_costs(self, project_id: UUID) -> list[ActualCost]:
        """
        Retrieve all actual cost records for a given project.

        Args:
            project_id: UUID of the project to retrieve costs for.

        Returns:
            List of ActualCost model instances for the project.
        """
        statement = select(ActualCost).where(
            ActualCost.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_monthly_trends(self, project_id: UUID) -> list[MonthlyCostTrend]:
        """
        Retrieve monthly cost trend records for a given project, ordered by year_month.

        Args:
            project_id: UUID of the project to retrieve trends for.

        Returns:
            List of MonthlyCostTrend model instances ordered chronologically.
        """
        statement = (
            select(MonthlyCostTrend)
            .where(MonthlyCostTrend.project_id == project_id)
            .order_by(MonthlyCostTrend.year_month)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_total_spent(self, project_id: UUID) -> Decimal:
        """
        Calculate the total amount spent on a project from actual cost records.

        Uses a SUM aggregation over actual_costs.amount for the given project.

        Args:
            project_id: UUID of the project to calculate total spend for.

        Returns:
            Total amount spent as a Decimal. Returns Decimal("0") if no
            cost records exist for the project.
        """
        statement = select(func.sum(ActualCost.amount)).where(
            ActualCost.project_id == project_id
        )
        result = await self._session.execute(statement)
        total = result.scalar()
        return total if total is not None else Decimal("0")

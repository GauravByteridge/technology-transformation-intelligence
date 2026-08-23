"""
Finance service — business logic layer for financial domain operations.

Provides budget variance calculations, cost aggregation, and project
finance data retrieval. Accepts FinanceRepository via constructor injection.

Variance semantics: positive = under budget, negative = over budget.
"""

import structlog
from decimal import Decimal
from uuid import UUID

from app.errors.health_errors import FinanceDataNotFoundError
from app.repositories.finance_repository import FinanceRepository

logger = structlog.get_logger(__name__)


class FinanceService:
    """
    Business logic for financial domain operations.

    Encapsulates budget variance calculations and project finance
    data retrieval. Dependencies injected via constructor.
    """

    def __init__(self, repository: FinanceRepository) -> None:
        """
        Initialize with a finance repository.

        Args:
            repository: FinanceRepository instance for data access.
        """
        self._repository = repository

    async def get_project_finance(self, project_id: UUID) -> dict:
        """
        Retrieve comprehensive finance data for a project.

        Fetches budget, actual costs, total spent, and monthly trends.
        Computes variance metrics from authoritative budget and cost data.

        Args:
            project_id: UUID of the project to retrieve finance data for.

        Returns:
            Dictionary containing budget, actual_costs, total_spent,
            budget_variance, variance_percentage, and monthly_trends.

        Raises:
            FinanceDataNotFoundError: If no budget exists for the project.
        """
        budget = await self._repository.get_budget_by_project(project_id)

        if budget is None:
            logger.info(
                "finance_data_not_found",
                project_id=str(project_id),
            )
            raise FinanceDataNotFoundError(project_id=str(project_id))

        actual_costs = await self._repository.list_actual_costs(project_id)
        total_spent = await self._repository.get_total_spent(project_id)
        monthly_trends = await self._repository.list_monthly_trends(project_id)

        budget_variance = self.calculate_budget_variance(
            budget.total_budget, total_spent
        )
        variance_percentage = self.calculate_variance_percentage(
            budget.total_budget, total_spent
        )

        logger.debug(
            "project_finance_retrieved",
            project_id=str(project_id),
            budget_total=str(budget.total_budget),
            total_spent=str(total_spent),
            budget_variance=str(budget_variance),
        )

        return {
            "budget": budget,
            "actual_costs": actual_costs,
            "total_spent": total_spent,
            "budget_variance": budget_variance,
            "variance_percentage": variance_percentage,
            "monthly_trends": monthly_trends,
        }

    def calculate_budget_variance(
        self, budget_total: Decimal, budget_spent: Decimal
    ) -> Decimal:
        """
        Calculate budget variance.

        Positive value indicates under budget, negative indicates over budget.

        Args:
            budget_total: Total approved budget amount.
            budget_spent: Total amount spent to date.

        Returns:
            Budget variance as budget_total - budget_spent.
        """
        return budget_total - budget_spent

    def calculate_variance_percentage(
        self, budget_total: Decimal, budget_spent: Decimal
    ) -> Decimal:
        """
        Calculate budget variance as a percentage of total budget.

        Negative percentage indicates over-budget spending.
        Returns Decimal("0") when budget_total is zero to avoid division by zero.

        Args:
            budget_total: Total approved budget amount.
            budget_spent: Total amount spent to date.

        Returns:
            Variance percentage: ((budget_total - budget_spent) / budget_total) * 100.
        """
        if budget_total == 0:
            return Decimal("0")
        return ((budget_total - budget_spent) / budget_total) * 100

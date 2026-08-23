"""
Resource service — business logic for resource management.

Calculates project-level resource utilization from active allocations
and utilization records, and computes capacity gaps from forecasts.
"""

import calendar
from datetime import date
from decimal import Decimal
from uuid import UUID

import structlog

from app.models.resource import (
    ResourceAllocation,
    ResourceForecast,
    ResourceUtilization,
)
from app.repositories.resource_repository import ResourceRepository

logger = structlog.get_logger(__name__)


class ResourceService:
    """
    Business logic for resource management.

    Handles utilization calculation (arithmetic mean of eligible members)
    and capacity gap computation (demand vs capacity across forecast months).
    Dependencies injected via constructor.
    """

    def __init__(self, repository: ResourceRepository) -> None:
        """
        Initialize with a resource repository.

        Args:
            repository: ResourceRepository instance for data access.
        """
        self._repository = repository

    async def get_project_resources(self, project_id: UUID) -> dict:
        """
        Retrieve resource data for a project: allocations, utilization, forecasts.

        Args:
            project_id: UUID of the project.

        Returns:
            Dictionary with allocations, utilization_percentage (or None),
            capacity_gap, and forecasts.
        """
        allocations = await self._repository.list_allocations_by_project(project_id)
        forecasts = await self._repository.list_forecasts_by_project(project_id)

        most_recent_month = await self._repository.get_most_recent_utilization_month()

        utilization_percentage: Decimal | None = None
        utilization_records: list[ResourceUtilization] = []

        if most_recent_month and allocations:
            member_ids = [a.team_member_id for a in allocations]
            utilization_records = await self._repository.list_utilization_by_members(
                member_ids, most_recent_month
            )
            utilization_percentage = self.calculate_project_utilization(
                allocations, utilization_records, most_recent_month
            )

        capacity_gap = self.calculate_capacity_gap(forecasts)

        logger.debug(
            "project_resources_retrieved",
            project_id=str(project_id),
            allocation_count=len(allocations),
            utilization_percentage=str(utilization_percentage),
            capacity_gap=str(capacity_gap),
        )

        return {
            "allocations": allocations,
            "utilization_percentage": utilization_percentage,
            "capacity_gap": capacity_gap,
            "forecasts": forecasts,
        }

    def calculate_project_utilization(
        self,
        allocations: list[ResourceAllocation],
        utilization_records: list[ResourceUtilization],
        most_recent_month: str,
    ) -> Decimal | None:
        """Calculate project-level resource utilization percentage.

        Algorithm:
        1. Parse most_recent_month to determine month start/end dates.
        2. Filter allocations active during that month:
           start_date <= month_end AND (end_date is None OR end_date >= month_start).
        3. Get team_member_ids from those active allocations.
        4. Filter utilization_records to only those team members.
        5. Calculate arithmetic mean of utilization_percentage values.

        Returns None if no eligible members or no matching records,
        signaling the caller should fall back to gap_fte.

        Args:
            allocations: All allocations for the project.
            utilization_records: Utilization records for the relevant month.
            most_recent_month: Year-month string in "YYYY-MM" format.

        Returns:
            Arithmetic mean of utilization percentages, or None.
        """
        month_start, month_end = self._parse_month_range(most_recent_month)

        # Step 1-2: Filter allocations active during the month
        active_member_ids: set[UUID] = set()
        for allocation in allocations:
            is_started = allocation.start_date <= month_end
            is_not_ended = (
                allocation.end_date is None or allocation.end_date >= month_start
            )
            if is_started and is_not_ended:
                active_member_ids.add(allocation.team_member_id)

        if not active_member_ids:
            return None

        # Step 3-4: Filter utilization records to active members
        eligible_records = [
            record
            for record in utilization_records
            if record.team_member_id in active_member_ids
        ]

        if not eligible_records:
            return None

        # Step 5: Arithmetic mean
        total = sum(record.utilization_percentage for record in eligible_records)
        return Decimal(str(total)) / Decimal(len(eligible_records))

    def calculate_capacity_gap(self, forecasts: list[ResourceForecast]) -> Decimal:
        """Sum of (demand_fte - capacity_fte) across all forecast months.

        Positive result means demand exceeds capacity (resource gap).
        Returns Decimal("0") when no forecasts exist.

        Args:
            forecasts: List of resource forecast records.

        Returns:
            Total capacity gap as a Decimal.
        """
        if not forecasts:
            return Decimal("0")
        return sum(
            ((f.demand_fte - f.capacity_fte) for f in forecasts),
            start=Decimal("0"),
        )

    @staticmethod
    def _parse_month_range(year_month: str) -> tuple[date, date]:
        """Parse a YYYY-MM string into (first_day, last_day) of that month.

        Args:
            year_month: String in "YYYY-MM" format.

        Returns:
            Tuple of (month_start, month_end) as date objects.
        """
        year, month = int(year_month[:4]), int(year_month[5:7])
        month_start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        month_end = date(year, month, last_day)
        return month_start, month_end

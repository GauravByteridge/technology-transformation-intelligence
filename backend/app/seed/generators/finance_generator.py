"""Finance seed generator.

Generates cost categories, project budgets with line items, actual costs,
and monthly cost trends for each project in the portfolio.

Key behaviors:
- 5 shared cost categories (Personnel, Infrastructure, Licensing, Professional Services, Training)
- 1 budget per project (FY2025) with at least 3 line items
- Actual costs with realistic variance per category
- Monthly cost trends spanning 8 months with cumulative progression
- Project Alpha (hero): over budget by ~12.5% (total_budget=2_000_000, actual~2_250_000)
- Other projects: realistic mix (some under, some slightly over, some on target)
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.seed.deterministic import deterministic_uuid
from app.seed.generators.project_generator import HERO_PROJECT_NAME, PROJECT_DEFINITIONS

# Shared cost category definitions.
COST_CATEGORY_DEFINITIONS: list[dict[str, str]] = [
    {
        "name": "Personnel",
        "description": "Staff salaries, contractor fees, and related human resource costs.",
    },
    {
        "name": "Infrastructure",
        "description": "Cloud hosting, on-premises hardware, network, and compute resources.",
    },
    {
        "name": "Licensing",
        "description": "Software licenses, SaaS subscriptions, and third-party tool fees.",
    },
    {
        "name": "Professional Services",
        "description": "Consulting, advisory, audit, and external professional engagements.",
    },
    {
        "name": "Training",
        "description": "Staff training, certifications, workshops, and knowledge transfer programs.",
    },
]

# Budget configurations per project.
# Each entry: (total_budget, variance_factor).
# variance_factor > 1.0 means over budget, < 1.0 means under budget.
# Project Alpha (index 0) is intentionally over budget by ~12.5%.
_PROJECT_BUDGET_CONFIGS: list[dict[str, Decimal | str]] = [
    {"total_budget": Decimal("2000000.00"), "variance_factor": Decimal("1.125")},   # Alpha: over
    {"total_budget": Decimal("1500000.00"), "variance_factor": Decimal("0.88")},    # Cloud Migration: under
    {"total_budget": Decimal("1200000.00"), "variance_factor": Decimal("0.95")},    # Data Platform: on target
    {"total_budget": Decimal("800000.00"), "variance_factor": Decimal("0.92")},     # API Gateway: under
    {"total_budget": Decimal("900000.00"), "variance_factor": Decimal("1.05")},     # Legacy Decommission: slightly over
    {"total_budget": Decimal("1100000.00"), "variance_factor": Decimal("1.08")},    # Security Ops: over
    {"total_budget": Decimal("600000.00"), "variance_factor": Decimal("0.85")},     # DevOps Pipeline: under
    {"total_budget": Decimal("750000.00"), "variance_factor": Decimal("0.98")},     # Customer Portal: on target
    {"total_budget": Decimal("1300000.00"), "variance_factor": Decimal("0.90")},    # Enterprise Data Lake: under
    {"total_budget": Decimal("950000.00"), "variance_factor": Decimal("1.03")},     # Mobile Banking: slightly over
    {"total_budget": Decimal("700000.00"), "variance_factor": Decimal("0.87")},     # Identity Access Mgmt: under
    {"total_budget": Decimal("850000.00"), "variance_factor": Decimal("0.93")},     # Regulatory Reporting: under
]

# Budget allocation distribution across categories (percentages must sum to 100).
# Each project distributes its budget across categories in these proportions.
_CATEGORY_ALLOCATION_PCTS: list[Decimal] = [
    Decimal("45"),  # Personnel
    Decimal("25"),  # Infrastructure
    Decimal("15"),  # Licensing
    Decimal("10"),  # Professional Services
    Decimal("5"),   # Training
]

# Fiscal year for all budgets.
FISCAL_YEAR = 2025

# Monthly trend period: 8 months starting Jan 2025.
_TREND_START_YEAR = 2025
_TREND_START_MONTH = 1
_TREND_MONTH_COUNT = 8


class FinanceSeedGenerator:
    """Generates financial seed data for the technology transformation portfolio.

    Produces:
    - Cost category records (shared across all projects)
    - Budget records with line items per project
    - Actual cost entries per project
    - Monthly cost trend records per project
    """

    def generate_cost_categories(self) -> list[dict]:
        """Generate the 5 shared cost category records.

        Returns:
            List of cost category dictionaries ready for DB insertion.
        """
        categories: list[dict] = []
        for cat_def in COST_CATEGORY_DEFINITIONS:
            cat_id = deterministic_uuid("cost_category", cat_def["name"])
            categories.append({
                "id": cat_id,
                "name": cat_def["name"],
                "description": cat_def["description"],
            })
        return categories

    def generate_budgets(
        self, project_count: int
    ) -> tuple[list[dict], list[dict]]:
        """Generate budget records and budget line items for each project.

        Args:
            project_count: Number of projects to generate budgets for.

        Returns:
            Tuple of (budgets, line_items) dictionaries.
        """
        budgets: list[dict] = []
        line_items: list[dict] = []
        categories = self.generate_cost_categories()
        selected_projects = PROJECT_DEFINITIONS[:project_count]

        for idx, project_def in enumerate(selected_projects):
            project_name = project_def["name"]
            project_id = deterministic_uuid("project", project_name)
            config = _PROJECT_BUDGET_CONFIGS[idx]
            total_budget = config["total_budget"]

            budget_id = deterministic_uuid("budget", project_name, str(FISCAL_YEAR))
            budgets.append({
                "id": budget_id,
                "project_id": project_id,
                "fiscal_year": FISCAL_YEAR,
                "total_budget": total_budget,
                "approved_date": date(2024, 11, 15),
                "status": "Approved",
            })

            # Create line items for each category (all 5 categories per project).
            for cat_idx, category in enumerate(categories):
                allocation_pct = _CATEGORY_ALLOCATION_PCTS[cat_idx]
                planned_amount = (total_budget * allocation_pct / Decimal("100")).quantize(
                    Decimal("0.01")
                )
                line_item_id = deterministic_uuid(
                    "budget_line_item", project_name, category["name"]
                )
                line_items.append({
                    "id": line_item_id,
                    "budget_id": budget_id,
                    "cost_category_id": category["id"],
                    "planned_amount": planned_amount,
                })

        return budgets, line_items

    def generate_actual_costs(self, project_count: int) -> list[dict]:
        """Generate actual cost records per project with realistic variance.

        Distributes actual spending across categories proportional to planned
        amounts, adjusted by the project's variance factor.

        Args:
            project_count: Number of projects to generate costs for.

        Returns:
            List of actual cost dictionaries.
        """
        actual_costs: list[dict] = []
        categories = self.generate_cost_categories()
        selected_projects = PROJECT_DEFINITIONS[:project_count]

        for idx, project_def in enumerate(selected_projects):
            project_name = project_def["name"]
            project_id = deterministic_uuid("project", project_name)
            config = _PROJECT_BUDGET_CONFIGS[idx]
            total_budget = config["total_budget"]
            variance_factor = config["variance_factor"]

            # Total actual spend based on variance factor.
            total_actual = (total_budget * variance_factor).quantize(Decimal("0.01"))

            # Distribute actual costs across categories with slight per-category variance.
            # Personnel gets slightly more overrun in over-budget projects.
            _category_variance_adjustments = [
                Decimal("1.03"),  # Personnel: slight additional overrun
                Decimal("1.00"),  # Infrastructure: neutral
                Decimal("0.98"),  # Licensing: slightly less
                Decimal("1.01"),  # Professional Services: slight
                Decimal("0.95"),  # Training: typically underspent
            ]

            # Calculate raw category amounts.
            raw_amounts: list[Decimal] = []
            for cat_idx in range(len(categories)):
                base_pct = _CATEGORY_ALLOCATION_PCTS[cat_idx]
                adjustment = _category_variance_adjustments[cat_idx]
                raw = total_actual * base_pct * adjustment / Decimal("100")
                raw_amounts.append(raw)

            # Normalize to match total_actual exactly.
            raw_sum = sum(raw_amounts)
            normalized_amounts = [
                (amt * total_actual / raw_sum).quantize(Decimal("0.01"))
                for amt in raw_amounts
            ]

            # Adjust rounding difference on the largest category (Personnel).
            rounding_diff = total_actual - sum(normalized_amounts)
            normalized_amounts[0] += rounding_diff

            # Create actual cost entries (one per category per project).
            for cat_idx, category in enumerate(categories):
                cost_id = deterministic_uuid(
                    "actual_cost", project_name, category["name"]
                )
                # Incurred date spread across the trend period.
                incurred_month = _TREND_START_MONTH + (cat_idx % _TREND_MONTH_COUNT)
                actual_costs.append({
                    "id": cost_id,
                    "project_id": project_id,
                    "cost_category_id": category["id"],
                    "amount": normalized_amounts[cat_idx],
                    "incurred_date": date(
                        _TREND_START_YEAR,
                        incurred_month,
                        15,
                    ),
                    "description": f"{category['name']} costs for {project_name}",
                })

        return actual_costs

    def generate_monthly_cost_trends(self, project_count: int) -> list[dict]:
        """Generate monthly cost trend records with cumulative progression.

        Each project gets 8 months of trend data. For Project Alpha, actual_spend
        exceeds planned_spend in recent months to show budget overrun trajectory.

        Args:
            project_count: Number of projects to generate trends for.

        Returns:
            List of monthly cost trend dictionaries.
        """
        trends: list[dict] = []
        selected_projects = PROJECT_DEFINITIONS[:project_count]

        for idx, project_def in enumerate(selected_projects):
            project_name = project_def["name"]
            project_id = deterministic_uuid("project", project_name)
            config = _PROJECT_BUDGET_CONFIGS[idx]
            total_budget = config["total_budget"]
            variance_factor = config["variance_factor"]

            # Monthly planned spend: evenly distributed across trend months.
            monthly_planned = (total_budget / Decimal(str(_TREND_MONTH_COUNT))).quantize(
                Decimal("0.01")
            )

            # Actual spend ramps up relative to variance factor.
            # For over-budget projects, later months show higher actual vs planned.
            # For under-budget projects, actual stays below planned.
            is_over_budget = variance_factor > Decimal("1.0")

            cumulative_planned = Decimal("0.00")
            cumulative_actual = Decimal("0.00")

            for month_offset in range(_TREND_MONTH_COUNT):
                month_num = _TREND_START_MONTH + month_offset
                year_month = f"{_TREND_START_YEAR}-{month_num:02d}"

                planned_spend = monthly_planned

                # Calculate actual spend with progressive variance.
                if is_over_budget:
                    # Over-budget: starts close to planned, grows over time.
                    progress_ratio = Decimal(str((month_offset + 1) / _TREND_MONTH_COUNT))
                    month_variance = (
                        Decimal("1.0")
                        + (variance_factor - Decimal("1.0")) * progress_ratio * Decimal("2")
                    )
                    actual_spend = (monthly_planned * month_variance).quantize(
                        Decimal("0.01")
                    )
                else:
                    # Under-budget: actual consistently below planned.
                    actual_spend = (monthly_planned * variance_factor).quantize(
                        Decimal("0.01")
                    )

                cumulative_planned += planned_spend
                cumulative_actual += actual_spend

                trend_id = deterministic_uuid(
                    "monthly_cost_trend", project_name, year_month
                )
                trends.append({
                    "id": trend_id,
                    "project_id": project_id,
                    "year_month": year_month,
                    "planned_spend": planned_spend,
                    "actual_spend": actual_spend,
                    "cumulative_planned": cumulative_planned.quantize(Decimal("0.01")),
                    "cumulative_actual": cumulative_actual.quantize(Decimal("0.01")),
                })

        return trends

    def generate(self, project_count: int) -> dict[str, list[dict]]:
        """Generate all finance seed data for the portfolio.

        Args:
            project_count: Number of projects in the portfolio.

        Returns:
            Dictionary with keys: "cost_categories", "budgets", "budget_line_items",
            "actual_costs", "monthly_cost_trends". Each value is a list of dicts.
        """
        categories = self.generate_cost_categories()
        budgets, line_items = self.generate_budgets(project_count)
        actual_costs = self.generate_actual_costs(project_count)
        monthly_trends = self.generate_monthly_cost_trends(project_count)

        return {
            "cost_categories": categories,
            "budgets": budgets,
            "budget_line_items": line_items,
            "actual_costs": actual_costs,
            "monthly_cost_trends": monthly_trends,
        }

    def get_hero_project_total_actual(self) -> Decimal:
        """Return the expected total actual spend for Project Alpha.

        Useful for other generators or verification:
        total_budget * variance_factor = 2_000_000 * 1.125 = 2_250_000.
        """
        config = _PROJECT_BUDGET_CONFIGS[0]
        return (config["total_budget"] * config["variance_factor"]).quantize(
            Decimal("0.01")
        )

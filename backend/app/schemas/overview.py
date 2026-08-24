"""Overview dashboard response schemas.

Provides the data contract for the Overview page: portfolio KPIs,
portfolio health (per-project progress + status), and recent activity feed.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OverviewKPIs(BaseModel):
    """Portfolio-level KPI aggregates for the Overview dashboard."""

    total_projects: int = Field(ge=0)
    at_risk_projects: int = Field(ge=0)
    total_budget: Decimal
    open_risks: int = Field(ge=0)


class PortfolioHealthItem(BaseModel):
    """Per-project health summary for the portfolio health section."""

    project_id: UUID
    name: str
    progress: int = Field(ge=0, le=100)
    status: str  # "AT_RISK", "ON_TRACK", "ATTENTION", "DELAYED", "COMPLETED"


class RecentActivityItem(BaseModel):
    """A single entry in the recent activity feed."""

    type: str  # e.g., "source_connected", "document_uploaded", "risk_updated", "project_created"
    description: str
    timestamp: datetime


class OverviewResponse(BaseModel):
    """Full overview dashboard response combining KPIs, health, and activity."""

    kpis: OverviewKPIs
    portfolio_health: list[PortfolioHealthItem]
    recent_activity: list[RecentActivityItem]

    model_config = {"from_attributes": True}

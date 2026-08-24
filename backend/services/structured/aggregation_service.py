"""
Aggregation Service.

Higher-level service for common financial and analytical aggregations.
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from .structured_query_service import StructuredQueryService, QueryResult
from models.structured_data_models import StructuredDataset, StructuredColumn, StructuredRow

logger = logging.getLogger(__name__)


@dataclass
class FinancialSummary:
    """Summary of financial data."""
    total_approved_budget: Optional[float]
    total_forecast_cost: Optional[float]
    total_actual_cost: Optional[float]
    total_cost_variance: Optional[float]
    project_count: int
    source_file: str
    source_sheet: str
    currency: str = "USD"


class AggregationService:
    """
    Service for domain-specific aggregations.
    
    Provides high-level methods for common analytical queries
    on financial, project, and audit data.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.query_service = StructuredQueryService(db)
    
    def get_financial_summary(self, file_name: Optional[str] = None,
                             sheet_name: str = "Financial Health") -> Optional[FinancialSummary]:
        """
        Get a comprehensive financial summary.
        
        Looks for Financial Health or similar financial sheets.
        """
        # Find the financial dataset
        dataset = self.query_service.find_dataset(
            file_name=file_name,
            sheet_name=sheet_name
        )
        
        if not dataset:
            # Try alternative names
            for alt_name in ["Financial", "Finance", "Budget", "Costs"]:
                dataset = self.query_service.find_dataset(sheet_name=alt_name)
                if dataset:
                    break
        
        if not dataset:
            logger.warning(f"No financial dataset found matching '{sheet_name}'")
            return None
        
        # Get currency from column metadata
        currency = "USD"
        currency_col = self.db.query(StructuredColumn).filter(
            StructuredColumn.dataset_id == dataset.id,
            StructuredColumn.is_currency == True
        ).first()
        if currency_col and currency_col.currency_symbol:
            currency = {"$": "USD", "£": "GBP", "€": "EUR"}.get(
                currency_col.currency_symbol, "USD"
            )
        
        # Try to get values from summary row first
        approved = self._get_numeric_value(dataset.id, "approved_budget")
        forecast = self._get_numeric_value(dataset.id, "forecast_total_cost")
        actual = self._get_numeric_value(dataset.id, "actual_cost")
        variance = self._get_numeric_value(dataset.id, "cost_variance")
        
        # Get project count
        count_result = self.query_service.count_rows(dataset.id)
        
        return FinancialSummary(
            total_approved_budget=approved,
            total_forecast_cost=forecast,
            total_actual_cost=actual,
            total_cost_variance=variance,
            project_count=count_result.row_count if count_result.success else 0,
            source_file=dataset.file_name,
            source_sheet=dataset.sheet_name,
            currency=currency
        )
    
    def _get_numeric_value(self, dataset_id: int, column_name: str) -> Optional[float]:
        """Get a numeric value - first try summary, then calculate."""
        # Try summary row first
        summary_result = self.query_service.get_summary_value(dataset_id, column_name)
        if summary_result and summary_result.success and summary_result.data is not None:
            return summary_result.data
        
        # Calculate sum
        sum_result = self.query_service.calculate_sum(dataset_id, column_name)
        if sum_result.success:
            return sum_result.data
        
        return None
    
    def get_project_financial_details(self, project_id: str) -> Optional[dict]:
        """Get financial details for a specific project."""
        # Find financial dataset
        dataset = self.query_service.find_dataset(sheet_name="Financial Health")
        if not dataset:
            dataset = self.query_service.find_dataset(sheet_name="Financial")
        
        if not dataset:
            return None
        
        # Get full row by searching in data
        rows = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset.id,
            StructuredRow.row_type == "data"
        ).all()
        
        for row in rows:
            if row.data.get("project_id") == project_id:
                return {
                    "project_id": project_id,
                    "data": row.data,
                    "source_file": dataset.file_name,
                    "source_sheet": dataset.sheet_name
                }
        
        return None
    
    def get_projects_by_condition(self, column: str, operator: str, 
                                 value: Any, sheet_name: str = "Financial Health") -> list[dict]:
        """
        Get projects matching a condition.
        
        Example: Get projects where approved_budget > 2000000
        """
        dataset = self.query_service.find_dataset(sheet_name=sheet_name)
        if not dataset:
            return []
        
        result = self.query_service.filter_rows(
            dataset.id,
            filter_column=column,
            operator=operator,
            filter_value=value
        )
        
        if result.success:
            return result.data
        
        return []
    
    def get_ranking(self, column: str, ascending: bool = False,
                   limit: int = 5, sheet_name: str = "Financial Health") -> list[dict]:
        """
        Get top/bottom N items by a column value.
        
        Example: Top 5 projects by approved_budget
        """
        dataset = self.query_service.find_dataset(sheet_name=sheet_name)
        if not dataset:
            return []
        
        result = self.query_service.get_all_rows(dataset.id)
        if not result.success:
            return []
        
        # Sort
        try:
            sorted_data = sorted(
                result.data,
                key=lambda x: float(x.get(column, 0) or 0),
                reverse=not ascending
            )
            return sorted_data[:limit]
        except (ValueError, TypeError):
            return result.data[:limit]
    
    def compare_actual_vs_budget(self, sheet_name: str = "Financial Health") -> list[dict]:
        """
        Compare actual cost vs budget for all projects.
        
        Returns list with project_id, approved_budget, actual_cost, variance, variance_pct
        """
        dataset = self.query_service.find_dataset(sheet_name=sheet_name)
        if not dataset:
            return []
        
        result = self.query_service.get_all_rows(dataset.id)
        if not result.success:
            return []
        
        comparison = []
        for row in result.data:
            try:
                budget = float(row.get("approved_budget", 0) or 0)
                actual = float(row.get("actual_cost", 0) or 0)
                variance = float(row.get("cost_variance", 0) or 0)
                
                comparison.append({
                    "project_id": row.get("project_id"),
                    "approved_budget": budget,
                    "actual_cost": actual,
                    "cost_variance": variance,
                    "variance_pct": (variance / budget * 100) if budget > 0 else 0
                })
            except (ValueError, TypeError):
                continue
        
        return comparison

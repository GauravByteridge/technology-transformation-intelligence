"""
Structured Query Service.

Executes queries against structured data stored in the database.
Supports filtering, aggregation, and lookup operations.
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.structured_data_models import (
    StructuredDataset, StructuredColumn, StructuredRow
)

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a structured query."""
    success: bool
    data: Any  # The actual result (value, list, dict)
    row_count: int
    source_dataset: Optional[str]
    source_sheet: Optional[str]
    source_column: Optional[str]
    calculation: Optional[str]  # SUM, AVG, COUNT, etc. or "lookup"
    error: Optional[str] = None
    
    def to_evidence(self) -> dict:
        """Convert to evidence dict for response."""
        return {
            "source_file": self.source_dataset,
            "sheet": self.source_sheet,
            "column": self.source_column,
            "calculation": self.calculation,
            "row_count": self.row_count,
        }


class StructuredQueryService:
    """
    Service for querying structured data.
    
    Provides methods for:
    - Aggregations (SUM, AVG, COUNT, MIN, MAX)
    - Lookups (get specific values)
    - Filtering
    - Retrieving summary rows
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_dataset(self, file_name: Optional[str] = None,
                    sheet_name: Optional[str] = None,
                    table_name: Optional[str] = None) -> Optional[StructuredDataset]:
        """
        Find a dataset by file/sheet/table name.
        
        Uses fuzzy matching if exact match not found.
        """
        query = self.db.query(StructuredDataset)
        
        if file_name:
            # Try exact match first
            dataset = query.filter(
                StructuredDataset.file_name.ilike(f"%{file_name}%")
            ).first()
            if dataset:
                if sheet_name:
                    # Further filter by sheet
                    dataset = query.filter(
                        StructuredDataset.file_name.ilike(f"%{file_name}%"),
                        StructuredDataset.sheet_name.ilike(f"%{sheet_name}%")
                    ).first()
                return dataset
        
        if sheet_name:
            return query.filter(
                StructuredDataset.sheet_name.ilike(f"%{sheet_name}%")
            ).first()
        
        if table_name:
            return query.filter(
                StructuredDataset.table_name.ilike(f"%{table_name}%")
            ).first()
        
        return None
    
    def find_column(self, dataset_id: int, 
                   column_name: str) -> Optional[StructuredColumn]:
        """Find a column by name (fuzzy match)."""
        # Try exact match
        column = self.db.query(StructuredColumn).filter(
            StructuredColumn.dataset_id == dataset_id,
            StructuredColumn.column_name == column_name
        ).first()
        
        if column:
            return column
        
        # Try case-insensitive match
        column = self.db.query(StructuredColumn).filter(
            StructuredColumn.dataset_id == dataset_id,
            StructuredColumn.column_name.ilike(column_name)
        ).first()
        
        if column:
            return column
        
        # Try partial match (for underscored names)
        search_term = column_name.replace("_", "%").replace(" ", "%")
        column = self.db.query(StructuredColumn).filter(
            StructuredColumn.dataset_id == dataset_id,
            StructuredColumn.column_name.ilike(f"%{search_term}%")
        ).first()
        
        return column
    
    def get_summary_value(self, dataset_id: int, 
                         column_name: str) -> Optional[QueryResult]:
        """
        Get a value from a summary row.
        
        First checks for explicit summary rows (TOTAL, PORTFOLIO TOTAL, etc.)
        """
        # Find summary row
        summary_row = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset_id,
            StructuredRow.row_type == "summary"
        ).first()
        
        if not summary_row:
            return None
        
        # Get the column
        column = self.find_column(dataset_id, column_name)
        if not column:
            return None
        
        # Extract value from summary row
        data = summary_row.data
        value = data.get(column.column_name)
        
        if value is None:
            return None
        
        # Get dataset info
        dataset = self.db.query(StructuredDataset).get(dataset_id)
        
        return QueryResult(
            success=True,
            data=value,
            row_count=1,
            source_dataset=dataset.file_name if dataset else None,
            source_sheet=dataset.sheet_name if dataset else None,
            source_column=column.column_name,
            calculation=f"Summary row: {summary_row.row_label or 'TOTAL'}"
        )
    
    def calculate_sum(self, dataset_id: int, 
                     column_name: str,
                     filter_column: Optional[str] = None,
                     filter_value: Optional[Any] = None) -> QueryResult:
        """
        Calculate SUM of a column.
        
        First checks for summary row, then calculates if not found.
        """
        # Try to get from summary row first
        summary_result = self.get_summary_value(dataset_id, column_name)
        if summary_result and summary_result.success and summary_result.data is not None:
            return summary_result
        
        # Get the column info
        column = self.find_column(dataset_id, column_name)
        if not column:
            return QueryResult(
                success=False,
                data=None,
                row_count=0,
                source_dataset=None,
                source_sheet=None,
                source_column=column_name,
                calculation=None,
                error=f"Column '{column_name}' not found"
            )
        
        # Get data rows
        query = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset_id,
            StructuredRow.row_type == "data"
        )
        
        rows = query.all()
        
        # Calculate sum
        total = 0.0
        valid_count = 0
        
        for row in rows:
            value = row.data.get(column.column_name)
            if value is not None:
                try:
                    total += float(value)
                    valid_count += 1
                except (ValueError, TypeError):
                    continue
        
        if valid_count == 0:
            return QueryResult(
                success=False,
                data=None,
                row_count=0,
                source_dataset=None,
                source_sheet=None,
                source_column=column.column_name,
                calculation="SUM",
                error="No valid numeric values found"
            )
        
        # Get dataset info
        dataset = self.db.query(StructuredDataset).get(dataset_id)
        
        return QueryResult(
            success=True,
            data=total,
            row_count=valid_count,
            source_dataset=dataset.file_name if dataset else None,
            source_sheet=dataset.sheet_name if dataset else None,
            source_column=column.column_name,
            calculation=f"SUM({column.column_name})"
        )
    
    def calculate_average(self, dataset_id: int, 
                         column_name: str) -> QueryResult:
        """Calculate AVERAGE of a column."""
        column = self.find_column(dataset_id, column_name)
        if not column:
            return QueryResult(
                success=False, data=None, row_count=0,
                source_dataset=None, source_sheet=None,
                source_column=column_name, calculation=None,
                error=f"Column '{column_name}' not found"
            )
        
        rows = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset_id,
            StructuredRow.row_type == "data"
        ).all()
        
        total = 0.0
        count = 0
        
        for row in rows:
            value = row.data.get(column.column_name)
            if value is not None:
                try:
                    total += float(value)
                    count += 1
                except (ValueError, TypeError):
                    continue
        
        if count == 0:
            return QueryResult(
                success=False, data=None, row_count=0,
                source_dataset=None, source_sheet=None,
                source_column=column.column_name, calculation="AVG",
                error="No valid numeric values found"
            )
        
        dataset = self.db.query(StructuredDataset).get(dataset_id)
        
        return QueryResult(
            success=True,
            data=total / count,
            row_count=count,
            source_dataset=dataset.file_name if dataset else None,
            source_sheet=dataset.sheet_name if dataset else None,
            source_column=column.column_name,
            calculation=f"AVG({column.column_name})"
        )
    
    def get_max(self, dataset_id: int, column_name: str) -> QueryResult:
        """Get MAX value and the row containing it."""
        column = self.find_column(dataset_id, column_name)
        if not column:
            return QueryResult(
                success=False, data=None, row_count=0,
                source_dataset=None, source_sheet=None,
                source_column=column_name, calculation=None,
                error=f"Column '{column_name}' not found"
            )
        
        rows = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset_id,
            StructuredRow.row_type == "data"
        ).all()
        
        max_value = None
        max_row = None
        
        for row in rows:
            value = row.data.get(column.column_name)
            if value is not None:
                try:
                    num_val = float(value)
                    if max_value is None or num_val > max_value:
                        max_value = num_val
                        max_row = row
                except (ValueError, TypeError):
                    continue
        
        if max_value is None:
            return QueryResult(
                success=False, data=None, row_count=0,
                source_dataset=None, source_sheet=None,
                source_column=column.column_name, calculation="MAX",
                error="No valid numeric values found"
            )
        
        dataset = self.db.query(StructuredDataset).get(dataset_id)
        
        return QueryResult(
            success=True,
            data={"value": max_value, "row": max_row.data if max_row else None},
            row_count=1,
            source_dataset=dataset.file_name if dataset else None,
            source_sheet=dataset.sheet_name if dataset else None,
            source_column=column.column_name,
            calculation=f"MAX({column.column_name})"
        )
    
    def get_min(self, dataset_id: int, column_name: str) -> QueryResult:
        """Get MIN value and the row containing it."""
        column = self.find_column(dataset_id, column_name)
        if not column:
            return QueryResult(
                success=False, data=None, row_count=0,
                source_dataset=None, source_sheet=None,
                source_column=column_name, calculation=None,
                error=f"Column '{column_name}' not found"
            )
        
        rows = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset_id,
            StructuredRow.row_type == "data"
        ).all()
        
        min_value = None
        min_row = None
        
        for row in rows:
            value = row.data.get(column.column_name)
            if value is not None:
                try:
                    num_val = float(value)
                    if min_value is None or num_val < min_value:
                        min_value = num_val
                        min_row = row
                except (ValueError, TypeError):
                    continue
        
        if min_value is None:
            return QueryResult(
                success=False, data=None, row_count=0,
                source_dataset=None, source_sheet=None,
                source_column=column.column_name, calculation="MIN",
                error="No valid numeric values found"
            )
        
        dataset = self.db.query(StructuredDataset).get(dataset_id)
        
        return QueryResult(
            success=True,
            data={"value": min_value, "row": min_row.data if min_row else None},
            row_count=1,
            source_dataset=dataset.file_name if dataset else None,
            source_sheet=dataset.sheet_name if dataset else None,
            source_column=column.column_name,
            calculation=f"MIN({column.column_name})"
        )
    
    def count_rows(self, dataset_id: int,
                  filter_column: Optional[str] = None,
                  filter_value: Optional[Any] = None) -> QueryResult:
        """Count rows, optionally with filter."""
        query = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset_id,
            StructuredRow.row_type == "data"
        )
        
        if filter_column and filter_value is not None:
            # Filter in application since data is JSON
            rows = query.all()
            count = sum(1 for r in rows if r.data.get(filter_column) == filter_value)
        else:
            count = query.count()
        
        dataset = self.db.query(StructuredDataset).get(dataset_id)
        
        return QueryResult(
            success=True,
            data=count,
            row_count=count,
            source_dataset=dataset.file_name if dataset else None,
            source_sheet=dataset.sheet_name if dataset else None,
            source_column=None,
            calculation="COUNT"
        )
    
    def lookup_value(self, dataset_id: int, 
                    lookup_column: str, lookup_value: Any,
                    return_column: str) -> QueryResult:
        """
        Lookup a specific value.
        
        Example: Get actual_cost where project_id = 'PRJ-005'
        """
        rows = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset_id,
            StructuredRow.row_type == "data"
        ).all()
        
        for row in rows:
            if row.data.get(lookup_column) == lookup_value:
                value = row.data.get(return_column)
                dataset = self.db.query(StructuredDataset).get(dataset_id)
                
                return QueryResult(
                    success=True,
                    data=value,
                    row_count=1,
                    source_dataset=dataset.file_name if dataset else None,
                    source_sheet=dataset.sheet_name if dataset else None,
                    source_column=return_column,
                    calculation=f"LOOKUP({lookup_column}='{lookup_value}')"
                )
        
        return QueryResult(
            success=False,
            data=None,
            row_count=0,
            source_dataset=None,
            source_sheet=None,
            source_column=return_column,
            calculation=None,
            error=f"No row found with {lookup_column} = '{lookup_value}'"
        )
    
    def get_all_rows(self, dataset_id: int,
                    columns: Optional[list[str]] = None) -> QueryResult:
        """Get all data rows from a dataset."""
        rows = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset_id,
            StructuredRow.row_type == "data"
        ).all()
        
        data = []
        for row in rows:
            if columns:
                data.append({k: v for k, v in row.data.items() if k in columns})
            else:
                data.append(row.data)
        
        dataset = self.db.query(StructuredDataset).get(dataset_id)
        
        return QueryResult(
            success=True,
            data=data,
            row_count=len(data),
            source_dataset=dataset.file_name if dataset else None,
            source_sheet=dataset.sheet_name if dataset else None,
            source_column=None,
            calculation="SELECT *"
        )
    
    def filter_rows(self, dataset_id: int,
                   filter_column: str, operator: str, filter_value: Any,
                   return_columns: Optional[list[str]] = None) -> QueryResult:
        """
        Filter rows by condition.
        
        Operators: =, !=, >, <, >=, <=, contains
        """
        rows = self.db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset_id,
            StructuredRow.row_type == "data"
        ).all()
        
        filtered = []
        
        for row in rows:
            value = row.data.get(filter_column)
            if value is None:
                continue
            
            match = False
            try:
                if operator == "=":
                    match = value == filter_value
                elif operator == "!=":
                    match = value != filter_value
                elif operator == ">":
                    match = float(value) > float(filter_value)
                elif operator == "<":
                    match = float(value) < float(filter_value)
                elif operator == ">=":
                    match = float(value) >= float(filter_value)
                elif operator == "<=":
                    match = float(value) <= float(filter_value)
                elif operator == "contains":
                    match = str(filter_value).lower() in str(value).lower()
            except (ValueError, TypeError):
                continue
            
            if match:
                if return_columns:
                    filtered.append({k: v for k, v in row.data.items() if k in return_columns})
                else:
                    filtered.append(row.data)
        
        dataset = self.db.query(StructuredDataset).get(dataset_id)
        
        return QueryResult(
            success=True,
            data=filtered,
            row_count=len(filtered),
            source_dataset=dataset.file_name if dataset else None,
            source_sheet=dataset.sheet_name if dataset else None,
            source_column=filter_column,
            calculation=f"WHERE {filter_column} {operator} {filter_value}"
        )
    
    def list_datasets(self) -> list[dict]:
        """List all available datasets with their columns."""
        datasets = self.db.query(StructuredDataset).all()
        
        result = []
        for ds in datasets:
            columns = self.db.query(StructuredColumn).filter(
                StructuredColumn.dataset_id == ds.id
            ).all()
            
            result.append({
                "id": ds.id,
                "file_name": ds.file_name,
                "sheet_name": ds.sheet_name,
                "row_count": ds.row_count,
                "columns": [
                    {
                        "name": c.column_name,
                        "type": c.data_type,
                        "is_currency": c.is_currency
                    }
                    for c in columns
                ]
            })
        
        return result
    
    def get_dataset_schema(self, dataset_id: int) -> Optional[dict]:
        """Get detailed schema for a dataset."""
        dataset = self.db.query(StructuredDataset).get(dataset_id)
        if not dataset:
            return None
        
        columns = self.db.query(StructuredColumn).filter(
            StructuredColumn.dataset_id == dataset_id
        ).order_by(StructuredColumn.column_index).all()
        
        return {
            "id": dataset.id,
            "file_name": dataset.file_name,
            "sheet_name": dataset.sheet_name,
            "table_name": dataset.table_name,
            "document_title": dataset.document_title,
            "row_count": dataset.row_count,
            "columns": [
                {
                    "name": c.column_name,
                    "type": c.data_type,
                    "python_type": c.python_type,
                    "is_currency": c.is_currency,
                    "currency_symbol": c.currency_symbol,
                    "is_percentage": c.is_percentage
                }
                for c in columns
            ]
        }

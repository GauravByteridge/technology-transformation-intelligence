"""
Query Router Service.

Routes queries to the appropriate processing pipeline based on classification:
- STRUCTURED: SQL-based queries against structured data tables
- UNSTRUCTURED: Vector search RAG pipeline
- HYBRID: Combination of both
"""

import logging
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from .query_classifier import QueryClassifier, QueryClassification, QueryType
from services.structured.structured_query_service import StructuredQueryService, QueryResult
from services.structured.aggregation_service import AggregationService
from models.structured_data_models import StructuredDataset, QueryLog

logger = logging.getLogger(__name__)


@dataclass
class RoutedResult:
    """Result from query routing."""
    success: bool
    pipeline: str  # "structured", "unstructured", "hybrid"
    
    # Structured results
    structured_result: Optional[QueryResult] = None
    
    # Unstructured context for LLM
    context_chunks: list[str] = None
    context_sources: list[str] = None
    
    # Combined answer hint for LLM
    data_summary: Optional[str] = None
    evidence: Optional[dict] = None
    
    # For logging
    classification: Optional[QueryClassification] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.context_chunks is None:
            self.context_chunks = []
        if self.context_sources is None:
            self.context_sources = []


class QueryRouter:
    """
    Routes queries based on classification and executes appropriate pipeline.
    
    For STRUCTURED queries:
    - Executes SQL-like operations against structured data
    - Returns exact numerical values
    
    For UNSTRUCTURED queries:
    - Performs vector search and retrieves relevant chunks
    - Passes to LLM for answer generation
    
    For HYBRID queries:
    - Executes structured query first
    - Retrieves relevant document context
    - Combines both for LLM
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.classifier = QueryClassifier()
        self.query_service = StructuredQueryService(db)
        self.aggregation_service = AggregationService(db)
    
    def route(self, question: str) -> RoutedResult:
        """
        Route a question to the appropriate pipeline.
        
        Args:
            question: User's question
            
        Returns:
            RoutedResult with data and metadata
        """
        # Step 1: Classify the question
        classification = self.classifier.classify(question)
        
        logger.info(
            f"Query classified as {classification.query_type.value} "
            f"(confidence: {classification.confidence:.2f})"
        )
        
        # Step 2: Route based on classification
        if classification.query_type == QueryType.STRUCTURED:
            result = self._execute_structured_query(classification, question)
        elif classification.query_type == QueryType.UNSTRUCTURED:
            result = self._execute_unstructured_query(classification, question)
        else:  # HYBRID
            result = self._execute_hybrid_query(classification, question)
        
        result.classification = classification
        
        # Step 3: Log the query
        self._log_query(question, classification, result)
        
        return result
    
    def _execute_structured_query(self, classification: QueryClassification,
                                 question: str) -> RoutedResult:
        """Execute a structured data query."""
        
        # Find the target dataset
        dataset = None
        if classification.target_dataset:
            dataset = self.query_service.find_dataset(
                sheet_name=classification.target_dataset
            )
        
        if not dataset:
            # Try to find any financial dataset
            dataset = self.query_service.find_dataset(sheet_name="Financial Health")
        
        if not dataset:
            # List available datasets
            available = self.query_service.list_datasets()
            if available:
                dataset_names = [f"{d['file_name']}/{d['sheet_name']}" for d in available]
                return RoutedResult(
                    success=False,
                    pipeline="structured",
                    error=f"Could not find target dataset '{classification.target_dataset}'. "
                          f"Available datasets: {', '.join(dataset_names)}"
                )
            return RoutedResult(
                success=False,
                pipeline="structured",
                error="No structured datasets found. Please upload structured data files."
            )
        
        # Execute based on operation
        result = None
        
        if classification.operation == "sum":
            # For sum operations, find the target column
            column = self._find_target_column(classification.target_columns, dataset.id)
            if column:
                result = self.query_service.calculate_sum(dataset.id, column)
        
        elif classification.operation == "avg":
            column = self._find_target_column(classification.target_columns, dataset.id)
            if column:
                result = self.query_service.calculate_average(dataset.id, column)
        
        elif classification.operation == "max":
            column = self._find_target_column(classification.target_columns, dataset.id)
            if column:
                result = self.query_service.get_max(dataset.id, column)
        
        elif classification.operation == "min":
            column = self._find_target_column(classification.target_columns, dataset.id)
            if column:
                result = self.query_service.get_min(dataset.id, column)
        
        elif classification.operation == "count":
            result = self.query_service.count_rows(dataset.id)
        
        elif classification.operation == "lookup":
            # Try to extract lookup parameters from question
            result = self._execute_lookup(classification, dataset.id, question)
        
        elif classification.operation == "filter":
            result = self._execute_filter(classification, dataset.id, question)
        
        if result and result.success:
            # Format the data summary
            data_summary = self._format_structured_result(result, classification)
            
            return RoutedResult(
                success=True,
                pipeline="structured",
                structured_result=result,
                data_summary=data_summary,
                evidence=result.to_evidence()
            )
        
        # Fallback - return dataset info
        schema = self.query_service.get_dataset_schema(dataset.id)
        return RoutedResult(
            success=False,
            pipeline="structured",
            error=result.error if result else "Could not execute structured query",
            data_summary=f"Dataset '{dataset.sheet_name}' has columns: "
                        f"{', '.join(c['name'] for c in schema['columns'])}" if schema else None
        )
    
    def _execute_unstructured_query(self, classification: QueryClassification,
                                   question: str) -> RoutedResult:
        """
        Mark query for unstructured RAG processing.
        
        Actual RAG retrieval is done by the Strands agent tools.
        This just returns the classification for the agent to use.
        """
        return RoutedResult(
            success=True,
            pipeline="unstructured",
            data_summary=None,
            context_chunks=[],  # Agent will retrieve these
            context_sources=[]
        )
    
    def _execute_hybrid_query(self, classification: QueryClassification,
                             question: str) -> RoutedResult:
        """Execute both structured and unstructured queries."""
        
        # First, try structured
        structured_result = self._execute_structured_query(classification, question)
        
        # Mark as hybrid - agent will add unstructured context
        return RoutedResult(
            success=structured_result.success,
            pipeline="hybrid",
            structured_result=structured_result.structured_result,
            data_summary=structured_result.data_summary,
            evidence=structured_result.evidence,
            context_chunks=[],  # Agent will add
            context_sources=[]
        )
    
    def _find_target_column(self, columns: list[str], 
                           dataset_id: int) -> Optional[str]:
        """Find the first valid column from the list."""
        for col in columns:
            found = self.query_service.find_column(dataset_id, col)
            if found:
                return found.column_name
        
        # If no explicit column found, try to infer from common financial columns
        for default_col in ["approved_budget", "actual_cost", "cost_variance", "forecast_total_cost"]:
            found = self.query_service.find_column(dataset_id, default_col)
            if found:
                return found.column_name
        
        return None
    
    def _execute_lookup(self, classification: QueryClassification,
                       dataset_id: int, question: str) -> Optional[QueryResult]:
        """Execute a lookup query."""
        import re
        
        # Try to extract project ID from question
        project_match = re.search(r'PRJ-\d+', question, re.IGNORECASE)
        if project_match:
            project_id = project_match.group().upper()
            
            # Determine which column to return
            return_col = self._find_target_column(classification.target_columns, dataset_id)
            if return_col:
                return self.query_service.lookup_value(
                    dataset_id,
                    lookup_column="project_id",
                    lookup_value=project_id,
                    return_column=return_col
                )
        
        return None
    
    def _execute_filter(self, classification: QueryClassification,
                       dataset_id: int, question: str) -> Optional[QueryResult]:
        """Execute a filter query."""
        import re
        
        # Try to extract filter conditions from question
        # e.g., "above 2 million", "greater than 1000000"
        
        column = self._find_target_column(classification.target_columns, dataset_id)
        if not column:
            return None
        
        # Look for numeric comparison
        amount_match = re.search(r'(above|below|more than|less than|greater than|over|under)\s*\$?([\d,]+)\s*(million|m)?', question.lower())
        
        if amount_match:
            direction = amount_match.group(1)
            amount = float(amount_match.group(2).replace(',', ''))
            unit = amount_match.group(3)
            
            if unit and unit.lower() in ('million', 'm'):
                amount *= 1_000_000
            
            operator = ">" if direction in ("above", "more than", "greater than", "over") else "<"
            
            return self.query_service.filter_rows(
                dataset_id,
                filter_column=column,
                operator=operator,
                filter_value=amount
            )
        
        return None
    
    def _format_structured_result(self, result: QueryResult,
                                 classification: QueryClassification) -> str:
        """Format structured query result as a data summary."""
        if not result.success:
            return None
        
        data = result.data
        
        # Format based on data type
        if isinstance(data, (int, float)):
            # Numeric result - format as currency if relevant
            if result.source_column and any(
                kw in result.source_column.lower() 
                for kw in ["budget", "cost", "expense", "variance"]
            ):
                formatted = f"${data:,.2f}" if isinstance(data, float) else f"${data:,}"
            else:
                formatted = f"{data:,.2f}" if isinstance(data, float) else f"{data:,}"
            
            return (
                f"EXACT VALUE: {formatted}\n"
                f"Source: {result.source_dataset}\n"
                f"Sheet: {result.source_sheet}\n"
                f"Column: {result.source_column}\n"
                f"Calculation: {result.calculation}\n"
                f"Records: {result.row_count}"
            )
        
        elif isinstance(data, dict):
            # Single row result
            if "value" in data and "row" in data:
                # MAX/MIN result
                formatted_value = f"${data['value']:,.2f}" if data['value'] else "N/A"
                row_info = data.get('row', {})
                return (
                    f"EXACT VALUE: {formatted_value}\n"
                    f"Row: {row_info}\n"
                    f"Source: {result.source_dataset}/{result.source_sheet}"
                )
            return f"Data: {data}"
        
        elif isinstance(data, list):
            # Multiple rows
            count = len(data)
            preview = data[:3] if count > 3 else data
            return (
                f"Found {count} matching records\n"
                f"Preview: {preview}\n"
                f"Source: {result.source_dataset}/{result.source_sheet}"
            )
        
        return str(data)
    
    def _log_query(self, question: str, classification: QueryClassification,
                  result: RoutedResult) -> None:
        """Log query for analysis."""
        try:
            log = QueryLog(
                question=question,
                query_type=classification.query_type.value,
                confidence=classification.confidence,
                pipeline_used=result.pipeline,
                target_dataset=classification.target_dataset,
                target_columns=classification.target_columns if classification.target_columns else None,
                answer=result.data_summary,
                sources=[result.evidence] if result.evidence else None,
                validated=result.success
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log query: {e}")

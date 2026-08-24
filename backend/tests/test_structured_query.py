"""
Tests for the structured data query pipeline.

These tests verify that numerical/financial questions are answered
accurately using the structured data pipeline, not vector search.
"""

import pytest
from db.database import SessionLocal
from models.structured_data_models import StructuredDataset, StructuredRow
from services.structured.structured_query_service import StructuredQueryService
from services.structured.aggregation_service import AggregationService
from services.ai.query_classifier import QueryClassifier, QueryType


class TestQueryClassifier:
    """Tests for query classification."""
    
    @pytest.fixture
    def classifier(self):
        return QueryClassifier()
    
    def test_classifies_total_budget_as_structured(self, classifier):
        """Total budget question should be classified as STRUCTURED."""
        result = classifier.classify("What is the portfolio total approved budget for Financial Health?")
        assert result.query_type == QueryType.STRUCTURED
        assert result.operation == "sum"
        assert "approved_budget" in result.target_columns
    
    def test_classifies_specific_cost_as_structured(self, classifier):
        """Specific project cost question should be STRUCTURED."""
        result = classifier.classify("What is the actual cost for PRJ-005?")
        assert result.query_type == QueryType.STRUCTURED
    
    def test_classifies_highest_budget_as_structured(self, classifier):
        """Highest budget question should be STRUCTURED with max operation."""
        result = classifier.classify("Which project has the highest approved budget?")
        assert result.query_type == QueryType.STRUCTURED
        assert result.operation == "max"
    
    def test_classifies_audit_findings_as_unstructured(self, classifier):
        """Audit findings question should be UNSTRUCTURED."""
        result = classifier.classify("What are the major audit findings?")
        assert result.query_type == QueryType.UNSTRUCTURED
    
    def test_classifies_brd_content_as_unstructured(self, classifier):
        """BRD content question should be UNSTRUCTURED."""
        result = classifier.classify("What does the BRD say about budget approval?")
        assert result.query_type == QueryType.UNSTRUCTURED
    
    def test_classifies_hybrid_query(self, classifier):
        """Question requiring both data types should be HYBRID."""
        result = classifier.classify("Which projects have high costs and unresolved audit issues?")
        assert result.query_type == QueryType.HYBRID


class TestStructuredQueryService:
    """Tests for structured data queries."""
    
    @pytest.fixture
    def db(self):
        db = SessionLocal()
        yield db
        db.close()
    
    @pytest.fixture
    def query_service(self, db):
        return StructuredQueryService(db)
    
    def test_find_financial_health_dataset(self, query_service):
        """Should find the Financial Health dataset."""
        dataset = query_service.find_dataset(sheet_name="Financial Health")
        assert dataset is not None
        assert dataset.sheet_name == "Financial Health"
        assert dataset.row_count == 15
    
    def test_calculate_sum_approved_budget(self, query_service):
        """SUM(approved_budget) should return $33,800,000."""
        dataset = query_service.find_dataset(sheet_name="Financial Health")
        assert dataset is not None
        
        result = query_service.calculate_sum(dataset.id, "approved_budget")
        assert result.success
        assert result.data == 33800000.0  # $33,800,000
        assert result.row_count == 15
        assert result.calculation == "SUM(approved_budget)"
    
    def test_calculate_sum_actual_cost(self, query_service):
        """SUM(actual_cost) should return $22,750,000."""
        dataset = query_service.find_dataset(sheet_name="Financial Health")
        assert dataset is not None
        
        result = query_service.calculate_sum(dataset.id, "actual_cost")
        assert result.success
        assert result.data == 22750000.0  # $22,750,000
    
    def test_get_max_approved_budget(self, query_service):
        """MAX(approved_budget) should return PRJ-005 with $4,500,000."""
        dataset = query_service.find_dataset(sheet_name="Financial Health")
        assert dataset is not None
        
        result = query_service.get_max(dataset.id, "approved_budget")
        assert result.success
        assert result.data["value"] == 4500000.0
        assert result.data["row"]["project_id"] == "PRJ-005"
    
    def test_lookup_specific_project(self, query_service):
        """Lookup PRJ-005's actual cost should return $2,950,000."""
        dataset = query_service.find_dataset(sheet_name="Financial Health")
        assert dataset is not None
        
        result = query_service.lookup_value(
            dataset.id,
            lookup_column="project_id",
            lookup_value="PRJ-005",
            return_column="actual_cost"
        )
        assert result.success
        assert result.data == 2950000.0  # $2,950,000
    
    def test_filter_projects_above_budget(self, query_service):
        """Filter projects with budget > $3,000,000."""
        dataset = query_service.find_dataset(sheet_name="Financial Health")
        assert dataset is not None
        
        result = query_service.filter_rows(
            dataset.id,
            filter_column="approved_budget",
            operator=">",
            filter_value=3000000
        )
        assert result.success
        assert result.row_count == 2  # PRJ-005 ($4.5M) and PRJ-008 ($3.2M)


class TestAggregationService:
    """Tests for high-level aggregation functions."""
    
    @pytest.fixture
    def db(self):
        db = SessionLocal()
        yield db
        db.close()
    
    @pytest.fixture
    def agg_service(self, db):
        return AggregationService(db)
    
    def test_get_financial_summary(self, agg_service):
        """Financial summary should return correct portfolio totals."""
        summary = agg_service.get_financial_summary()
        assert summary is not None
        assert summary.total_approved_budget == 33800000.0
        assert summary.total_actual_cost == 22750000.0
        assert summary.project_count == 15
        assert summary.source_sheet == "Financial Health"
    
    def test_get_project_financial_details(self, agg_service):
        """Should return correct details for specific project."""
        details = agg_service.get_project_financial_details("PRJ-001")
        assert details is not None
        assert details["data"]["approved_budget"] == 2400000.0
        assert details["data"]["actual_cost"] == 1750000.0


class TestDataIntegrity:
    """Tests to verify data was ingested correctly."""
    
    @pytest.fixture
    def db(self):
        db = SessionLocal()
        yield db
        db.close()
    
    def test_financial_health_has_15_projects(self, db):
        """Financial Health should have exactly 15 data rows."""
        dataset = db.query(StructuredDataset).filter(
            StructuredDataset.sheet_name == "Financial Health"
        ).first()
        
        assert dataset is not None
        
        data_rows = db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset.id,
            StructuredRow.row_type == "data"
        ).count()
        
        assert data_rows == 15
    
    def test_financial_health_has_summary_row(self, db):
        """Financial Health should have a summary row."""
        dataset = db.query(StructuredDataset).filter(
            StructuredDataset.sheet_name == "Financial Health"
        ).first()
        
        summary = db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset.id,
            StructuredRow.row_type == "summary"
        ).first()
        
        assert summary is not None
        assert "TOTAL" in summary.row_label.upper() or "AVERAGE" in summary.row_label.upper()
    
    def test_budget_values_are_numeric(self, db):
        """All approved_budget values should be numeric (not strings)."""
        dataset = db.query(StructuredDataset).filter(
            StructuredDataset.sheet_name == "Financial Health"
        ).first()
        
        rows = db.query(StructuredRow).filter(
            StructuredRow.dataset_id == dataset.id,
            StructuredRow.row_type == "data"
        ).all()
        
        for row in rows:
            budget = row.data.get("approved_budget")
            assert budget is not None
            assert isinstance(budget, (int, float)), f"Budget should be numeric, got {type(budget)}"
            assert budget > 0

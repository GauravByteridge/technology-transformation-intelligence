"""Unit tests for GroundednessClassifier."""

import pytest

from app.ai.groundedness import GroundednessClassifier


@pytest.fixture
def classifier() -> GroundednessClassifier:
    return GroundednessClassifier()


class TestClassify:
    """Tests for classify() — full claim classification with evidence context."""

    def test_retrieved_fact_with_currency(self, classifier: GroundednessClassifier):
        """Claim with currency value is classified as retrieved_fact."""
        result = classifier.classify(
            claim_text="Actual cost = $1.14M",
            evidence_items=[{"excerpt": "actual_cost: 1140000"}],
            tool_results=[{"rows": [{"actual_cost": 1140000}]}],
        )
        assert result == "retrieved_fact"

    def test_retrieved_fact_with_date(self, classifier: GroundednessClassifier):
        """Claim with a date value is classified as retrieved_fact."""
        result = classifier.classify(
            claim_text="The project started on 2024-01-15",
            evidence_items=[{"excerpt": "start_date: 2024-01-15"}],
            tool_results=[],
        )
        assert result == "retrieved_fact"

    def test_derived_calculation_with_percentage(self, classifier: GroundednessClassifier):
        """Claim with percentage value is classified as derived_calculation."""
        result = classifier.classify(
            claim_text="The project is 14% over budget",
            evidence_items=[{"excerpt": "budget: 1000000, actual_cost: 1140000"}],
            tool_results=[],
        )
        assert result == "derived_calculation"

    def test_derived_calculation_with_variance_keyword(self, classifier: GroundednessClassifier):
        """Claim with variance keyword and number is derived_calculation."""
        result = classifier.classify(
            claim_text="Budget variance is 140000",
            evidence_items=[],
            tool_results=[],
        )
        assert result == "derived_calculation"

    def test_ai_explanation_no_data(self, classifier: GroundednessClassifier):
        """Claim with reasoning but no data values is ai_explanation."""
        result = classifier.classify(
            claim_text="This indicates the project is at risk",
            evidence_items=[],
            tool_results=[],
        )
        assert result == "ai_explanation"

    def test_ai_explanation_interpretation(self, classifier: GroundednessClassifier):
        """Interpretive/synthesis claim is ai_explanation."""
        result = classifier.classify(
            claim_text="The team should consider reallocating resources to mitigate this risk",
            evidence_items=[],
            tool_results=[],
        )
        assert result == "ai_explanation"

    def test_empty_claim_is_ai_explanation(self, classifier: GroundednessClassifier):
        """Empty claim text defaults to ai_explanation."""
        result = classifier.classify(
            claim_text="",
            evidence_items=[],
            tool_results=[],
        )
        assert result == "ai_explanation"

    def test_retrieved_fact_with_matching_numbers_in_evidence(
        self, classifier: GroundednessClassifier
    ):
        """Claim with numbers that match evidence data is retrieved_fact."""
        result = classifier.classify(
            claim_text="The budget is 1000000 and there are 5 team members",
            evidence_items=[{"excerpt": "budget=1000000, team_size=5"}],
            tool_results=[],
        )
        assert result == "retrieved_fact"

    def test_derived_calculation_over_budget(self, classifier: GroundednessClassifier):
        """Claim stating 'over budget' with a number is derived_calculation."""
        result = classifier.classify(
            claim_text="Project is $140K over budget",
            evidence_items=[],
            tool_results=[],
        )
        # "over budget" is a calculation keyword, and there's a currency amount
        # Currency detected first → could be retrieved_fact, but "over budget"
        # with a number triggers calculation
        assert result == "derived_calculation"


class TestClassifyEvidenceItem:
    """Tests for classify_evidence_item() — single evidence item classification."""

    def test_retrieved_fact_with_currency_in_excerpt(
        self, classifier: GroundednessClassifier
    ):
        """Evidence item with currency values is retrieved_fact."""
        result = classifier.classify_evidence_item(
            {"excerpt": "actual_cost: $1,140,000, budget: $1,000,000"}
        )
        assert result == "retrieved_fact"

    def test_retrieved_fact_with_date_in_excerpt(
        self, classifier: GroundednessClassifier
    ):
        """Evidence item with date values is retrieved_fact."""
        result = classifier.classify_evidence_item(
            {"excerpt": "start_date: 2024-01-15, end_date: 2024-12-31"}
        )
        assert result == "retrieved_fact"

    def test_derived_calculation_with_percentage(
        self, classifier: GroundednessClassifier
    ):
        """Evidence item with percentage is derived_calculation."""
        result = classifier.classify_evidence_item(
            {"excerpt": "Budget utilization: 114%"}
        )
        assert result == "derived_calculation"

    def test_derived_calculation_with_variance(
        self, classifier: GroundednessClassifier
    ):
        """Evidence item mentioning variance with a number is derived_calculation."""
        result = classifier.classify_evidence_item(
            {"excerpt": "Cost variance: 140000"}
        )
        assert result == "derived_calculation"

    def test_ai_explanation_narrative_text(self, classifier: GroundednessClassifier):
        """Evidence item with only narrative text is ai_explanation."""
        result = classifier.classify_evidence_item(
            {"excerpt": "The project team discussed potential risks during the meeting"}
        )
        assert result == "ai_explanation"

    def test_empty_excerpt_with_records_summary(
        self, classifier: GroundednessClassifier
    ):
        """Evidence item without excerpt but with records_summary is retrieved_fact."""
        result = classifier.classify_evidence_item(
            {"excerpt": "", "records_summary": {"budget": 1000000, "actual_cost": 1140000}}
        )
        assert result == "retrieved_fact"

    def test_empty_excerpt_no_data_is_ai_explanation(
        self, classifier: GroundednessClassifier
    ):
        """Evidence item with no excerpt and no records is ai_explanation."""
        result = classifier.classify_evidence_item({"excerpt": ""})
        assert result == "ai_explanation"

    def test_retrieved_fact_multiple_numbers(
        self, classifier: GroundednessClassifier
    ):
        """Evidence item with multiple distinct numbers is retrieved_fact."""
        result = classifier.classify_evidence_item(
            {"excerpt": "team_size: 12, active_tasks: 45, completed: 30"}
        )
        assert result == "retrieved_fact"

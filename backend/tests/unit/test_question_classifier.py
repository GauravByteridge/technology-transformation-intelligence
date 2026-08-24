"""
Unit tests for QuestionClassifier.

Verifies:
- Deterministic classification: same input always yields same output
- QUALITATIVE keyword detection
- QUANTITATIVE keyword detection
- HYBRID when both keyword sets match
- QUALITATIVE as default fallback when no keywords match
- Case-insensitive matching
"""

import pytest

from app.ai.question_classifier import QuestionClassifier, QuestionIntent


@pytest.fixture
def classifier() -> QuestionClassifier:
    return QuestionClassifier()


class TestQuestionIntentEnum:
    """Verify enum values are stable."""

    def test_qualitative_value(self) -> None:
        assert QuestionIntent.QUALITATIVE.value == "qualitative"

    def test_quantitative_value(self) -> None:
        assert QuestionIntent.QUANTITATIVE.value == "quantitative"

    def test_hybrid_value(self) -> None:
        assert QuestionIntent.HYBRID.value == "hybrid"

    def test_enum_has_exactly_three_members(self) -> None:
        assert len(QuestionIntent) == 3


class TestQualitativeClassification:
    """Questions with only qualitative keywords → QUALITATIVE."""

    def test_risk_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("What are the key risks for this project?")
        assert result == QuestionIntent.QUALITATIVE

    def test_audit_finding_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("Describe the audit findings from Q3")
        assert result == QuestionIntent.QUALITATIVE

    def test_recommendation_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("What is the recommendation for the next phase?")
        assert result == QuestionIntent.QUALITATIVE

    def test_why_question(self, classifier: QuestionClassifier) -> None:
        # "Why is" is a hybrid phrase — questions starting with "Why is" inherently
        # benefit from both document and structured data evidence
        result = classifier.classify("Why is Project Alpha at risk?")
        assert result == QuestionIntent.HYBRID

    def test_meeting_notes_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("Summarize the meeting notes from last week")
        assert result == QuestionIntent.QUALITATIVE


class TestQuantitativeClassification:
    """Questions with only quantitative keywords → QUANTITATIVE."""

    def test_budget_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("What is the total budget for this quarter?")
        assert result == QuestionIntent.QUANTITATIVE

    def test_cost_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("How much did the infrastructure cost?")
        assert result == QuestionIntent.QUANTITATIVE

    def test_metric_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("Show me the utilization percentage")
        assert result == QuestionIntent.QUANTITATIVE

    def test_trend_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("What is the spend trend over the last 6 months?")
        assert result == QuestionIntent.QUANTITATIVE

    def test_count_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("How many tasks are overdue?")
        assert result == QuestionIntent.QUANTITATIVE


class TestHybridClassification:
    """Questions with both keyword sets → HYBRID."""

    def test_risk_and_budget(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("What risks are related to budget overrun?")
        assert result == QuestionIntent.HYBRID

    def test_audit_and_cost(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("Describe the audit findings on cost variance")
        assert result == QuestionIntent.HYBRID

    def test_report_and_forecast(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("Show the report with the forecast for next quarter")
        assert result == QuestionIntent.HYBRID


class TestFallbackBehavior:
    """Questions with no recognized keywords → QUALITATIVE (fallback)."""

    def test_generic_question(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("Tell me about the project")
        assert result == QuestionIntent.QUALITATIVE

    def test_empty_string(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("")
        assert result == QuestionIntent.QUALITATIVE

    def test_unrelated_content(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("The quick brown fox jumps over the lazy dog")
        assert result == QuestionIntent.QUALITATIVE


class TestDeterminism:
    """Classification must be deterministic: same input → same output."""

    def test_same_input_same_output(self, classifier: QuestionClassifier) -> None:
        question = "What risks affect the budget forecast for this project?"
        results = [classifier.classify(question) for _ in range(100)]
        assert all(r == results[0] for r in results)

    def test_case_insensitive(self, classifier: QuestionClassifier) -> None:
        lower = classifier.classify("what is the budget?")
        upper = classifier.classify("WHAT IS THE BUDGET?")
        mixed = classifier.classify("What Is The Budget?")
        assert lower == upper == mixed == QuestionIntent.QUANTITATIVE


class TestMultiWordKeywords:
    """Multi-word keywords like 'how much' and 'what happened' work correctly."""

    def test_how_much(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("How much did we spend on cloud?")
        assert result == QuestionIntent.QUANTITATIVE

    def test_how_many(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("How many deliverables are pending?")
        assert result == QuestionIntent.QUANTITATIVE

    def test_what_happened(self, classifier: QuestionClassifier) -> None:
        result = classifier.classify("What happened in the last sprint?")
        assert result == QuestionIntent.QUALITATIVE

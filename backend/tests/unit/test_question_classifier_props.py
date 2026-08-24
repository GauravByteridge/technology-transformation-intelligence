"""
Property-based tests for QuestionClassifier (Properties 1, 2, 13).

Uses Hypothesis to verify correctness properties across random inputs:
- Property 1: Classification Determinism — same input always returns same result
- Property 2: Classification Completeness — any non-empty string returns exactly
  one QuestionIntent, never raises
- Property 13: Fallback to Qualitative — strings without recognized keywords
  return QUALITATIVE

Feature: phase7-ai-query-experience
Validates: Requirements 10.5, 10.1, 2.5
"""

from hypothesis import given, settings, strategies as st

from app.ai.question_classifier import QuestionClassifier, QuestionIntent


@settings(max_examples=100)
@given(question=st.text(min_size=1, max_size=500))
def test_classification_determinism(question: str):
    """Property 1: Same input always produces the same output.

    Feature: phase7-ai-query-experience
    Validates: Requirement 10.5
    """
    classifier = QuestionClassifier()
    result1 = classifier.classify(question)
    result2 = classifier.classify(question)
    assert result1 == result2


@settings(max_examples=100)
@given(question=st.text(min_size=1, max_size=500))
def test_classification_completeness(question: str):
    """Property 2: Any non-empty string returns exactly one QuestionIntent.

    Never raises an exception, never returns None, always returns a valid enum.

    Feature: phase7-ai-query-experience
    Validates: Requirement 10.1
    """
    classifier = QuestionClassifier()
    result = classifier.classify(question)
    assert result is not None
    assert isinstance(result, QuestionIntent)
    assert result in (QuestionIntent.QUALITATIVE, QuestionIntent.QUANTITATIVE, QuestionIntent.HYBRID)


@settings(max_examples=100)
@given(question=st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
))
def test_fallback_to_qualitative(question: str):
    """Property 13: Strings without recognized keywords return QUALITATIVE.

    Feature: phase7-ai-query-experience
    Validates: Requirement 2.5
    """
    classifier = QuestionClassifier()

    # Filter out strings that happen to contain any known keywords or phrases
    lower_q = question.lower()
    all_keywords = (
        classifier.QUALITATIVE_KEYWORDS
        | classifier.QUANTITATIVE_KEYWORDS
        | classifier.HYBRID_PHRASES
    )
    if any(kw in lower_q for kw in all_keywords):
        # Skip this example — it contains a keyword
        return

    result = classifier.classify(question)
    assert result == QuestionIntent.QUALITATIVE, (
        f"Question without keywords should default to QUALITATIVE, got {result} for: {question!r}"
    )

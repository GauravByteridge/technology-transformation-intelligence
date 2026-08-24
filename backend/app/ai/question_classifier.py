"""
Question Classifier — Deterministic intent classification for Demo Mode.

This module provides keyword-based classification of user questions into
three intent categories: QUALITATIVE, QUANTITATIVE, or HYBRID.

DEPENDENCY CONSTRAINT:
    This module is an implementation detail of Demo Mode. It MUST ONLY be
    imported by _MockStrandsModel. It MUST NOT be imported by:
    - AIService
    - StrandsAgentWrapper
    - Real LLM providers
    - Frontend
    - Shared production agent orchestration

The real LLM path handles classification implicitly through reasoning.
"""

from enum import Enum


class QuestionIntent(Enum):
    """Classification of a user question by retrieval intent.

    QUALITATIVE: Narrative/document retrieval via search_documents
    QUANTITATIVE: Structured data retrieval via query_dataset
    HYBRID: Both document search and structured data query
    """

    QUALITATIVE = "qualitative"
    QUANTITATIVE = "quantitative"
    HYBRID = "hybrid"


class QuestionClassifier:
    """Deterministic question intent classifier for demo mode.

    Uses keyword and pattern matching to categorize questions.
    Classification is deterministic: same input always produces the same output.
    Ambiguous questions default to QUALITATIVE (search_documents as fallback).
    """

    QUALITATIVE_KEYWORDS: set[str] = {
        "concern",
        "risk",
        "finding",
        "recommendation",
        "meeting",
        "note",
        "issue",
        "audit",
        "review",
        "report",
        "observation",
        "why",
        "describe",
        "explain",
        "what happened",
        "summary",
    }

    QUANTITATIVE_KEYWORDS: set[str] = {
        "cost",
        "budget",
        "spend",
        "metric",
        "progress",
        "utilization",
        "percentage",
        "total",
        "amount",
        "how much",
        "how many",
        "count",
        "average",
        "trend",
        "forecast",
        "variance",
    }

    # Well-known dataset name patterns that allow skipping list_available_datasets
    KNOWN_DATASET_PATTERNS: dict[str, str] = {
        "budget": "project_financials",
        "financial": "project_financials",
        "cost": "project_financials",
        "spend": "project_financials",
        "finance": "project_financials",
        "progress": "project_milestones",
        "milestone": "project_milestones",
        "timeline": "project_milestones",
        "schedule": "project_milestones",
        "resource": "project_resources",
        "utilization": "project_resources",
        "staff": "project_resources",
    }

    # Hybrid trigger phrases — questions that inherently require both document
    # and structured data evidence regardless of individual keyword matches
    HYBRID_PHRASES: set[str] = {
        "at risk",
        "why is",
        "root cause",
        "what caused",
        "overall status",
        "project health",
        "on track",
        "behind schedule",
    }

    def classify(self, question: str) -> QuestionIntent:
        """Classify a question by intent type.

        Args:
            question: The user's natural-language question.

        Returns:
            The classified intent. Defaults to QUALITATIVE when ambiguous.
        """
        lower_q = question.lower()

        # Check for hybrid phrases first — these always require both sources
        has_hybrid_phrase = any(phrase in lower_q for phrase in self.HYBRID_PHRASES)
        if has_hybrid_phrase:
            return QuestionIntent.HYBRID

        has_qual = any(kw in lower_q for kw in self.QUALITATIVE_KEYWORDS)
        has_quant = any(kw in lower_q for kw in self.QUANTITATIVE_KEYWORDS)

        if has_qual and has_quant:
            return QuestionIntent.HYBRID
        elif has_quant:
            return QuestionIntent.QUANTITATIVE
        else:
            # Default: qualitative (search_documents as fallback)
            return QuestionIntent.QUALITATIVE

    def infer_dataset_name(self, question: str) -> str | None:
        """Attempt to infer a well-known dataset name from the question.

        If a dataset name can be inferred, query_dataset can be called
        directly without requiring list_available_datasets first.

        Args:
            question: The user's natural-language question.

        Returns:
            A dataset name string if inferable, None otherwise.
        """
        lower_q = question.lower()
        for keyword, dataset_name in self.KNOWN_DATASET_PATTERNS.items():
            if keyword in lower_q:
                return dataset_name
        return None

"""
Groundedness Classifier — Heuristic classification of AI response claims.

Classifies each claim or evidence item into one of three groundedness levels:
- "retrieved_fact": The claim directly states data values found in evidence/tool results
- "derived_calculation": The claim states a computed/derived value from retrieved data
- "ai_explanation": The claim is reasoning/interpretation not directly from data values

This is a simple heuristic classifier for the POC. It uses pattern matching
against numeric values, currency, percentages, and calculation-related keywords.
No LLM call is needed.
"""

import re


# Patterns indicating a retrieved fact (specific data values)
_CURRENCY_PATTERN = re.compile(
    r"\$[\d,]+\.?\d*[KMBkmb]?"  # $1,234 or $1.14M
    r"|[\d,]+\.?\d*\s*(?:USD|EUR|GBP|JPY|dollars|yen)"  # 1234 USD
)
_NUMBER_PATTERN = re.compile(
    r"\b\d[\d,]*\.?\d*(?=\b|[^A-Za-z]|$)"  # Any standalone number like 1234, 1,234.56
)
_DATE_PATTERN = re.compile(
    r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"  # 2024-01-15
    r"|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b"  # 01/15/2024
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s*\d{2,4}\b"
)

# Patterns indicating a derived calculation
_PERCENTAGE_PATTERN = re.compile(
    r"\b\d+\.?\d*\s*%"  # 14%, 3.5%
)
_CALCULATION_KEYWORDS = {
    "variance",
    "difference",
    "delta",
    "change",
    "increase",
    "decrease",
    "over budget",
    "under budget",
    "ahead of schedule",
    "behind schedule",
    "deviation",
    "margin",
    "ratio",
    "growth",
    "decline",
    "surplus",
    "deficit",
    "net",
    "gross",
    "average",
    "mean",
    "median",
    "total",
    "sum",
    "cumulative",
}
# NOTE: Hyphens in dates (2024-01-15) must not trigger this pattern.
# Only match operators that appear outside of date-like contexts.
_MATH_OPERATOR_PATTERN = re.compile(
    r"(?<!\d{4})\s[\+\-\×÷]\s\d"  # spaced operators: + 5, - 3 (not in dates)
    r"|\d\s*[\×÷]\s*\d"  # multiplication/division always indicate calculation
)


class GroundednessClassifier:
    """Heuristic groundedness classifier for POC.

    Classifies claims and evidence items based on pattern matching
    against data-value indicators, calculation indicators, and
    explanation/reasoning text.
    """

    def classify(
        self,
        claim_text: str,
        evidence_items: list[dict],
        tool_results: list[dict],
    ) -> str:
        """Classify a claim based on its text and supporting data.

        Checks if the claim directly references data values from evidence/tool
        results (retrieved_fact), computes values from those data
        (derived_calculation), or provides reasoning/interpretation
        (ai_explanation).

        Args:
            claim_text: The text of the claim to classify.
            evidence_items: Evidence items supporting this claim.
            tool_results: Raw tool execution results available during the query.

        Returns:
            One of: "retrieved_fact", "derived_calculation", "ai_explanation"
        """
        if not claim_text:
            return "ai_explanation"

        lower_claim = claim_text.lower()

        # Check for derived calculation indicators first — a percentage or
        # variance keyword with numeric data suggests computation
        if self._has_calculation_indicators(lower_claim):
            return "derived_calculation"

        # Check if claim references specific data values
        if self._has_data_value_indicators(claim_text, evidence_items, tool_results):
            return "retrieved_fact"

        return "ai_explanation"

    def classify_evidence_item(self, evidence_item: dict) -> str:
        """Classify a single evidence item based on its content.

        Uses the excerpt/data values within the evidence item to determine
        the groundedness classification.

        Args:
            evidence_item: A dict containing at minimum an 'excerpt' field.

        Returns:
            One of: "retrieved_fact", "derived_calculation", "ai_explanation"
        """
        excerpt = evidence_item.get("excerpt", "")
        if not excerpt:
            # Fall back to checking records_summary or other data fields
            records_summary = evidence_item.get("records_summary")
            if records_summary and isinstance(records_summary, dict):
                return "retrieved_fact"
            return "ai_explanation"

        lower_excerpt = excerpt.lower()

        # Derived calculation: contains percentage, variance, or calculation keywords
        if self._has_calculation_indicators(lower_excerpt):
            return "derived_calculation"

        # Retrieved fact: contains specific data values (numbers, currency, dates)
        if self._has_specific_data_values(excerpt):
            return "retrieved_fact"

        return "ai_explanation"

    def _has_calculation_indicators(self, lower_text: str) -> bool:
        """Check if text contains indicators of a derived calculation."""
        # Percentage pattern is a strong signal
        if _PERCENTAGE_PATTERN.search(lower_text):
            return True

        # Calculation keywords combined with numeric or currency data
        has_calc_keyword = any(kw in lower_text for kw in _CALCULATION_KEYWORDS)
        has_number = bool(_NUMBER_PATTERN.search(lower_text))
        has_currency = bool(_CURRENCY_PATTERN.search(lower_text))

        if has_calc_keyword and (has_number or has_currency):
            return True

        # Math operators with numbers (excluding date-like patterns)
        if _MATH_OPERATOR_PATTERN.search(lower_text):
            return True

        return False

    def _has_data_value_indicators(
        self,
        claim_text: str,
        evidence_items: list[dict],
        tool_results: list[dict],
    ) -> bool:
        """Check if the claim references specific data values from evidence."""
        # If the claim contains currency values, dates, or specific numbers
        # and those values also appear in evidence/tool results, it's a fact
        if _CURRENCY_PATTERN.search(claim_text):
            return True

        if _DATE_PATTERN.search(claim_text):
            return True

        # Check if claim contains specific numbers that match evidence data
        claim_numbers = set(_NUMBER_PATTERN.findall(claim_text))
        if claim_numbers and self._numbers_in_evidence(claim_numbers, evidence_items, tool_results):
            return True

        return False

    def _has_specific_data_values(self, text: str) -> bool:
        """Check if text contains specific data values (numbers, currency, dates)."""
        if _CURRENCY_PATTERN.search(text):
            return True

        if _DATE_PATTERN.search(text):
            return True

        # Multiple distinct numbers suggest structured data
        numbers_found = _NUMBER_PATTERN.findall(text)
        if len(numbers_found) >= 2:
            return True

        return False

    def _numbers_in_evidence(
        self,
        claim_numbers: set[str],
        evidence_items: list[dict],
        tool_results: list[dict],
    ) -> bool:
        """Check if numbers from the claim appear in evidence or tool results."""
        # Extract numbers from evidence excerpts
        for evidence in evidence_items:
            excerpt = evidence.get("excerpt", "")
            evidence_numbers = set(_NUMBER_PATTERN.findall(str(excerpt)))
            if claim_numbers & evidence_numbers:
                return True

            # Also check records_summary values
            records = evidence.get("records_summary", {})
            if isinstance(records, dict):
                record_values = set(
                    _NUMBER_PATTERN.findall(str(records))
                )
                if claim_numbers & record_values:
                    return True

        # Extract numbers from tool result rows
        for result in tool_results:
            rows = result.get("rows", [])
            for row in rows:
                row_numbers = set(_NUMBER_PATTERN.findall(str(row)))
                if claim_numbers & row_numbers:
                    return True

        return False

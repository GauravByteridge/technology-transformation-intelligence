"""
ContentClassifier: Deterministic heuristic-based content classification.

Classifies detected regions by content structure to determine downstream
processing strategy. Runs AFTER region detection and examines actual content
to assign one of: STRUCTURED, SEMI_STRUCTURED, UNSTRUCTURED, or IGNORE.

Does NOT use LLM — relies on deterministic signal analysis for POC.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.models.enums import ContentClassification, ProcessingStrategy
from app.processors.protocol import ClassificationResult, DetectedRegion

logger = logging.getLogger(__name__)

# Threshold constants for signal analysis
_MIN_ROWS_FOR_TABULAR = 3  # Header + at least 2 data rows
_NARRATIVE_CELL_LENGTH_THRESHOLD = 50  # Chars above which a cell is "narrative"
_MAX_COLUMNS_FOR_NARRATIVE = 2  # Low column count signals prose


class ContentClassifier:
    """Classifies detected regions by content structure using deterministic heuristics.

    Runs AFTER region detection. Examines actual content to determine whether
    each region is STRUCTURED, SEMI_STRUCTURED, UNSTRUCTURED, or IGNORE.
    Does NOT use LLM — relies on deterministic signal analysis for POC.

    Args:
        confidence_threshold: Minimum confidence to assign a definitive strategy.
            Below this threshold, regions get REVIEW_REQUIRED. Defaults to 0.75.
    """

    def __init__(self, confidence_threshold: float = 0.75) -> None:
        if not (0.0 <= confidence_threshold <= 1.0):
            raise ValueError(
                f"confidence_threshold must be between 0.0 and 1.0, got {confidence_threshold}"
            )
        self._confidence_threshold = confidence_threshold

    @property
    def confidence_threshold(self) -> float:
        """The configured confidence threshold for strategy assignment."""
        return self._confidence_threshold

    def classify(self, region: DetectedRegion) -> ClassificationResult:
        """Classify a single region's content type and assign processing strategy.

        Classification signals:
        - STRUCTURED: clear tabular layout, consistent columns, repeated records,
          identifiable header, consistent data types per column
        - SEMI_STRUCTURED: partially tabular with some narrative elements
        - UNSTRUCTURED: free-form narrative, paragraphs, comments, descriptions, prose
        - IGNORE: empty regions, decorative content, single-cell separators

        Args:
            region: A detected region with content samples for analysis.

        Returns:
            ClassificationResult with classification, processing_strategy,
            confidence, reason, and signal scores.
        """
        # Check for empty/decorative first
        if self._is_empty_or_decorative(region):
            return ClassificationResult(
                classification=ContentClassification.IGNORE.value,
                processing_strategy=ProcessingStrategy.IGNORE.value,
                confidence=1.0,
                reason="Region is empty, single-cell, or decorative",
                signals={"empty_or_decorative": 1.0},
            )

        tabular_score = self._calculate_tabular_score(region)
        narrative_score = self._calculate_narrative_score(region)

        signals = {
            "tabular_score": tabular_score,
            "narrative_score": narrative_score,
        }

        classification, confidence, reason = self._resolve_classification(
            tabular_score, narrative_score, region
        )

        strategy = self._map_strategy(classification, confidence)

        logger.debug(
            "Classified region",
            extra={
                "region_id": region.region_id,
                "classification": classification.value,
                "strategy": strategy.value,
                "confidence": confidence,
                "tabular_score": tabular_score,
                "narrative_score": narrative_score,
            },
        )

        return ClassificationResult(
            classification=classification.value,
            processing_strategy=strategy.value,
            confidence=round(confidence, 4),
            reason=reason,
            signals=signals,
        )

    def classify_batch(self, regions: list[DetectedRegion]) -> list[ClassificationResult]:
        """Classify multiple regions. Each region is classified independently.

        Args:
            regions: List of detected regions to classify.

        Returns:
            List of ClassificationResult, one per input region (same order).
        """
        return [self.classify(region) for region in regions]

    def _calculate_tabular_score(self, region: DetectedRegion) -> float:
        """Score how tabular the content is (0.0 to 1.0).

        Signals evaluated:
        - Consistent column count across rows
        - Non-null density (high percentage of filled cells)
        - Consistent data types per column
        - First row looks like headers (text, unique values)
        - Numeric/date columns present
        - Sufficient row count (> 2 data rows)

        Args:
            region: Region with content_sample to analyze.

        Returns:
            Float between 0.0 and 1.0 indicating tabular likelihood.
        """
        sample = region.content_sample
        if not sample:
            return 0.0

        scores: list[float] = []

        # Signal 1: Consistent column count across rows
        col_counts = [len(row) for row in sample]
        if col_counts:
            most_common_count = max(set(col_counts), key=col_counts.count)
            consistency = col_counts.count(most_common_count) / len(col_counts)
            scores.append(consistency)
        else:
            scores.append(0.0)

        # Signal 2: Non-null density (filled cells)
        total_cells = sum(len(row) for row in sample)
        if total_cells > 0:
            filled_cells = sum(
                1 for row in sample for cell in row if cell and cell.strip()
            )
            density = filled_cells / total_cells
            scores.append(density)
        else:
            scores.append(0.0)

        # Signal 3: First row looks like headers (text, unique values)
        header_score = self._score_header_row(sample)
        scores.append(header_score)

        # Signal 4: Numeric/date columns present
        numeric_date_score = self._score_numeric_date_columns(sample)
        scores.append(numeric_date_score)

        # Signal 5: Sufficient row count
        row_count = region.row_count
        if row_count >= _MIN_ROWS_FOR_TABULAR:
            row_score = min(1.0, row_count / 10.0)  # Scales up to 10 rows
        else:
            row_score = 0.2
        scores.append(row_score)

        # Signal 6: Column count suggests structured data (3+ columns)
        col_count = region.column_count
        if col_count >= 3:
            col_score = min(1.0, col_count / 5.0)
        elif col_count == 2:
            col_score = 0.4
        else:
            col_score = 0.1
        scores.append(col_score)

        # Weighted average: consistency and header are most important
        weights = [0.25, 0.15, 0.25, 0.15, 0.10, 0.10]
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)

        return round(min(1.0, weighted_sum / total_weight), 4)

    def _calculate_narrative_score(self, region: DetectedRegion) -> float:
        """Score how narrative/prose-like the content is (0.0 to 1.0).

        Signals evaluated:
        - High average cell text length (> 50 chars)
        - Sentence-like content (periods, capitalization patterns)
        - Low column count (1-2 columns)
        - Varying row content lengths
        - Presence of paragraph-like breaks

        Args:
            region: Region with content_sample and/or raw_text to analyze.

        Returns:
            Float between 0.0 and 1.0 indicating narrative likelihood.
        """
        scores: list[float] = []
        weights: list[float] = []

        # If raw_text is available, use it for stronger narrative signals
        if region.raw_text and region.raw_text.strip():
            text_length_score = min(1.0, len(region.raw_text) / 300.0)
            scores.append(text_length_score)
            weights.append(0.25)

            sentence_score = self._score_sentence_patterns(region.raw_text)
            scores.append(sentence_score)
            weights.append(0.30)

            # Paragraph breaks
            paragraph_count = region.raw_text.count("\n\n")
            paragraph_score = min(1.0, paragraph_count / 3.0)
            scores.append(paragraph_score)
            weights.append(0.10)
        else:
            # Analyze content_sample for narrative signals
            sample = region.content_sample
            if not sample:
                return 0.0

            # Signal 1: Average cell text length
            all_cells = [cell for row in sample for cell in row if cell and cell.strip()]
            if all_cells:
                avg_length = sum(len(cell) for cell in all_cells) / len(all_cells)
                # Cells > 50 chars strongly suggest narrative
                length_score = min(1.0, avg_length / 80.0)
                scores.append(length_score)
                weights.append(0.30)
            else:
                scores.append(0.0)
                weights.append(0.30)

            # Signal 2: Sentence-like content
            combined_text = " ".join(all_cells) if all_cells else ""
            sentence_score = self._score_sentence_patterns(combined_text)
            scores.append(sentence_score)
            weights.append(0.25)

            # Signal 3: Varying row content lengths (high variance suggests prose)
            if len(all_cells) > 1:
                lengths = [len(cell) for cell in all_cells]
                mean_len = sum(lengths) / len(lengths)
                variance = sum((ln - mean_len) ** 2 for ln in lengths) / len(lengths)
                cv = (variance**0.5) / mean_len if mean_len > 0 else 0
                variance_score = min(1.0, cv / 2.0)
                scores.append(variance_score)
                weights.append(0.10)
            else:
                scores.append(0.0)
                weights.append(0.10)

        # Signal: Low column count (1-2 columns → likely prose)
        col_count = region.column_count
        if col_count <= 1:
            col_score = 1.0
        elif col_count == 2:
            col_score = 0.7
        elif col_count <= 4:
            col_score = 0.3
        else:
            col_score = 0.0
        scores.append(col_score)
        weights.append(0.35)

        if not scores:
            return 0.0

        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)

        return round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    def _is_empty_or_decorative(self, region: DetectedRegion) -> bool:
        """Check if region is empty, single-cell, or purely decorative.

        A region is considered empty/decorative if:
        - It has 0 rows or 0 columns
        - All cells are empty or whitespace
        - It's a single-cell region (unless it has substantial raw_text)
        - It's very small (< 2 rows and < 2 columns) with minimal content

        Args:
            region: Region to check.

        Returns:
            True if the region should be classified as IGNORE.
        """
        # If region has significant raw_text content, it's not decorative.
        # This handles PDFs and other unstructured documents that appear as
        # single-cell regions (row_count=pages, column_count=1) but contain
        # real document text.
        if region.raw_text and len(region.raw_text.strip()) > 50:
            return False

        # Zero dimensions
        if region.row_count <= 0 or region.column_count <= 0:
            return True

        # Single cell
        if region.row_count == 1 and region.column_count == 1:
            return True

        # Very small region with minimal content
        if region.row_count < 2 and region.column_count < 2:
            return True

        # Check content: all empty/whitespace
        sample = region.content_sample
        if not sample:
            # No sample content and no raw_text → treat as empty
            if not region.raw_text or not region.raw_text.strip():
                return True
            return False

        has_content = any(
            cell and cell.strip()
            for row in sample
            for cell in row
        )

        if not has_content:
            # Also check raw_text
            if not region.raw_text or not region.raw_text.strip():
                return True

        return not has_content

    # -------------------------------------------------------------------------
    # Private helper methods
    # -------------------------------------------------------------------------

    def _resolve_classification(
        self,
        tabular_score: float,
        narrative_score: float,
        region: DetectedRegion,
    ) -> tuple[ContentClassification, float, str]:
        """Determine classification from tabular and narrative scores.

        The classification uses the relative difference between scores.
        A score that exceeds the other by a significant margin wins.
        When both are close, SEMI_STRUCTURED is assigned.

        Returns:
            Tuple of (classification, confidence, reason).
        """
        score_diff = tabular_score - narrative_score

        # Strong tabular signal: tabular clearly dominates
        if score_diff >= 0.15 and tabular_score >= 0.5:
            confidence = tabular_score
            return (
                ContentClassification.STRUCTURED,
                confidence,
                f"Strong tabular signals (score={tabular_score:.2f}): "
                f"consistent columns, header detected, sufficient rows",
            )

        # Strong narrative signal: narrative clearly dominates
        if score_diff <= -0.15 and narrative_score >= 0.5:
            confidence = narrative_score
            return (
                ContentClassification.UNSTRUCTURED,
                confidence,
                f"Strong narrative signals (score={narrative_score:.2f}): "
                f"long text, sentence patterns, low column count",
            )

        # Scores are close — mixed signals → SEMI_STRUCTURED
        if tabular_score >= 0.3 and narrative_score >= 0.3:
            confidence = (tabular_score + narrative_score) / 2.0 * 0.85
            return (
                ContentClassification.SEMI_STRUCTURED,
                confidence,
                f"Mixed content signals (tabular={tabular_score:.2f}, "
                f"narrative={narrative_score:.2f}): partial structure with prose",
            )

        # Default: use the stronger signal
        if tabular_score > narrative_score:
            confidence = tabular_score
            classification = ContentClassification.STRUCTURED
            reason = (
                f"Tabular signal dominant (tabular={tabular_score:.2f}, "
                f"narrative={narrative_score:.2f})"
            )
        elif narrative_score > tabular_score:
            confidence = narrative_score
            classification = ContentClassification.UNSTRUCTURED
            reason = (
                f"Narrative signal dominant (narrative={narrative_score:.2f}, "
                f"tabular={tabular_score:.2f})"
            )
        else:
            # Equal low scores → semi-structured with low confidence
            confidence = max(tabular_score, 0.3)
            classification = ContentClassification.SEMI_STRUCTURED
            reason = (
                f"Ambiguous content (tabular={tabular_score:.2f}, "
                f"narrative={narrative_score:.2f})"
            )

        return classification, confidence, reason

    def _map_strategy(
        self,
        classification: ContentClassification,
        confidence: float,
    ) -> ProcessingStrategy:
        """Map classification + confidence to processing strategy.

        Mapping rules:
        - STRUCTURED (confidence >= threshold) → DATASET_QUERY
        - STRUCTURED (confidence < threshold) → REVIEW_REQUIRED
        - SEMI_STRUCTURED (confidence >= threshold) → HYBRID
        - SEMI_STRUCTURED (confidence < threshold) → REVIEW_REQUIRED
        - UNSTRUCTURED (confidence >= threshold) → RAG
        - UNSTRUCTURED (confidence < threshold) → REVIEW_REQUIRED
        - IGNORE (any) → IGNORE
        """
        if classification == ContentClassification.IGNORE:
            return ProcessingStrategy.IGNORE

        if confidence < self._confidence_threshold:
            return ProcessingStrategy.REVIEW_REQUIRED

        strategy_map = {
            ContentClassification.STRUCTURED: ProcessingStrategy.DATASET_QUERY,
            ContentClassification.SEMI_STRUCTURED: ProcessingStrategy.HYBRID,
            ContentClassification.UNSTRUCTURED: ProcessingStrategy.RAG,
        }

        return strategy_map.get(classification, ProcessingStrategy.REVIEW_REQUIRED)

    def _score_header_row(self, sample: list[list[str]]) -> float:
        """Score whether the first row looks like a header.

        Headers typically have: all text (no numbers), unique values,
        shorter than data rows, consistent formatting.
        """
        if not sample or not sample[0]:
            return 0.0

        first_row = sample[0]
        if not first_row:
            return 0.0

        # Check that first row cells are non-empty text
        non_empty_cells = [cell for cell in first_row if cell and cell.strip()]
        if not non_empty_cells:
            return 0.0

        score = 0.0

        # Uniqueness: header values should be unique
        unique_count = len(set(non_empty_cells))
        total_count = len(non_empty_cells)
        if total_count > 0:
            uniqueness = unique_count / total_count
            score += uniqueness * 0.4

        # Text-only: headers are typically non-numeric
        text_count = sum(
            1 for cell in non_empty_cells if not self._looks_numeric(cell)
        )
        if total_count > 0:
            text_ratio = text_count / total_count
            score += text_ratio * 0.3

        # Headers tend to be shorter than data cells
        if len(sample) > 1:
            header_avg_len = sum(len(c) for c in non_empty_cells) / len(non_empty_cells)
            data_cells = [
                cell
                for row in sample[1:]
                for cell in row
                if cell and cell.strip()
            ]
            if data_cells:
                data_avg_len = sum(len(c) for c in data_cells) / len(data_cells)
                if header_avg_len <= data_avg_len:
                    score += 0.3
                else:
                    score += 0.1

        return min(1.0, score)

    def _score_numeric_date_columns(self, sample: list[list[str]]) -> float:
        """Score whether the sample contains numeric or date columns."""
        if not sample or len(sample) < 2:
            return 0.0

        # Skip first row (potential header), check data rows
        data_rows = sample[1:] if len(sample) > 1 else sample

        if not data_rows:
            return 0.0

        # Determine column count from first row
        col_count = max(len(row) for row in sample) if sample else 0
        if col_count == 0:
            return 0.0

        numeric_cols = 0
        date_cols = 0

        for col_idx in range(col_count):
            col_values = []
            for row in data_rows:
                if col_idx < len(row) and row[col_idx] and row[col_idx].strip():
                    col_values.append(row[col_idx].strip())

            if not col_values:
                continue

            # Check if column is mostly numeric
            numeric_count = sum(1 for v in col_values if self._looks_numeric(v))
            if numeric_count / len(col_values) >= 0.7:
                numeric_cols += 1
                continue

            # Check if column is mostly dates
            date_count = sum(1 for v in col_values if self._looks_date(v))
            if date_count / len(col_values) >= 0.5:
                date_cols += 1

        total_typed = numeric_cols + date_cols
        if col_count > 0:
            return min(1.0, total_typed / max(1, col_count - 1))

        return 0.0

    def _score_sentence_patterns(self, text: str) -> float:
        """Score how sentence-like the text is.

        Looks for: periods followed by spaces/newlines, capitalization
        at start of sentences, question marks, commas.
        """
        if not text or not text.strip():
            return 0.0

        score = 0.0

        # Sentence-ending punctuation
        sentence_endings = len(re.findall(r"[.!?]\s", text))
        if sentence_endings >= 1:
            score += min(0.4, sentence_endings * 0.1)

        # Capital letters at sentence starts
        capital_starts = len(re.findall(r"(?:^|[.!?]\s+)[A-Z]", text))
        if capital_starts >= 1:
            score += min(0.3, capital_starts * 0.075)

        # Commas (suggest complex sentences)
        comma_count = text.count(",")
        if comma_count >= 2:
            score += min(0.2, comma_count * 0.05)

        # Word count suggests prose
        word_count = len(text.split())
        if word_count >= 20:
            score += 0.1

        return min(1.0, score)

    @staticmethod
    def _looks_numeric(value: str) -> bool:
        """Check if a string value looks like a number."""
        cleaned = value.strip().replace(",", "").replace("$", "").replace("%", "")
        if not cleaned:
            return False
        try:
            float(cleaned)
            return True
        except ValueError:
            return False

    @staticmethod
    def _looks_date(value: str) -> bool:
        """Check if a string value looks like a date using common patterns."""
        date_patterns = [
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",  # 2024-01-15 or 2024/1/15
            r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",  # 01/15/2024 or 1-15-24
            r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4}",
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{2,4}",
        ]
        for pattern in date_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

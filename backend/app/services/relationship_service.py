"""
Relationship detection service — identifies candidate relationships between datasets.

Compares column names and data types across datasets within a project to
discover shared identifiers and potential join paths. Only creates
relationships above a configurable confidence threshold.
"""

from __future__ import annotations

import logging
from itertools import combinations
from uuid import UUID

from app.models.dataset import Dataset, DatasetColumn, DatasetRelationship
from app.repositories.dataset_repository import DatasetRepository

logger = logging.getLogger(__name__)

# Minimum confidence to persist a relationship
_CONFIDENCE_THRESHOLD = 0.6

# Column name patterns that indicate identifiers
_ID_SUFFIXES = ("_id", "id", "_key", "_code", "_no", "_number")


class RelationshipService:
    """Detects candidate relationships between datasets in a project.

    Compares column names across datasets within a project, identifies
    shared identifiers, and scores confidence based on name match,
    data type compatibility, and pattern recognition.
    """

    def __init__(self, dataset_repository: DatasetRepository) -> None:
        """Initialize with dataset repository dependency.

        Args:
            dataset_repository: Repository for dataset and relationship persistence.
        """
        self._dataset_repo = dataset_repository

    async def detect_relationships(self, project_id: UUID) -> list[dict]:
        """Detect candidate relationships between all READY datasets in a project.

        For each pair of datasets, compares column names for exact matches,
        scores confidence based on name match and data type compatibility,
        and creates DatasetRelationship records for matches above threshold.

        Args:
            project_id: UUID of the project to analyze.

        Returns:
            List of relationship dicts describing detected relationships.
        """
        # Load all READY datasets for the project with their columns
        datasets = await self._dataset_repo.list_by_project(project_id)
        ready_datasets = [
            ds for ds in datasets if ds.status == "READY"
        ]

        if len(ready_datasets) < 2:
            logger.info(
                "relationship_detection_skipped",
                project_id=str(project_id),
                reason="fewer than 2 READY datasets",
                dataset_count=len(ready_datasets),
            )
            return []

        # Load columns for each dataset
        dataset_columns: dict[UUID, list[DatasetColumn]] = {}
        for ds in ready_datasets:
            full_ds = await self._dataset_repo.get_dataset_with_relations(ds.id)
            if full_ds and full_ds.columns:
                dataset_columns[ds.id] = list(full_ds.columns)

        # Compare each pair of datasets
        detected: list[dict] = []

        for ds_a, ds_b in combinations(ready_datasets, 2):
            cols_a = dataset_columns.get(ds_a.id, [])
            cols_b = dataset_columns.get(ds_b.id, [])

            if not cols_a or not cols_b:
                continue

            pair_relationships = self._find_column_matches(
                ds_a, cols_a, ds_b, cols_b
            )
            detected.extend(pair_relationships)

        # Persist relationships above threshold
        persisted: list[dict] = []
        for rel_data in detected:
            if rel_data["confidence"] >= _CONFIDENCE_THRESHOLD:
                relationship = DatasetRelationship(
                    source_dataset_id=rel_data["source_dataset_id"],
                    target_dataset_id=rel_data["target_dataset_id"],
                    source_column=rel_data["source_column"],
                    target_column=rel_data["target_column"],
                    relationship_type=rel_data["relationship_type"],
                    confidence=rel_data["confidence"],
                )
                self._dataset_repo._session.add(relationship)
                persisted.append(rel_data)

        if persisted:
            await self._dataset_repo._session.flush()
            logger.info(
                "relationships_detected",
                project_id=str(project_id),
                count=len(persisted),
            )

        return persisted

    def _find_column_matches(
        self,
        ds_a: Dataset,
        cols_a: list[DatasetColumn],
        ds_b: Dataset,
        cols_b: list[DatasetColumn],
    ) -> list[dict]:
        """Find matching columns between two datasets.

        Identifies shared identifiers by exact column name match and
        scores confidence based on name patterns and type compatibility.

        Args:
            ds_a: First dataset.
            cols_a: Columns of the first dataset.
            ds_b: Second dataset.
            cols_b: Columns of the second dataset.

        Returns:
            List of relationship dicts for this pair.
        """
        relationships: list[dict] = []

        # Build lookup maps
        cols_b_by_name: dict[str, DatasetColumn] = {
            col.name.lower().strip(): col for col in cols_b
        }

        for col_a in cols_a:
            col_a_name = col_a.name.lower().strip()

            # Check for exact name match
            if col_a_name in cols_b_by_name:
                col_b = cols_b_by_name[col_a_name]
                confidence = self._score_relationship(col_a, col_b)

                # Determine relationship type
                rel_type = self._determine_relationship_type(col_a_name)

                relationships.append({
                    "source_dataset_id": ds_a.id,
                    "target_dataset_id": ds_b.id,
                    "source_column": col_a.name,
                    "target_column": col_b.name,
                    "relationship_type": rel_type,
                    "confidence": round(confidence, 4),
                    "source_dataset_name": ds_a.name,
                    "target_dataset_name": ds_b.name,
                })

        return relationships

    def _score_relationship(
        self, col_a: DatasetColumn, col_b: DatasetColumn
    ) -> float:
        """Score the confidence of a column relationship.

        Scores based on:
        - Name match (exact): 0.5
        - Data type compatibility: 0.3
        - ID-like pattern: 0.2

        Args:
            col_a: Column from the source dataset.
            col_b: Column from the target dataset.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        score = 0.0

        # Exact name match (already confirmed by caller)
        score += 0.5

        # Data type compatibility
        if col_a.data_type == col_b.data_type:
            score += 0.3
        elif self._types_compatible(col_a.data_type, col_b.data_type):
            score += 0.15

        # ID-like pattern bonus
        col_name_lower = col_a.name.lower()
        if any(col_name_lower.endswith(suffix) for suffix in _ID_SUFFIXES):
            score += 0.2
        elif col_name_lower.startswith("id"):
            score += 0.15

        return min(1.0, score)

    def _determine_relationship_type(self, column_name: str) -> str:
        """Determine the relationship type based on column name patterns.

        Args:
            column_name: Lowercase column name.

        Returns:
            One of: "primary_key", "foreign_key", "shared_identifier".
        """
        if column_name.endswith("_id") or column_name == "id":
            return "foreign_key"
        if any(column_name.endswith(s) for s in ("_key", "_code", "_no", "_number")):
            return "shared_identifier"
        return "shared_identifier"

    @staticmethod
    def _types_compatible(type_a: str, type_b: str) -> bool:
        """Check if two data types are compatible for relationship matching.

        Args:
            type_a: Data type of column A.
            type_b: Data type of column B.

        Returns:
            True if types are considered compatible.
        """
        # Numeric types are compatible with each other
        numeric_types = {"integer", "decimal"}
        if type_a in numeric_types and type_b in numeric_types:
            return True

        # String is compatible with most types (common in CSV/JSON)
        if "string" in (type_a, type_b):
            return True

        return False

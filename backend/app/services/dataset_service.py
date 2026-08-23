"""
Dataset service — business logic for dataset lifecycle management.

Handles dataset creation from inspection results, confirmation workflows,
querying, and region management. Applies confidence threshold logic to
determine whether datasets require user review or are auto-confirmed.
"""

import structlog
from uuid import UUID

from app.models.dataset import Dataset, DataRegion, DatasetColumn
from app.models.enums import ProcessingStatus, ProcessingStrategy
from app.processors.protocol import ClassificationResult, InspectionResult
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.file_repository import FileRepository

logger = structlog.get_logger(__name__)

# Confidence threshold for auto-confirmation
CONFIDENCE_THRESHOLD = 0.75


class DatasetService:
    """Business logic for dataset lifecycle management."""

    def __init__(
        self,
        dataset_repository: DatasetRepository,
        file_repository: FileRepository,
    ) -> None:
        """
        Initialize with required dependencies.

        Args:
            dataset_repository: Repository for dataset persistence.
            file_repository: Repository for file record lookups.
        """
        self._dataset_repo = dataset_repository
        self._file_repo = file_repository

    async def create_datasets_from_inspection(
        self,
        file_id: UUID,
        inspection: InspectionResult,
        classifications: list[ClassificationResult],
    ) -> list[dict]:
        """
        Create datasets and data regions from file inspection and classification results.

        For each classified region:
        - DATASET_QUERY or HYBRID: creates Dataset + DataRegion + DatasetColumns
        - RAG, IGNORE, or REVIEW_REQUIRED: creates DataRegion only (no dataset)

        Confidence threshold logic:
        - >= 0.75: auto-confirm → status READY
        - < 0.75: status REVIEW_REQUIRED

        Args:
            file_id: UUID of the source uploaded file.
            inspection: InspectionResult containing detected regions.
            classifications: Classification results matching inspection regions by index.

        Returns:
            List of created dataset summary dicts.
        """
        created_datasets: list[dict] = []

        for region_data, classification in zip(
            inspection.regions, classifications
        ):
            strategy = classification.processing_strategy

            # Determine status based on confidence
            status = self._determine_status(classification.confidence)

            if strategy in (
                ProcessingStrategy.DATASET_QUERY.value,
                ProcessingStrategy.HYBRID.value,
            ):
                # Create dataset for structured/hybrid regions
                dataset_name = self._generate_dataset_name(
                    inspection.file_name, region_data.sheet_name
                )

                dataset = Dataset(
                    file_id=file_id,
                    name=dataset_name,
                    source_type=inspection.file_type,
                    sheet_name=region_data.sheet_name,
                    classification=classification.classification,
                    confidence=classification.confidence,
                    status=status,
                    record_count=region_data.row_count,
                )
                dataset = await self._dataset_repo.create_dataset(dataset)

                # Create data region linked to dataset
                data_region = DataRegion(
                    file_id=file_id,
                    dataset_id=dataset.id,
                    sheet_name=region_data.sheet_name or "Sheet1",
                    start_row=region_data.start_row,
                    end_row=region_data.end_row,
                    start_column=region_data.start_column,
                    end_column=region_data.end_column,
                    header_row=region_data.header_row,
                    classification=classification.classification,
                    processing_strategy=strategy,
                    confidence=classification.confidence,
                    classification_reason=classification.reason,
                )
                await self._dataset_repo.create_data_region(data_region)

                # Create columns from content sample headers if available
                if region_data.header_row is not None and region_data.content_sample:
                    columns = self._build_columns_from_sample(
                        dataset.id, region_data.content_sample
                    )
                    if columns:
                        await self._dataset_repo.create_columns_batch(columns)

                created_datasets.append(self._to_dataset_summary(dataset))

                logger.info(
                    "dataset_created_from_inspection",
                    dataset_id=str(dataset.id),
                    file_id=str(file_id),
                    strategy=strategy,
                    status=status,
                    confidence=classification.confidence,
                )
            else:
                # RAG, IGNORE, or REVIEW_REQUIRED: create region only
                data_region = DataRegion(
                    file_id=file_id,
                    dataset_id=None,
                    sheet_name=region_data.sheet_name or "Sheet1",
                    start_row=region_data.start_row,
                    end_row=region_data.end_row,
                    start_column=region_data.start_column,
                    end_column=region_data.end_column,
                    header_row=region_data.header_row,
                    classification=classification.classification,
                    processing_strategy=strategy,
                    confidence=classification.confidence,
                    classification_reason=classification.reason,
                )
                await self._dataset_repo.create_data_region(data_region)

                logger.info(
                    "region_created_without_dataset",
                    file_id=str(file_id),
                    strategy=strategy,
                    classification=classification.classification,
                )

        return created_datasets

    async def get_dataset(self, dataset_id: UUID) -> dict:
        """
        Retrieve dataset details with columns and regions.

        Args:
            dataset_id: UUID of the dataset.

        Returns:
            Dictionary with dataset details.

        Raises:
            ValueError: If dataset not found.
        """
        dataset = await self._dataset_repo.get_dataset_with_relations(dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset not found: {dataset_id}")

        return self._to_dataset_detail(dataset)

    async def list_datasets(
        self,
        project_id: UUID | None = None,
        file_id: UUID | None = None,
    ) -> list[dict]:
        """
        List datasets with optional project or file filter.

        Args:
            project_id: Optional project UUID to filter by.
            file_id: Optional file UUID to filter by.

        Returns:
            List of dataset summary dicts.
        """
        if file_id is not None:
            datasets = await self._dataset_repo.list_by_file(file_id)
        else:
            datasets = await self._dataset_repo.list_by_project(project_id)

        return [self._to_dataset_summary(ds) for ds in datasets]

    async def preview_dataset(self, dataset_id: UUID, limit: int = 20) -> dict:
        """
        Return sample rows and schema for a dataset preview.

        Args:
            dataset_id: UUID of the dataset to preview.
            limit: Maximum number of sample rows (default 20).

        Returns:
            Dict with "dataset" summary, "columns" schema, and "records" sample rows.

        Raises:
            ValueError: If dataset not found.
        """
        dataset = await self._dataset_repo.get_dataset_with_relations(dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset not found: {dataset_id}")

        # Fetch limited records for preview
        query_result = await self._dataset_repo.query_records(
            dataset_id=dataset_id, limit=limit
        )

        return {
            "dataset": self._to_dataset_summary(dataset),
            "columns": [
                {
                    "name": col.name,
                    "data_type": col.data_type,
                    "nullable": col.nullable,
                    "column_index": col.column_index,
                }
                for col in sorted(dataset.columns, key=lambda c: c.column_index)
            ],
            "records": query_result["records"],
            "total_count": query_result["total_count"],
        }

    async def confirm_dataset(
        self, dataset_id: UUID, adjustments: dict | None = None
    ) -> dict:
        """
        Confirm a dataset, transitioning from REVIEW_REQUIRED to READY.

        Optionally applies adjustments (rename, change header, region bounds,
        classification).

        Args:
            dataset_id: UUID of the dataset to confirm.
            adjustments: Optional dict with adjustment fields.

        Returns:
            Updated dataset detail dict.

        Raises:
            ValueError: If dataset not found or not in REVIEW_REQUIRED status.
        """
        dataset = await self._dataset_repo.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset not found: {dataset_id}")

        if dataset.status != ProcessingStatus.REVIEW_REQUIRED.value:
            raise ValueError(
                f"Dataset {dataset_id} is not in REVIEW_REQUIRED status, "
                f"current status: {dataset.status}"
            )

        updates: dict = {"status": ProcessingStatus.READY.value}

        # Apply optional adjustments
        if adjustments:
            if "name" in adjustments:
                updates["name"] = adjustments["name"]
            if "description" in adjustments:
                updates["description"] = adjustments["description"]
            if "classification" in adjustments:
                updates["classification"] = adjustments["classification"]
            if "domain" in adjustments:
                updates["domain"] = adjustments["domain"]

        updated = await self._dataset_repo.update_dataset(dataset_id, updates)

        logger.info(
            "dataset_confirmed",
            dataset_id=str(dataset_id),
            adjustments_applied=bool(adjustments),
        )

        # Reload with relations for full detail response
        full_dataset = await self._dataset_repo.get_dataset_with_relations(dataset_id)
        return self._to_dataset_detail(full_dataset or updated)

    async def query_dataset(self, dataset_id: UUID, query_params: dict) -> dict:
        """
        Query dataset records using JSONB operators.

        Delegates to repository's query_records with the provided parameters.

        Args:
            dataset_id: UUID of the dataset to query.
            query_params: Dict with optional keys: filters, sort, limit, offset,
                          columns, aggregations.

        Returns:
            Dict with "records", "total_count", and "aggregations".

        Raises:
            ValueError: If dataset not found.
        """
        dataset = await self._dataset_repo.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset not found: {dataset_id}")

        return await self._dataset_repo.query_records(
            dataset_id=dataset_id,
            filters=query_params.get("filters"),
            sort=query_params.get("sort"),
            limit=query_params.get("limit"),
            offset=query_params.get("offset", 0),
            columns=query_params.get("columns"),
            aggregations=query_params.get("aggregations"),
        )

    async def get_file_structure(self, file_id: UUID) -> dict:
        """
        Return the file's inspection/structure info including datasets and regions.

        Args:
            file_id: UUID of the uploaded file.

        Returns:
            Dict with file info, datasets, and regions.

        Raises:
            ValueError: If file not found.
        """
        uploaded_file = await self._file_repo.get_file(file_id)
        if uploaded_file is None:
            raise ValueError(f"File not found: {file_id}")

        datasets = await self._dataset_repo.list_by_file(file_id)
        regions = await self._dataset_repo.get_regions_by_file(file_id)

        return {
            "file_id": str(file_id),
            "file_name": uploaded_file.file_name,
            "file_type": uploaded_file.file_type,
            "processing_status": uploaded_file.processing_status,
            "datasets": [self._to_dataset_summary(ds) for ds in datasets],
            "regions": [self._to_region_dict(r) for r in regions],
        }

    async def get_file_regions(self, file_id: UUID) -> list[dict]:
        """
        Return all regions for a file with their classifications.

        Args:
            file_id: UUID of the uploaded file.

        Returns:
            List of region dicts with classification info.
        """
        regions = await self._dataset_repo.get_regions_by_file(file_id)
        return [self._to_region_dict(r) for r in regions]

    async def assign_project(self, dataset_id: UUID, project_id: UUID) -> dict:
        """
        Associate a dataset with a project.

        Args:
            dataset_id: UUID of the dataset.
            project_id: UUID of the project to assign.

        Returns:
            Updated dataset summary dict.

        Raises:
            ValueError: If dataset not found.
        """
        updated = await self._dataset_repo.update_dataset(
            dataset_id, {"project_id": project_id}
        )
        if updated is None:
            raise ValueError(f"Dataset not found: {dataset_id}")

        logger.info(
            "dataset_project_assigned",
            dataset_id=str(dataset_id),
            project_id=str(project_id),
        )

        return self._to_dataset_summary(updated)

    # --- Private Helpers ---

    def _determine_status(self, confidence: float) -> str:
        """Determine dataset status based on confidence threshold."""
        if confidence >= CONFIDENCE_THRESHOLD:
            return ProcessingStatus.READY.value
        return ProcessingStatus.REVIEW_REQUIRED.value

    def _generate_dataset_name(
        self, file_name: str, sheet_name: str | None
    ) -> str:
        """Generate a descriptive dataset name from file and sheet."""
        # Strip extension from filename
        base_name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        if sheet_name:
            return f"{base_name} - {sheet_name}"
        return base_name

    def _build_columns_from_sample(
        self, dataset_id: UUID, content_sample: list[list[str]]
    ) -> list[DatasetColumn]:
        """Build DatasetColumn instances from content sample headers."""
        if not content_sample:
            return []

        # First row of content_sample is treated as headers
        headers = content_sample[0]
        columns = []
        for idx, header in enumerate(headers):
            col_name = str(header).strip() if header else f"column_{idx}"
            columns.append(
                DatasetColumn(
                    dataset_id=dataset_id,
                    name=col_name,
                    data_type="string",  # Default; refined during normalization
                    nullable=True,
                    column_index=idx,
                )
            )
        return columns

    def _to_dataset_summary(self, dataset: Dataset) -> dict:
        """Convert a Dataset model to a summary response dict."""
        return {
            "id": str(dataset.id),
            "file_id": str(dataset.file_id),
            "project_id": str(dataset.project_id) if dataset.project_id else None,
            "name": dataset.name,
            "source_type": dataset.source_type,
            "sheet_name": dataset.sheet_name,
            "classification": dataset.classification,
            "record_count": dataset.record_count,
            "confidence": dataset.confidence,
            "status": dataset.status,
            "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        }

    def _to_dataset_detail(self, dataset: Dataset) -> dict:
        """Convert a Dataset model to a detailed response dict."""
        detail = self._to_dataset_summary(dataset)
        detail["description"] = dataset.description
        detail["domain"] = dataset.domain
        detail["processing_error"] = dataset.processing_error
        detail["updated_at"] = (
            dataset.updated_at.isoformat() if dataset.updated_at else None
        )
        detail["columns"] = [
            {
                "id": str(col.id),
                "name": col.name,
                "data_type": col.data_type,
                "nullable": col.nullable,
                "column_index": col.column_index,
                "sample_values": col.sample_values,
                "confidence": col.confidence,
            }
            for col in sorted(dataset.columns, key=lambda c: c.column_index)
        ] if dataset.columns else []
        detail["regions"] = [
            self._to_region_dict(r) for r in dataset.regions
        ] if dataset.regions else []
        return detail

    def _to_region_dict(self, region: DataRegion) -> dict:
        """Convert a DataRegion model to a response dict."""
        return {
            "id": str(region.id),
            "file_id": str(region.file_id),
            "dataset_id": str(region.dataset_id) if region.dataset_id else None,
            "sheet_name": region.sheet_name,
            "start_row": region.start_row,
            "end_row": region.end_row,
            "start_column": region.start_column,
            "end_column": region.end_column,
            "header_row": region.header_row,
            "classification": region.classification,
            "processing_strategy": region.processing_strategy,
            "confidence": region.confidence,
            "classification_reason": region.classification_reason,
            "warnings": region.warnings,
        }

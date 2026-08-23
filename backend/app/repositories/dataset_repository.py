"""
Dataset repository — database access layer for Dataset entities and related models.

Provides typed, parameterized access to datasets, data_regions, dataset_columns,
and dataset_records tables. All queries use SQLAlchemy ORM with bound parameters
(inherited from BaseRepository).

The query_records method uses PostgreSQL JSONB operators (->>, @>, ?) for
structured querying of record data stored as JSONB.
"""

from uuid import UUID

from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.types import Numeric, Text

from app.models.dataset import Dataset, DataRegion, DatasetColumn, DatasetRecord
from app.repositories.base import BaseRepository


class DatasetRepository(BaseRepository[Dataset]):
    """Data access layer for Dataset entities and related models."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, Dataset)

    async def create_dataset(self, dataset: Dataset) -> Dataset:
        """
        Persist a new dataset to the database.

        Args:
            dataset: Dataset model instance to persist.

        Returns:
            The persisted Dataset with server-generated fields populated.
        """
        return await self._create(dataset)

    async def get_dataset(self, dataset_id: UUID) -> Dataset | None:
        """
        Retrieve a dataset by its primary key.

        Args:
            dataset_id: UUID of the dataset.

        Returns:
            Dataset instance or None if not found.
        """
        return await self._get_by_id(dataset_id)

    async def get_dataset_with_relations(self, dataset_id: UUID) -> Dataset | None:
        """
        Retrieve a dataset with eagerly loaded columns and regions.

        Args:
            dataset_id: UUID of the dataset.

        Returns:
            Dataset instance with columns and regions loaded, or None.
        """
        statement = (
            select(Dataset)
            .where(Dataset.id == dataset_id)
            .options(
                selectinload(Dataset.columns),
                selectinload(Dataset.regions),
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: UUID | None) -> list[Dataset]:
        """
        List datasets filtered by project. If project_id is None, returns all.

        Args:
            project_id: UUID of the project to filter by, or None for all.

        Returns:
            List of Dataset instances.
        """
        if project_id is None:
            return await self._list_all()

        statement = select(Dataset).where(Dataset.project_id == project_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_by_file(self, file_id: UUID) -> list[Dataset]:
        """
        Retrieve all datasets extracted from a specific file.

        Args:
            file_id: UUID of the uploaded file.

        Returns:
            List of Dataset instances for the given file.
        """
        statement = select(Dataset).where(Dataset.file_id == file_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def update_dataset(self, dataset_id: UUID, updates: dict) -> Dataset | None:
        """
        Apply partial updates to an existing dataset.

        Args:
            dataset_id: UUID of the dataset to update.
            updates: Dictionary of field names to new values.

        Returns:
            Updated Dataset instance, or None if not found.
        """
        dataset = await self._get_by_id(dataset_id)
        if dataset is None:
            return None

        for field, value in updates.items():
            if hasattr(dataset, field):
                setattr(dataset, field, value)

        await self._session.flush()
        await self._session.refresh(dataset)
        return dataset

    async def delete_dataset(self, dataset_id: UUID) -> bool:
        """
        Delete a dataset by its primary key (cascades to columns, records, regions).

        Args:
            dataset_id: UUID of the dataset to delete.

        Returns:
            True if the dataset was deleted, False if not found.
        """
        return await self._delete_by_id(dataset_id)

    async def create_columns_batch(
        self, columns: list[DatasetColumn]
    ) -> list[DatasetColumn]:
        """
        Bulk insert dataset columns.

        Args:
            columns: List of DatasetColumn model instances.

        Returns:
            List of persisted DatasetColumn instances.
        """
        self._session.add_all(columns)
        await self._session.flush()
        for col in columns:
            await self._session.refresh(col)
        return columns

    async def create_records_batch(
        self, records: list[DatasetRecord]
    ) -> list[DatasetRecord]:
        """
        Bulk insert dataset records. Performance-optimized using add_all
        with a single flush for batch persistence.

        Args:
            records: List of DatasetRecord model instances.

        Returns:
            List of persisted DatasetRecord instances.
        """
        # NOTE: For large record sets, using add_all + single flush
        # is significantly faster than individual add + flush cycles.
        self._session.add_all(records)
        await self._session.flush()
        return records

    async def create_data_region(self, region: DataRegion) -> DataRegion:
        """
        Persist a data region to the database.

        Args:
            region: DataRegion model instance.

        Returns:
            Persisted DataRegion with server-generated fields populated.
        """
        self._session.add(region)
        await self._session.flush()
        await self._session.refresh(region)
        return region

    async def get_regions_by_file(self, file_id: UUID) -> list[DataRegion]:
        """
        Retrieve all data regions for a specific file.

        Args:
            file_id: UUID of the uploaded file.

        Returns:
            List of DataRegion instances for the file.
        """
        statement = select(DataRegion).where(DataRegion.file_id == file_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def query_records(
        self,
        dataset_id: UUID,
        filters: dict | None = None,
        sort: list[tuple[str, str]] | None = None,
        limit: int | None = None,
        offset: int = 0,
        columns: list[str] | None = None,
        aggregations: list[dict] | None = None,
    ) -> dict:
        """
        JSONB-aware query using PostgreSQL JSON operators.

        Builds SQL safely using SQLAlchemy constructs for filtering, sorting,
        and aggregation on JSONB data fields.

        Args:
            dataset_id: UUID of the dataset to query.
            filters: Optional dict of column_name -> value for equality filtering.
            sort: Optional list of (column_name, direction) tuples. direction is "asc" or "desc".
            limit: Optional max number of records to return.
            offset: Number of records to skip (default 0).
            columns: Optional list of column names to extract from JSONB.
            aggregations: Optional list of dicts with "function", "column", and optional "group_by".
                          Supported functions: COUNT, SUM, AVG.

        Returns:
            Dict with "records" (list of dicts), "total_count" (int),
            and "aggregations" (list of dicts or None).
        """
        # --- Total count query ---
        count_stmt = (
            select(func.count(DatasetRecord.id))
            .where(DatasetRecord.dataset_id == dataset_id)
        )
        count_stmt = self._apply_filters(count_stmt, filters)
        count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar_one()

        # --- Records query ---
        if columns:
            # Select specific JSONB keys using ->> operator
            select_columns = [DatasetRecord.id, DatasetRecord.row_index]
            for col_name in columns:
                select_columns.append(
                    DatasetRecord.data[col_name].astext.label(col_name)
                )
            stmt = select(*select_columns).where(
                DatasetRecord.dataset_id == dataset_id
            )
        else:
            stmt = select(DatasetRecord).where(
                DatasetRecord.dataset_id == dataset_id
            )

        stmt = self._apply_filters(stmt, filters)
        stmt = self._apply_sort(stmt, sort)

        # Pagination
        stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)

        if columns:
            records = [dict(row._mapping) for row in result.all()]
        else:
            records = [
                {
                    "id": str(record.id),
                    "row_index": record.row_index,
                    "data": record.data,
                    "source_sheet": record.source_sheet,
                    "source_row": record.source_row,
                }
                for record in result.scalars().all()
            ]

        # --- Aggregations ---
        agg_results = None
        if aggregations:
            agg_results = await self._execute_aggregations(
                dataset_id, aggregations, filters
            )

        return {
            "records": records,
            "total_count": total_count,
            "aggregations": agg_results,
        }

    # --- Private helpers for query_records ---

    def _apply_filters(self, stmt, filters: dict | None):
        """Apply JSONB equality filters to a statement."""
        if not filters:
            return stmt
        for col_name, value in filters.items():
            # Use ->> for text comparison of JSONB values
            stmt = stmt.where(
                DatasetRecord.data[col_name].astext == str(value)
            )
        return stmt

    def _apply_sort(self, stmt, sort: list[tuple[str, str]] | None):
        """Apply ORDER BY on JSONB extracted values."""
        if not sort:
            return stmt
        for col_name, direction in sort:
            json_col = DatasetRecord.data[col_name].astext
            if direction.lower() == "desc":
                stmt = stmt.order_by(json_col.desc())
            else:
                stmt = stmt.order_by(json_col.asc())
        return stmt

    async def _execute_aggregations(
        self,
        dataset_id: UUID,
        aggregations: list[dict],
        filters: dict | None,
    ) -> list[dict]:
        """Execute aggregation queries on JSONB data."""
        results = []

        for agg in aggregations:
            agg_func = agg.get("function", "").upper()
            col_name = agg.get("column")
            group_by_col = agg.get("group_by")

            # Build the aggregation expression
            if agg_func == "COUNT":
                agg_expr = func.count(DatasetRecord.id)
            elif agg_func == "SUM" and col_name:
                # Cast JSONB text to numeric for SUM
                agg_expr = func.sum(
                    cast(DatasetRecord.data[col_name].astext, Numeric)
                )
            elif agg_func == "AVG" and col_name:
                # Cast JSONB text to numeric for AVG
                agg_expr = func.avg(
                    cast(DatasetRecord.data[col_name].astext, Numeric)
                )
            else:
                results.append({"function": agg_func, "error": "unsupported"})
                continue

            # Build statement
            if group_by_col:
                group_col = DatasetRecord.data[group_by_col].astext.label(
                    "group_key"
                )
                stmt = (
                    select(group_col, agg_expr.label("value"))
                    .where(DatasetRecord.dataset_id == dataset_id)
                    .group_by(group_col)
                )
            else:
                stmt = select(agg_expr.label("value")).where(
                    DatasetRecord.dataset_id == dataset_id
                )

            stmt = self._apply_filters(stmt, filters)
            result = await self._session.execute(stmt)

            if group_by_col:
                rows = [
                    {"group": row.group_key, "value": float(row.value) if row.value else 0}
                    for row in result.all()
                ]
                results.append(
                    {"function": agg_func, "column": col_name, "groups": rows}
                )
            else:
                row = result.one()
                results.append(
                    {
                        "function": agg_func,
                        "column": col_name,
                        "value": float(row.value) if row.value else 0,
                    }
                )

        return results

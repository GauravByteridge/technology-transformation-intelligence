"""
ORM models for the dataset ingestion pipeline (App_DB).

Models:
- Dataset: First-class entity representing structured data extracted from a file
- DataRegion: A detected area within a file, classified by content structure
- DatasetColumn: Column definition within a dataset's inferred schema
- DatasetRecord: Individual record (row) within a normalized dataset
- DatasetRelationship: Candidate relationship between two datasets

All models inherit from AppBase and use UUID primary keys with timestamps.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class Dataset(AppBase):
    """First-class entity representing a structured dataset extracted from a file."""

    __tablename__ = "datasets"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    file_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("uploaded_files.id"), nullable=False
    )
    project_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    source_type: Mapped[str] = mapped_column(
        sa.String(20), nullable=False
    )  # xlsx, csv, json
    sheet_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    classification: Mapped[str] = mapped_column(
        sa.String(20), nullable=False
    )  # from ContentClassification enum
    record_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    confidence: Mapped[float] = mapped_column(
        sa.Float, nullable=False, default=0.0
    )
    status: Mapped[str] = mapped_column(
        sa.String(30), nullable=False, default="REVIEW_REQUIRED"
    )
    processing_error: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    # Relationships
    columns: Mapped[list["DatasetColumn"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    records: Mapped[list["DatasetRecord"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    regions: Mapped[list["DataRegion"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} name={self.name}>"


class DataRegion(AppBase):
    """A detected area within a file, classified by content structure.

    Each region has an independent processing_strategy determined by content
    classification, NOT by file type. A single file may produce regions with
    different strategies.
    """

    __tablename__ = "data_regions"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    file_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("uploaded_files.id"), nullable=False
    )
    dataset_id: Mapped[UUID | None] = mapped_column(
        sa.UUID,
        sa.ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    sheet_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    start_row: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    end_row: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    start_column: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    end_column: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    header_row: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    classification: Mapped[str] = mapped_column(
        sa.String(20), nullable=False
    )  # STRUCTURED, SEMI_STRUCTURED, UNSTRUCTURED, IGNORE
    processing_strategy: Mapped[str] = mapped_column(
        sa.String(20), nullable=False
    )  # DATASET_QUERY, RAG, HYBRID, IGNORE, REVIEW_REQUIRED
    confidence: Mapped[float] = mapped_column(
        sa.Float, nullable=False, default=0.0
    )
    classification_reason: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    warnings: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )  # JSON array as text
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    dataset: Mapped["Dataset | None"] = relationship(
        back_populates="regions"
    )

    def __repr__(self) -> str:
        return f"<DataRegion id={self.id} sheet={self.sheet_name}>"


class DatasetColumn(AppBase):
    """Column definition within a dataset's inferred schema."""

    __tablename__ = "dataset_columns"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    dataset_id: Mapped[UUID] = mapped_column(
        sa.UUID,
        sa.ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(
        sa.String(20), nullable=False
    )  # string, integer, decimal, boolean, date, datetime, unknown
    nullable: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True
    )
    column_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    sample_values: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )  # JSON array stored as text
    confidence: Mapped[float] = mapped_column(
        sa.Float, nullable=False, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship(back_populates="columns")

    def __repr__(self) -> str:
        return f"<DatasetColumn id={self.id} name={self.name}>"


class DatasetRecord(AppBase):
    """Individual record (row) within a normalized dataset.

    Uses JSONB for the data column to enable efficient structured querying
    within PostgreSQL (filtering, indexing on JSON paths).
    """

    __tablename__ = "dataset_records"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    dataset_id: Mapped[UUID] = mapped_column(
        sa.UUID,
        sa.ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_sheet: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    source_row: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship(back_populates="records")

    def __repr__(self) -> str:
        return f"<DatasetRecord id={self.id} row_index={self.row_index}>"


class DatasetRelationship(AppBase):
    """Candidate relationship between two datasets."""

    __tablename__ = "dataset_relationships"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    source_dataset_id: Mapped[UUID] = mapped_column(
        sa.UUID,
        sa.ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_dataset_id: Mapped[UUID] = mapped_column(
        sa.UUID,
        sa.ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_column: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    target_column: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    relationship_type: Mapped[str] = mapped_column(
        sa.String(30), nullable=False
    )  # primary_key, foreign_key, shared_identifier
    confidence: Mapped[float] = mapped_column(
        sa.Float, nullable=False, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<DatasetRelationship id={self.id} "
            f"source={self.source_dataset_id} target={self.target_dataset_id}>"
        )

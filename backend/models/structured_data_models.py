"""
SQLAlchemy ORM models for structured data storage.

These models store structured data extracted from Excel, CSV, and JSON files
in a queryable relational format, enabling SQL-based answering for numerical
and aggregation questions.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text, 
    Boolean, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from db.database import Base


class StructuredDataset(Base):
    """
    Represents a structured dataset extracted from a file.
    A single file (e.g., Excel workbook) may contain multiple datasets (sheets/tables).
    """
    __tablename__ = "structured_datasets"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    sheet_name = Column(String(255), nullable=True)  # NULL for CSV/JSON
    table_name = Column(String(255), nullable=True)  # Derived or explicit table name
    
    # Metadata extracted from the sheet
    document_title = Column(Text, nullable=True)  # e.g., "ENTERPRISE REPORT: ..."
    document_context = Column(Text, nullable=True)  # e.g., "Global Technology Transformation..."
    
    # Data range info
    header_row_index = Column(Integer, nullable=True)  # 0-based index
    data_start_row = Column(Integer, nullable=True)
    data_end_row = Column(Integer, nullable=True)
    row_count = Column(Integer, default=0)
    
    # Processing metadata
    source_type = Column(String(50), nullable=False)  # xlsx, csv, json
    data_classification = Column(String(50), default="structured")  # structured, semi-structured, unstructured
    ingestion_timestamp = Column(DateTime, default=datetime.utcnow)
    project_id = Column(Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    columns = relationship("StructuredColumn", back_populates="dataset", cascade="all, delete-orphan")
    rows = relationship("StructuredRow", back_populates="dataset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_dataset_file_sheet", "file_id", "sheet_name"),
    )

    def __repr__(self):
        return f"<StructuredDataset(id={self.id}, file='{self.file_name}', sheet='{self.sheet_name}')>"


class StructuredColumn(Base):
    """
    Represents a column in a structured dataset.
    Stores column metadata including inferred data types.
    """
    __tablename__ = "structured_columns"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("structured_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    column_name = Column(String(255), nullable=False)
    column_index = Column(Integer, nullable=False)  # 0-based position
    
    # Inferred type information
    data_type = Column(String(50), nullable=False)  # numeric, currency, percentage, date, text, id
    python_type = Column(String(50), nullable=True)  # int, float, str, datetime
    
    # For numeric columns
    is_currency = Column(Boolean, default=False)
    currency_symbol = Column(String(10), nullable=True)
    is_percentage = Column(Boolean, default=False)
    
    # Statistics (for validation)
    null_count = Column(Integer, default=0)
    unique_count = Column(Integer, default=0)
    
    # Semantic information
    description = Column(Text, nullable=True)
    
    # Relationship
    dataset = relationship("StructuredDataset", back_populates="columns")

    __table_args__ = (
        UniqueConstraint("dataset_id", "column_index", name="uq_dataset_column_idx"),
    )

    def __repr__(self):
        return f"<StructuredColumn(id={self.id}, name='{self.column_name}', type='{self.data_type}')>"


class StructuredRow(Base):
    """
    Represents a row of data in a structured dataset.
    Stores the actual data values as JSON for flexibility.
    """
    __tablename__ = "structured_rows"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("structured_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    row_index = Column(Integer, nullable=False)  # 0-based position within data rows
    
    # Row classification
    row_type = Column(String(50), default="data")  # data, summary, subtotal, header
    row_label = Column(String(255), nullable=True)  # e.g., "PORTFOLIO TOTAL / AVERAGE"
    
    # The actual data stored as JSON dict
    # Keys are column names, values are typed (numbers stay numbers)
    data = Column(JSON, nullable=False)
    
    # For quick lookup of primary identifiers
    primary_key_value = Column(String(255), nullable=True)  # e.g., project_id value
    
    # Relationship
    dataset = relationship("StructuredDataset", back_populates="rows")

    __table_args__ = (
        Index("idx_row_dataset_type", "dataset_id", "row_type"),
        Index("idx_row_pk_value", "dataset_id", "primary_key_value"),
    )

    def __repr__(self):
        return f"<StructuredRow(id={self.id}, dataset_id={self.dataset_id}, row_type='{self.row_type}')>"


class QueryLog(Base):
    """
    Logs queries for debugging and analysis.
    Tracks which pipeline handled each question.
    """
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    
    # Classification
    query_type = Column(String(50), nullable=False)  # STRUCTURED, UNSTRUCTURED, HYBRID
    confidence = Column(Float, nullable=True)
    
    # Execution details
    pipeline_used = Column(String(50), nullable=False)  # structured, rag, hybrid
    
    # For structured queries
    target_dataset = Column(String(255), nullable=True)
    target_columns = Column(JSON, nullable=True)
    sql_query = Column(Text, nullable=True)
    
    # Results
    answer = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)
    
    # Validation
    validated = Column(Boolean, default=False)
    validation_notes = Column(Text, nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    execution_time_ms = Column(Integer, nullable=True)
    
    project_id = Column(Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=True)

    def __repr__(self):
        return f"<QueryLog(id={self.id}, type='{self.query_type}', pipeline='{self.pipeline_used}')>"

"""
RAG_DB ORM models for document intelligence.

Models:
- Document: Uploaded file metadata and processing state
- DocumentChunk: Text chunks extracted from documents
- DocumentMetadata: Key-value metadata pairs for documents
- Embedding: Vector embeddings for document chunks

All models inherit from RAGBase and use UUID primary keys with
created_at/updated_at timestamps.
"""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import RAGBase

# Default embedding dimension — matches OpenAI text-embedding-ada-002.
# Configurable at runtime via EMBEDDING_DIMENSION env var for validation,
# but the database column is fixed at migration time.
EMBEDDING_DIMENSION = 1536


class Document(RAGBase):
    """
    Represents an uploaded document in the RAG pipeline.

    Tracks file metadata, processing lifecycle, and ownership.
    A document belongs to a project and may be associated with a data source.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    project_id: Mapped[str] = mapped_column(sa.Uuid, nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(sa.Uuid, nullable=True)
    file_name: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    processing_status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="pending"
    )
    processing_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(sa.Uuid, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    # Relationships
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    metadata_entries: Mapped[list["DocumentMetadata"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(RAGBase):
    """
    A text chunk extracted from a document.

    Retains positional information (chunk_index, page_number, section)
    to enable evidence tracing back to the source location.
    """

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    document_id: Mapped[str] = mapped_column(
        sa.Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="chunks")
    embedding: Mapped["Embedding | None"] = relationship(
        back_populates="chunk", cascade="all, delete-orphan", uselist=False
    )


class DocumentMetadata(RAGBase):
    """
    Key-value metadata associated with a document.

    Stores extracted metadata (title, author, creation date, etc.)
    as flexible key-value pairs.
    """

    __tablename__ = "document_metadata"

    id: Mapped[str] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    document_id: Mapped[str] = mapped_column(
        sa.Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    value: Mapped[str] = mapped_column(sa.String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="metadata_entries")


class Embedding(RAGBase):
    """
    Vector embedding for a document chunk.

    Stores the embedding vector generated by the configured Embedding Provider,
    along with the model name and dimension for traceability.
    """

    __tablename__ = "embeddings"

    id: Mapped[str] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    chunk_id: Mapped[str] = mapped_column(
        sa.Uuid,
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    embedding = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    model_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    dimension: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    # Relationships
    chunk: Mapped["DocumentChunk"] = relationship(back_populates="embedding")

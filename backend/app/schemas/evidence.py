"""
Evidence schemas for Phase 5 AI agent consumption.

Defines structured evidence types returned by semantic search (DocumentEvidence)
and dataset queries (StructuredEvidence). These are the building blocks for
source attribution in AI-generated responses.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentEvidence:
    """Evidence from semantic document search (includes Excel-region RAG content).

    Returned by DocumentSearchService when the AI agent queries ingested
    documents. Contains the relevant text excerpt with full source traceability.

    Attributes:
        file_name: Name of the source file.
        page_number: Page number in the source document (None for non-paginated).
        section: Section heading from the source (None if no heading detected).
        sheet_name: Excel sheet name when evidence comes from an Excel region.
        region: Region identifier (e.g., "rows 5-50") for Excel sources.
        excerpt: The relevant text content (chunk text).
        similarity_score: Cosine similarity score (0.0 to 1.0).
        document_id: UUID string of the stored document in RAG_DB.
        chunk_id: UUID string of the specific chunk in RAG_DB.
    """

    file_name: str
    page_number: int | None
    section: str | None
    sheet_name: str | None
    region: str | None
    excerpt: str
    similarity_score: float
    document_id: str
    chunk_id: str


@dataclass(frozen=True)
class StructuredEvidence:
    """Evidence from dataset query results.

    Returned when the AI agent queries structured datasets created from
    tabular file regions. Provides full context about where the data came
    from and what was returned.

    Attributes:
        file_name: Name of the source file.
        sheet_name: Excel sheet name (None for non-Excel sources).
        dataset_id: UUID string of the dataset in App_DB.
        region: Source region identifier (e.g., "A1:F50").
        row_range: Human-readable row range (e.g., "rows 5-15").
        column_info: List of column names involved in the query result.
        records: List of record dicts matching the query.
        query_context: Description of the query that produced these results.
    """

    file_name: str
    sheet_name: str | None
    dataset_id: str
    region: str | None
    row_range: str
    column_info: list[str]
    records: list[dict]
    query_context: str

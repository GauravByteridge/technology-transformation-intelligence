"""
Strands Agent Service for the Project Intelligence Hub.

Enhanced agentic RAG with intelligent query routing:
- Structured data queries using SQL-like operations
- Unstructured document search using vector similarity
- Hybrid queries combining both approaches

The agent automatically chooses the right approach based on the question type.
"""

import os
import re
import logging
from typing import Optional

from strands import Agent, tool
from strands.models.litellm import LiteLLMModel

from services.embeddings import EmbeddingGenerator
from db.chroma_client import query_embeddings, get_collection_count
from db.database import SessionLocal
from models.database_models import File
from models.structured_data_models import StructuredDataset, StructuredColumn, StructuredRow
from services.ai.query_classifier import QueryClassifier, QueryType
from services.structured.structured_query_service import StructuredQueryService
from services.structured.aggregation_service import AggregationService

logger = logging.getLogger(__name__)

# Singleton embedding generator for efficiency
_embedding_generator: Optional[EmbeddingGenerator] = None


def _get_embedding_generator() -> EmbeddingGenerator:
    """Get or create the singleton embedding generator."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator


def _get_db_session():
    """Get a database session for tool use."""
    return SessionLocal()


# ============================================================================
# STRUCTURED DATA TOOLS
# ============================================================================

@tool
def query_structured_data(
    question: str,
    dataset_name: str = "",
    column_name: str = "",
    operation: str = "auto"
) -> str:
    """
    Query structured data (Excel, CSV) for exact numerical answers.
    
    Use this tool for questions about:
    - Totals, sums, averages of financial data
    - Specific project costs, budgets, variances
    - Counting records
    - Finding maximum or minimum values
    
    DO NOT use this for document content questions (use search_documents instead).
    
    Args:
        question: The user's question about structured data
        dataset_name: Specific sheet/dataset name (e.g., "Financial Health"), or empty for auto-detect
        column_name: Specific column to query (e.g., "approved_budget"), or empty for auto-detect
        operation: One of: auto, sum, avg, max, min, count, lookup
    """
    db = _get_db_session()
    try:
        query_service = StructuredQueryService(db)
        classifier = QueryClassifier()
        
        # Convert empty strings to None for internal processing
        actual_dataset = dataset_name.strip() if dataset_name else None
        actual_column = column_name.strip() if column_name else None
        
        # Classify the question if operation is auto
        if operation == "auto":
            classification = classifier.classify(question)
            operation = classification.operation or "lookup"
            if not actual_dataset and classification.target_dataset:
                actual_dataset = classification.target_dataset
            if not actual_column and classification.target_columns:
                actual_column = classification.target_columns[0] if classification.target_columns else None
        
        # Find the dataset
        dataset = query_service.find_dataset(sheet_name=actual_dataset)
        if not dataset:
            # List available datasets
            datasets = query_service.list_datasets()
            if datasets:
                available = "\n".join([
                    f"  - {d['file_name']} / {d['sheet_name']} ({d['row_count']} rows)"
                    for d in datasets
                ])
                return f"Dataset '{actual_dataset}' not found. Available structured datasets:\n{available}"
            return "No structured datasets available. Only unstructured documents are loaded."
        
        # Find column if needed
        if actual_column:
            col = query_service.find_column(dataset.id, actual_column)
            if col:
                actual_column = col.column_name
        
        # Execute operation
        if operation == "sum":
            if not actual_column:
                return "Please specify which column to sum (e.g., approved_budget, actual_cost)"
            result = query_service.calculate_sum(dataset.id, actual_column)
        elif operation == "avg":
            if not actual_column:
                return "Please specify which column to average"
            result = query_service.calculate_average(dataset.id, actual_column)
        elif operation == "max":
            if not actual_column:
                return "Please specify which column to find maximum"
            result = query_service.get_max(dataset.id, actual_column)
        elif operation == "min":
            if not actual_column:
                return "Please specify which column to find minimum"
            result = query_service.get_min(dataset.id, actual_column)
        elif operation == "count":
            result = query_service.count_rows(dataset.id)
        else:  # lookup
            # Try to find specific value
            result = query_service.get_all_rows(dataset.id)
        
        if not result.success:
            return f"Query failed: {result.error}"
        
        # Format response
        logger.info(f"[STRUCTURED PIPELINE] Query: {question} -> Result: {result.data}")
        
        if isinstance(result.data, (int, float)):
            # Format as currency if appropriate
            if actual_column and any(kw in actual_column.lower() for kw in ["budget", "cost", "variance", "expense"]):
                formatted = f"${result.data:,.2f}" if isinstance(result.data, float) else f"${result.data:,}"
            else:
                formatted = f"{result.data:,.2f}" if isinstance(result.data, float) else f"{result.data:,}"
            
            return (
                f"STRUCTURED DATA RESULT:\n"
                f"Value: {formatted}\n"
                f"Source: {result.source_dataset}\n"
                f"Sheet: {result.source_sheet}\n"
                f"Column: {result.source_column}\n"
                f"Calculation: {result.calculation}\n"
                f"Records used: {result.row_count}"
            )
        elif isinstance(result.data, dict) and "value" in result.data:
            # MAX/MIN result
            val = result.data["value"]
            row = result.data.get("row", {})
            formatted = f"${val:,.2f}" if isinstance(val, float) else str(val)
            return (
                f"STRUCTURED DATA RESULT:\n"
                f"Value: {formatted}\n"
                f"Full record: {row}\n"
                f"Source: {result.source_dataset}/{result.source_sheet}\n"
                f"Calculation: {result.calculation}"
            )
        elif isinstance(result.data, list):
            count = len(result.data)
            preview = result.data[:5]
            return (
                f"STRUCTURED DATA RESULT:\n"
                f"Found {count} records\n"
                f"Sample: {preview}\n"
                f"Source: {result.source_dataset}/{result.source_sheet}"
            )
        
        return f"STRUCTURED DATA RESULT: {result.data}"
        
    finally:
        db.close()


@tool
def get_financial_summary(project_id: str = "") -> str:
    """
    Get financial summary from structured data.
    
    Returns portfolio-level financial metrics including:
    - Total approved budget
    - Total forecast cost
    - Total actual cost
    - Cost variance
    
    If project_id is provided, returns data for that specific project.
    If empty string or omitted, returns portfolio-level summary.
    
    Args:
        project_id: Project ID (e.g., "PRJ-001") for project-specific data, or empty for portfolio summary
    """
    db = _get_db_session()
    try:
        agg_service = AggregationService(db)
        
        # Treat empty string as None
        actual_project_id = project_id.strip() if project_id else None
        
        if actual_project_id:
            # Get specific project
            details = agg_service.get_project_financial_details(actual_project_id)
            if details:
                data = details["data"]
                return (
                    f"FINANCIAL DATA FOR {actual_project_id}:\n"
                    f"Approved Budget: ${data.get('approved_budget', 0):,.2f}\n"
                    f"Forecast Cost: ${data.get('forecast_total_cost', 0):,.2f}\n"
                    f"Actual Cost: ${data.get('actual_cost', 0):,.2f}\n"
                    f"Cost Variance: ${data.get('cost_variance', 0):,.2f}\n"
                    f"Source: {details['source_file']}/{details['source_sheet']}"
                )
            return f"Project {actual_project_id} not found in financial data."
        
        # Get portfolio summary
        summary = agg_service.get_financial_summary()
        if summary:
            logger.info(f"[STRUCTURED PIPELINE] Financial summary retrieved: ${summary.total_approved_budget:,.2f}")
            return (
                f"PORTFOLIO FINANCIAL SUMMARY:\n"
                f"Total Approved Budget: ${summary.total_approved_budget:,.2f}\n"
                f"Total Forecast Cost: ${summary.total_forecast_cost:,.2f}\n"
                f"Total Actual Cost: ${summary.total_actual_cost:,.2f}\n"
                f"Total Cost Variance: ${summary.total_cost_variance:,.2f}\n"
                f"Number of Projects: {summary.project_count}\n"
                f"Currency: {summary.currency}\n"
                f"Source: {summary.source_file}/{summary.source_sheet}"
            )
        
        return "No financial data available. Please check if financial sheets have been uploaded."
        
    finally:
        db.close()


@tool
def list_structured_datasets() -> str:
    """
    List all available structured datasets with their columns.
    
    Use this to understand what structured data is available for querying.
    Shows file names, sheet names, row counts, and column information.
    """
    db = _get_db_session()
    try:
        query_service = StructuredQueryService(db)
        datasets = query_service.list_datasets()
        
        if not datasets:
            return "No structured datasets found. Only unstructured documents may be available."
        
        output = [f"AVAILABLE STRUCTURED DATASETS ({len(datasets)} total):"]
        
        for ds in datasets:
            cols = [f"{c['name']} ({c['type']})" for c in ds['columns'][:5]]
            col_str = ", ".join(cols)
            if len(ds['columns']) > 5:
                col_str += f", ... ({len(ds['columns'])} total)"
            
            output.append(
                f"\n{ds['file_name']} / {ds['sheet_name']}:\n"
                f"  Rows: {ds['row_count']}\n"
                f"  Columns: {col_str}"
            )
        
        return "\n".join(output)
        
    finally:
        db.close()


# ============================================================================
# UNSTRUCTURED DOCUMENT TOOLS
# ============================================================================

@tool
def search_documents(query: str, n_results: int = 8) -> str:
    """
    Search unstructured documents (PDFs, text files, document sheets) for relevant content.
    
    Use this tool for questions about:
    - Document content, policies, procedures
    - Audit findings and recommendations
    - BRD requirements and objectives
    - Meeting notes, Jira descriptions
    - Any qualitative or textual information
    
    DO NOT use this for numerical totals or aggregations (use query_structured_data instead).
    
    Args:
        query: The search query to find relevant information. Be specific.
        n_results: Number of results to return (default 8, max 20)
    """
    n_results = min(max(n_results, 1), 20)

    try:
        embedding_gen = _get_embedding_generator()
        embedding = embedding_gen.generate([query])[0]
        results = query_embeddings(embedding, n_results=n_results)

        docs = results.get("documents", [[]])[0] or []
        metas = results.get("metadatas", [[]])[0] or []
        distances = results.get("distances", [[]])[0] or []

        if not docs:
            return "No relevant information found in documents. Try rephrasing or check if relevant files have been uploaded."

        # Filter by relevance (cosine distance < 0.7 is considered relevant)
        output = []
        for doc, meta, dist in zip(docs, metas, distances):
            if dist < 0.7:  # cosine distance threshold
                source = meta.get("file_name", "unknown")
                category = meta.get("category", "unknown")
                section = meta.get("section", "")
                page = meta.get("page_number", "")
                
                source_info = f"[Source: {source}"
                if section:
                    source_info += f" | Section: {section}"
                if page:
                    source_info += f" | Page: {page}"
                source_info += f" | Category: {category} | Relevance: {1 - dist:.2f}]"
                
                output.append(f"{source_info}\n{doc}")

        if not output:
            return (
                f"Found {len(docs)} results but none were sufficiently relevant (relevance < 0.3). "
                "Try more specific search terms or check if relevant files have been uploaded."
            )

        logger.info(f"[UNSTRUCTURED PIPELINE] Search: {query} -> Found {len(output)} relevant chunks")
        return "\n\n---\n\n".join(output)

    except Exception as e:
        logger.error(f"search_documents error: {e}")
        return f"Search failed: {str(e)}"


@tool
def get_files_by_category(category: str) -> str:
    """
    Get a list of uploaded files filtered by category.
    Use this to understand what data is available in a specific category
    before searching for detailed information.

    Args:
        category: One of: Project Costs, Burndown, Audit, IT Controls,
                  Remediation, Business Intelligence, Internal Data, Other
    """
    db = _get_db_session()
    try:
        files = db.query(File).filter(File.category == category).all()
        if not files:
            return f"No files found in category '{category}'. Available categories: Project Costs, Burndown, Audit, IT Controls, Remediation, Business Intelligence, Internal Data, Other."

        result_lines = [f"Files in category '{category}':"]
        for f in files:
            result_lines.append(
                f"  - {f.file_name} ({f.file_type}, {f.chunk_count} chunks, uploaded {f.uploaded_at.strftime('%Y-%m-%d')})"
            )
        return "\n".join(result_lines)
    finally:
        db.close()


@tool
def list_all_files() -> str:
    """
    Get a summary of all uploaded files with their categories and types.
    Use this at the start to understand what data is available before answering.
    """
    db = _get_db_session()
    try:
        files = db.query(File).all()
        if not files:
            return "No files have been uploaded yet. Ask the user to upload relevant files first."

        # Group by category
        by_category: dict[str, list[str]] = {}
        for f in files:
            cat = f.category or "Uncategorized"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f"{f.file_name} ({f.file_type})")

        result_lines = [f"Total files: {len(files)}"]
        for cat, file_list in sorted(by_category.items()):
            result_lines.append(f"\n[{cat}] ({len(file_list)} files)")
            for fname in file_list:
                result_lines.append(f"  - {fname}")

        return "\n".join(result_lines)
    finally:
        db.close()


@tool
def get_knowledge_base_stats() -> str:
    """
    Get statistics about the knowledge base: total chunks, total files, structured datasets.
    Useful for understanding the size and scope of available data.
    """
    db = _get_db_session()
    try:
        file_count = db.query(File).count()
        files = db.query(File).all()
        total_file_chunks = sum(f.chunk_count for f in files)
        
        # Get ChromaDB count
        chroma_count = get_collection_count()
        
        # Get structured data stats
        dataset_count = db.query(StructuredDataset).count()
        total_struct_rows = db.query(StructuredRow).filter(
            StructuredRow.row_type == "data"
        ).count()

        return (
            f"Knowledge Base Statistics:\n"
            f"  - Total files: {file_count}\n"
            f"  - Total text chunks (unstructured): {total_file_chunks}\n"
            f"  - Indexed vectors in ChromaDB: {chroma_count}\n"
            f"  - Structured datasets: {dataset_count}\n"
            f"  - Structured data rows: {total_struct_rows}"
        )
    finally:
        db.close()


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """You are the AI assistant for Project Intelligence Hub.
Your role is to help users understand and analyse information from uploaded project files.

## CRITICAL: CHOOSING THE RIGHT TOOL

You have TWO types of data available:

### 1. STRUCTURED DATA (for exact numbers)
Use `query_structured_data` or `get_financial_summary` for:
- Questions about totals, sums, averages
- Questions about budgets, costs, expenses, variances
- Questions asking "how much", "what is the total", "what is the sum"
- Questions about specific project financial data
- Numerical comparisons (highest, lowest, above X)

Examples:
- "What is the portfolio total approved budget?" → Use `get_financial_summary` or `query_structured_data`
- "What is the actual cost for PRJ-005?" → Use `query_structured_data` with project lookup
- "Which project has the highest budget?" → Use `query_structured_data` with operation=max

### 2. UNSTRUCTURED DATA (for document content)
Use `search_documents` for:
- Questions about document content, policies, procedures
- Questions about audit findings, recommendations
- Questions about BRD objectives, requirements
- Qualitative questions ("describe", "explain", "what does X say")
- Questions about meeting notes, issues, risks described in text

Examples:
- "What are the audit findings?" → Use `search_documents`
- "What does the BRD say about budget approval?" → Use `search_documents`
- "Summarize the remediation strategy" → Use `search_documents`

## ANSWERING NUMERICAL QUESTIONS

For numerical/financial questions:
1. FIRST call `query_structured_data` or `get_financial_summary`
2. The tool will return the EXACT value from the database
3. Report this exact value - DO NOT recalculate or estimate
4. DO NOT use `search_documents` for numerical totals

If the structured query returns a value like:
"STRUCTURED DATA RESULT: Value: $33,800,000..."

Then your answer should report exactly "$33,800,000" - not an estimate.

## TOOL USAGE RULES

1. Tool responses are internal working information.
2. Never return raw tool output directly to the user.
3. Always transform tool results into a polished, natural-language response.
4. Do not expose technical details like ChromaDB, embeddings, SQL, etc.
5. Cite sources properly.

## FORMATTING RULES

NEVER use tables with | characters. Use numbered lists or bullet points instead.

For financial summaries:
### Financial Summary
- **Total Approved Budget**: $33,800,000
- **Total Actual Cost**: $20,750,000
- **Projects**: 15

## EVIDENCE

For numerical answers, include source evidence:
- File: Executive_Portfolio_Report.xlsx
- Sheet: Financial Health
- Calculation: SUM(approved_budget) or "Summary row: PORTFOLIO TOTAL / AVERAGE"

## IMPORTANT

- For NUMERICAL questions, prefer structured data tools
- For DOCUMENT questions, use search_documents
- Never hallucinate numbers - if structured data is unavailable, say so
- Always cite your sources
"""


class StrandsRAGAgent:
    """Wrapper class for the Strands-based RAG agent with intelligent routing."""

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """
        Initialize the Strands RAG agent.

        Args:
            groq_api_key: Groq API key. If None, reads from GROQ_API_KEY env variable.
            model_id: LiteLLM model identifier. If None, reads from GROQ_MODEL env variable.
        """
        self._api_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
        env_model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        
        # Map unsupported models to gpt-oss-120b
        unsupported_models = ("compound-beta", "compound", "compound-mini", "groq/compound", "groq/compound-mini")
        if env_model in unsupported_models:
            logger.warning(f"GROQ_MODEL={env_model} is not supported by LiteLLM. Falling back to openai/gpt-oss-120b")
            env_model = "openai/gpt-oss-120b"
        
        if "llama-3.3" in env_model or "llama-3.1" in env_model or "llama-4-scout" in env_model:
            logger.warning(f"GROQ_MODEL={env_model} is deprecated. Falling back to openai/gpt-oss-120b")
            env_model = "openai/gpt-oss-120b"
        
        self._model_id = model_id or f"groq/{env_model}"
        self._agent: Optional[Agent] = None

    def _build_agent(self) -> Agent:
        """Build and return the Strands agent."""
        if not self._api_key:
            raise RuntimeError("Groq API key is not configured. Set the GROQ_API_KEY environment variable.")

        logger.info(f"Building Strands agent with model: {self._model_id}")

        model = LiteLLMModel(
            model_id=self._model_id,
            params={
                "temperature": 0.3,
                "max_tokens": 4096,
                "api_key": self._api_key,
            },
        )

        return Agent(
            model=model,
            tools=[
                # Structured data tools
                query_structured_data,
                get_financial_summary,
                list_structured_datasets,
                # Unstructured document tools
                search_documents,
                get_files_by_category,
                list_all_files,
                get_knowledge_base_stats,
            ],
            system_prompt=SYSTEM_PROMPT,
        )

    def query(self, question: str) -> dict:
        """
        Process a question using the Strands agent.

        Args:
            question: The user's natural language question.

        Returns:
            Dict with 'answer' (str) and 'sources' (list of file names).
        """
        # Pre-classify to log which pipeline will be used
        classifier = QueryClassifier()
        classification = classifier.classify(question)
        logger.info(f"Query pre-classification: {classification.query_type.value} (confidence: {classification.confidence:.2f})")
        
        agent = self._build_agent()

        try:
            result = agent(question)
            answer = str(result)

            # Extract source file names from the conversation
            sources = self._extract_sources(result, answer)

            return {
                "answer": answer,
                "sources": list(sources),
                "pipeline": classification.query_type.value,
            }

        except Exception as e:
            logger.error(f"Strands agent error: {e}")
            raise RuntimeError(f"AI agent failed: {str(e)}") from e

    def _extract_sources(self, result, answer: str) -> set[str]:
        """Extract source file names from agent result and answer text."""
        sources = set()

        # Pattern to match [Source: filename ...] in the answer
        source_pattern = r'\[Source:\s*([^\|\]]+)'
        for match in re.findall(source_pattern, answer):
            sources.add(match.strip())
        
        # Also look for "Source: filename" format
        simple_pattern = r'Source:\s*([^\n\|]+)'
        for match in re.findall(simple_pattern, answer):
            cleaned = match.strip()
            if cleaned and not cleaned.startswith("$"):
                sources.add(cleaned)

        # Check message history if available
        if hasattr(result, "message_history") and result.message_history:
            for msg in result.message_history:
                if hasattr(msg, "content"):
                    content = msg.content
                    if isinstance(content, list):
                        for block in content:
                            if hasattr(block, "text") and block.text:
                                for match in re.findall(source_pattern, block.text):
                                    sources.add(match.strip())
                    elif isinstance(content, str):
                        for match in re.findall(source_pattern, content):
                            sources.add(match.strip())

        return sources

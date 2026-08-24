// Re-export relevant types from the shared types module
export type {
  AIQueryRequest,
  AIResponse,
  ChatMessage,
  Conversation,
  QueryHistoryEntry,
  SourceEvidence,
  SourceType,
} from '@/types';

// ---------------------------------------------------------------------------
// Phase 8 — Cross-Source Intelligence: Strongly-typed response fields
// ---------------------------------------------------------------------------

/** Identifies a data source consulted during query execution. */
export interface SourceReference {
  source_id: string;
  source_type: 'postgresql' | 'mongodb' | 'document';
  source_name: string;
  object_name: string;
  records_returned: number;
  query_duration_ms: number;
}

/** A single piece of evidence linking an answer claim to retrieved data. */
export interface EvidenceItem {
  evidence_id: string;
  source_id: string;
  source_type: 'postgresql' | 'mongodb' | 'document';
  source_name: string;
  object_name: string;
  // Database-specific
  database_name?: string;
  schema_name?: string;
  table_name?: string;
  collection_name?: string;
  column_names?: string[];
  record_reference?: string;
  records_summary?: Record<string, unknown>;
  // Document-specific
  document_id?: string;
  file_name?: string;
  page_number?: number;
  sheet_name?: string;
  section?: string;
  // Common
  excerpt: string;
  confidence: 'retrieved_fact' | 'derived_calculation' | 'ai_explanation';
}

/** A single step in the data lineage execution trace. */
export interface LineageStep {
  step_type: 'catalog_lookup' | 'tool_invocation' | 'synthesis';
  tool_name?: string;
  source_id?: string;
  source_name?: string;
  object_name?: string;
  status: 'success' | 'failed' | 'timeout';
  duration_ms: number;
  records_count: number;
  timestamp: string;
  error?: string;
}

/** Full lineage trace for a single AI query execution. */
export interface LineageTrace {
  query_id: string;
  question: string;
  steps: LineageStep[];
  total_duration_ms: number;
  sources_consulted: string[];
  failed_sources: string[];
  is_partial: boolean;
}

/** Information about a source that failed during partial execution. */
export interface PartialFailureInfo {
  source: string;
  error: string;
}

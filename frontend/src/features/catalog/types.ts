// ---------------------------------------------------------------------------
// Phase 8 — Enterprise Data Catalog types
// ---------------------------------------------------------------------------

/** Describes a single field within a catalog entry (table column or document field). */
export interface CatalogField {
  name: string;
  field_type: string;
  nullable: boolean;
  is_primary_key: boolean;
  semantic_label?: string;
  semantic_description?: string;
  is_project_field: boolean;
  is_sensitive: boolean;
}

/** A foreign key relationship between catalog entries. */
export interface ForeignKeyRef {
  column: string;
  references_table: string;
  references_column: string;
}

/** A fully-resolved catalog entry representing a discovered database object. */
export interface CatalogEntry {
  entry_id: string;
  source_id: string;
  source_type: 'postgresql' | 'mongodb' | 'document';
  source_name: string;
  // Technical metadata
  database_name?: string;
  schema_name?: string;
  object_name: string;
  object_type: 'table' | 'collection' | 'view' | 'document';
  fields: CatalogField[];
  primary_keys: string[];
  foreign_keys: ForeignKeyRef[];
  indexes: string[];
  // Semantic metadata
  semantic_name?: string;
  semantic_description?: string;
  domain_tags: string[];
  query_capabilities: string[];
  suggested_queries: string[];
  confidence: 'high' | 'medium' | 'low';
  // Project relationships
  project_fields: string[];
  // Versioning
  version: number;
  discovered_at: string;
}

/** Maps a catalog entry to a specific project via a project-identifying field. */
export interface ProjectMapping {
  source_id: string;
  catalog_entry_id: string;
  project_id: string;
  project_field: string;
  mapping_type: 'discovered' | 'configured';
}

/** Result of a source discovery operation. */
export interface DiscoveryResult {
  source_id: string;
  success: boolean;
  objects_discovered: number;
  fields_discovered: number;
  relationships_discovered: number;
  project_fields_found: string[];
  duration_ms: number;
  error?: string;
  discovered_at: string;
}

/** Semantic profile generated from technical metadata during discovery. */
export interface SemanticProfile {
  semantic_name: string;
  description: string;
  domain_tags: string[];
  query_capabilities: string[];
  suggested_questions: string[];
  confidence: 'high' | 'medium' | 'low';
  project_fields: string[];
}

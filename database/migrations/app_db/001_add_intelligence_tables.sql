-- Migration: Add Enterprise Intelligence tables
-- Phase: Full Implementation (UI + DB spec)
-- Tables: data_source_credentials, data_source_discovery_runs,
--          catalog_fields, catalog_relationships, catalog_versions,
--          catalog_project_mappings, document_versions, document_processing_runs,
--          query_source_usage, evidence, lineage_runs, lineage_nodes,
--          executive_briefs, brief_sources

-- ────────────────────────────────────────────────────────────────────────────
-- Data Source Credentials
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS data_source_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    credential_type VARCHAR(50) NOT NULL,
    secret_reference VARCHAR(500) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_data_source_credentials_source
    ON data_source_credentials(data_source_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Data Source Discovery Runs
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS data_source_discovery_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    objects_discovered INTEGER NOT NULL DEFAULT 0,
    fields_discovered INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    catalog_version INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_discovery_runs_source
    ON data_source_discovery_runs(data_source_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Catalog Versions
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS catalog_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    discovery_run_id UUID NOT NULL REFERENCES data_source_discovery_runs(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_catalog_versions_source_version UNIQUE (data_source_id, version_number)
);

-- ────────────────────────────────────────────────────────────────────────────
-- Catalog Fields
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS catalog_fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalog_entry_id UUID NOT NULL REFERENCES catalog_entries(id) ON DELETE CASCADE,
    field_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    data_type VARCHAR(100) NOT NULL,
    semantic_type VARCHAR(100),
    description TEXT,
    nullable BOOLEAN NOT NULL DEFAULT TRUE,
    is_identifier BOOLEAN NOT NULL DEFAULT FALSE,
    is_project_key BOOLEAN NOT NULL DEFAULT FALSE,
    is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    sample_metadata JSONB,
    confidence_score NUMERIC(5,4),
    ordinal_position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_catalog_fields_entry
    ON catalog_fields(catalog_entry_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Catalog Relationships
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS catalog_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entry_id UUID NOT NULL REFERENCES catalog_entries(id) ON DELETE CASCADE,
    target_entry_id UUID NOT NULL REFERENCES catalog_entries(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    source_field_id UUID REFERENCES catalog_fields(id),
    target_field_id UUID REFERENCES catalog_fields(id),
    confidence_score NUMERIC(5,4),
    discovered_by VARCHAR(100) NOT NULL DEFAULT 'discovery_engine',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_catalog_relationships_source
    ON catalog_relationships(source_entry_id);
CREATE INDEX IF NOT EXISTS ix_catalog_relationships_target
    ON catalog_relationships(target_entry_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Catalog Project Mappings
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS catalog_project_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalog_entry_id UUID NOT NULL REFERENCES catalog_entries(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    mapping_type VARCHAR(50) NOT NULL DEFAULT 'automatic',
    mapping_expression JSONB,
    confidence_score NUMERIC(5,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_catalog_project_mappings_entry_project UNIQUE (catalog_entry_id, project_id)
);

-- ────────────────────────────────────────────────────────────────────────────
-- Document Versions (App_DB, cross-DB reference to RAG documents)
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    checksum VARCHAR(128) NOT NULL,
    storage_reference TEXT NOT NULL,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_document_versions_doc_version UNIQUE (document_id, version_number)
);

CREATE INDEX IF NOT EXISTS ix_document_versions_doc
    ON document_versions(document_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Document Processing Runs
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS document_processing_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    parser_type VARCHAR(100),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    chunks_created INTEGER NOT NULL DEFAULT 0,
    datasets_created INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS ix_document_processing_runs_doc
    ON document_processing_runs(document_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Query Source Usage
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS query_source_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id UUID NOT NULL REFERENCES query_history(id) ON DELETE CASCADE,
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    catalog_entry_id UUID REFERENCES catalog_entries(id),
    tool_name VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    records_retrieved INTEGER NOT NULL DEFAULT 0,
    chunks_retrieved INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_query_source_usage_query
    ON query_source_usage(query_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Evidence
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id UUID NOT NULL REFERENCES query_history(id) ON DELETE CASCADE,
    query_source_usage_id UUID NOT NULL REFERENCES query_source_usage(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL,
    source_reference JSONB,
    content TEXT,
    structured_value JSONB,
    page_number INTEGER,
    sheet_name VARCHAR(255),
    record_reference VARCHAR(500),
    relevance_score NUMERIC(5,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_evidence_query
    ON evidence(query_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Lineage Runs
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS lineage_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id UUID NOT NULL UNIQUE REFERENCES query_history(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────────
-- Lineage Nodes
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS lineage_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lineage_run_id UUID NOT NULL REFERENCES lineage_runs(id) ON DELETE CASCADE,
    node_type VARCHAR(50) NOT NULL,
    node_key VARCHAR(255) NOT NULL,
    label VARCHAR(500) NOT NULL,
    source_id UUID REFERENCES data_sources(id),
    catalog_entry_id UUID REFERENCES catalog_entries(id),
    tool_name VARCHAR(255),
    metadata JSONB,
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_lineage_nodes_run
    ON lineage_nodes(lineage_run_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Executive Briefs
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS executive_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    content JSONB,
    generated_by_query UUID REFERENCES query_history(id),
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_executive_briefs_project
    ON executive_briefs(project_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Brief Sources
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS brief_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_id UUID NOT NULL REFERENCES executive_briefs(id) ON DELETE CASCADE,
    evidence_id UUID REFERENCES evidence(id),
    query_id UUID REFERENCES query_history(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_brief_sources_brief
    ON brief_sources(brief_id);

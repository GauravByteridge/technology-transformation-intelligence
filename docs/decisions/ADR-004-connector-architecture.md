# ADR-004: Capability-Based Connector Architecture

## Status

Accepted

## Context

The platform needs to connect to multiple external data sources (PostgreSQL, MongoDB, and future sources like MySQL, SQL Server, Snowflake, REST APIs). Each source has different:

- Query semantics (SQL vs MongoDB aggregation pipelines vs REST calls)
- Authentication mechanisms
- Schema discovery capabilities
- Connection management patterns

We needed an abstraction that enables:

- Adding new connector types without modifying existing business logic
- AI tools that retrieve data without knowing which specific database type backs a source
- Consistent error handling and metadata across all connector types
- Read-only access enforcement for security

We considered three approaches:

1. **Unified SQL abstraction**: Force all sources into SQL-like query semantics
2. **Capability-based protocol**: Define a common interface with source-native query formats
3. **No abstraction**: Direct integration per source type scattered through services

## Decision

The platform uses a **capability-based DataSourceConnector protocol** with a **ConnectorRegistry** for type resolution. Each connector:

- Implements a common interface (`test_connection`, `discover_metadata`, `discover_schema`, `execute_read`)
- Accepts source-native query formats (SQL for PostgreSQL, aggregation dicts for MongoDB)
- Exposes only read operations (write access excluded by design)
- Raises domain-specific errors with source context

The registry maps source type strings to connector implementations and supports runtime resolution.

## Reasoning

**Why capability-based over unified SQL:**

- MongoDB queries are fundamentally different from SQL. Forcing MongoDB into SQL semantics loses expressiveness and creates a leaky abstraction.
- Each source type has unique strengths — the connector should expose them, not hide them behind a lowest-common-denominator interface.
- The AI tools invoke connectors by business intent (e.g., "query finance data for project X"). The tool layer handles translation to source-native formats.

**Why a registry pattern:**

- Adding a new connector type requires creating one new file and registering it — zero changes to existing connectors, services, or AI tools.
- The registry provides runtime validation (unsupported types produce clear errors with available alternatives).
- Services resolve connectors dynamically from stored source configurations.

**Why read-only by design:**

- External data sources are customer/business databases. The platform should never modify them.
- Read-only enforcement is documented as a database-level responsibility (credentials with SELECT-only grants). The connector interface simply does not expose write operations.

## Consequences

### Positive

- New source types can be added without modifying existing code (Open/Closed Principle)
- Each connector can fully leverage its native capabilities
- Clear error hierarchy (DataSourceConnectionError, SchemaDiscoveryError, QueryExecutionError) with source context
- AI tools remain source-agnostic — they request data by intent, not by SQL dialect
- Read-only interface prevents accidental data modification

### Negative

- AI tools must handle different query formats when invoking connectors
- Testing requires mocking source-specific behaviors
- The protocol defines method signatures but cannot enforce semantic correctness at compile time

### Neutral

- The architecture supports future connectors (MySQL, Snowflake, REST) without structural changes
- Full query execution implementation is deferred to Phase 1 — Phase 0 proves the pattern with `test_connection()`

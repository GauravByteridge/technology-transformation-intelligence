# ADR-008: Project as Primary Business Context

## Status

Accepted

## Context

The platform manages multiple types of business information: finance data, SDLC metrics, resource allocations, audit findings, controls, remediation plans, and ingested documents. Each of these data categories needs to be scoped to a meaningful business boundary for both data isolation and AI query accuracy.

We needed to determine the primary organizational unit that:
1. Scopes all business data consistently.
2. Provides the context boundary for AI queries.
3. Supports multiple data sources of different types.
4. Maps naturally to how users think about their work.

Alternatives considered:
- **Organization-level scoping** — too broad; a single org may have dozens of unrelated transformation efforts.
- **Data-source-level scoping** — too narrow; a single business question often spans multiple sources.
- **User-level scoping** — doesn't reflect team collaboration or shared business context.

## Decision

We designate **Project** as the primary business context. All business information connects to a project. All AI queries are scoped by the currently selected project.

Specifically:
- Every data source association is linked to a project via `project_data_sources`.
- Every conversation and AI query carries a `project_id`.
- Every AI tool receives `project_id` and scopes its data retrieval to that project.
- Every uploaded document is associated with a project.
- A project can have multiple data sources of different types (PostgreSQL for finance, MongoDB for resources, uploaded documents for meeting notes).

## Reasoning

- **Natural mental model** — Technology transformation work is organized by project. Users ask questions like "What's the budget status of Project X?" not "What's in Database Y?"
- **AI query scoping** — The agent needs a clear boundary to avoid cross-contamination of data between unrelated efforts. Project provides this boundary.
- **Multi-source aggregation** — A project can have finance in PostgreSQL, JIRA data in MongoDB, and meeting notes as documents. The AI synthesizes across all sources within the project boundary.
- **Access control readiness** — When authorization is added in future phases, project membership provides a natural permission boundary.
- **Data source reuse** — A single external database can be associated with multiple projects if needed (many-to-many relationship via `project_data_sources`).

## Consequences

### Positive

- Clear, consistent scoping for all data and AI queries.
- AI tools have a single `project_id` parameter for data isolation — simple and effective.
- Frontend navigation is project-centric, matching user expectations.
- Multi-source queries are naturally bounded without complex filter logic.
- The same external source can serve multiple projects when appropriate.

### Negative

- Cross-project queries (e.g., "compare budgets across all projects") require explicit handling — Phase 0 does not support this.
- Orphaned data sources (not linked to any project) need lifecycle management in future phases.
- Project deletion has cascading implications across conversations, documents, and source associations.
- Very large organizations with hundreds of projects may need project grouping or filtering in future phases.

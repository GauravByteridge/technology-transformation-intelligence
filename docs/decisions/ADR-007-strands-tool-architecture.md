# ADR-007: Strands Tool Architecture

## Status

Accepted

## Context

The platform uses an AI agent to answer natural-language questions by gathering data from multiple sources (internal databases, external connectors, document embeddings). The agent must:

1. Access project-scoped data from various backends.
2. Never receive database credentials or connection strings.
3. Be testable in isolation without real data sources.
4. Support adding new data domains without modifying existing code.

We needed an architecture that separates **what the agent wants** (data) from **how data is retrieved** (implementation details).

## Decision

We adopt a **tool-mediated architecture** where the AI agent invokes domain-scoped tools by business intent. Tools are thin callables registered in a `ToolRegistry`. Each tool delegates to domain services, which in turn call repositories or connectors.

```
Agent → Tool (by name) → Service → Repository/Connector → Data Source
```

Key constraints:

- The agent invokes tools by **business-intent names** (e.g., `get_project_context`, `query_project_finance`), not by data-source identifiers.
- Tools **call domain services only** — never repositories, connectors, or database drivers directly.
- Tools **never receive credentials** as parameters. Database sessions are created per-invocation by the composition root, not passed through the agent.
- Tools return structured dicts with a `source_label` for attribution — the agent never sees internal implementation details like table names or connection strings.
- The agent boundary is enforced by the `ToolRegistry`: the agent can only call what is registered.

## Reasoning

- **Security** — Credentials never enter the agent's context. Even if the LLM's prompt were leaked, no secrets would be exposed.
- **Testability** — Tools are individually testable async functions. The agent can be tested with mock tool functions without a database.
- **Extensibility** — Adding a new domain (e.g., SDLC, audit, resources) requires only:
  1. Creating a tool function in `app/ai/tools/<domain>_tools.py`.
  2. Registering it in the composition root.
  No changes to the agent, existing tools, or services.
- **Project scoping** — Every tool receives `project_id` and scopes its queries to that project, preventing cross-project data leakage.
- **Partial failure resilience** — If one tool fails, others still return data. The response is marked `is_partial: true` with `failed_sources` listing what went wrong.

## Consequences

### Positive

- Clear security boundary: the agent operates in a credential-free sandbox.
- Tools are independently unit-testable without database or LLM dependencies.
- Adding capabilities is purely additive — existing tools remain unchanged.
- Source attribution is natural: each tool returns its `source_label`, aggregated into the response.
- The same tool architecture works identically in Demo Mode (seeded DB) and Live Mode (real data).

### Negative

- In Phase 0, the agent uses a simplified invocation pattern (call all registered tools). Full LLM-driven tool selection is deferred to Phase 1 when Strands is fully integrated.
- Each tool invocation creates a new database session, which adds slight overhead compared to a single shared session. This ensures isolation and proper lifecycle management.
- Developers must remember the boundary: tools → services only. Code review must catch violations where a tool directly imports a repository or connector.

## Implementation Details

### Tool Registration

```python
# In composition root (dependencies.py)
registry = ToolRegistry()
registry.register("get_project_context", project_context_tool_fn)
registry.register("query_project_finance", finance_tool_fn)
```

### Tool Function Pattern

```python
# app/ai/tools/project_tools.py
async def get_project_context(project_id: UUID) -> dict:
    """Retrieve project context via service layer."""
    # Session created per-invocation by the composition root wrapper
    project = await project_service.get_project(project_id)
    return {
        "source_label": "Project Database",
        "source_type": "internal",
        "record_count": 1,
        "data": {"name": project.name, "status": project.status, ...},
    }
```

### Agent Invocation Flow

1. API layer generates `query_id`, calls `AIService.execute_query()`.
2. `AIService` invokes `AIAgent.invoke()` with question and project context.
3. Agent determines relevant tools and calls each with `project_id`.
4. Each tool creates a fresh session → service → repository → DB.
5. Tool results are collected; failures are isolated.
6. Agent calls `TextGenerationProvider.generate()` to synthesize an answer.
7. `AIService` builds the `AIResponse` contract with sources, evidence, and trace.

### Security Enforcement

- `ToolRegistry` only accepts `Callable[..., Coroutine[..., dict]]` — no arbitrary code execution.
- Composition root creates per-invocation sessions (tools cannot hold or reuse sessions).
- The `sanitize_log_value()` function in the trace module strips credential patterns from log output.
- Tools return `source_label` strings (e.g., "Finance PostgreSQL") — never connection URIs.

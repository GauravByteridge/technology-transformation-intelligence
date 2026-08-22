# ADR-006: Demo Mode Architecture

## Status

Accepted

## Context

The platform needs a Demo Mode for local development, stakeholder demonstrations, and onboarding new team members without requiring external credentials (LLM API keys, external database connections, embedding service endpoints).

Two approaches were considered:

1. **Separate demo logic** — Create demo-only endpoints, services, or conditional branches that return hard-coded responses when `DEMO_MODE=true`.
2. **Same execution path with seeded data** — Demo Mode exercises the identical code path as Live Mode (API → Service → Repository → DB), but uses seeded data in the internal databases and a `MockTextGenerationProvider` instead of a real LLM.

## Decision

We use approach 2: **Demo Mode shares the same execution path as Live Mode**.

- `DEMO_MODE=true` is a configuration flag, not a code branch.
- The application starts with the same FastAPI routes, services, repositories, and AI orchestration in both modes.
- Demo Mode uses deterministic seed data in App_DB and RAG_DB.
- The `MockTextGenerationProvider` produces deterministic, canned responses so AI orchestration can be smoke-tested without external credentials.
- Configuration validation is mode-aware: Live Mode fails startup if required credentials are missing; Demo Mode skips credential validation for providers and external sources that are not in use.

## Reasoning

- **No demo-only code rot** — There are no parallel implementations that can drift from production logic. If a service or repository changes, demo mode automatically exercises the new path.
- **Bug parity** — Bugs found in Demo Mode will also exist in Live Mode, making local testing representative of production behavior.
- **Simpler codebase** — No `if demo_mode: return fake_data` scattered through services or tools. The same DI composition root handles both modes with different provider selections.
- **Faster onboarding** — A new developer clones the repo, seeds the databases, and has a fully functional system without configuring external services.
- **Credential isolation** — Demo Mode never touches external credentials, reducing the risk of accidental key exposure during development.

## Consequences

### Positive

- Same code is tested in both modes — fewer gaps between development and production.
- AI tools never contain hard-coded business data; data flows through the standard repository → DB path.
- Adding a new feature requires no demo-specific implementation — just appropriate seed data.
- Startup validation is clear: Demo Mode logs warnings for missing credentials but continues; Live Mode fails fast with descriptive error messages.

### Negative

- Demo Mode requires a running PostgreSQL instance (App_DB) with seeded data — cannot run with zero dependencies.
- Seed scripts must be maintained as the schema evolves (migrations and seeds must stay in sync).
- The `MockTextGenerationProvider` answers are not contextually intelligent — useful for integration testing but not for evaluating AI quality.

## Implementation Details

- Configuration: `DEMO_MODE` environment variable (default: `true`).
- In Demo Mode, `LLM_PROVIDER` defaults to `"mock"` if not explicitly set.
- In Demo Mode, `EMBEDDING_PROVIDER` defaults to `"mock"` if not explicitly set.
- Startup validation (`validate_live_mode_settings`) is skipped entirely when `DEMO_MODE=true`.
- Seed scripts in `database/seeds/` are idempotent — running them multiple times produces the same state.
- Placeholder embeddings use a seeded PRNG to produce vectors of exactly `EMBEDDING_DIMENSION` length.

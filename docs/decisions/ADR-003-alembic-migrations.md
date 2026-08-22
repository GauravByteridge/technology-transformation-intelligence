# ADR-003: Alembic for Database Migrations

## Status

Accepted

## Context

The platform has two internal PostgreSQL databases (App_DB and RAG_DB) that require version-controlled schema management. Schema changes must be:

- Tracked in source control alongside application code
- Applied in a deterministic, ordered sequence
- Reversible (supporting rollback to the previous version)
- Independently managed per database

We considered the following approaches:

1. **Alembic**: The standard migration tool for SQLAlchemy-based Python applications
2. **Custom migration scripts**: Hand-written SQL files with a custom runner
3. **Django-style migrations**: Using Django's ORM migration system (would require Django dependency)
4. **Raw SQL files with a version table**: Manual versioning without a framework

## Decision

The platform uses **Alembic** for all schema migrations across both App_DB and RAG_DB, with separate Alembic configuration files and migration directories for each database.

## Reasoning

**Why Alembic over custom migration scripts:**

- Alembic provides automatic revision ordering and dependency tracking — custom scripts require building this infrastructure from scratch.
- Alembic integrates natively with SQLAlchemy, which the backend already uses for ORM models. This enables auto-generation of migration diffs from model changes.
- Alembic supports both upgrade and downgrade operations out of the box — custom frameworks often lack reliable rollback.
- Alembic is battle-tested in production Python applications and well-documented.
- The team does not need to maintain migration tooling infrastructure.

**Why Alembic over Django migrations:**

- The backend uses FastAPI, not Django. Introducing Django's ORM solely for migrations would add a conflicting dependency and architectural confusion.
- Alembic is the native migration tool for the SQLAlchemy ecosystem already in use.

**Why two separate Alembic configurations:**

- App_DB and RAG_DB evolve independently (per ADR-002).
- Separate `alembic.ini` and `alembic_rag.ini` files allow each database to have its own migration history, revision chain, and deployment timeline.
- A migration applied to RAG_DB (e.g., changing embedding dimensions) does not need to be coordinated with App_DB schema changes.

## Consequences

### Positive

- Schema changes are version-controlled and reproducible across environments
- Migrations are reversible — `alembic downgrade -1` rolls back one revision
- Auto-generation of migration stubs from model changes reduces manual SQL writing
- Clear migration history with unique revision identifiers
- Standard tooling that new developers will already know
- Each database has independent migration timelines

### Negative

- Developers must learn Alembic's revision model and commands
- Two migration configurations adds slight operational overhead (two commands to apply all migrations)
- Auto-generated migrations may need manual review for complex schema changes
- Alembic adds a development dependency to the backend

### Neutral

- Alembic is already the de facto standard for SQLAlchemy projects — no novelty risk
- Migration files are plain Python, allowing custom logic when needed
- The same approach scales to additional databases if future phases require them

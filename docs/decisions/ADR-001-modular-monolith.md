# ADR-001: Modular Monolith Architecture

## Status

Accepted

## Context

The Technology Transformation Intelligence platform needs an architecture that supports:

- A small development team working on a single codebase
- Local development without infrastructure overhead
- A recorded demo that transitions to live client walkthroughs
- Multiple internal modules (projects, AI, connectors, documents) with clear boundaries
- Incremental feature delivery across phased development

Two primary architectural approaches were considered:

1. **Microservices**: Each domain (AI, connectors, documents, projects) as a separate deployable service
2. **Modular monolith**: Single deployable unit with strict internal module boundaries

## Decision

The platform uses a **modular monolith** architecture — a single deployable application with clear internal boundaries enforced through layering conventions, dependency injection, and protocol-based interfaces.

No Docker containers, service meshes, or distributed infrastructure are required for development.

## Reasoning

**Why not microservices:**

- The team is small. Microservices add operational complexity (networking, discovery, deployment, observability) that a small team cannot efficiently maintain.
- The platform is in early/POC phase. Premature distribution introduces latency and debugging complexity without proven scaling needs.
- Local development with microservices requires Docker Compose or equivalent, adding friction to onboarding and daily development.
- Cross-service transactions (e.g., project creation + data source linking + audit logging) become significantly harder to implement correctly.

**Why modular monolith:**

- A single process is simpler to deploy, debug, and reason about.
- Module boundaries enforced through Python protocols and layered architecture provide the same logical separation as services without network overhead.
- The registry pattern (connectors, providers) enables extensibility without requiring separate deployments.
- If scaling needs emerge later, well-defined module boundaries make extraction to services possible without a rewrite.

## Consequences

### Positive

- Simple local development: single command launches the entire platform
- No Docker required for development in Phase 0
- All code in one repository with shared types and contracts
- Straightforward debugging — single process, no network hops between internal modules
- Easy to enforce coding standards and architectural rules across the codebase
- Fast iteration during POC and demo phases

### Negative

- All modules must scale together (not independently scalable per-domain)
- A bug in one module can potentially affect the entire application process
- Requires discipline to maintain module boundaries without service-level enforcement
- If the team grows significantly, merge conflicts and coordination may increase

### Neutral

- Module extraction to services remains possible via the protocol-based interfaces
- The architecture does not prevent future containerization for production deployment

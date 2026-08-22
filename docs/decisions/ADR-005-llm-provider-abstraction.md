# ADR-005: LLM Provider Abstraction with Separated Capabilities

## Status

Accepted

## Context

The platform requires AI text generation and embedding generation capabilities. Multiple LLM providers are potential backends:

- Azure AI Foundry (text generation)
- Azure OpenAI (text generation + embeddings)
- Groq (text generation)
- Future providers

Key constraints:

- Switching providers must require only a configuration change, not code modifications
- Text generation and embedding generation may use different providers (e.g., Groq for text, Azure OpenAI for embeddings)
- Not all providers support both capabilities
- Demo Mode must function without real provider credentials
- Provider-specific logic must be fully contained within provider modules

## Decision

The platform defines **two independent protocols**:

1. **TextGenerationProvider** — for LLM text generation (generate, stream methods)
2. **EmbeddingProvider** — for embedding generation (embed, embed_batch methods)

Each protocol is resolved independently via environment variables (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`) through a **ProviderRegistry**. A provider is not required to implement both protocols.

A **MockTextGenerationProvider** is included for Phase 0 smoke testing, producing deterministic canned responses without external API calls.

## Reasoning

**Why two independent protocols:**

- Not all providers support both text generation and embeddings (e.g., Groq provides only text generation).
- Embedding models evolve on a different cadence than text generation models. Decoupling allows upgrading one without affecting the other.
- Different providers may offer better price/performance ratios for each capability.

**Why environment-variable-driven resolution:**

- Switching providers between Demo Mode and Live Mode requires only changing environment variables and restarting.
- No code branches like `if provider == "azure": ...` in service layers.
- The registry pattern validates provider configuration at startup with clear error messages.

**Why a MockTextGenerationProvider:**

- Phase 0 needs to prove the full AI orchestration path (API → Service → Agent → Tool → Service → Repository → DB) without requiring real LLM credentials.
- The mock provider produces deterministic responses, making smoke tests reproducible.
- It registers as "mock" in the provider registry and follows the same protocol as real providers.

**Why conditional startup validation:**

- Demo Mode defaults `LLM_PROVIDER` to "mock" if not set, requiring no credentials.
- Live Mode validates that the configured provider has all required credentials present.
- This prevents runtime surprises while keeping Demo Mode frictionless.

## Consequences

### Positive

- Provider switching is a configuration change — no source code modifications
- Text and embedding providers can be mixed independently
- All provider-specific logic is encapsulated in provider modules
- MockTextGenerationProvider enables full orchestration testing without credentials
- Clear startup errors when configuration is invalid

### Negative

- Two registry configurations to manage (text + embedding)
- Provider stubs exist in Phase 0 that raise NotImplementedError on actual calls
- Developers must understand the distinction between the two capability protocols

### Neutral

- Real provider integration (actual API calls) is deferred to Phase 1
- The registry supports future providers without modifying existing implementations
- Provider selection is transparent through structured logging

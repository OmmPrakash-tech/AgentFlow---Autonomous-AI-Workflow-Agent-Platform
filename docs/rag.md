# RAG — deferred design

Vector retrieval is **not implemented**. The current engine uses targeted filesystem tools and bounded evidence. No embedding or retrieval quality claims are made.

Proposed future pipeline:

```mermaid
flowchart LR
 D[Approved documents] --> P[Parse and redact]
 P --> C[Chunk with project and source metadata]
 C --> E[Embedding provider]
 E --> V[Replaceable vector-store interface]
 Q[Authorized task query] --> R[Project-filtered retrieval]
 V --> R
 R --> A[Untrusted evidence context]
```

Implement only after the P0 acceptance gates are reliable. Start with PostgreSQL-backed storage if scale justifies embeddings; do not add a separate vector database merely for the architecture diagram. Retrieval must enforce project ownership before similarity results reach the model.

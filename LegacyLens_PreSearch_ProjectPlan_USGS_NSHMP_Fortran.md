# LegacyLens Pre-Search and Project Plan (USGS NSHMP Legacy Hazard Fortran)

Last updated: 2026-03-02 (America/Chicago)

## Executive intent

LegacyLens is a Retrieval-Augmented Generation (RAG) system for **legacy scientific codebase comprehension**. It ingests a repository, builds a searchable index and lightweight metadata graph, and answers natural-language questions with **file/line-grounded citations**, plus code-understanding utilities (call-site exploration, include/dependency mapping, pattern queries, and change-impact reports).

This version is tailored to the chosen primary corpus:

- **Primary corpus:** USGS **NSHMP legacy hazard Fortran** repository (Fortran; “legacy codes” used for national seismic hazard map updates).
- **Goal:** compress “time to understanding” for complex scientific modeling code: program structure, subroutine flow, configuration/build wiring, I/O formats, and numerical routines.

## Problem statement

Legacy scientific codebases (Fortran/C mixed systems, decades-old numerical models, complex build wiring) are difficult to navigate because they often have:
- Sparse or outdated documentation
- Domain-specific conventions and terminology (hazard, attenuation, site response, recurrence)
- Cross-cutting global state (modules, COMMON blocks, shared include files)
- Hidden runtime wiring via build flags, scripts, and data/config file formats

LegacyLens aims to reduce onboarding and maintenance friction by combining syntax-aware chunking, semantic retrieval, and strictly source-grounded answers.

## Target users and use cases

Primary users:
- Engineers onboarding to the NSHMP codebase
- Scientific programmers maintaining hazard modeling pipelines
- Researchers auditing algorithm choices and numerical implementation details

Core use cases:
- “Where is X computed and what subroutines feed it?”
- “What does subroutine/function Y do in plain language?”
- “Where is parameter Z read, transformed, and used?”
- “Explain build configuration and platform branches.”
- “Show the call sites for routine R and likely side effects of changing it.”
- “Summarize module responsibilities and the high-level architecture.”

## Definitions and terminology

- **Corpus**: The set of files ingested from a repository (source, docs, scripts, configs).
- **Chunk**: Smallest retrievable unit (prefer subroutine/function/module boundaries; fallback to windowed text).
- **Span**: `(file path, start line, end line)` attached to every chunk.
- **Embedding**: Dense vector representation of a chunk/query for similarity search.
- **Vector store**: Database holding embeddings + metadata for retrieval.
- **Hybrid retrieval**: Combining lexical search (identifier and token search) with vector similarity search.
- **Reranking**: Second-stage reordering of retrieved candidates.
- **Grounded answer**: Output referencing retrieved chunks with citations linked to spans.
- **Include**: Fortran `INCLUDE` file usage; treated like “copybooks” in COBOL.

## Scope

### In scope

- Repository ingestion and normalization (encoding, line endings, path rules)
- Syntax-aware chunking with span metadata (Fortran-aware)
- Embedding, indexing, retrieval
- Web UI query interface (initially)
- Answer generation with citations to spans
- Code-understanding utilities beyond Q&A:
  - Subroutine/function lookup and call-site exploration
  - Include and module dependency mapping
  - Pattern queries (I/O patterns, error handling conventions, numerical solver usage)
  - Change impact analysis (probable blast radius)
  - Documentation extraction and summarization

### Out of scope (initially)

- Fully precise whole-program static analysis across all languages
- Dynamic tracing/profiling
- Multi-tenant SaaS hardening (beyond basic demo security)
- Arbitrary public ingestion endpoints on the deployed demo (demo uses preloaded corpus)

## Success metrics

Retrieval and answer quality:
- **Precision@5**: >70% relevant chunks in top-5 (gold set)
- **Hit@5**: percent of queries with at least one relevant chunk in top-5
- **MRR@10**: time-to-first-relevant proxy
- **Citation coverage**: answer sentences have citations; no uncited named-symbol claims

System performance:
- Ingestion: 10,000+ LOC in <5 minutes (for the chosen corpus slice)
- Query latency: <3 seconds end-to-end p95 on typical loads

Usability:
- Time-to-first-relevant-snippet for novice users
- Percentage of sessions ending with user opening a cited file span

Operational:
- One-command local run (Docker Compose)
- CI pipeline passes (lint/typecheck/tests + eval subset)

## Constraints and assumptions

Assumptions:
- Estimates are in **person-days**
- LLM provider available for answer generation (model selection deferred)
- First iteration prioritizes grounded correctness over UI polish
- Primary corpus is public and can be cloned for ingestion

Key constraints:
- Mixed encodings and fixed-format conventions may exist
- Parsing quality for legacy Fortran varies; chunking must degrade gracefully
- Scientific repos include large data files or build artifacts; must enforce ignore rules

## Selected open-source base approach

- **Backend framework:** thin **FastAPI** service (custom) to avoid document-RAG product constraints.
- **Vector store:** **Postgres + pgvector** (single-service persistence for metadata + vectors).
- **Embeddings:** OpenAI embeddings (model name TBD; stored in DB for reproducibility).
- **Retrieval (v1):** vector-only baseline; lexical/hybrid expansion planned.
- **Demo posture:** public instance is **query-only** on a **preloaded corpus**; ingestion endpoints disabled or admin-only.

## Proposed technical architecture

### Backend
- Python 3.11+, FastAPI
- Postgres 15+ with pgvector
- Background job runner optional (start with a one-shot ingest command; add worker later)
- Structured logging with per-request timings and cost estimates

### Data model (minimum viable)
- `corpus` (repo URL, commit SHA, created_at, status)
- `file` (path, language, encoding, hashes, line_count)
- `chunk` (type, spans, text, token_count, hashes)
- `embedding` (chunk_id, model, dims, vector)
- `symbol` (name, kind: MODULE|SUBROUTINE|FUNCTION|PROGRAM|INCLUDE, span)
- `reference` (kind: CALL|USE|INCLUDE, from_symbol, to_symbol, span, snippet)

### Retrieval pipeline
1. Parse query, extract likely identifiers (e.g., subroutine names, module names, filenames).
2. Compute query embedding (same embedding model as ingestion).
3. Vector similarity search (top-N candidates, filtered by corpus_id).
4. (Optional later) lexical boosts for identifiers; (optional) rerank.
5. Context assembly with dedupe, span-aware clipping.
6. Answer generation with citations mapped to retrieved spans.

### Fortran-aware chunking strategy (primary differentiator)
- Prefer boundaries in this order:
  - `MODULE ... END MODULE`
  - `SUBROUTINE ... END SUBROUTINE`
  - `FUNCTION ... END FUNCTION`
  - `PROGRAM ... END PROGRAM`
  - `CONTAINS` blocks handled as nested subroutine/function chunks
- Include files:
  - treat `INCLUDE 'file.inc'` as a dependency edge
  - index include files as normal files; optionally show “expanded context” by linking include definitions, not by text-inlining in v1
- Fallback:
  - window by line ranges with overlap when boundaries cannot be identified
- Chunk sizing:
  - target 200–500 tokens; cap ~800; merge tiny routines; split huge blocks

### Deployment
- Docker Compose: `api` + `db`
- Public demo:
  - preloaded NSHMP corpus indexed at build/startup
  - rate-limited query endpoint
  - no public ingestion

### Security
- Treat repository content as untrusted.
- Do not execute repository code.
- Disable public ingestion; if enabled for admin:
  - strict extension allowlist, file size caps, timeouts
  - block symlinks and binaries
  - no network egress for workers when possible

## Timeline phases and milestones (person-days)

Discovery (5–8)
- Confirm repo and commit SHA snapshot to index.
- Confirm ignore rules and file allowlist.
- Define 30–40 gold queries with expected spans (>=30 required).
- Decide embedding model + answer model; define rate limits and caps.

Prototype (10–15)
- End-to-end ingest → search → answer on a subset of the NSHMP repo.
- Implement Fortran-aware chunker (module/subroutine/function) + fallback windows.
- Implement pgvector storage and vector-only retrieval.
- Build minimal web UI with snippet list, relevance scores, and file drilldown.

MVP (20–30)
- Full ingestion for the chosen repo snapshot.
- Implement 4 code-understanding features (Fortran-adapted):
  1) Explain symbol (module/subroutine/function) with citations
  2) Call-site finder (CALL graph edges; best-effort)
  3) Include/module usage explorer (`INCLUDE`, `USE`)
  4) Impact report (probable blast radius via reference edges + lexical matches)
- Evaluation harness with precision@5, hit@5, MRR@10.
- Public deployment (query-only, preloaded corpus).

Launch (8–12)
- Hardening: performance tuning, better caching, UI polish.
- Observability: p50/p95, ingest metrics, cost estimates.
- Documentation: architecture doc, cost analysis, demo script/video.

Maintenance (3–5 per month)
- Dependency upgrades, eval regressions, incremental indexing if added later.

## Risk register (top items)

- **Vector-only retrieval misses identifier-heavy queries.**
  - Mitigation: add identifier extraction + Postgres FTS lexical boost; optional hybrid union.
- **Chunking errors reduce span accuracy or relevance.**
  - Mitigation: robust boundary detection; strict fallback; unit tests on chunk boundaries.
- **Context bloat for long routines.**
  - Mitigation: chunk caps; snippet clipping; dedupe; (optional) local summary fields.
- **Public demo abuse/cost blowups.**
  - Mitigation: preloaded-only, rate limits, strict caps, timeouts.
- **Licensing or data-file issues in repo.**
  - Mitigation: index code and docs; exclude large data; include third-party notices if needed.

## Next 30 days prioritized tasks (revised for NSHMP Fortran)

Week 1
- Pin repo snapshot (URL + commit SHA) and ingest rules.
- Implement Fortran-aware chunker (module/subroutine/function) + fallback windows.
- Implement ingestion to Postgres: files, chunks, embeddings.
- Create gold set (>=30 queries) with expected spans in `eval/gold.json`.

Week 2
- Implement pgvector retrieval and snippet dedupe.
- Add identifier extraction from queries (for display and future lexical boost).
- Build minimal web UI:
  - query box
  - retrieved snippet list with relevance scores
  - syntax highlighting
  - file drilldown with line anchors
- Implement answer generation with citations (LLM model TBD but required).

Week 3
- Implement 4 code-understanding features:
  1) Explain symbol
  2) Call-site finder
  3) Include/module usage explorer
  4) Impact report
- Implement evaluation harness and baseline measurements.
- Tune chunking and retrieval parameters against gold set.

Week 4
- Deploy publicly (query-only, preloaded corpus).
- Add observability and cost logging.
- Finalize documentation: Pre-Search, architecture doc, cost analysis, demo video.

## Appendix: primary repo link
- USGS NSHMP legacy hazard Fortran code (selected primary corpus)

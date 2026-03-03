# LegacyLens - AGENTS.md (Source of Truth)

> **Purpose:** RAG system for legacy Fortran scientific codebases (USGS NSHMP hazard modeling)
> **Last Updated:** 2026-03-02
> **Status:** Week 1 - Foundation & Discovery

---

## Project Overview

LegacyLens is a Retrieval-Augmented Generation (RAG) system for **legacy scientific codebase comprehension**. It ingests a repository, builds a searchable index and lightweight metadata graph, and answers natural-language questions with **file/line-grounded citations**.

**Primary Corpus:**
- Repository: https://github.com/usgs/nshmp-haz-fortran
- Target: Tag `nshm2014r1` (2014 NSHM Release 1)
- Language: 97% Fixed-format Fortran 77 (.f extension)
- License: Public domain (US Government work)

---

## Technical Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Backend | FastAPI | Thin service, avoids document-RAG product constraints |
| Database | Postgres 15 + pgvector | Single-service persistence for metadata + vectors |
| Embeddings | OpenAI `text-embedding-3-small` | 1536 dims, $0.02/1M tokens |
| Answer LLM | Claude Sonnet 4 (`claude-sonnet-4-20250514`) | $3/1M input, $15/1M output |
| UI | Streamlit | Rapid prototyping, Python-native |
| Chunking | Regex-based (Week 1), tree-sitter fallback (Week 2 if needed) | Discovery-driven approach |

---

## Project Structure

```
src/legacylens/
├── api/                  # FastAPI routes
│   ├── main.py
│   └── routes/           # query.py, symbols.py, impact.py, ingest.py, health.py
├── chunking/             # Fortran-aware chunking (KEY DIFFERENTIATOR)
│   ├── fortran_parser.py # MODULE/SUBROUTINE/FUNCTION detection
│   ├── chunker.py
│   └── fallback.py       # Window-based fallback
├── ingestion/            # Repository ingestion
│   ├── repo_loader.py
│   ├── file_normalizer.py
│   └── ingest_service.py
├── embedding/            # OpenAI embedding
│   ├── embedder.py
│   └── batch_embedder.py
├── retrieval/            # pgvector retrieval
│   ├── vector_store.py
│   ├── retriever.py
│   └── context_assembler.py
├── generation/           # Answer generation
│   ├── llm_client.py     # Claude client
│   ├── answer_generator.py
│   └── prompts.py
├── analysis/             # Code-understanding utilities
│   ├── symbol_explainer.py
│   ├── call_site_finder.py
│   ├── usage_explorer.py
│   └── impact_analyzer.py
├── db/                   # Database layer
│   ├── models.py         # SQLAlchemy models
│   └── repository.py
├── core/                 # Utilities
│   ├── config.py
│   ├── schemas.py
│   └── spans.py
└── observability/
ui/                       # Streamlit frontend
├── app.py
└── components/
tests/
├── unit/
├── integration/
└── eval/
eval/
├── gold.json             # 30+ gold queries
├── metrics.py
└── run_eval.py
scripts/
└── ingest_corpus.py
docker/
```

---

## Data Model (Postgres + pgvector)

```sql
-- Core tables
corpus (id, repo_url, commit_sha, created_at, status)
file (id, corpus_id, path, language, encoding, line_count, hash)
chunk (id, file_id, type, start_line, end_line, text, token_count, hash)
embedding (id, chunk_id, model, dims, vector)

-- Code understanding tables (Week 2+)
symbol (id, corpus_id, name, kind, file_id, start_line, end_line)
  -- kind: SUBROUTINE | FUNCTION | PROGRAM | MODULE | COMMON
reference (id, from_symbol_id, to_symbol_id, kind, file_id, line, snippet)
  -- kind: CALL | USE | INCLUDE
```

---

## Core API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `POST /api/v1/query` | Natural language query with citations |
| `GET /api/v1/symbols/{name}` | Symbol definition lookup |
| `GET /api/v1/symbols/{name}/call-sites` | Find all CALL sites |
| `GET /api/v1/symbols/{name}/usage` | INCLUDE/USE explorer |
| `POST /api/v1/impact/{symbol}` | Blast radius analysis |
| `POST /api/v1/ingest` | Admin-only corpus ingestion |

---

## Chunking Strategy (Fortran-Specific)

**Preferred boundaries (in order):**
1. `SUBROUTINE ... END SUBROUTINE`
2. `FUNCTION ... END FUNCTION`
3. `PROGRAM ... END PROGRAM`
4. `MODULE ... END MODULE` (if F90+ sections exist)

**COMMON blocks:**
- Extract from declarations: `COMMON /name/ var1, var2`
- Track as symbol with variable list in metadata

**Include files:**
- Week 1: Track `INCLUDE 'file.inc'` as reference edges
- Week 2: Decision - inline expansion vs link-only based on retrieval quality

**Chunk sizing:**
- Target: 200-500 tokens
- Cap: 800 tokens
- Merge: Routines <50 tokens combined
- Fallback: 50-line windows with 10-line overlap

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Precision@5 | >70% relevant chunks in top-5 |
| Hit@5 | >80% queries have ≥1 relevant chunk in top-5 |
| MRR@10 | >0.6 |
| Citation coverage | All code claims cited |
| Ingestion | 10k+ LOC in <5 minutes |
| Query latency | <3 seconds p95 |
| Dev cost | <$50 total |

---

## Week 1 Targets (Days 1-7)

### Day 1: Setup & Exploration
- [ ] Clone repo and checkout `nshm2014r1`
- [ ] File inventory (count .f files, estimate LOC)
- [ ] Sample 5-10 files, document patterns
- [ ] Set up Python environment

### Day 2-3: Chunker Implementation
- [ ] Implement regex-based FortranChunker
- [ ] Test on sample files
- [ ] Measure coverage (>80% target)
- [ ] Unit tests

### Day 4: Database Setup
- [ ] Docker Compose with pgvector
- [ ] SQLAlchemy models
- [ ] Test connection and basic operations

### Day 5-6: Ingestion & Retrieval
- [ ] Implement ingestion pipeline
- [ ] OpenAI embedding integration
- [ ] Basic retrieval with pgvector

### Day 7: Testing & Planning
- [ ] Write 10 test queries
- [ ] Manual relevance assessment
- [ ] Document findings for Week 2

---

## Key Decisions (Do Not Modify Without Discussion)

1. **Regex-based chunking first** - Evaluate tree-sitter only if coverage <70%
2. **Claude Sonnet 4 for answers** - Switch to Haiku only if costs exceed budget
3. **Vector-only retrieval baseline** - Add lexical search Week 3 if identifier queries fail
4. **Preloaded demo only** - No public ingestion endpoints

---

## Risk Register

| Risk | Mitigation | Status |
|------|------------|--------|
| Regex misses >30% of code | Evaluate tree-sitter-fortran | Week 1 test |
| COMMON blocks cause missing context | Add to symbol extraction Week 2 | Planned |
| Identifier queries fail | Add lexical search Week 3 | Deferred |
| API costs exceed budget | Switch to Haiku, cache embeddings | Monitor |
| Public demo abuse | Preloaded only, rate limits, timeouts | Week 4 |

---

## Commands

```bash
# Start database
docker-compose up -d

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Ingest corpus
python scripts/ingest_corpus.py --repo-url https://github.com/usgs/nshmp-haz-fortran --tag nshm2014r1

# Run API
uvicorn src.legacylens.api.main:app --reload

# Run UI
streamlit run ui/app.py
```

---

## Related Files

- **Task Tracking:** `tasks.md`
- **Continuity:** `HANDOFF.md`
- **Week 1 Checklist:** `Week1_Checklist.md`
- **Full Plan:** `LegacyLens_Updated_ProjectPlan.md`

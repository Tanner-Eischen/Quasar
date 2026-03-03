# LegacyLens - Task Tracking

> **Last Updated:** 2026-03-02
> **Current Phase:** Week 1 - Foundation & Discovery

---

## Phase 0: Bootstrap (Days 0-1) ✅ COMPLETE

- [x] Create project directory structure
- [x] Initialize git repo with `.gitignore`
- [x] Create `pyproject.toml` with dependencies
- [x] Set up `.pre-commit-config.yaml` (ruff, black, mypy)
- [x] Create `Makefile` with common commands
- [x] Write `AGENTS.md`, `tasks.md`, `HANDOFF.md`
- [x] Set up GitHub Actions CI
- [x] Create `docker-compose.yml`
- [x] Create core schemas and config
- [x] Create database models (SQLAlchemy)
- [x] Implement Fortran chunker (key differentiator)
- [x] Implement embedding client
- [x] Create FastAPI app skeleton with health endpoint
- [x] Create Streamlit UI skeleton
- [x] Create CLI entry point
- [x] Create ingest_corpus.py script
- [x] Create initial gold.json (10 queries)
- [x] Create eval metrics module
- [x] Write unit tests for chunking and core

---

## Week 1: Foundation & Discovery (Days 1-7)

### Day 1: Setup & Exploration
- [ ] Clone repo: `git clone https://github.com/usgs/nshmp-haz-fortran.git`
- [ ] Checkout target: `git checkout nshm2014r1`
- [ ] Confirm commit SHA: `git log -1`
- [ ] File inventory: count .f files, estimate LOC
- [ ] Sample 5-10 representative files
- [ ] Read and document patterns (subroutines, COMMON, INCLUDE)
- [ ] Create `week1_discovery.md` notes
- [ ] Set up Python environment

### Day 2: Chunker Design
- [ ] Design `FortranChunker` class architecture
- [ ] Write regex patterns for boundaries:
  - `^\s*SUBROUTINE \w+` → `END SUBROUTINE`
  - `^\s*FUNCTION \w+` → `END FUNCTION`
  - `^\s*PROGRAM \w+` → `END PROGRAM`
- [ ] Test patterns manually on 2-3 sample files
- [ ] Implement `FortranChunker` class methods:
  - `chunk_file(filepath) -> List[Chunk]`
  - `extract_subroutines(text) -> List[Span]`
  - `fallback_window(text, lines=50, overlap=10) -> List[Span]`
- [ ] Document chunking strategy and limitations

### Day 3: Chunker Testing
- [ ] Write unit tests for boundary detection
- [ ] Test edge cases: nested blocks, comments, continuations
- [ ] Measure coverage: `(chunked_lines / total_lines) * 100`
- [ ] **Target: >80% coverage on sample files**
- [ ] Refine patterns based on failures

### Day 4: Infrastructure - Database
- [ ] Create `docker-compose.yml` with pgvector
- [ ] Write SQLAlchemy models: corpus, file, chunk, embedding
- [ ] Test DB connection from Python
- [ ] Implement data access layer:
  - `insert_corpus(repo_url, commit_sha)`
  - `insert_file(corpus_id, path, language, line_count)`
  - `insert_chunk(file_id, type, start_line, end_line, text)`
  - `insert_embedding(chunk_id, model, vector)`
- [ ] Verify pgvector extension working
- [ ] Test basic vector insert and similarity query

### Day 5: Ingestion Pipeline
- [ ] Implement `ingest_repository(repo_path, corpus_id)`
- [ ] Add OpenAI embedding calls with batching
- [ ] Test on 5-10 sample files
- [ ] Measure performance (time, tokens, embeddings)
- [ ] Calculate cost estimate for full corpus

### Day 6: Retrieval Prototype
- [ ] Implement `search_chunks(query, top_k=10)`:
  - Query embedding computation
  - pgvector similarity search
- [ ] Implement context assembly:
  - Dedupe overlapping spans
  - Sort by relevance score
- [ ] Test with sample queries: "hazard", "ground motion", subroutine names

### Day 7: Initial Testing & Planning
- [ ] Write 10 diverse test queries
- [ ] Run queries, manually assess top-5 results
- [ ] Calculate informal precision@5 and hit@5
- [ ] Document failure modes
- [ ] Update Week 2 plan based on findings

---

## Week 2: Retrieval & UI (Days 8-15)

### Days 8-10: Full Ingestion
- [ ] Ingest all .f files from src/
- [ ] Ingest configuration files from conf/
- [ ] Ingest scripts/ if relevant
- [ ] Verify: chunk count, token distribution, embedding storage

### Days 11-13: Web UI
- [ ] FastAPI endpoints: /query, /file/{path}
- [ ] Streamlit frontend
- [ ] Query interface with results display
- [ ] File viewer with syntax highlighting and line numbers

### Days 14-15: Answer Generation
- [ ] Implement answer generation with Claude Sonnet 4
- [ ] Citation extraction and validation
- [ ] Cost logging per query
- [ ] Error handling (rate limits, timeouts)

---

## Week 3: Code Understanding & Eval (Days 16-25)

### Days 16-18: Symbol Extraction
- [ ] Extract symbols: SUBROUTINE, FUNCTION, PROGRAM, COMMON
- [ ] Populate symbol table with spans
- [ ] Extract references: CALL statements, INCLUDE directives
- [ ] Build reference graph edges

### Days 19-21: Code Understanding Features
- [ ] Feature 1: Symbol explainer
- [ ] Feature 2: Call site finder
- [ ] Feature 3: Include/dependency viewer
- [ ] Feature 4: Impact report

### Days 22-25: Evaluation
- [ ] Expand to 30+ gold queries
- [ ] Implement eval harness (P@5, Hit@5, MRR@10)
- [ ] Run baseline metrics
- [ ] Decision: Add lexical search if needed

---

## Week 4: Deploy & Document (Days 26-32)

### Days 26-28: Deployment
- [ ] Containerize with preloaded corpus
- [ ] Add rate limiting and query timeouts
- [ ] Deploy to Railway/Fly.io

### Days 29-31: Polish & Documentation
- [ ] UI improvements
- [ ] Performance optimization
- [ ] Architecture documentation
- [ ] Demo video (3-5 minutes)
- [ ] Cost analysis report

### Day 32: Buffer
- [ ] Final testing
- [ ] Bug fixes
- [ ] Launch prep

---

## Notes & Decisions

### Key Decisions Made
- (Track decisions as they're made)

### Blockers
- (Track blockers here)

### Discoveries
- (Track key discoveries from corpus exploration)

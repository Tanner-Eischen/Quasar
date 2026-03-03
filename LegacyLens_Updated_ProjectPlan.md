# LegacyLens Project Plan (USGS NSHMP Fortran) - Updated with Discovery Approach

Last updated: 2026-03-02

## Executive intent

LegacyLens is a Retrieval-Augmented Generation (RAG) system for **legacy scientific codebase comprehension**. It ingests a repository, builds a searchable index and lightweight metadata graph, and answers natural-language questions with **file/line-grounded citations**, plus code-understanding utilities (call-site exploration, include/dependency mapping, pattern queries, and change-impact reports).

**Primary corpus:** USGS NSHMP legacy hazard Fortran repository  
**Repository:** https://github.com/usgs/nshmp-haz-fortran  
**Target commit:** `nshm2014r1` tag (2014 NSHM release)

## Problem statement

Legacy scientific codebases (Fortran/C mixed systems, decades-old numerical models, complex build wiring) are difficult to navigate because they often have:
- Sparse or outdated documentation
- Domain-specific conventions and terminology (hazard, attenuation, site response, recurrence)
- Cross-cutting global state (modules, COMMON blocks, shared include files)
- Hidden runtime wiring via build flags, scripts, and data/config file formats

LegacyLens aims to reduce onboarding and maintenance friction by combining syntax-aware chunking, semantic retrieval, and strictly source-grounded answers.

---

## Corpus Details (Confirmed)

**Repository:** https://github.com/usgs/nshmp-haz-fortran  
**Language composition:** 97% Fortran, plus Shell scripts, Makefiles  
**Fortran dialect:** Fixed-format Fortran 77 (.f extension)  
**Structure:**
- `src/` - Main source code (hazard calculations, GMPEs, deaggregation)
- `conf/` - Configuration files (input decks, parameter files)
- `scripts/` - Shell scripts for running calculations
- `docs/` - Limited documentation
- `etc/` - Utilities and helpers

**Key characteristics discovered:**
- Fixed-format F77 with C-style comments
- COMMON blocks for shared state (legacy pattern)
- Ground Motion Prediction Equations (GMPEs) - domain-specific
- Configuration-driven execution (many .in files)
- Build via Makefile + GFortran

**Estimated scope:**
- ~10,000-20,000 LOC in src/ (to be confirmed Week 1)
- ~100-200 Fortran source files (to be confirmed)
- Configuration files should be indexed (contain parameter documentation)

---

## Target users and use cases

Primary users:
- Engineers onboarding to the NSHMP codebase
- Scientific programmers maintaining hazard modeling pipelines
- Researchers auditing algorithm choices and numerical implementation details

Core use cases:
- "Where is X computed and what subroutines feed it?"
- "What does subroutine/function Y do in plain language?"
- "Where is parameter Z read, transformed, and used?"
- "Explain build configuration and platform branches."
- "Show the call sites for routine R and likely side effects of changing it."
- "Summarize module responsibilities and the high-level architecture."

---

## Technical decisions with sensible defaults

### Parsing strategy (Discovery-driven)

**Week 1 approach: Regex-based chunking**
- Start with pattern matching for subroutine/function boundaries
- Patterns to detect:
  - `^\s*SUBROUTINE \w+` ... `END SUBROUTINE`
  - `^\s*FUNCTION \w+` ... `END FUNCTION`
  - `^\s*PROGRAM \w+` ... `END PROGRAM`
  - `^\s*MODULE \w+` ... `END MODULE` (if present in F90 sections)
- Fallback: 50-line windows with 10-line overlap for unparseable sections
- **Decision point:** If regex misses >30% of code in Week 2, evaluate tree-sitter-fortran

**COMMON blocks:**
- Track as symbol type in Week 2 (discovered to be important)
- Add to symbol table: `COMMON /blockname/`
- Extract variable lists for reference tracking

**Include files:**
- Week 1: Track `INCLUDE 'file.inc'` as reference edges only
- Week 2: Decision point - expand inline if retrieval misses context
- Store as separate indexed files regardless

### Model selection (Balanced budget)

**Embeddings:** OpenAI `text-embedding-3-small`
- Cost: ~$0.02 per 1M tokens
- Dimensions: 1536
- Estimated corpus cost: $0.50-$2.00 for full index

**Answer generation:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- Cost: $3 per 1M input tokens, $15 per 1M output
- Estimated per-query: $0.01-$0.05 (context + answer)
- Monthly dev budget estimate: $20-$50 for prototyping

**Alternative if costs are too high:** 
- Claude Haiku for development/testing
- Sonnet for production only

### Retrieval approach

**Phase 1 (Week 1-2): Vector-only baseline**
- Simple pgvector cosine similarity
- Top-K retrieval (K=10 initially)
- Evaluate against initial query set

**Phase 2 (Week 3): Add lexical if needed**
- Postgres full-text search on identifiers
- Hybrid: union of vector + lexical results
- Decision based on evaluation metrics

**Identifier extraction:**
- Regex patterns for Fortran identifiers in queries
- Used for display and potential lexical boost
- Patterns: CALL statements, subroutine names, module names

---

## Proposed technical architecture

### Backend
- Python 3.11+, FastAPI
- Postgres 15+ with pgvector extension
- Background jobs: Start with CLI commands, add worker queue if needed (Week 3+)
- Structured logging with request timings and cost tracking

### Data model (minimum viable)

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

### Chunking strategy (Fortran-specific)

**Preferred boundaries (in order):**
1. `SUBROUTINE ... END SUBROUTINE`
2. `FUNCTION ... END FUNCTION`
3. `PROGRAM ... END PROGRAM`
4. `MODULE ... END MODULE` (if F90+ sections exist)

**Include files:**
- Index separately as normal files
- Track dependency edges in `reference` table
- Week 2 decision: inline expansion vs link-only

**COMMON blocks:**
- Extract from declarations: `COMMON /name/ var1, var2`
- Track as symbol with variable list in metadata
- Critical for understanding shared state

**Chunk sizing:**
- Target: 200-500 tokens per chunk
- Cap: 800 tokens (split if exceeded)
- Merge: Routines <50 tokens combined into file-level chunks
- Fallback: 50-line windows with 10-line overlap

### Retrieval pipeline

1. **Query preprocessing**
   - Extract likely identifiers (subroutine names, file refs)
   - Compute query embedding (same model as corpus)

2. **Vector search**
   - pgvector cosine similarity
   - Filter by corpus_id
   - Top-N candidates (N=10 initially)

3. **Context assembly**
   - Dedupe by file+span
   - Clip overlapping spans
   - Assemble with line numbers

4. **Answer generation**
   - Pass retrieved chunks + query to Claude
   - Extract citations from answer
   - Map citations to spans

### Deployment

**Development:**
```yaml
# docker-compose.yml
services:
  db:
    image: pgvector/pgvector:pg15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://...
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
```

**Public demo (Week 4):**
- Preload corpus at container build time
- Disable ingestion endpoints (or admin-only)
- Rate limit: 10 queries/minute per IP
- Query timeout: 30 seconds
- Deploy on Render/Railway/Fly.io

---

## Scope (refined)

### In scope - MVP

**Core functionality:**
- [x] Repository ingestion (clone, normalize, chunk, embed)
- [x] Syntax-aware Fortran chunking with fallback
- [x] Vector search and retrieval
- [x] Web UI: query box, results list, file viewer
- [x] Answer generation with citations
- [x] Span-grounded output (file paths + line ranges)

**Code understanding features (pick 4):**
1. **Symbol explainer:** "What does subroutine X do?" → grounded summary
2. **Call site finder:** "Where is X called?" → list call sites with context
3. **Include/dependency viewer:** "What includes/uses X?" → dependency graph
4. **Impact report:** "What breaks if I change X?" → probable blast radius

**Evaluation:**
- Precision@5, Hit@5, MRR@10
- Gold set: 30+ queries with expected spans
- Automated eval harness

### Out of scope (post-MVP)

- Whole-program static analysis across all languages
- Dynamic tracing/profiling integration
- Multi-repo corpus management
- Incremental indexing (re-index from scratch for updates)
- Public ingestion endpoints on demo
- Advanced visualizations (call graphs, dependency diagrams)

---

## Success metrics

**Retrieval quality:**
- Precision@5: >70% relevant chunks in top-5
- Hit@5: >80% queries have ≥1 relevant chunk in top-5
- MRR@10: Mean Reciprocal Rank >0.6

**System performance:**
- Full corpus ingestion: <10 minutes
- Query latency: <3 seconds p95
- Embedding cost: <$5 for full corpus

**Usability (qualitative):**
- Time-to-first-relevant-snippet for novice queries
- Citation accuracy (no hallucinated file/line refs)
- User opens cited file in ≥50% of sessions

---

## Timeline phases (discovery-driven)

### Week 1: Foundation & Discovery (5-7 days)

**Days 1-2: Repository exploration**
- [ ] Clone repo: `git clone https://github.com/usgs/nshmp-haz-fortran.git`
- [ ] Checkout target: `git checkout nshm2014r1`
- [ ] File inventory: Count .f files, estimate LOC, check for .f90
- [ ] Sample inspection: Read 5-10 representative files
- [ ] Document findings: Fortran dialect, COMMON usage, include patterns

**Days 3-4: Chunker prototype**
- [ ] Write regex-based chunker for subroutines/functions
- [ ] Test on sample files, measure coverage (% of code chunked)
- [ ] Implement fallback windowing for unparsed sections
- [ ] Verify span accuracy (file, start_line, end_line)
- [ ] Unit tests for boundary detection

**Days 5-6: Infrastructure setup**
- [ ] Docker Compose: Postgres + pgvector
- [ ] Database schema: corpus, file, chunk, embedding tables
- [ ] Ingest pipeline: file → chunks → embeddings → DB
- [ ] Test: Index 5-10 sample files end-to-end

**Day 7: Initial queries**
- [ ] Write 10 basic test queries (mix of identifier + conceptual)
- [ ] Test retrieval: query → embedding → search → results
- [ ] Document gaps/issues for Week 2

**Deliverables:**
- Chunking coverage report (~% of LOC successfully chunked)
- Docker Compose stack running locally
- 10 test queries with manual relevance assessment

### Week 2: Retrieval & UI (6-8 days)

**Days 8-10: Full ingestion**
- [ ] Ingest all .f files from src/
- [ ] Ingest configuration files from conf/ (as separate file type)
- [ ] Ingest scripts/ if relevant
- [ ] Verify: chunk count, token distribution, embedding storage

**Days 11-13: Web UI**
- [ ] FastAPI endpoints: /query, /file/{path}
- [ ] Frontend: React/Vue/vanilla JS (pick simplest)
- [ ] Query interface: input box, "search" button
- [ ] Results display: snippets with scores, file/line links
- [ ] File viewer: syntax highlighting, line numbers, scroll to span

**Days 14-15: Answer generation**
- [ ] Implement answer generation with Claude Sonnet 4
- [ ] Citation extraction and validation
- [ ] Cost logging per query
- [ ] Error handling (rate limits, timeouts)

**Deliverables:**
- Full corpus indexed (~10K-20K LOC)
- Working web UI with search and file viewer
- Answer generation with citations functional

### Week 3: Code Understanding & Eval (7-10 days)

**Days 16-18: Symbol extraction**
- [ ] Extract symbols: SUBROUTINE, FUNCTION, PROGRAM, COMMON
- [ ] Populate symbol table with spans
- [ ] Extract references: CALL statements, INCLUDE directives
- [ ] Build reference graph edges

**Days 19-21: Code understanding features**
- [ ] Feature 1: Symbol explainer (query → symbol → grounded summary)
- [ ] Feature 2: Call site finder (symbol → CALL edges → contexts)
- [ ] Feature 3: Include/dependency viewer
- [ ] Feature 4: Impact report (symbol → references → blast radius)

**Days 22-25: Evaluation**
- [ ] Expand to 30+ gold queries with expected spans
- [ ] Implement eval harness (precision@5, hit@5, MRR@10)
- [ ] Run baseline metrics
- [ ] Identify failure modes

**Decision point:** Add lexical search if identifier queries fail?

**Deliverables:**
- 4 code understanding features operational
- Gold set with 30+ queries
- Baseline evaluation metrics
- Decision: lexical search needed? (If yes, add to Week 4)

### Week 4: Deploy & Document (5-7 days)

**Days 26-28: Deployment**
- [ ] Containerize with preloaded corpus
- [ ] Add rate limiting and query timeouts
- [ ] Deploy to hosting platform (Render/Railway)
- [ ] Public URL with query interface

**Days 29-31: Polish & documentation**
- [ ] UI improvements based on testing
- [ ] Performance optimization (caching, query rewriting)
- [ ] Architecture documentation
- [ ] Demo video (3-5 minutes)
- [ ] Cost analysis report

**Days 32: Buffer**
- [ ] Final testing
- [ ] Bug fixes
- [ ] Launch prep

**Deliverables:**
- Public demo deployed
- Architecture doc
- Demo video
- Cost analysis

---

## Week 1 Action Plan (Detailed)

### Day 1: Setup & Exploration

**Morning (3 hours):**
```bash
# Clone and inspect
git clone https://github.com/usgs/nshmp-haz-fortran.git
cd nshmp-haz-fortran
git checkout nshm2014r1
git log -1  # Confirm commit SHA

# File inventory
find . -name "*.f" | wc -l
find . -name "*.f90" | wc -l
find src -type f | wc -l
wc -l src/*.f | tail -1  # Total LOC estimate

# Sample 5 files
ls src/*.f | head -5 > sample_files.txt
```

**Afternoon (3 hours):**
- Read sample files, document patterns observed
- Check for COMMON blocks, INCLUDE statements
- Note subroutine/function naming conventions
- Create notes document: `week1_discovery.md`

**Evening (1 hour):**
- Set up Python environment: `python -m venv venv`
- Install initial dependencies: `pip install openai anthropic psycopg2-binary`

### Day 2: Chunker Design

**Morning (3 hours):**
- Design chunker architecture (class structure)
- Write regex patterns for boundaries
- Test patterns on 2-3 sample files manually

**Afternoon (3 hours):**
- Implement `FortranChunker` class
- Methods: `chunk_file()`, `extract_subroutines()`, `fallback_window()`
- Test on sample files, print chunks with spans

**Evening (1 hour):**
- Document chunking strategy decisions
- List known limitations and gaps

### Day 3: Chunker Testing

**Full day:**
- Write unit tests for chunker
- Test edge cases: nested blocks, comments, continuations
- Measure coverage: what % of sample LOC is chunked successfully?
- Refine patterns based on failures
- Target: >80% coverage on sample files

### Day 4: Infrastructure - Database

**Morning (3 hours):**
- Create `docker-compose.yml` with Postgres + pgvector
- Write SQL schema: corpus, file, chunk, embedding tables
- Create migration script or ORM models (SQLAlchemy)

**Afternoon (3 hours):**
- Test DB connection from Python
- Write data access layer: `insert_file()`, `insert_chunk()`, etc.
- Test inserting sample data

**Evening (1 hour):**
- Verify pgvector extension working
- Test basic vector insert and cosine similarity query

### Day 5: Ingestion Pipeline

**Morning (3 hours):**
- Implement `ingest_repository()` function
- Loop through files, call chunker, store in DB
- Add OpenAI embedding calls (batch if possible)

**Afternoon (3 hours):**
- Test full pipeline on 5-10 files
- Measure: time per file, tokens per chunk, embeddings stored
- Add logging and progress indicators

**Evening (1 hour):**
- Cost estimation: calculate token usage, estimate full corpus cost
- Document pipeline performance

### Day 6: Retrieval Prototype

**Morning (3 hours):**
- Implement `search_chunks()` function
- Query embedding → pgvector similarity search
- Return top-K chunks with scores

**Afternoon (3 hours):**
- Implement context assembly: dedupe, sort by relevance
- Format results with file paths and line ranges
- Test with simple queries: "hazard calculation", "ground motion"

**Evening (1 hour):**
- Verify retrieval working end-to-end
- Note any issues with result quality

### Day 7: Initial Testing & Planning

**Morning (2 hours):**
- Write 10 test queries (diverse types)
- Examples:
  - "Where is hazard computed?"
  - "What does subroutine CY201305_NGA do?"
  - "How are ground motion prediction equations called?"
  - "What parameters are read from configuration files?"

**Afternoon (3 hours):**
- Run queries, manually assess relevance of top-5 results
- Calculate informal precision@5 for each query
- Document failure modes and hypotheses

**Evening (2 hours):**
- Update Week 2 plan based on Week 1 findings
- Document decisions made and open questions
- Prepare status update

---

## Risk register (updated)

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Vector-only retrieval misses identifier queries | High | Add lexical search Week 3 if eval shows gaps | Monitor |
| Chunking fails on >30% of code | High | Evaluate tree-sitter-fortran; accept degraded coverage | Week 1 test |
| COMMON blocks cause missing context | Medium | Add COMMON to symbol extraction Week 2 | Planned |
| Include file expansion required | Medium | Week 2 decision based on retrieval quality | Deferred |
| API costs exceed budget | Medium | Switch to Haiku for dev; cache embeddings | Monitor |
| Gold set quality insufficient | Medium | Start with 10 queries, iterate as corpus knowledge grows | Iterative |
| Public demo abuse | Low | Preloaded only, rate limits, query timeouts | Week 4 |
| Fortran 77 fixed-format edge cases | Medium | Accept imperfect parsing; focus on 80% coverage | Week 1 test |

---

## Cost estimates (balanced budget)

### Development phase (Weeks 1-4)

**Embeddings (one-time):**
- Corpus size: ~15K-20K LOC → ~400K-600K tokens
- Cost: $0.02/1M tokens × 0.5M = **$0.01** (negligible)

**Answer generation (development):**
- Queries during dev: ~200-300 queries
- Avg context: 5K tokens input, 500 tokens output per query
- Cost: (200 × 5K × $3/1M) + (200 × 500 × $15/1M) = **$3 + $1.50 = $4.50**

**Total dev cost estimate: $5-10** (very affordable for balanced budget)

### Production (monthly estimates)

**Assume: 1000 queries/month**
- Input: 1000 × 5K = 5M tokens × $3/1M = **$15/month**
- Output: 1000 × 500 = 0.5M tokens × $15/1M = **$7.50/month**
- **Total: ~$22.50/month** for production queries

**Hosting:**
- Render/Railway/Fly.io: ~$7-15/month for basic tier
- **Total monthly cost: ~$30-40** (well within balanced budget)

---

## Next steps (post-MVP, optional)

**If successful, consider:**
- Multi-corpus support (index multiple repos)
- Incremental indexing (detect changes, re-index diffs)
- Advanced visualizations (call graphs, module dependencies)
- IDE plugin (VSCode extension for in-editor queries)
- Lexical search improvements (BM25, hybrid reranking)
- Domain-specific query types ("Find all GMPEs", "List fault sources")
- Export functionality (save search results, citation lists)

---

## Appendix: Repository details

**Primary corpus:** https://github.com/usgs/nshmp-haz-fortran  
**Target commit:** Tag `nshm2014r1` (2014 NSHM Release 1)  
**License:** Public domain (US Government work)  
**Status:** Legacy code, superseded by Java version (nshmp-haz)  

**Directories to index:**
- `src/` - Main Fortran source (priority)
- `conf/` - Configuration files (index as documentation)
- `scripts/` - Shell scripts (optional, if relevant)
- `docs/` - Limited docs (index if present)

**Directories to ignore:**
- Build artifacts: `*.o`, `*.mod`, `*.exe`
- Data outputs: `CA_hazCurves/` (results, not source)
- Git metadata: `.git/`

**Key domain terminology (for gold queries):**
- GMPE: Ground Motion Prediction Equation
- PSHA: Probabilistic Seismic Hazard Analysis
- Attenuation: How ground motion decreases with distance
- Recurrence: Earthquake frequency models
- Deaggregation: Breaking down hazard contributions
- Site response: How local geology affects shaking

---

## Questions remaining (to be answered during execution)

1. **Week 1:** What % of code can regex chunker successfully parse?
2. **Week 1:** How many COMMON blocks exist? Are they heavily used?
3. **Week 2:** Do include files need inline expansion or are links sufficient?
4. **Week 2:** What's the actual token distribution of chunks? (Validate 200-500 target)
5. **Week 3:** Does vector-only retrieval work well for identifier queries?
6. **Week 3:** What are the main failure modes in evaluation?
7. **Week 4:** What's the actual query latency p95 in production?

**Discovery-driven approach:** These questions will be answered through hands-on work, not upfront speculation. The plan adapts based on empirical findings each week.

---

## Success definition

**MVP is successful if:**
1. ✅ Full corpus indexed with span metadata
2. ✅ Queries return relevant chunks with >70% precision@5
3. ✅ Answers include file/line citations that are accurate
4. ✅ 4 code understanding features operational
5. ✅ Public demo deployed and usable
6. ✅ Total cost <$50 for development phase

**Stretch goals:**
- Lexical search integrated if needed
- Evaluation metrics exceed targets (P@5 >80%, Hit@5 >90%)
- Query latency <2 seconds p95
- User testing with 3-5 domain experts shows value


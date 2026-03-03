# LegacyLens - HANDOFF.md

> **Purpose:** Continuity file for session handoffs
> **Last Updated:** 2026-03-02
> **Status:** Bootstrap Complete - Ready for Week 1 Discovery

---

## Current State

**Phase:** Week 1 - Discovery & Foundation (Starting)
**Next Milestone:** Clone NSHMP corpus and explore codebase

### What's Done
- Project directory structure created
- All bootstrap scaffolding files in place
- Generation module implemented (OpenAI GPT-4o)
- Config updated for OpenAI-only (removed Anthropic)
- README.md created for package installation

### What's In Progress
- Week 1 Day 1: Repository Exploration (clone and inventory NSHMP)

### What's Blocked
- Nothing

---

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `AGENTS.md` | Source of truth, technical decisions | Done |
| `tasks.md` | Task tracking, phase breakdown | Done |
| `HANDOFF.md` | Session continuity | This file |
| `pyproject.toml` | Dependencies, build config | Done |
| `docker-compose.yml` | Postgres + pgvector | Done |
| `.gitignore` | Git ignore rules | Done |
| `.pre-commit-config.yaml` | Ruff, black, mypy hooks | Done |
| `Makefile` | Common commands | Done |
| `README.md` | Package overview | Done |
| `src/legacylens/core/config.py` | Settings (OpenAI-only) | Done |
| `src/legacylens/core/schemas.py` | Pydantic models | Done |
| `src/legacylens/chunking/` | Fortran parser + chunker | Done |
| `src/legacylens/embedding/embedder.py` | OpenAI embedding client | Done |
| `src/legacylens/generation/` | GPT-4o answer generation | Done |
| `src/legacylens/db/models.py` | SQLAlchemy models | Done |
| `src/legacylens/api/` | FastAPI routes | Stub |
| `src/legacylens/retrieval/` | Vector search | Stub |
| `src/legacylens/ingestion/` | Pipeline | Stub |
| `ui/app.py` | Streamlit UI | Skeleton |

---

## Environment Setup

### Prerequisites
- Python 3.11+ (project requires >=3.11)
- Docker Desktop
- Git

### Required API Keys
```bash
OPENAI_API_KEY=sk-...      # For embeddings AND answer generation
```

### Quick Start
```bash
# Install (requires Python 3.11+)
pip install -e ".[dev]"

# Start database
docker-compose up -d

# Clone corpus (Week 1 Day 1)
git clone https://github.com/usgs/nshmp-haz-fortran.git corpus/
cd corpus && git checkout nshm2014r1

# Run tests
pytest tests/

# Start API
uvicorn src.legacylens.api.main:app --reload

# Start UI
streamlit run ui/app.py
```

---

## Corpus Details

**Repository:** https://github.com/usgs/nshmp-haz-fortran
**Target Tag:** `nshm2014r1`
**Language:** Fixed-format Fortran 77 (.f extension)
**Estimated Size:** 10,000-20,000 LOC (to be confirmed Week 1)

**Key Directories:**
- `src/` - Main source code (priority)
- `conf/` - Configuration files
- `scripts/` - Shell scripts
- `docs/` - Limited documentation

---

## Technical Context

### Stack Decisions
- **Embeddings:** OpenAI `text-embedding-3-small` (1536 dims)
- **Answer LLM:** OpenAI GPT-4o (changed from Claude)
- **Database:** Postgres 15 + pgvector
- **UI:** Streamlit
- **Chunking:** Regex-based with fallback windows

### Cost Estimates
- Full corpus embedding: ~$0.01 (negligible)
- Development queries (200-300): ~$4.50
- Monthly production (1000 queries): ~$22.50
- Hosting: ~$10-15/month
- **Total dev budget: <$50**

---

## Lessons Learned (Session 2)

### Configuration Changes
- **Decision:** Switched to OpenAI-only stack (removed Anthropic)
  - Rationale: Simpler dependency tree, single API key
  - Files affected: `pyproject.toml`, `.env.example`, `config.py`
  - Model change: `claude-sonnet-4-20250514` → `gpt-4o`

### Generation Module Implementation
- Created `src/legacylens/generation/` with:
  - `llm_client.py` - Async OpenAI client with retry logic
  - `answer_generator.py` - Context formatting + citation extraction
  - `prompts.py` - System prompt optimized for Fortran codebase Q&A
- Citation extraction uses regex to find `filename:line` patterns in answers

### Python Version Requirement
- Project requires Python 3.11+ (specified in pyproject.toml)
- System had Python 3.10.11, so `pip install -e .` failed
- Workaround: Verified syntax with `py_compile` instead

### Package Installation
- Hatchling requires `README.md` to exist
- Created minimal README.md to enable editable install

---

## Week 1 Priorities

### Day 1: Repository Exploration (NEXT)
1. [ ] Clone NSHMP repo to `corpus/`
2. [ ] File inventory (count .f files, LOC)
3. [ ] Sample 5-10 files, document patterns in `week1_discovery.md`
4. [ ] Test existing chunker against real files

### Day 2-3: Chunker Testing
1. [ ] Run chunker on actual corpus files
2. [ ] **Measure coverage: target >80%**
3. [ ] Refine regex patterns if needed

### Day 4: Database
1. [ ] Start `docker-compose up -d`
2. [ ] Test DB connection
3. [ ] Run migrations (create Alembic)

### Day 5-6: Ingestion & Retrieval
1. [ ] Wire up ingestion pipeline
2. [ ] Test embeddings on sample files
3. [ ] Basic retrieval working

### Day 7: Testing
1. [ ] 10 test queries
2. [ ] Manual relevance assessment

---

## Known Issues / Gotchas

### Fortran Quirks (To be confirmed Week 1)
- Fixed-format F77 with column restrictions
- COMMON blocks for shared state
- INCLUDE statements for file inclusion
- Continuation lines (column 6)
- C-style comments (column 1)

### Potential Risks
- Regex chunking may miss edge cases
- Identifier queries might fail without lexical search
- Context window limits for large subroutines

---

## Session Notes

### Session 1 (2026-03-02)
- Created project structure
- Wrote AGENTS.md, tasks.md, HANDOFF.md
- Beginning bootstrap phase

### Session 2 (2026-03-02)
- Completed bootstrap scaffolding review
- Removed Anthropic dependency (OpenAI-only)
- Implemented generation module:
  - `llm_client.py` - GPT-4o client
  - `answer_generator.py` - Answer synthesis with citations
  - `prompts.py` - LegacyLens system prompt
- Created README.md for package installation
- Verified syntax of all new files
- Ready for Week 1 discovery phase

---

## Handoff Checklist

Before ending a session, update:
- [x] This file (HANDOFF.md) with current state
- [ ] tasks.md with completed/in-progress items
- [ ] Any relevant code comments or docs
- [ ] Git status (commit or note uncommitted changes)

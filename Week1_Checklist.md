# LegacyLens - Week 1 Checklist

## Repository & Project Details
- **Repo:** https://github.com/usgs/nshmp-haz-fortran
- **Target:** Tag `nshm2014r1`
- **Budget:** Balanced (~$5-10 for Week 1)

---

## Day 1: Setup & Exploration ✅

### Morning Tasks
- [ ] Clone repository: `git clone https://github.com/usgs/nshmp-haz-fortran.git`
- [ ] Checkout target: `git checkout nshm2014r1`
- [ ] Confirm commit SHA: `git log -1`
- [ ] File inventory:
  ```bash
  find . -name "*.f" | wc -l     # Count F77 files
  find . -name "*.f90" | wc -l   # Count F90 files
  find src -type f | wc -l       # Total source files
  wc -l src/*.f | tail -1        # Total LOC estimate
  ```

### Afternoon Tasks
- [ ] Sample 5 representative files: `ls src/*.f | head -5`
- [ ] Read and document patterns:
  - Subroutine/function structure
  - COMMON block usage
  - INCLUDE statement patterns
  - Comment conventions
- [ ] Create `week1_discovery.md` notes

### Evening Tasks
- [ ] Set up Python environment: `python -m venv venv && source venv/bin/activate`
- [ ] Install dependencies:
  ```bash
  pip install openai anthropic psycopg2-binary sqlalchemy
  ```

---

## Day 2: Chunker Design ✅

### Morning Tasks
- [ ] Design `FortranChunker` class architecture
- [ ] Write regex patterns:
  - `^\s*SUBROUTINE \w+` → `END SUBROUTINE`
  - `^\s*FUNCTION \w+` → `END FUNCTION`
  - `^\s*PROGRAM \w+` → `END PROGRAM`
- [ ] Test patterns manually on 2-3 files

### Afternoon Tasks
- [ ] Implement `FortranChunker` class:
  - `chunk_file(filepath) -> List[Chunk]`
  - `extract_subroutines(text) -> List[Span]`
  - `fallback_window(text, lines=50, overlap=10) -> List[Span]`
- [ ] Test on sample files
- [ ] Print chunks with (file, start_line, end_line)

### Evening Tasks
- [ ] Document chunking strategy
- [ ] List known limitations and edge cases

---

## Day 3: Chunker Testing ✅

### All Day Tasks
- [ ] Write unit tests for boundary detection
- [ ] Test edge cases:
  - Nested blocks (if any)
  - Comment lines in subroutines
  - Continuation lines (F77 style)
  - Empty subroutines
- [ ] Measure coverage: `(chunked_lines / total_lines) * 100`
- [ ] **Target: >80% coverage on sample files**
- [ ] Refine patterns based on failures

---

## Day 4: Infrastructure - Database ✅

### Morning Tasks
- [ ] Create `docker-compose.yml`:
  ```yaml
  services:
    db:
      image: pgvector/pgvector:pg15
      environment:
        POSTGRES_USER: legacylens
        POSTGRES_PASSWORD: dev
        POSTGRES_DB: legacylens
      ports:
        - "5432:5432"
      volumes:
        - postgres_data:/var/lib/postgresql/data
  
  volumes:
    postgres_data:
  ```
- [ ] Start database: `docker-compose up -d`
- [ ] Write SQL schema or SQLAlchemy models:
  - `corpus` table
  - `file` table
  - `chunk` table
  - `embedding` table (with pgvector column)

### Afternoon Tasks
- [ ] Test DB connection from Python
- [ ] Implement data access layer:
  - `insert_corpus(repo_url, commit_sha)`
  - `insert_file(corpus_id, path, language, line_count)`
  - `insert_chunk(file_id, type, start_line, end_line, text)`
  - `insert_embedding(chunk_id, model, vector)`
- [ ] Test inserting sample data

### Evening Tasks
- [ ] Verify pgvector extension: `CREATE EXTENSION vector;`
- [ ] Test vector insert: `INSERT INTO embedding (vector) VALUES ('[0.1, 0.2, ...]')`
- [ ] Test cosine similarity query

---

## Day 5: Ingestion Pipeline ✅

### Morning Tasks
- [ ] Implement `ingest_repository(repo_path, corpus_id)`:
  1. Walk all .f files in src/
  2. For each file: chunk it
  3. Store file record in DB
  4. Store chunk records in DB
- [ ] Add logging: `logging.info(f"Processing {filepath}")`

### Afternoon Tasks
- [ ] Add OpenAI embedding calls:
  ```python
  from openai import OpenAI
  client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
  
  response = client.embeddings.create(
      model="text-embedding-3-small",
      input=[chunk.text for chunk in chunks]
  )
  ```
- [ ] Batch embeddings (max 100 chunks per call for efficiency)
- [ ] Test on 5-10 files

### Evening Tasks
- [ ] Measure performance:
  - Time per file
  - Tokens per chunk (estimate with tiktoken)
  - Embeddings stored count
- [ ] Calculate cost: `(total_tokens / 1M) * $0.02`
- [ ] Document: "Full corpus estimated at $X"

---

## Day 6: Retrieval Prototype ✅

### Morning Tasks
- [ ] Implement `search_chunks(query, top_k=10)`:
  ```python
  # 1. Get query embedding
  query_emb = client.embeddings.create(...)
  
  # 2. pgvector similarity search
  cursor.execute("""
      SELECT chunk_id, file.path, chunk.start_line, chunk.end_line, 
             chunk.text, 1 - (embedding.vector <=> %s) AS score
      FROM embedding
      JOIN chunk ON embedding.chunk_id = chunk.id
      JOIN file ON chunk.file_id = file.id
      WHERE corpus_id = %s
      ORDER BY embedding.vector <=> %s
      LIMIT %s
  """, (query_emb, corpus_id, query_emb, top_k))
  ```

### Afternoon Tasks
- [ ] Implement context assembly:
  - Dedupe overlapping spans
  - Sort by relevance score
  - Format with file paths and line ranges
- [ ] Test queries:
  - "hazard calculation"
  - "ground motion"
  - "subroutine CY201305_NGA"

### Evening Tasks
- [ ] Verify end-to-end: query → embedding → search → results
- [ ] Note result quality issues for Week 2

---

## Day 7: Initial Testing & Planning ✅

### Morning Tasks
- [ ] Write 10 test queries (diverse):
  1. "Where is hazard computed?"
  2. "What does subroutine CY201305_NGA do?"
  3. "How are ground motion prediction equations implemented?"
  4. "What parameters are read from configuration files?"
  5. "Where are fault rupture models defined?"
  6. "How is seismic attenuation calculated?"
  7. "What does the deaggregation routine do?"
  8. "Where are site response factors applied?"
  9. "How are GMPE weights determined?"
  10. "What does the sum_haz program do?"

### Afternoon Tasks
- [ ] Run each query
- [ ] Manually assess top-5 results for relevance (0=irrelevant, 1=relevant)
- [ ] Calculate: `precision@5 = (relevant_in_top5 / 5) * 100` per query
- [ ] Calculate: `hit@5 = (queries_with_any_relevant / 10) * 100`
- [ ] Document failure modes:
  - Identifier queries not working? (need lexical search)
  - Conceptual queries too broad? (need narrower chunks)
  - Wrong file types retrieved? (filter by file type)

### Evening Tasks
- [ ] Update Week 2 plan based on findings
- [ ] Document key decisions made:
  - Chunking coverage: X%
  - Estimated full corpus cost: $Y
  - Retrieval baseline: P@5 = Z%
- [ ] Prepare brief status update
- [ ] Identify blockers or risks for Week 2

---

## End of Week 1 Deliverables

Must have:
1. ✅ Chunking coverage report (~% of LOC successfully chunked)
2. ✅ Docker Compose stack running locally (DB + pgvector)
3. ✅ 5-10 sample files indexed with embeddings
4. ✅ 10 test queries with manual relevance scores
5. ✅ Week 2 plan updated based on findings

Nice to have:
- Script to automate full corpus ingestion
- Initial cost estimate for full corpus
- Notes on Fortran dialect quirks discovered

---

## Quick Commands Reference

```bash
# Start database
docker-compose up -d

# Run ingestion
python ingest.py --repo-path ./nshmp-haz-fortran --corpus-id 1

# Test search
python search.py --query "hazard calculation" --top-k 10

# Check database
psql -U legacylens -d legacylens -h localhost
\dt  # List tables
SELECT COUNT(*) FROM chunk;
SELECT COUNT(*) FROM embedding;

# Estimate costs
python -c "import tiktoken; enc = tiktoken.get_encoding('cl100k_base'); print(len(enc.encode(open('src/hazFXnga13l.f').read())))"
```

---

## Decision Points for Week 2

Based on Week 1 findings, decide:
- [ ] Is chunking coverage acceptable (>80%)? If no → explore tree-sitter
- [ ] Are identifier queries failing? If yes → add lexical search to Week 3
- [ ] Are COMMON blocks critical to understanding? If yes → add to symbol extraction
- [ ] Are include files causing missing context? If yes → add expansion logic

---

## Notes Space

**What I discovered:**
- 
- 
- 

**What surprised me:**
- 
- 
- 

**What I'm worried about:**
- 
- 
- 

**What I'm excited about:**
- 
- 
- 

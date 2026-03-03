# LegacyLens

RAG system for legacy Fortran scientific codebases.

## Overview

LegacyLens helps developers understand complex Fortran scientific code by providing natural-language queries with file/line-grounded citations.

## Features

- **Fortran-aware chunking**: Parses subroutines, functions, modules with regex patterns
- **Semantic search**: OpenAI embeddings with pgvector storage
- **Cited answers**: GPT-4o generated responses with source code citations
- **Discovery-driven**: Learn from your corpus before overbuilding

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env with your OpenAI API key

# Start database
docker-compose up -d

# Run ingestion
legacylens ingest --repo https://github.com/usgs/nshmp-haz-fortran --tag nshm2014r1

# Start API
legacylens serve

# Or run the Streamlit UI
streamlit run ui/app.py
```

## Architecture

```
src/legacylens/
├── chunking/       # Fortran parser + fallback chunker
├── embedding/      # OpenAI embedding client
├── generation/     # GPT-4o answer generation
├── retrieval/      # Vector search
├── db/             # SQLAlchemy models
├── api/            # FastAPI routes
└── core/           # Config and schemas
```

## License

MIT

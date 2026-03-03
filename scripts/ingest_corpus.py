#!/usr/bin/env python
"""Script to ingest a corpus into LegacyLens.

Usage:
    python scripts/ingest_corpus.py --repo-url https://github.com/usgs/nshmp-haz-fortran --tag nshm2014r1
"""

import argparse
import asyncio
import hashlib
import logging
import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacylens.chunking import FortranChunker
from legacylens.core.config import get_settings
from legacylens.core.schemas import ChunkType, CorpusStatus, ReferenceKind, SymbolKind
from legacylens.db import (
    ChunkRepository,
    CorpusRepository,
    EmbeddingRepository,
    FileRepository,
    ReferenceRepository,
    SymbolRepository,
    get_session_factory,
    init_db,
)
from legacylens.embedding.embedder import EmbeddingClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def clone_repo(repo_url: str, target_dir: Path, tag: str | None = None, commit: str | None = None) -> str:
    """Clone repository and return commit SHA."""
    if target_dir.exists():
        logger.info(f"Repository already exists at {target_dir}")
        subprocess.run(["git", "-C", str(target_dir), "fetch"], check=True)
    else:
        logger.info(f"Cloning {repo_url} to {target_dir}")
        subprocess.run(["git", "clone", repo_url, str(target_dir)], check=True)

    if tag:
        logger.info(f"Checking out tag: {tag}")
        subprocess.run(["git", "-C", str(target_dir), "checkout", f"tags/{tag}"], check=True)
    elif commit:
        logger.info(f"Checking out commit: {commit}")
        subprocess.run(["git", "-C", str(target_dir), "checkout", commit], check=True)

    # Get current commit SHA
    result = subprocess.run(
        ["git", "-C", str(target_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of file contents."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


async def ingest_corpus(
    repo_url: str,
    corpus_path: Path,
    commit_sha: str,
    batch_size: int = 100,
) -> None:
    """Ingest corpus into database with embeddings.

    Args:
        repo_url: Original repository URL
        corpus_path: Path to cloned repository
        commit_sha: Current commit SHA
        batch_size: Batch size for embedding generation
    """
    # Initialize database
    await init_db()

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Create corpus record
        corpus_repo = CorpusRepository(session)
        corpus = await corpus_repo.create(
            repo_url=repo_url,
            commit_sha=commit_sha,
            status=CorpusStatus.INGESTING,
        )
        await session.commit()
        logger.info(f"Created corpus record: ID={corpus.id}")

        # Find source directories
        src_dirs = []
        for src_dir in ["src", "source", "code"]:
            if (corpus_path / src_dir).exists():
                src_dirs.append(corpus_path / src_dir)

        if not src_dirs:
            src_dirs = [corpus_path]

        logger.info(f"Source directories: {src_dirs}")

        # Chunk files
        chunker = FortranChunker()
        file_repo = FileRepository(session)
        chunk_repo = ChunkRepository(session)

        all_chunks_data = []
        all_results = []  # Store all ChunkerResults for later use
        file_id_map = {}  # path -> file_id
        files_created = 0
        chunks_created = 0

        for src_dir in src_dirs:
            logger.info(f"Chunking files in {src_dir}")
            results = chunker.chunk_directory(src_dir)

            for result in results:
                if not result.chunks:
                    continue

                # Store result for later symbol/reference extraction
                all_results.append(result)

                # Get relative path from corpus root
                try:
                    rel_path = str(result.filepath.relative_to(corpus_path))
                except ValueError:
                    rel_path = str(result.filepath.name)

                # Create file record
                file_hash = compute_file_hash(result.filepath)
                file_record = await file_repo.create(
                    corpus_id=corpus.id,
                    path=rel_path,
                    line_count=result.total_lines,
                    hash=file_hash,
                )
                file_id_map[rel_path] = file_record.id
                files_created += 1

                # Create chunk records
                for chunk in result.chunks:
                    chunk_data = {
                        "file_id": file_record.id,
                        "chunk_type": chunk.chunk_type,
                        "name": chunk.name,
                        "start_line": chunk.span.start_line,
                        "end_line": chunk.span.end_line,
                        "text": chunk.text,
                        "token_count": chunk.token_count,
                        "hash": chunk.hash,
                    }
                    all_chunks_data.append(chunk_data)

        # Batch create chunks
        logger.info(f"Creating {len(all_chunks_data)} chunks...")
        for i in range(0, len(all_chunks_data), batch_size):
            batch = all_chunks_data[i : i + batch_size]
            await chunk_repo.batch_create(batch)
            chunks_created += len(batch)
            if (i + batch_size) % 1000 == 0 or i + batch_size >= len(all_chunks_data):
                logger.info(f"Created {chunks_created}/{len(all_chunks_data)} chunks")

        await session.commit()
        logger.info(f"Created {files_created} files, {chunks_created} chunks")

        # Extract and store symbols and references
        logger.info("Extracting symbols and references...")
        symbol_repo = SymbolRepository(session)
        reference_repo = ReferenceRepository(session)

        symbols_created = 0
        references_created = 0

        # Use stored results for symbol extraction
        for result in all_results:
            if not result.chunks:
                continue

            try:
                rel_path = str(result.filepath.relative_to(corpus_path))
            except ValueError:
                rel_path = str(result.filepath.name)

            file_id = file_id_map.get(rel_path)
            if not file_id:
                continue

            # Extract symbols from chunks (SUBROUTINE, FUNCTION, etc.)
            for chunk in result.chunks:
                if chunk.chunk_type in [ChunkType.SUBROUTINE, ChunkType.FUNCTION, ChunkType.PROGRAM, ChunkType.MODULE]:
                    await symbol_repo.create(
                        corpus_id=corpus.id,
                        name=chunk.name,
                        kind=SymbolKind(chunk.chunk_type.value),
                        file_id=file_id,
                        start_line=chunk.span.start_line,
                        end_line=chunk.span.end_line,
                        signature=chunk.name,  # TODO: Extract full signature
                    )
                    symbols_created += 1

            # Extract COMMON blocks as symbols
            for common in result.common_blocks:
                await symbol_repo.create(
                    corpus_id=corpus.id,
                    name=common.name,
                    kind=SymbolKind.COMMON,
                    file_id=file_id,
                    start_line=common.start_line,
                    end_line=common.end_line,
                    signature=common.signature,
                )
                symbols_created += 1

        await session.commit()
        logger.info(f"Created {symbols_created} symbols")

        # Now extract references (CALL and INCLUDE statements)
        logger.info("Extracting references...")

        # Build a lookup of symbols by name
        all_symbols = await symbol_repo.list_by_corpus(corpus.id, limit=10000)
        symbol_by_name: dict[str, list] = {}
        for sym in all_symbols:
            name_lower = sym.name.lower()
            if name_lower not in symbol_by_name:
                symbol_by_name[name_lower] = []
            symbol_by_name[name_lower].append(sym)

        # Use stored results for reference extraction
        for result in all_results:
            if not result.chunks:
                continue

            try:
                rel_path = str(result.filepath.relative_to(corpus_path))
            except ValueError:
                rel_path = str(result.filepath.name)

            file_id = file_id_map.get(rel_path)
            if not file_id:
                continue

            # Extract CALL references
            for line_num, callee_name, args in result.calls:
                # Find the symbol this call is within (optional)
                caller_symbol = await symbol_repo.find_at_line(file_id, line_num)
                from_symbol_id = caller_symbol.id if caller_symbol else None

                # Find the callee symbol (may not exist in corpus)
                callee_symbols = symbol_by_name.get(callee_name.lower(), [])
                to_symbol_id = callee_symbols[0].id if callee_symbols else None

                snippet = f"CALL {callee_name}({args})" if args else f"CALL {callee_name}"

                await reference_repo.create(
                    from_symbol_id=from_symbol_id,
                    to_symbol_id=to_symbol_id,
                    to_name=callee_name,
                    kind=ReferenceKind.CALL,
                    file_id=file_id,
                    line=line_num,
                    snippet=snippet,
                )
                references_created += 1

            # Extract INCLUDE references
            for line_num, include_path in result.includes:
                # Find the symbol this include is within (optional)
                container_symbol = await symbol_repo.find_at_line(file_id, line_num)
                from_symbol_id = container_symbol.id if container_symbol else None

                await reference_repo.create(
                    from_symbol_id=from_symbol_id,
                    to_symbol_id=None,  # INCLUDEs don't have a target symbol
                    to_name=include_path,
                    kind=ReferenceKind.INCLUDE,
                    file_id=file_id,
                    line=line_num,
                    snippet=f"INCLUDE '{include_path}'",
                )
                references_created += 1

        await session.commit()
        logger.info(f"Created {references_created} references")

        # Generate embeddings
        logger.info("Generating embeddings...")
        embedding_client = EmbeddingClient()
        embedding_repo = EmbeddingRepository(session)

        # Get all chunks with their IDs
        chunks = await chunk_repo.list_by_corpus(corpus.id)
        logger.info(f"Found {len(chunks)} chunks to embed")

        embeddings_created = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [chunk.text for chunk in batch]

            try:
                embeddings = await embedding_client.embed_batch(texts)
            except Exception as e:
                logger.error(f"Failed to generate embeddings for batch {i}: {e}")
                continue

            # Store embeddings
            embedding_data = []
            settings = get_settings()
            for chunk, embedding in zip(batch, embeddings):
                embedding_data.append({
                    "chunk_id": chunk.id,
                    "model": settings.embedding_model,
                    "dims": settings.embedding_dims,
                    "vector": embedding,
                })

            await embedding_repo.batch_create(embedding_data)
            embeddings_created += len(embedding_data)

            if (i + batch_size) % 500 == 0 or i + batch_size >= len(chunks):
                logger.info(f"Created {embeddings_created}/{len(chunks)} embeddings")

        await session.commit()
        logger.info(f"Created {embeddings_created} embeddings")

        # Update corpus status to READY
        await corpus_repo.update_status(corpus.id, CorpusStatus.READY)
        await session.commit()
        logger.info(f"Corpus {corpus.id} ingestion complete - status: READY")


async def main_async(args: argparse.Namespace) -> int:
    """Async main entry point."""
    # Clone repository
    corpus_path = Path(args.corpus_dir)
    try:
        commit_sha = clone_repo(args.repo_url, corpus_path, args.tag, args.commit)
        logger.info(f"Repository at commit: {commit_sha}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone repository: {e}")
        return 1

    if args.dry_run:
        # Just test chunking without database
        chunker = FortranChunker()
        all_results = []

        src_dirs = []
        for src_dir in ["src", "source", "code"]:
            if (corpus_path / src_dir).exists():
                src_dirs.append(corpus_path / src_dir)

        if not src_dirs:
            src_dirs = [corpus_path]

        for src_dir in src_dirs:
            logger.info(f"Chunking files in {src_dir}")
            results = chunker.chunk_directory(src_dir)
            all_results.extend(results)

        report = chunker.get_coverage_report(all_results)

        logger.info("=== Chunking Report ===")
        logger.info(f"Total files: {report['total_files']}")
        logger.info(f"Total lines: {report['total_lines']}")
        logger.info(f"Chunked lines: {report['chunked_lines']}")
        logger.info(f"Coverage: {report['coverage_pct']:.1f}%")
        logger.info(f"Total chunks: {report['total_chunks']}")
        logger.info(f"Chunks by type: {report['chunks_by_type']}")

        if report["files_below_threshold"]:
            logger.warning(f"Files below 80% coverage: {len(report['files_below_threshold'])}")

        logger.info("Dry run complete - no data stored in database")
        return 0

    # Run full ingestion
    try:
        await ingest_corpus(args.repo_url, corpus_path, commit_sha, args.batch_size)
        return 0
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest corpus into LegacyLens")
    parser.add_argument(
        "--repo-url",
        required=True,
        help="Repository URL to clone",
    )
    parser.add_argument(
        "--tag",
        help="Git tag to checkout",
    )
    parser.add_argument(
        "--commit",
        help="Git commit SHA to checkout",
    )
    parser.add_argument(
        "--corpus-dir",
        default="corpus",
        help="Directory to clone repository into",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for embedding generation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually store in database, just test chunking",
    )

    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())

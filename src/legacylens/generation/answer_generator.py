"""Answer generator with citation extraction."""

import re
import time
from typing import Any

from legacylens.core.schemas import (
    ChunkWithScore,
    Citation,
    QueryResponse,
    Span,
)
from legacylens.generation.llm_client import LLMClient
from legacylens.generation.prompts import CONTEXT_PROMPT, SYSTEM_PROMPT


class AnswerGenerator:
    """Generates answers with citations from retrieved chunks."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
    ):
        """Initialize the answer generator.

        Args:
            llm_client: LLM client for generation (created if not provided)
        """
        self.llm_client = llm_client or LLMClient()

    def _format_chunks_for_context(
        self,
        chunks: list[ChunkWithScore],
        max_chunks: int = 10,
        max_chars_per_chunk: int = 2000,
    ) -> str:
        """Format chunks into context string for the LLM.

        Args:
            chunks: Retrieved chunks with scores
            max_chunks: Maximum number of chunks to include
            max_chars_per_chunk: Maximum characters per chunk

        Returns:
            Formatted context string
        """
        context_parts = []

        for i, chunk in enumerate(chunks[:max_chunks]):
            # Truncate chunk text if needed
            text = chunk.text
            if len(text) > max_chars_per_chunk:
                text = text[:max_chars_per_chunk] + "\n... [truncated]"

            context_parts.append(
                f"### Chunk {i + 1} (score: {chunk.score:.3f})\n"
                f"File: {chunk.span.file_path}\n"
                f"Lines: {chunk.span.start_line}-{chunk.span.end_line}\n"
                f"Type: {chunk.chunk_type.value}\n"
                f"Name: {chunk.name or 'N/A'}\n\n"
                f"```\n{text}\n```\n"
            )

        return "\n".join(context_parts)

    def _extract_citations_from_answer(
        self,
        answer: str,
        chunks: list[ChunkWithScore],
    ) -> list[Citation]:
        """Extract citations mentioned in the answer.

        Looks for patterns like:
        - `filename:123`
        - `filename:123-456`
        - "in filename line 123"

        Args:
            answer: Generated answer text
            chunks: Source chunks to match citations against

        Returns:
            List of citations found in the answer
        """
        citations = []
        seen_spans: set[str] = set()

        # Build a lookup of chunks by file path
        chunks_by_file: dict[str, list[ChunkWithScore]] = {}
        for chunk in chunks:
            if chunk.span.file_path not in chunks_by_file:
                chunks_by_file[chunk.span.file_path] = []
            chunks_by_file[chunk.span.file_path].append(chunk)

        # Pattern 1: `filename:line` or `filename:line-line`
        pattern1 = r"`([^`]+?):(\d+)(?:-(\d+))?`"
        # Pattern 2: "in filename line 123" or "in filename lines 123-456"
        pattern2 = r"in\s+(\S+?)\s+lines?\s+(\d+)(?:-(\d+))?"

        for pattern in [pattern1, pattern2]:
            matches = re.finditer(pattern, answer, re.IGNORECASE)

            for match in matches:
                filepath = match.group(1)
                start_line = int(match.group(2))
                end_line = int(match.group(3)) if match.group(3) else start_line

                # Normalize file path (remove any leading path components)
                filename = filepath.split("/")[-1]

                # Find matching chunk(s)
                for file_chunks in chunks_by_file.values():
                    for chunk in file_chunks:
                        chunk_filename = chunk.span.file_path.split("/")[-1]
                        if chunk_filename == filename:
                            # Check if the cited lines overlap with the chunk
                            if (
                                start_line <= chunk.span.end_line
                                and end_line >= chunk.span.start_line
                            ):
                                span_key = f"{chunk.span.file_path}:{start_line}-{end_line}"
                                if span_key not in seen_spans:
                                    seen_spans.add(span_key)

                                    # Extract snippet from answer near the citation
                                    snippet_match = re.search(
                                        rf".{{0,100}}{re.escape(match.group(0))}.{{0,100}}",
                                        answer,
                                        re.DOTALL,
                                    )
                                    snippet = (
                                        snippet_match.group(0).strip()
                                        if snippet_match
                                        else chunk.text[:500]
                                    )

                                    citations.append(
                                        Citation(
                                            span=Span(
                                                file_path=chunk.span.file_path,
                                                start_line=start_line,
                                                end_line=end_line,
                                            ),
                                            snippet=snippet,
                                            relevance=f"Referenced in answer",
                                        )
                                    )
                                break

        return citations[:10]  # Limit to 10 citations

    async def generate_answer(
        self,
        query: str,
        chunks: list[ChunkWithScore],
        max_chunks: int = 10,
        temperature: float = 0.1,
    ) -> QueryResponse:
        """Generate an answer for a query using retrieved chunks.

        Args:
            query: User's natural language query
            chunks: Retrieved chunks with relevance scores
            max_chunks: Maximum chunks to include in context
            temperature: LLM temperature (lower = more deterministic)

        Returns:
            QueryResponse with answer and citations
        """
        start_time = time.time()

        if not chunks:
            return QueryResponse(
                query=query,
                answer="I couldn't find any relevant code in the corpus for your query. "
                "Try rephrasing your question or checking if the code has been ingested.",
                citations=[],
                chunks=[],
                latency_ms=(time.time() - start_time) * 1000,
            )

        # Format context from chunks
        context = self._format_chunks_for_context(chunks, max_chunks)

        # Build prompt
        user_prompt = CONTEXT_PROMPT.format(context=context, query=query)

        # Generate answer
        answer = await self.llm_client.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=temperature,
        )

        # Extract citations from answer
        citations = self._extract_citations_from_answer(answer, chunks)

        latency_ms = (time.time() - start_time) * 1000

        return QueryResponse(
            query=query,
            answer=answer,
            citations=citations,
            chunks=chunks[:max_chunks],
            latency_ms=latency_ms,
        )

"""OpenAI embedding client with rate limiting and batching."""

import asyncio
import logging
from typing import Any

import tiktoken
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from legacylens.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Client for generating embeddings using OpenAI API."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        max_tokens: int = 8000,  # Leave buffer below 8191 limit for safety
    ):
        """Initialize the embedding client.

        Args:
            model: Embedding model to use (default from settings)
            api_key: OpenAI API key (default from settings)
            max_tokens: Maximum tokens per text (default 8000 for safety margin)
        """
        settings = get_settings()
        self.model = model or settings.embedding_model
        self.dims = settings.embedding_dims
        self.max_tokens = max_tokens
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self._encoder = tiktoken.encoding_for_model("text-embedding-3-small")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self._encoder.encode(text))

    def truncate_text(self, text: str, max_tokens: int | None = None) -> str:
        """Truncate text to fit within token limit.

        Preserves beginning and end of text, removes middle.
        This keeps important context from both ends of code chunks.

        Args:
            text: Text to potentially truncate
            max_tokens: Maximum tokens allowed (default from self.max_tokens)

        Returns:
            Text truncated to fit within limit, with marker if truncated
        """
        if max_tokens is None:
            max_tokens = self.max_tokens

        tokens = self._encoder.encode(text)

        if len(tokens) <= max_tokens:
            return text

        # Log truncation
        logger.warning(
            f"Truncating text from {len(tokens)} to {max_tokens} tokens "
            f"({len(tokens) - max_tokens} tokens removed)"
        )

        # Keep first 60% and last 40% of tokens
        # This preserves function signatures and return statements in code
        keep_start = int(max_tokens * 0.6)
        keep_end = max_tokens - keep_start

        truncated_tokens = tokens[:keep_start] + tokens[-keep_end:]

        # Decode and add truncation marker
        start_text = self._encoder.decode(tokens[:keep_start])
        end_text = self._encoder.decode(tokens[-keep_end:])

        marker = "\n\n... [truncated for embedding] ...\n\n"
        return start_text + marker + end_text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
    )
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed (will be truncated if too long)

        Returns:
            List of embedding values
        """
        # Truncate if needed
        text = self.truncate_text(text)

        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return list(response.data[0].embedding)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
    )
    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed (each will be truncated if needed)
            batch_size: Number of texts per API call (max 100 for efficiency)

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Truncate each text in batch
            truncated_batch = [self.truncate_text(text) for text in batch]

            response = await self.client.embeddings.create(
                model=self.model,
                input=truncated_batch,
            )

            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            batch_embeddings = [list(item.embedding) for item in sorted_data]
            all_embeddings.extend(batch_embeddings)

            # Rate limiting: small delay between batches
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)

        return all_embeddings

    async def embed_chunks(
        self,
        chunks: list[Any],
        text_attr: str = "text",
    ) -> list[tuple[int, list[float]]]:
        """Generate embeddings for chunks.

        Args:
            chunks: List of chunk objects with text attribute
            text_attr: Attribute name for text content

        Returns:
            List of (chunk_id, embedding) tuples
        """
        texts = [getattr(chunk, text_attr) for chunk in chunks]
        embeddings = await self.embed_batch(texts)

        return [
            (chunk.id, embedding)
            for chunk, embedding in zip(chunks, embeddings)
            if chunk.id is not None
        ]

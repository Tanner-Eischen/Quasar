"""OpenAI GPT-4o client for answer generation."""

from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from legacylens.core.config import get_settings


class LLMClient:
    """Client for generating answers using OpenAI GPT-4o."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize the LLM client.

        Args:
            model: Model to use (default from settings)
            api_key: OpenAI API key (default from settings)
        """
        settings = get_settings()
        self.model = model or settings.answer_model
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
    )
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User query with context
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
    )
    async def generate_with_messages(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a response from the LLM with custom message history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Note: This is a rough estimate. For precise counts, use tiktoken.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token for English/code
        return len(text) // 4

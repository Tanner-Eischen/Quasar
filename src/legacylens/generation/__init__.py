"""Generation module for answer synthesis."""

from legacylens.generation.answer_generator import AnswerGenerator
from legacylens.generation.llm_client import LLMClient
from legacylens.generation.prompts import CONTEXT_PROMPT, SYSTEM_PROMPT

__all__ = [
    "AnswerGenerator",
    "LLMClient",
    "SYSTEM_PROMPT",
    "CONTEXT_PROMPT",
]

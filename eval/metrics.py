"""Evaluation metrics for LegacyLens."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""

    query_id: str
    query: str
    retrieved_chunks: list[dict]  # List of chunk dicts with 'file_path', 'start_line', etc.
    expected_files: list[str]
    expected_symbols: list[str]
    latency_ms: float


@dataclass
class EvaluationMetrics:
    """Computed evaluation metrics."""

    precision_at_5: float
    precision_at_10: float
    hit_at_5: bool
    hit_at_10: bool
    mrr: float  # Mean Reciprocal Rank
    recall: float


def is_relevant(chunk: dict, expected_files: list[str], expected_symbols: list[str]) -> bool:
    """Determine if a chunk is relevant to the query.

    A chunk is relevant if:
    - Its file_path matches an expected file, OR
    - Its name (subroutine/function) matches an expected symbol
    """
    chunk_file = chunk.get("file_path", "")
    chunk_name = chunk.get("name", "")

    # Check file match
    for expected_file in expected_files:
        if expected_file in chunk_file or chunk_file.endswith(expected_file):
            return True

    # Check symbol match
    if chunk_name:
        for expected_symbol in expected_symbols:
            if chunk_name.upper() == expected_symbol.upper():
                return True

    return False


def compute_metrics(result: RetrievalResult, k_values: list[int] = [5, 10]) -> EvaluationMetrics:
    """Compute evaluation metrics for a single query result.

    Args:
        result: RetrievalResult with retrieved chunks and expected items
        k_values: Values of K for Precision@K

    Returns:
        EvaluationMetrics object
    """
    retrieved = result.retrieved_chunks
    expected_files = result.expected_files
    expected_symbols = result.expected_symbols

    # Check relevance for each retrieved chunk
    relevance = [
        is_relevant(chunk, expected_files, expected_symbols)
        for chunk in retrieved
    ]

    # Precision@K
    precision_at_5 = sum(relevance[:5]) / min(5, len(relevance)) if relevance else 0.0
    precision_at_10 = sum(relevance[:10]) / min(10, len(relevance)) if relevance else 0.0

    # Hit@K (at least one relevant in top K)
    hit_at_5 = any(relevance[:5])
    hit_at_10 = any(relevance[:10])

    # Mean Reciprocal Rank (position of first relevant result)
    mrr = 0.0
    for i, rel in enumerate(relevance):
        if rel:
            mrr = 1.0 / (i + 1)
            break

    # Recall (how many expected items found)
    # This is approximate since we're not tracking all expected chunks
    found_files = set()
    found_symbols = set()
    for chunk, rel in zip(retrieved, relevance):
        if rel:
            chunk_file = chunk.get("file_path", "")
            chunk_name = chunk.get("name", "")
            for expected_file in expected_files:
                if expected_file in chunk_file:
                    found_files.add(expected_file)
            if chunk_name:
                for expected_symbol in expected_symbols:
                    if chunk_name.upper() == expected_symbol.upper():
                        found_symbols.add(expected_symbol)

    total_expected = len(expected_files) + len(expected_symbols)
    total_found = len(found_files) + len(found_symbols)
    recall = total_found / total_expected if total_expected > 0 else 1.0

    return EvaluationMetrics(
        precision_at_5=precision_at_5,
        precision_at_10=precision_at_10,
        hit_at_5=hit_at_5,
        hit_at_10=hit_at_10,
        mrr=mrr,
        recall=recall,
    )


def aggregate_metrics(results: list[EvaluationMetrics]) -> dict[str, float]:
    """Aggregate metrics across multiple queries.

    Args:
        results: List of EvaluationMetrics

    Returns:
        Dictionary of aggregated metrics
    """
    if not results:
        return {}

    n = len(results)

    return {
        "mean_precision_at_5": sum(r.precision_at_5 for r in results) / n,
        "mean_precision_at_10": sum(r.precision_at_10 for r in results) / n,
        "hit_at_5_rate": sum(1 for r in results if r.hit_at_5) / n,
        "hit_at_10_rate": sum(1 for r in results if r.hit_at_10) / n,
        "mean_mrr": sum(r.mrr for r in results) / n,
        "mean_recall": sum(r.recall for r in results) / n,
    }

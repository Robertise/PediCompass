"""
Cross-encoder reranker singleton (CPU-only).

Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` to rerank Qdrant candidates
before returning them to the agent. Loaded once and cached.

Only used in the backend (not in the ingestion pipeline).
"""

import logging
from functools import lru_cache

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def get_reranker() -> "CrossEncoder":
    """
    Bypass loading the cross-encoder model for fast local startup.
    """
    logger.info("Cross-encoder loading bypassed.")
    return None


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 3,
) -> list[dict]:
    """
    Rerank a list of candidate chunks using the cross-encoder.

    Args:
        query: The original query string.
        candidates: List of chunk dicts, each must have a "text" field.
        top_k: Number of top results to return.

    Returns:
        Top-k chunk dicts sorted by descending rerank score, with
        a "rerank_score" field added to each.
    """
    if not candidates:
        return []

    model = get_reranker()
    pairs = [(query, c.get("text", "")) for c in candidates]
    scores = model.predict(pairs)

    ranked = sorted(
        zip(scores, candidates),
        key=lambda x: x[0],
        reverse=True,
    )

    result = []
    for score, chunk in ranked[:top_k]:
        enriched = dict(chunk)
        enriched["rerank_score"] = float(score)
        result.append(enriched)

    return result

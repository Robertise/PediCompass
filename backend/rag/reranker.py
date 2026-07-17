"""
Cross-encoder reranker singleton (CPU-only).

Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` to rerank Qdrant candidates
before returning them to the agent. Loaded once and cached.

Only used in the backend (not in the ingestion pipeline).
"""

import logging
import math
from functools import lru_cache

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def get_reranker() -> "CrossEncoder":
    """
    Load the cross-encoder model once and cache it for the process lifetime.

    CPU-only — avoids downloading the heavy CUDA build.
    """
    logger.info("Loading cross-encoder: %s", _RERANKER_MODEL)
    model = CrossEncoder(_RERANKER_MODEL, device="cpu")
    logger.info("Cross-encoder loaded.")
    return model


def _sigmoid(x: float) -> float:
    """Normalize a raw logit to [0, 1] probability scale."""
    return 1.0 / (1.0 + math.exp(-x))


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
        a "rerank_score" field added to each. Score is sigmoid-normalized
        to [0, 1] for stable threshold comparisons.
    """
    if not candidates:
        return []

    model = get_reranker()
    pairs = [(query, c.get("text", "")) for c in candidates]
    raw_scores = model.predict(pairs)

    ranked = sorted(
        zip(raw_scores, candidates),
        key=lambda x: x[0],
        reverse=True,
    )

    result = []
    for raw_score, chunk in ranked[:top_k]:
        enriched = dict(chunk)
        normalized = _sigmoid(float(raw_score))
        enriched["rerank_score"] = normalized
        enriched["rerank_score_raw"] = float(raw_score)  # retained for debug logging
        result.append(enriched)

    return result

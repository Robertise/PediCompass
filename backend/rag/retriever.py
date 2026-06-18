"""
Two-pass retrieval pipeline.

Pass 1: Qdrant semantic search with age_group metadata filter
         → up to 10 candidates
Pass 2: Cross-encoder rerank
         → top 3 chunks returned to Stage 3
"""

import logging

from common.age_utils import AgeGroup
from rag.qdrant_client import QdrantManager
from rag.reranker import CrossEncoder, rerank

logger = logging.getLogger(__name__)

# Number of candidates to pull from Qdrant before reranking
_CANDIDATE_K = 10
# Number of final results after reranking
_TOP_K = 3


class Retriever:
    """
    Two-pass retriever: Qdrant filtered search → cross-encoder rerank → top-3.
    """

    def __init__(self, qdrant_manager: QdrantManager, reranker: "CrossEncoder") -> None:
        self.qdrant = qdrant_manager
        self.reranker = reranker

    async def retrieve(
        self,
        query_vector: list[float],
        age_group: AgeGroup,
        query_text: str = "",
    ) -> list[dict]:
        """
        Retrieve top-3 guideline chunks for the given query.

        Args:
            query_vector: 384-dim embedding of the symptom summary.
            age_group: Child's age group (used as Qdrant metadata filter).
            query_text: Original query text for cross-encoder reranking.
                        If empty, chunk texts are ranked by vector score only.

        Returns:
            Up to 3 chunk dicts, sorted by rerank score (descending).
        """
        # Pass 1: Qdrant with age_group filter
        # Include both the child's specific group AND "all" (universal guidelines)
        age_filter = [age_group.value, "all"]
        candidates = self.qdrant.search(
            query_vector=query_vector,
            age_group_filter=age_filter,
            top_k=_CANDIDATE_K,
        )
        logger.info(
            "Qdrant returned %d candidates for age_group=%s",
            len(candidates),
            age_group.value,
        )

        if not candidates:
            return []

        # Pass 2: Cross-encoder rerank
        # Use query_text if available; fall back to vector score ordering
        if query_text:
            ranked = rerank(query=query_text, candidates=candidates, top_k=_TOP_K)
        else:
            # No query text — sort by Qdrant vector score (already provided)
            ranked = sorted(candidates, key=lambda c: c.get("score", 0), reverse=True)[:_TOP_K]

        logger.info("After rerank: returning %d chunks", len(ranked))
        return ranked

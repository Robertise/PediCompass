"""
Stage 2 — Retrieval.

Two-pass retrieval pipeline:
  1. Embed the symptom query using common.embedder (same model + config as ingestion).
  2. Filter by age_group in Qdrant (must match child's group or "all").
  3. Rerank top-10 candidates with the cross-encoder singleton.
  4. Return top-3 chunks with full metadata.
"""

import logging
from typing import Optional

from common.age_utils import AgeGroup
from common.embedder import embed
from rag.retriever import Retriever

logger = logging.getLogger(__name__)


class Stage2Retriever:
    """
    Stage 2: Retrieve relevant guideline chunks for the symptom summary
    filtered to the child's age group.
    """

    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever

    async def retrieve(
        self,
        symptom_summary: str,
        age_group: AgeGroup,
    ) -> list[dict]:
        """
        Retrieve and rerank guideline chunks relevant to the symptom summary.

        Args:
            symptom_summary: Concise symptom description from Stage 1.
            age_group: Resolved age group for metadata filtering.

        Returns:
            List of up to 3 chunk dicts, each containing:
              - chunk_id, text, source_authority, age_group, score (rerank score)
        """
        logger.info(
            "Stage 2: retrieving for age_group=%s, query=%r",
            age_group.value,
            symptom_summary[:80],
        )

        query_vector = embed(symptom_summary)
        chunks = await self.retriever.retrieve(
            query_vector=query_vector,
            age_group=age_group,
        )

        logger.info("Stage 2: returned %d chunks", len(chunks))
        return chunks

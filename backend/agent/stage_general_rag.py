"""
Stage General RAG — Handles GENERAL intent queries by searching the entire KB
without age stratification and generating a prose response.
"""

from dataclasses import dataclass
import asyncio
import logging

from common.embedder import embed
from rag.retriever import Retriever
from llm.bedrock_client import BedrockClient
from llm.prompts.general_rag_prompt import GENERAL_RAG_SYSTEM_PROMPT
from guardrails.prompt_constraints import SAFETY_SYSTEM_PROMPT_SNIPPET

logger = logging.getLogger(__name__)


@dataclass
class GeneralRAGResult:
    text: str
    cited_sources: list[dict]


# Minimum sigmoid-normalized reranker score to consider a chunk as relevant.
# ms-marco-MiniLM-L-6-v2 raw logit → sigmoid. Threshold 0.25 ≈ raw logit ~-1.1,
# which reliably separates topic-adjacent noise from actual relevant content.
# Calibrate by observing logged raw/normalized scores in production.
MIN_RELEVANCE_SCORE = 0.25

OUT_OF_SCOPE_RESPONSE = (
    "That topic isn't covered in my pediatric knowledge base. "
    "My expertise covers common childhood illnesses, symptoms, and care guidance "
    "based on WHO, CDC, and AAP guidelines.\n\n"
    "If you have concerns about your child's health, please consult a qualified "
    "pediatric healthcare professional."
)

SOFT_NUDGE = (
    "If you're asking because your child is currently showing these symptoms, "
    "please describe their specific situation and I can provide more personalized guidance."
)


class GeneralRAGHandler:
    def __init__(self, retriever: Retriever, bedrock_client: BedrockClient) -> None:
        self.retriever = retriever
        self.llm = bedrock_client

    async def handle(
        self,
        topic_summary: str,
        context: list[dict],
    ) -> GeneralRAGResult:
        # 1. Embed the topic summary
        loop = asyncio.get_running_loop()
        query_vector = await loop.run_in_executor(None, embed, topic_summary)

        # 2. Retrieve from Qdrant — NO age_group filter
        chunks = await self.retriever.retrieve_general(
            query_vector=query_vector,
            query_text=topic_summary,
        )

        # 3. Grounding check — log scores and short-circuit if not relevant enough
        if not chunks:
            logger.info(
                "GeneralRAG: no chunks retrieved for topic=%r — returning out-of-scope",
                topic_summary,
            )
            return GeneralRAGResult(text=OUT_OF_SCOPE_RESPONSE, cited_sources=[])

        best_chunk = chunks[0]
        best_normalized = best_chunk.get("rerank_score", 0.0)
        best_raw = best_chunk.get("rerank_score_raw", None)
        logger.info(
            "GeneralRAG: topic=%r | best_score_normalized=%.4f | best_score_raw=%s | threshold=%.2f",
            topic_summary,
            best_normalized,
            f"{best_raw:.4f}" if best_raw is not None else "n/a (vector-score-only)",
            MIN_RELEVANCE_SCORE,
        )

        if best_normalized < MIN_RELEVANCE_SCORE:
            logger.info(
                "GeneralRAG: score %.4f below threshold %.2f — returning out-of-scope",
                best_normalized,
                MIN_RELEVANCE_SCORE,
            )
            return GeneralRAGResult(text=OUT_OF_SCOPE_RESPONSE, cited_sources=[])

        # 4. Build system + user message
        system = GENERAL_RAG_SYSTEM_PROMPT + "\n\n" + SAFETY_SYSTEM_PROMPT_SNIPPET
        user_msg = self._build_user_message(topic_summary, chunks)

        # 5. Generate prose
        text = await self.llm.ainvoke_text(
            system=system,
            messages=[{"role": "user", "content": user_msg}],
            max_tokens=400,
        )

        # 6. If LLM returned the sentinel grounding phrase, map to canonical OOS response
        stripped = text.strip()
        if "isn't covered in my pediatric knowledge base" in stripped:
            logger.info("GeneralRAG: LLM returned out-of-scope sentinel — using OOS response")
            return GeneralRAGResult(text=OUT_OF_SCOPE_RESPONSE, cited_sources=[])

        # 7. Append soft nudge and return
        full_text = stripped + "\n\n" + SOFT_NUDGE
        cited_sources = self._build_citations(chunks)
        return GeneralRAGResult(text=full_text, cited_sources=cited_sources)

    def _build_user_message(self, topic_summary: str, chunks: list[dict]) -> str:
        prompt = f"The parent is asking about: {topic_summary}\n\n"
        prompt += "Relevant pediatric guidelines (use these to answer if helpful):\n"
        for i, chunk in enumerate(chunks, 1):
            prompt += f"\n--- Source [{i}] ---\n"
            prompt += f"Authority: {chunk.get('source_authority', 'Unknown')}\n"
            prompt += f"Content:\n{chunk.get('text', '')}\n"
        prompt += "\nPlease write your response now."
        return prompt

    def _build_citations(self, chunks: list[dict]) -> list[dict]:
        citations = []
        for chunk in chunks:
            citations.append({
                "source_authority": chunk.get("source_authority", "Unknown"),
                "doc_id": chunk.get("doc_id", "Unknown"),
            })
        # Deduplicate by doc_id while preserving order
        seen = set()
        deduped = []
        for c in citations:
            if c["doc_id"] not in seen:
                seen.add(c["doc_id"])
                deduped.append(c)
        return deduped

"""
Stage General RAG — Handles GENERAL intent queries by searching the entire KB
without age stratification and generating a prose response.
"""

from dataclasses import dataclass
import asyncio

from common.embedder import embed
from rag.retriever import Retriever
from llm.bedrock_client import BedrockClient
from llm.prompts.general_rag_prompt import GENERAL_RAG_SYSTEM_PROMPT
from guardrails.prompt_constraints import SAFETY_SYSTEM_PROMPT_SNIPPET


@dataclass
class GeneralRAGResult:
    text: str
    cited_sources: list[dict]


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

        # 3. Build system + user message
        system = GENERAL_RAG_SYSTEM_PROMPT + "\n\n" + SAFETY_SYSTEM_PROMPT_SNIPPET
        user_msg = self._build_user_message(topic_summary, chunks)

        # 4. Generate prose
        text = await self.llm.ainvoke_text(
            system=system,
            messages=[{"role": "user", "content": user_msg}],
            max_tokens=400,
        )

        # 5. Append soft nudge
        full_text = text.strip() + "\n\n" + SOFT_NUDGE
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

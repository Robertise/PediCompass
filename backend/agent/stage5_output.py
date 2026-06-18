"""
Stage 5 — Parent-Facing Output Generation.

Uses invoke_text (no tool_use) to produce warm, empathetic prose that
a non-medical parent can understand and act on.

max_tokens = 800.
"""

import logging
from dataclasses import dataclass

from agent.models import CarePathway, ReasoningTrace
from guardrails.prompt_constraints import SAFETY_SYSTEM_PROMPT_SNIPPET
from llm.bedrock_client import BedrockClient
from llm.prompts.stage5_prompt import STAGE5_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class Stage5Output:
    """Container for Stage 5 output."""

    text: str
    pre_visit_checklist: list[str]
    warning_signs: list[str]
    cited_sources: list[dict]


class Stage5OutputGenerator:
    """
    Stage 5: Generates parent-facing prose from the CarePathway and
    retrieved evidence.
    """

    MAX_TOKENS = 800

    def __init__(self, bedrock_client: BedrockClient) -> None:
        self.llm = bedrock_client

    async def generate(
        self,
        pathway: CarePathway,
        chunks: list[dict],
        trace: ReasoningTrace,
    ) -> Stage5Output:
        """
        Generate a parent-friendly response.

        Args:
            pathway: The final CarePathway from Stage 3.
            chunks: Retrieved guideline chunks for source citation.
            trace: Full reasoning trace (for context, not exposed to parents).

        Returns:
            Stage5Output with the prose text plus structured sub-sections.
        """
        system = STAGE5_SYSTEM_PROMPT + "\n\n" + SAFETY_SYSTEM_PROMPT_SNIPPET
        user_message = self._build_user_message(pathway, chunks)

        messages = [{"role": "user", "content": user_message}]

        text = self.llm.invoke_text(
            system=system,
            messages=messages,
            max_tokens=self.MAX_TOKENS,
        )

        cited_sources = self._build_citations(chunks)
        checklist = self._extract_checklist(pathway)
        warning_signs = self._extract_warning_signs(pathway, chunks)

        return Stage5Output(
            text=text,
            pre_visit_checklist=checklist,
            warning_signs=warning_signs,
            cited_sources=cited_sources,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _build_user_message(self, pathway: CarePathway, chunks: list[dict]) -> str:
        sources = "\n".join(
            f"  [{i+1}] {c.get('source_authority', 'Unknown')}: {c.get('text', '')[:200]}…"
            for i, c in enumerate(chunks)
        )
        return (
            f"CARE PATHWAY:\n"
            f"  Urgency level: {pathway.urgency_level.value}\n"
            f"  Care setting: {pathway.care_setting}\n"
            f"  Immediate actions:\n"
            + "\n".join(f"    - {a}" for a in pathway.immediate_actions)
            + f"\n  Clinical reasoning: {pathway.clinical_reasoning}\n\n"
            f"SUPPORTING EVIDENCE:\n{sources or '  None available.'}\n\n"
            "Write a warm, clear, parent-facing response based on the above pathway."
        )

    def _build_citations(self, chunks: list[dict]) -> list[dict]:
        citations = []
        for i, chunk in enumerate(chunks, start=1):
            citations.append({
                "index": i,
                "chunk_id": chunk.get("chunk_id", f"chunk_{i}"),
                "source_authority": chunk.get("source_authority", "Unknown"),
                "text_snippet": chunk.get("text", "")[:150],
            })
        return citations

    def _extract_checklist(self, pathway: CarePathway) -> list[str]:
        """Convert immediate_actions into a pre-visit checklist."""
        checklist = []
        for action in pathway.immediate_actions:
            checklist.append(action)
        # Add universal items
        if pathway.care_setting in ("Pediatric ED", "Urgent Care", "Pediatrician"):
            checklist.append("Note down when symptoms started and any changes since then.")
            checklist.append("Bring a list of any medications your child takes.")
            checklist.append("Bring your child's vaccination record if available.")
        return checklist

    def _extract_warning_signs(
        self, pathway: CarePathway, chunks: list[dict]
    ) -> list[str]:
        """Extract warning signs from clinical reasoning or return sensible defaults."""
        warning_signs = [
            "Your child stops breathing or has great difficulty breathing.",
            "Your child's lips or face turn blue.",
            "Your child has a seizure (uncontrolled shaking).",
            "Your child becomes unresponsive or very difficult to wake.",
            "Symptoms worsen significantly or new symptoms appear.",
        ]
        if pathway.urgency_level.value in ("routine", "self_care"):
            warning_signs.append(
                "Fever persists for more than 48 hours despite home treatment."
            )
        return warning_signs

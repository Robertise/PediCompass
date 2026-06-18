"""
Stage 3 — Clinical Reasoning via Bedrock Tool Use.

Uses Claude's function-calling API with CARE_PATHWAY_TOOL to produce a
schema-guaranteed CarePathway. ESI v4 algorithm is encoded in the system
prompt to guide urgency level decisions.

max_tokens = 500.
"""

import logging
from typing import Optional

from agent.models import CarePathway, UrgencyLevel
from common.age_utils import AgeGroup
from guardrails.prompt_constraints import SAFETY_SYSTEM_PROMPT_SNIPPET
from llm.bedrock_client import BedrockClient
from llm.prompts.stage3_prompt import STAGE3_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ── Tool definition ───────────────────────────────────────────────────────────

CARE_PATHWAY_TOOL: dict = {
    "name": "submit_care_pathway",
    "description": (
        "Submit a structured care pathway assessment for the child's symptoms. "
        "Base urgency on ESI v4 criteria provided in the system prompt. "
        "You MUST call this tool with all required fields."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "urgency_level": {
                "type": "string",
                "enum": ["emergency", "urgent", "soon", "routine", "self_care"],
                "description": "ESI v4 urgency level.",
            },
            "care_setting": {
                "type": "string",
                "enum": [
                    "Pediatric ED",
                    "Urgent Care",
                    "Pediatrician",
                    "Home monitoring",
                ],
                "description": "Recommended care setting.",
            },
            "immediate_actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of actions the parent should take.",
            },
            "clinical_reasoning": {
                "type": "string",
                "description": (
                    "Clinical reasoning narrative. Must reference the child's age group "
                    "and the specific ESI criterion applied."
                ),
            },
            "supporting_guidelines": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Guideline source references or chunk IDs used.",
            },
        },
        "required": [
            "urgency_level",
            "care_setting",
            "immediate_actions",
            "clinical_reasoning",
            "supporting_guidelines",
        ],
    },
}


class Stage3Reasoner:
    """
    Stage 3: Produces a structured CarePathway by reasoning over the
    conversation context and retrieved guideline chunks using ESI v4.
    """

    MAX_TOKENS = 500

    def __init__(self, bedrock_client: BedrockClient) -> None:
        self.llm = bedrock_client

    async def reason(
        self,
        context: list[dict],
        chunks: list[dict],
        age_group: AgeGroup,
    ) -> CarePathway:
        """
        Reason over symptoms + retrieved evidence to produce a CarePathway.

        Args:
            context: Conversation history in Bedrock Messages format.
            chunks: Retrieved guideline chunks from Stage 2.
            age_group: Resolved age group for prompt context.

        Returns:
            CarePathway with urgency level, care setting, actions, and reasoning.
        """
        system = self._build_system(chunks, age_group)
        messages = list(context)  # copy to avoid mutation

        tool_input = self.llm.invoke_with_tools(
            system=system,
            messages=messages,
            tools=[CARE_PATHWAY_TOOL],
            max_tokens=self.MAX_TOKENS,
        )

        return self._parse_tool_input(tool_input)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _build_system(self, chunks: list[dict], age_group: AgeGroup) -> str:
        chunks_text = self._format_chunks(chunks)
        return (
            STAGE3_SYSTEM_PROMPT.format(
                age_group=age_group.value,
                retrieved_chunks=chunks_text,
            )
            + "\n\n"
            + SAFETY_SYSTEM_PROMPT_SNIPPET
        )

    def _format_chunks(self, chunks: list[dict]) -> str:
        if not chunks:
            return "No relevant guidelines retrieved."
        lines = []
        for i, chunk in enumerate(chunks, start=1):
            source = chunk.get("source_authority", "Unknown")
            text = chunk.get("text", "")
            chunk_id = chunk.get("chunk_id", f"chunk_{i}")
            lines.append(f"[{i}] SOURCE: {source} (ID: {chunk_id})\n{text}")
        return "\n\n---\n\n".join(lines)

    def _parse_tool_input(self, tool_input: dict) -> CarePathway:
        return CarePathway(
            urgency_level=UrgencyLevel(tool_input["urgency_level"]),
            care_setting=tool_input["care_setting"],
            immediate_actions=tool_input.get("immediate_actions", []),
            clinical_reasoning=tool_input.get("clinical_reasoning", ""),
            supporting_guidelines=tool_input.get("supporting_guidelines", []),
        )

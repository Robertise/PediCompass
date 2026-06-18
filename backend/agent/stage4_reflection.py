"""
Stage 4 — Reflection.

Uses Bedrock tool_use to evaluate whether the CarePathway produced by Stage 3
is complete and sufficient. If not, `is_complete=False` causes the orchestrator
to append the missing_info to context and loop back to Stage 2 for another
retrieval + reasoning pass.

max_tokens = 300.
"""

import logging

from agent.models import CarePathway, ReflectionResult
from common.age_utils import AgeGroup
from guardrails.prompt_constraints import SAFETY_SYSTEM_PROMPT_SNIPPET
from llm.bedrock_client import BedrockClient
from llm.prompts.stage4_prompt import STAGE4_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ── Tool definition ───────────────────────────────────────────────────────────

REFLECTION_TOOL: dict = {
    "name": "submit_reflection",
    "description": (
        "Evaluate whether the care pathway is complete and sufficient for a parent "
        "to take informed action. Return structured reflection with a completeness verdict."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "is_complete": {
                "type": "boolean",
                "description": (
                    "True if the care pathway addresses the child's situation adequately. "
                    "False if critical information is missing or reasoning is insufficient."
                ),
            },
            "missing_info": {
                "type": "string",
                "description": (
                    "Description of what is still needed. Empty string if is_complete=True."
                ),
            },
            "reason": {
                "type": "string",
                "description": "Brief explanation of the reflection decision.",
            },
        },
        "required": ["is_complete", "missing_info", "reason"],
    },
}


class Stage4Reflector:
    """
    Stage 4: Reflects on the CarePathway to determine whether another
    retrieval + reasoning iteration is needed.
    """

    MAX_TOKENS = 300

    def __init__(self, bedrock_client: BedrockClient) -> None:
        self.llm = bedrock_client

    async def reflect(
        self,
        pathway: CarePathway,
        chunks: list[dict],
        age_group: AgeGroup,
    ) -> ReflectionResult:
        """
        Evaluate the CarePathway for completeness.

        Args:
            pathway: The CarePathway produced by Stage 3.
            chunks: The guideline chunks used by Stage 3.
            age_group: Child's age group (for context).

        Returns:
            ReflectionResult with is_complete, missing_info, and reason.
        """
        system = STAGE4_SYSTEM_PROMPT + "\n\n" + SAFETY_SYSTEM_PROMPT_SNIPPET
        messages = [
            {
                "role": "user",
                "content": self._build_user_message(pathway, chunks, age_group),
            }
        ]

        tool_input = self.llm.invoke_with_tools(
            system=system,
            messages=messages,
            tools=[REFLECTION_TOOL],
            max_tokens=self.MAX_TOKENS,
        )

        return ReflectionResult(
            is_complete=tool_input.get("is_complete", True),
            missing_info=tool_input.get("missing_info", ""),
            reason=tool_input.get("reason", ""),
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _build_user_message(
        self,
        pathway: CarePathway,
        chunks: list[dict],
        age_group: AgeGroup,
    ) -> str:
        chunks_summary = f"{len(chunks)} guideline chunks were retrieved."
        return (
            f"CHILD AGE GROUP: {age_group.value}\n\n"
            f"CARE PATHWAY PRODUCED:\n"
            f"  Urgency: {pathway.urgency_level.value}\n"
            f"  Care setting: {pathway.care_setting}\n"
            f"  Clinical reasoning: {pathway.clinical_reasoning}\n"
            f"  Immediate actions: {'; '.join(pathway.immediate_actions)}\n"
            f"  Guidelines cited: {', '.join(pathway.supporting_guidelines) or 'none'}\n\n"
            f"EVIDENCE USED: {chunks_summary}\n\n"
            "Evaluate whether this care pathway is complete and sufficient. "
            "Call submit_reflection with your assessment."
        )

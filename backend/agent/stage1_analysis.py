"""
Stage 1 — Structured Query Analysis via Bedrock Tool Use.

Uses Claude's function-calling (tool_use) API so that the output is
schema-guaranteed. No try/catch JSON decode required — Bedrock enforces
the schema on the model side.

max_tokens = 300 (sufficient for structured tool call, not prose).
"""

import logging
from typing import Optional

from agent.models import ChildProfile, QueryAnalysis
from common.age_utils import AgeGroup, map_age_to_group
from guardrails.prompt_constraints import SAFETY_SYSTEM_PROMPT_SNIPPET
from llm.bedrock_client import BedrockClient
from llm.prompts.stage1_prompt import STAGE1_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ── Tool definition (Anthropic Messages API format) ───────────────────────────

QUERY_ANALYSIS_TOOL: dict = {
    "name": "submit_query_analysis",
    "description": (
        "Submit a structured analysis of the parent's query about their child's symptoms. "
        "You MUST call this tool with all required fields populated."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "child_age_resolved": {
                "type": "boolean",
                "description": "True if the child's age can be determined from the conversation.",
            },
            "child_age_days": {
                "type": "integer",
                "description": "Child's age in days. Set to null if not resolved.",
            },
            "symptom_summary": {
                "type": "string",
                "description": "Concise one-sentence summary of the reported symptoms.",
            },
            "needs_clarification": {
                "type": "boolean",
                "description": (
                    "True if critical information is missing (other than age, which has "
                    "its own field). False if enough information is available to proceed."
                ),
            },
            "clarification_questions": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
                "description": "Questions to ask the parent. Empty list if no clarification needed.",
            },
        },
        "required": [
            "child_age_resolved",
            "symptom_summary",
            "needs_clarification",
            "clarification_questions",
        ],
    },
}


class Stage1Analyzer:
    """
    Stage 1: Uses Bedrock tool_use to extract structured query analysis
    from the conversation context.
    """

    MAX_TOKENS = 300

    def __init__(self, bedrock_client: BedrockClient) -> None:
        self.llm = bedrock_client

    async def analyze(
        self,
        context: list[dict],
        child_profile: Optional[ChildProfile] = None,
    ) -> QueryAnalysis:
        """
        Analyse the conversation to extract age, symptoms, and whether
        clarification is needed.

        Args:
            context: List of {"role": ..., "content": ...} message dicts.
            child_profile: Optional attached child profile (provides DOB).

        Returns:
            QueryAnalysis with structured fields.
        """
        system = self._build_system(child_profile)
        messages = self._build_messages(context)

        tool_input = self.llm.invoke_with_tools(
            system=system,
            messages=messages,
            tools=[QUERY_ANALYSIS_TOOL],
            max_tokens=self.MAX_TOKENS,
        )

        return self._parse_tool_input(tool_input, child_profile)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _build_system(self, child_profile: Optional[ChildProfile]) -> str:
        profile_info = ""
        if child_profile:
            profile_info = (
                f"\nATTACHED CHILD PROFILE:\n"
                f"  Nickname: {child_profile.nickname}\n"
                f"  Date of birth: {child_profile.dob or 'not provided'}\n"
                f"  Known conditions: {', '.join(child_profile.medical_conditions) or 'none'}\n"
            )
        return STAGE1_SYSTEM_PROMPT + profile_info + "\n\n" + SAFETY_SYSTEM_PROMPT_SNIPPET

    def _build_messages(self, context: list[dict]) -> list[dict]:
        """Convert session context dicts to Bedrock Messages API format."""
        messages = []
        for msg in context:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            messages.append({"role": role, "content": content})
        return messages

    def _parse_tool_input(
        self, tool_input: dict, child_profile: Optional[ChildProfile]
    ) -> QueryAnalysis:
        """Map raw tool_use input dict to a QueryAnalysis model."""
        child_age_days: Optional[int] = tool_input.get("child_age_days")
        child_age_resolved: bool = tool_input.get("child_age_resolved", False)

        age_group: Optional[str] = None
        if child_age_days is not None:
            try:
                age_group = map_age_to_group(child_age_days).value
            except Exception:
                age_group = None

        return QueryAnalysis(
            child_age_resolved=child_age_resolved,
            child_age_days=child_age_days,
            age_group=age_group,
            symptom_summary=tool_input.get("symptom_summary", ""),
            needs_clarification=tool_input.get("needs_clarification", False),
            clarification_questions=tool_input.get("clarification_questions", []),
        )

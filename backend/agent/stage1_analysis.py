"""
Stage 1 — Structured Query Analysis via Bedrock Tool Use.

Uses Claude's function-calling (tool_use) API so that the output is
schema-guaranteed. No try/catch JSON decode required — Bedrock enforces
the schema on the model side.

max_tokens = 300 (sufficient for structured tool call, not prose).
"""

import logging
from typing import Optional

from agent.models import ChildProfile, QueryAnalysis, IntentClassification, IntentType
from common.age_utils import AgeGroup, map_age_to_group
from guardrails.prompt_constraints import SAFETY_SYSTEM_PROMPT_SNIPPET
from llm.bedrock_client import BedrockClient
from llm.prompts.stage1_prompt import STAGE1_SYSTEM_PROMPT, INTENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ── Tool definition (Anthropic Messages API format) ───────────────────────────

INTENT_CLASSIFICATION_TOOL: dict = {
    "name": "classify_intent",
    "description": "Classify the parent's message intent.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["triage", "general", "high_stakes_general"],
            },
            "topic_summary": {
                "type": "string",
                "description": "One-sentence summary of the topic being asked about.",
            },
            "high_stakes_reason": {
                "type": "string",
                "description": "Why flagged high-stakes. Empty string if not high_stakes_general.",
            },
        },
        "required": ["intent", "topic_summary", "high_stakes_reason"],
    },
}

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


class IntentDetector:
    MAX_TOKENS = 150  # Structured tool call — minimal output needed

    def __init__(self, bedrock_client: BedrockClient) -> None:
        self.llm = bedrock_client

    async def classify(self, context: list[dict]) -> IntentClassification:
        # Convert context dicts to Bedrock format
        messages = []
        for msg in context:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            
        tool_input = await self.llm.ainvoke_with_tools(
            system=INTENT_SYSTEM_PROMPT,
            messages=messages,
            tools=[INTENT_CLASSIFICATION_TOOL],
            max_tokens=self.MAX_TOKENS,
        )
        return IntentClassification(
            intent=IntentType(tool_input["intent"]),
            topic_summary=tool_input.get("topic_summary", ""),
            high_stakes_reason=tool_input.get("high_stakes_reason", ""),
        )


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

        tool_input = await self.llm.ainvoke_with_tools(
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
        """Map raw tool_use input dict to a QueryAnalysis model.

        Defensively sanitises fields because Claude occasionally returns:
          - The string "null" instead of JSON null for nullable fields.
          - The strings "true"/"false" instead of JSON booleans.
        """
        # ── child_age_days ────────────────────────────────────────────────────
        raw_age = tool_input.get("child_age_days")
        child_age_days: Optional[int] = None
        if raw_age is not None and str(raw_age).strip().lower() not in ("null", "", "none"):
            try:
                child_age_days = int(raw_age)
            except (ValueError, TypeError):
                child_age_days = None

        # ── boolean fields ────────────────────────────────────────────────────
        def _to_bool(val, default: bool = False) -> bool:
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.strip().lower() in ("true", "1", "yes")
            return bool(val) if val is not None else default

        child_age_resolved: bool = _to_bool(tool_input.get("child_age_resolved"), False)
        needs_clarification: bool = _to_bool(tool_input.get("needs_clarification"), False)

        # ── age_group ─────────────────────────────────────────────────────────
        age_group: Optional[str] = None
        if child_age_days is not None:
            try:
                age_group = map_age_to_group(child_age_days).value
            except Exception:
                age_group = None

        # ── clarification_questions ───────────────────────────────────────────
        raw_questions = tool_input.get("clarification_questions")
        clarification_questions: list = (
            raw_questions if isinstance(raw_questions, list) else []
        )

        return QueryAnalysis(
            child_age_resolved=child_age_resolved,
            child_age_days=child_age_days,
            age_group=age_group,
            symptom_summary=tool_input.get("symptom_summary", ""),
            needs_clarification=needs_clarification,
            clarification_questions=clarification_questions,
        )

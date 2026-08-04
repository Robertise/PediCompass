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

from agent.tools.openfda_client import OpenFDAClient

logger = logging.getLogger(__name__)

# ── Tool definitions ───────────────────────────────────────────────────────────

OPENFDA_LOOKUP_TOOL: dict = {
    "name": "lookup_openfda",
    "description": (
        "Look up real-world pediatric adverse event reports for a specific medication "
        "from the FDA Adverse Event Reporting System (FAERS). Call this tool ONLY when "
        "the parent has mentioned giving their child a specific medication or asked about "
        "medication safety. Do NOT call this for general symptom queries."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "drug_name": {
                "type": "string",
                "description": "The medication name (brand or generic, e.g. 'Tylenol', 'acetaminophen', 'ibuprofen').",
            },
        },
        "required": ["drug_name"],
    },
}

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


COMMON_MEDICATIONS: list[str] = [
    "paracetamol", "acetaminophen", "tylenol", "ibuprofen",
    "advil", "motrin", "benadryl", "panadol", "aspirin",
    "amoxicillin", "augmentin", "calpol",
]


class Stage3Reasoner:
    """
    Stage 3: Produces a structured CarePathway by reasoning over the
    conversation context and retrieved guideline chunks using ESI v4.
    Supports agentic OpenFDA tool lookup if medications are mentioned.
    """

    MAX_TOKENS = 600

    def __init__(
        self,
        bedrock_client: BedrockClient,
        openfda_client: Optional[OpenFDAClient] = None,
    ) -> None:
        self.llm = bedrock_client
        self.openfda = openfda_client or OpenFDAClient()

    @staticmethod
    def _extract_text_from_message(msg: dict) -> str:
        """Extract plain text from a Bedrock message regardless of content format.

        Handles:
          - content as str  →  "My child has a fever..."
          - content as list →  [{"type": "text", "text": "..."}, ...]
          - missing content →  ""
        """
        content = msg.get("content")
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            return " ".join(parts)
        return ""

    def _extract_mentioned_medication(self, context: list[dict]) -> Optional[str]:
        """Scan conversation history for known medication names.

        Robust against all Bedrock Messages content formats (str, list of
        content blocks, or None).
        """
        full_text = " ".join(
            self._extract_text_from_message(m) for m in context
        ).lower()
        for med in COMMON_MEDICATIONS:
            if med in full_text:
                return med
        return None

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
            CarePathway with urgency level, care setting, actions, reasoning, and optional medication_safety.
        """
        system = self._build_system(chunks, age_group)
        messages = list(context)  # copy to avoid mutation

        tools = [OPENFDA_LOOKUP_TOOL, CARE_PATHWAY_TOOL]
        executors = {
            "lookup_openfda": self.openfda.lookup_pediatric_adverse_events,
        }

        tool_input, executed_results = await self.llm.ainvoke_with_tools_loop(
            system=system,
            messages=messages,
            tools=tools,
            tool_executors=executors,
            final_tool_name="submit_care_pathway",
            max_tokens=self.MAX_TOKENS,
        )

        medication_safety = executed_results.get("lookup_openfda")
        if not medication_safety:
            detected_med = self._extract_mentioned_medication(context)
            if detected_med:
                logger.info(
                    "Stage 3 fallback: detected medication %r in context, executing OpenFDA lookup",
                    detected_med,
                )
                medication_safety = await self.openfda.lookup_pediatric_adverse_events(detected_med)

        return self._parse_tool_input(tool_input, medication_safety=medication_safety)

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

    def _parse_tool_input(
        self, tool_input: dict, medication_safety: Optional[dict] = None
    ) -> CarePathway:
        return CarePathway(
            urgency_level=UrgencyLevel(tool_input["urgency_level"]),
            care_setting=tool_input["care_setting"],
            immediate_actions=tool_input.get("immediate_actions", []),
            clinical_reasoning=tool_input.get("clinical_reasoning", ""),
            supporting_guidelines=tool_input.get("supporting_guidelines", []),
            medication_safety=medication_safety,
        )


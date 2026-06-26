"""
PediCompass Agent Orchestrator.

Coordinates all 5 stages of the agentic RAG pipeline:

  Stage 0 — Deterministic safety screen (no LLM, <10ms)
  Stage 1 — Structured query analysis (Bedrock tool_use, OUTSIDE loop)
  Loop (max 2 iterations):
    Stage 2 — Retrieve guideline chunks (Qdrant + reranker)
    Stage 3 — Clinical reasoning (Bedrock tool_use, ESI v4)
    Stage 4 — Reflection (Bedrock tool_use, loop termination)
  Stage 5 — Parent-facing prose output (Bedrock invoke_text)
  Layer 3 — Output validation (regex guardrails)

Design decision: Stage 1 is OUTSIDE the loop. Re-analyzing the query on each
iteration adds no value once age and symptoms are established — it just wastes
an extra LLM call. This differs from the original proposal pseudocode, but is
the correct engineering decision (documented in implementation_plan.md).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from agent.models import (
    AgentResponse,
    ChildProfile,
    CarePathway,
    ReasoningTrace,
    UrgencyLevel,
)
from agent.stage0_safety import PediatricEmergencyScreen
from agent.stage1_analysis import Stage1Analyzer
from agent.stage2_retrieval import Stage2Retriever
from agent.stage3_reasoning import Stage3Reasoner
from agent.stage4_reflection import Stage4Reflector
from agent.stage5_output import Stage5OutputGenerator
from common.age_utils import AgeGroup, map_age_to_group
from db.session_store import SessionStore
from db.analytics_store import AnalyticsStore
from guardrails.output_validator import OutputValidator

logger = logging.getLogger(__name__)


class PediCompassAgent:
    """
    Top-level orchestrator for the 5-stage agentic RAG pipeline.
    """

    MAX_ITERATIONS = 2

    def __init__(
        self,
        safety_screen: PediatricEmergencyScreen,
        stage1: Stage1Analyzer,
        stage2: Stage2Retriever,
        stage3: Stage3Reasoner,
        stage4: Stage4Reflector,
        stage5: Stage5OutputGenerator,
        session_store: SessionStore,
        analytics_store: AnalyticsStore,
        output_validator: OutputValidator,
    ) -> None:
        self.safety_screen = safety_screen
        self.stage1 = stage1
        self.stage2 = stage2
        self.stage3 = stage3
        self.stage4 = stage4
        self.stage5 = stage5
        self.session_store = session_store
        self.analytics_store = analytics_store
        self.output_validator = output_validator

    async def run(
        self,
        message: str,
        session_id: str,
        child_profile: Optional[ChildProfile] = None,
        user_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Execute the full agentic pipeline for a single parent message.

        Args:
            message: Raw free-text message from the parent.
            session_id: Existing session ID for conversation history.
            child_profile: Optional attached child profile (provides DOB + history).
            user_id: Authenticated user ID (None for anonymous sessions).

        Returns:
            AgentResponse — either "emergency", "clarification", or "recommendation".
        """
        trace = ReasoningTrace()
        profile_dob = child_profile.dob if child_profile else None

        # ── Stage 0: Deterministic Safety Screen ─────────────────────────────
        red_flag, screened_age_days = self.safety_screen.screen(message, profile_dob)
        trace.stage0 = {
            "checked": True,
            "red_flag_detected": red_flag.detected if red_flag else False,
            "triggered_pattern": red_flag.triggered_pattern if red_flag else None,
            "age_days_resolved": screened_age_days,
        }

        if red_flag and red_flag.detected:
            # age_days is resolved inside screen() — reuse here so analytics on
            # the emergency path records a real age_group, not None.
            emergency_age_group: Optional[AgeGroup] = (
                map_age_to_group(screened_age_days) if screened_age_days is not None else None
            )
            await self.analytics_store.log_query(
                session_id=session_id,
                user_id=user_id,
                urgency_level="emergency",
                age_group=emergency_age_group.value if emergency_age_group else None,
                iterations=0,
            )
            return AgentResponse(
                type="emergency",
                urgency_level=UrgencyLevel.EMERGENCY,
                parent_message=(
                    f"⚠️ **{red_flag.reason}**\n\n"
                    f"{red_flag.immediate_action}\n\n"
                    "Please consult a qualified pediatric healthcare professional "
                    "for proper evaluation."
                ),
                reasoning_trace=trace,
                session_id=session_id,
            )

        # ── Stage 1: Query Analysis (OUTSIDE loop) ────────────────────────────
        session = await self.session_store.get_session(session_id)
        history = [{"role": m.role, "content": m.content} for m in session.messages]
        context = history + [{"role": "user", "content": message}]

        analysis = await self.stage1.analyze(context, child_profile)
        trace.stage1 = analysis.dict()

        # If age unknown, ask for it before anything else
        if not analysis.child_age_resolved:
            return AgentResponse(
                type="clarification",
                clarification_questions=["How old is your child?"],
                parent_message=(
                    "To give you the most appropriate guidance, I need to know your "
                    "child's age. Could you please tell me how old they are?"
                ),
                reasoning_trace=trace,
                session_id=session_id,
            )

        # If other clarification needed
        if analysis.needs_clarification:
            questions = analysis.clarification_questions or [
                "Could you tell me more about the symptoms?"
            ]
            return AgentResponse(
                type="clarification",
                clarification_questions=questions,
                parent_message=(
                    "I have a few questions to better understand your child's situation:\n\n"
                    + "\n".join(f"- {q}" for q in questions)
                ),
                reasoning_trace=trace,
                session_id=session_id,
            )

        child_age_days: int = analysis.child_age_days  # type: ignore[assignment]
        age_group = map_age_to_group(child_age_days)

        # ── Loop: Stage 2 → 3 → 4 (max MAX_ITERATIONS) ───────────────────────
        pathway: Optional[CarePathway] = None
        chunks: list[dict] = []

        for iteration in range(self.MAX_ITERATIONS):
            trace.iterations = iteration + 1
            logger.info("Iteration %d/%d", iteration + 1, self.MAX_ITERATIONS)

            # Stage 2 — Retrieve
            chunks = await self.stage2.retrieve(analysis.symptom_summary, age_group)
            trace.stage2 = {
                "age_group": age_group.value,
                "chunks_retrieved": len(chunks),
                "iteration": iteration + 1,
            }

            # Stage 3 — Reason
            pathway = await self.stage3.reason(context, chunks, age_group)
            trace.stage3 = pathway.dict()

            # Stage 4 — Reflect
            reflection = await self.stage4.reflect(pathway, chunks, age_group)
            trace.stage4 = reflection.dict()

            if reflection.is_complete:
                logger.info("Reflection: complete after iteration %d", iteration + 1)
                break

            logger.info("Reflection: not complete — %s", reflection.missing_info)
            # Append missing info as assistant turn to guide next retrieval
            context.append({
                "role": "assistant",
                "content": f"Additional information needed: {reflection.missing_info}",
            })

        # pathway is guaranteed non-None here (loop runs at least once)
        assert pathway is not None

        # ── Stage 5: Parent-Facing Output ─────────────────────────────────────
        output = await self.stage5.generate(pathway, chunks, trace)

        # ── Layer 3: Output Validation ────────────────────────────────────────
        validation = self.output_validator.validate(output.text)
        if not validation.safe:
            logger.warning(
                "Output validator flagged pattern: %s — using safe fallback",
                validation.flagged_pattern,
            )
            safe_text = self._safe_fallback_text(session_id, validation.flagged_pattern)
        else:
            safe_text = output.text

        # ── Persist & Analytics ───────────────────────────────────────────────
        await self.session_store.append_message(session_id, "user", message)
        await self.session_store.append_message(session_id, "assistant", safe_text)

        await self.analytics_store.log_query(
            session_id=session_id,
            user_id=user_id,
            urgency_level=pathway.urgency_level.value,
            age_group=age_group.value,
            iterations=trace.iterations,
        )

        return AgentResponse(
            type="recommendation",
            urgency_level=pathway.urgency_level,
            care_pathway=pathway,
            parent_message=safe_text,
            pre_visit_checklist=output.pre_visit_checklist,
            warning_signs=output.warning_signs,
            cited_sources=output.cited_sources,
            reasoning_trace=trace,
            session_id=session_id,
        )

    # ── private helpers ───────────────────────────────────────────────────────

    def _safe_fallback_text(self, session_id: str, flagged_pattern: str) -> str:
        """
        Return a safe fallback message when the output validator fires.
        Logs the flagged pattern for review.
        """
        logger.error(
            "Output validator triggered fallback. session_id=%s pattern=%s",
            session_id,
            flagged_pattern,
        )
        return (
            "I'm not able to provide a specific assessment for this situation. "
            "Please consult a qualified pediatric healthcare professional for proper evaluation. "
            "If you are concerned about your child's wellbeing right now, "
            "please contact your local emergency services or go to the nearest "
            "Pediatric Emergency Department."
        )


def create_agent() -> PediCompassAgent:
    """
    Factory function: wire up all dependencies and return a ready-to-use agent.
    Called once at application startup.
    """
    from llm.bedrock_client import BedrockClient
    from rag.retriever import Retriever
    from rag.qdrant_client import get_qdrant_manager
    from rag.reranker import get_reranker
    from db.session_store import SessionStore
    from db.analytics_store import AnalyticsStore
    from db.dynamodb_client import get_dynamodb_client
    from guardrails.output_validator import OutputValidator

    bedrock = BedrockClient()
    qdrant_mgr = get_qdrant_manager()
    reranker = get_reranker()
    db_client = get_dynamodb_client()

    retriever = Retriever(qdrant_manager=qdrant_mgr, reranker=reranker)
    session_store = SessionStore(db_client)
    analytics_store = AnalyticsStore(db_client)
    output_validator = OutputValidator()

    return PediCompassAgent(
        safety_screen=PediatricEmergencyScreen(),
        stage1=Stage1Analyzer(bedrock),
        stage2=Stage2Retriever(retriever),
        stage3=Stage3Reasoner(bedrock),
        stage4=Stage4Reflector(bedrock),
        stage5=Stage5OutputGenerator(bedrock),
        session_store=session_store,
        analytics_store=analytics_store,
        output_validator=output_validator,
    )

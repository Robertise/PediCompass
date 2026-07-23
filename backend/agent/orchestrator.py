"""
Pedix Agent Orchestrator.

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

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from agent.models import (
    AgentResponse,
    ChildProfile,
    CarePathway,
    ReasoningTrace,
    UrgencyLevel,
    IntentType,
    SSEEventType,
    SSEStageEvent,
    StageNames,
)
from agent.stage_content_check import ContentCheck, GREETING_RESPONSE_TEXT
from agent.stage0_safety import PediatricEmergencyScreen
from agent.stage1_analysis import Stage1Analyzer, IntentDetector
from agent.stage_general_rag import GeneralRAGHandler
from agent.stage2_retrieval import Stage2Retriever
from agent.stage3_reasoning import Stage3Reasoner
from agent.stage4_reflection import Stage4Reflector
from agent.stage5_output import Stage5OutputGenerator
from common.age_utils import AgeGroup, map_age_to_group
from db.session_store import SessionStore
from db.analytics_store import AnalyticsStore
from guardrails.output_validator import OutputValidator

logger = logging.getLogger(__name__)


class PedixAgent:
    """
    Top-level orchestrator for the 5-stage agentic RAG pipeline.
    """

    MAX_ITERATIONS = 2

    # Special prefix tokens sent by frontend when user clicks a button.
    # These bypass Content Check and Intent Detection, routing directly to the
    # appropriate path. Tokens are stripped before persisting to session history.
    CONFIRM_GENERAL_PREFIX = "__CONFIRM_GENERAL__"
    CONFIRM_TRIAGE_PREFIX = "__CONFIRM_TRIAGE__"
    GENERAL_INTRO_PREFIX = "__GENERAL_INTRO__"

    # Rich intro response returned when user clicks 'Learn about children's health'.
    # Predefined — no RAG needed, covers what the KB actually contains.
    GENERAL_INTRO_RESPONSE = (
        "I'm here to help with general pediatric health questions! "
        "Here are some topics I can answer:\n\n"
        "- **Fever management** — when to worry, how to treat at home, warning signs\n"
        "- **Respiratory illnesses** — RSV, croup, bronchiolitis, coughs, wheezing\n"
        "- **Ear & throat infections** — recognising symptoms, when to see a doctor\n"
        "- **Stomach bugs & diarrhea** — rehydration, when to seek care\n"
        "- **Skin conditions** — rashes, eczema, jaundice in newborns\n"
        "- **Vaccinations** — recommended schedules, common side effects\n"
        "- **Nutrition & feeding** — breastfeeding, introducing solids, age-appropriate food\n"
        "- **Growth & development** — developmental milestones, red flags\n"
        "- **Medications** — paracetamol and ibuprofen dosing, safety guidelines\n\n"
        "Feel free to ask any specific question and I'll provide evidence-based information "
        "from WHO, CDC, and AAP guidelines."
    )

    def __init__(
        self,
        safety_screen: PediatricEmergencyScreen,
        intent_detector: IntentDetector,
        general_rag_handler: GeneralRAGHandler,
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
        self.intent_detector = intent_detector
        self.general_rag_handler = general_rag_handler
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

        # ── CONFIRMATION TOKEN DETECTION (must be first — before Stage 0) ─────
        # Frontend prefixes confirmation button presses with a special token so
        # the backend can route them without going through Intent Detection again.
        # The clean message (without the token) is what gets persisted to session.

        if message.startswith(self.CONFIRM_GENERAL_PREFIX):
            clean_message = message[len(self.CONFIRM_GENERAL_PREFIX):].strip()
            return await self._handle_confirm_general(
                clean_message=clean_message,
                session_id=session_id,
                user_id=user_id,
                trace=trace,
            )

        if message.startswith(self.CONFIRM_TRIAGE_PREFIX):
            # Strip token and let normal flow handle it
            message = message[len(self.CONFIRM_TRIAGE_PREFIX):].strip()
            # Fall through to Stage 0 below

        if message.startswith(self.GENERAL_INTRO_PREFIX):
            # User clicked 'Learn about children's health' button — return predefined rich intro
            clean_message = message[len(self.GENERAL_INTRO_PREFIX):].strip()
            session = await self.session_store.get_session(session_id)
            await self.session_store.append_message(session_id, "user", clean_message)
            await self.session_store.append_message(session_id, "assistant", self.GENERAL_INTRO_RESPONSE)
            await self.analytics_store.log_query(
                session_id=session_id,
                user_id=user_id,
                urgency_level="n/a",
                age_group=None,
                iterations=0,
                intent_type="general_intro",
            )
            return AgentResponse(
                type="general",
                parent_message=self.GENERAL_INTRO_RESPONSE,
                reasoning_trace=trace,
                session_id=session_id,
            )

        # ── Stage 0: Deterministic Safety Screen ─────────────────────────────
        red_flag, screened_age_days = await self.safety_screen.screen(message, profile_dob)
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
                intent_type="emergency",
                symptoms=message[:500],
            )
            parent_message_str = (
                f"⚠️ **{red_flag.reason}**\n\n"
                f"{red_flag.immediate_action}\n\n"
                "Please consult a qualified pediatric healthcare professional "
                "for proper evaluation."
            )
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", parent_message_str)
            return AgentResponse(
                type="emergency",
                urgency_level=UrgencyLevel.EMERGENCY,
                parent_message=parent_message_str,
                reasoning_trace=trace,
                session_id=session_id,
            )

        # ── CONTENT CHECK ─────────────────────────────────────────────────────────────
        # Load history before content check (needed to determine multi-turn vs first msg)
        session = await self.session_store.get_session(session_id)
        history = [{"role": m.role, "content": m.content} for m in session.messages]
        context = history + [{"role": "user", "content": message}]

        content_check = ContentCheck.check(message=message, history=history)
        trace.content_check = {"passed": content_check.should_pass, "reason": content_check.reason}

        if not content_check.should_pass:
            greeting_msg = GREETING_RESPONSE_TEXT
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", greeting_msg)
            await self.analytics_store.log_query(
                session_id=session_id,
                user_id=user_id,
                urgency_level="n/a",
                age_group=None,
                iterations=0,
                intent_type="greeting",
            )
            return AgentResponse(
                type="greeting",
                parent_message=greeting_msg,
                reasoning_trace=trace,
                session_id=session_id,
            )

        # ── INTENT DETECTION ──────────────────────────────────────────────────────────
        intent = await self.intent_detector.classify(context)
        trace.intent = intent.model_dump()

        if intent.intent == IntentType.HIGH_STAKES_GENERAL:
            confirmation_msg = (
                f"I want to make sure I give you the right information. "
                f"Are you asking about {intent.topic_summary} to learn in general, "
                f"or is your child currently experiencing this?"
            )
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", confirmation_msg)
            await self.analytics_store.log_query(
                session_id=session_id,
                user_id=user_id,
                urgency_level="n/a",
                age_group=None,
                iterations=0,
                intent_type="confirmation",
            )
            return AgentResponse(
                type="confirmation",
                parent_message=confirmation_msg,
                confirmation_options=[
                    "My child is experiencing this right now",
                    "I'm asking to learn in general",
                ],
                reasoning_trace=trace,
                session_id=session_id,
            )

        if intent.intent == IntentType.GENERAL:
            general_result = await self.general_rag_handler.handle(
                topic_summary=intent.topic_summary,
                context=context,
            )
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", general_result.text)
            await self.analytics_store.log_query(
                session_id=session_id,
                user_id=user_id,
                urgency_level="n/a",
                age_group=None,
                iterations=0,
                intent_type="general",
            )
            return AgentResponse(
                type="general",
                parent_message=general_result.text,
                cited_sources=general_result.cited_sources,
                reasoning_trace=trace,
                session_id=session_id,
            )

        # ── TRIAGE PATH — Stage 1 analyze runs HERE, unchanged ───────────────────────
        # IMPORTANT: stage1.analyze() MUST be called here, not before intent detection.
        # IntentDetector and Stage1Analyzer are separate classes — no shared state.
        analysis = await self.stage1.analyze(context, child_profile)
        trace.stage1 = analysis.model_dump()

        # If age unknown, ask for it before anything else
        if not analysis.child_age_resolved:
            parent_message_str = (
                "To give you the most appropriate guidance, I need to know your "
                "child's age. Could you please tell me how old they are?"
            )
            age_options = analysis.clarification_options or [
                "2 months old", "6 months old", "2 years old", "4 years old"
            ]
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", parent_message_str)
            return AgentResponse(
                type="clarification",
                clarification_questions=["How old is your child?"],
                clarification_options=age_options,
                parent_message=parent_message_str,
                reasoning_trace=trace,
                session_id=session_id,
            )

        # If other clarification needed
        if analysis.needs_clarification:
            questions = analysis.clarification_questions or [
                "Could you tell me more about the symptoms?"
            ]
            # Fallback symptom choices in English if LLM returns empty clarification options
            options = analysis.clarification_options if (analysis.clarification_options and len(analysis.clarification_options) > 0) else [
                "Fever", "Cough & Cold", "Vomiting / Diarrhea", "Skin Rash"
            ]
            parent_message_str = (
                "I have a few questions to better understand your child's situation:\n\n"
                + "\n".join(f"- {q}" for q in questions)
            )
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", parent_message_str)
            return AgentResponse(
                type="clarification",
                clarification_questions=questions,
                clarification_options=options,
                parent_message=parent_message_str,
                reasoning_trace=trace,
                session_id=session_id,
            )



        child_age_days: int = analysis.child_age_days  # type: ignore[assignment]
        age_group = map_age_to_group(child_age_days)

        # ── Loop: Stage 2 → 3 → 4 (max MAX_ITERATIONS) ───────────────────────
        pathway: Optional[CarePathway] = None
        chunks: list[dict] = []
        enriched_query = analysis.symptom_summary

        for iteration in range(self.MAX_ITERATIONS):
            trace.iterations = iteration + 1
            logger.info("Iteration %d/%d", iteration + 1, self.MAX_ITERATIONS)

            # Stage 2 — Retrieve
            chunks = await self.stage2.retrieve(enriched_query, age_group)
            trace.stage2 = {
                "age_group": age_group.value,
                "chunks_retrieved": len(chunks),
                "iteration": iteration + 1,
            }

            # Stage 3 — Reason
            pathway = await self.stage3.reason(context, chunks, age_group)
            trace.stage3 = pathway.model_dump()
            if pathway.medication_safety:
                trace.openfda_lookup = pathway.medication_safety

            # Stage 4 — Reflect
            reflection = await self.stage4.reflect(pathway, chunks, age_group)
            trace.stage4 = reflection.model_dump()

            if reflection.is_complete:
                logger.info("Reflection: complete after iteration %d", iteration + 1)
                break

            logger.info("Reflection: not complete — %s", reflection.missing_info)
            # Append missing info as assistant turn to guide next retrieval
            context.append({
                "role": "assistant",
                "content": f"Additional information needed: {reflection.missing_info}".strip(),
            })
            enriched_query = f"{analysis.symptom_summary}. Additional context: {reflection.missing_info}"

        if pathway is None:
            raise RuntimeError("Agent loop completed without producing a care pathway.")

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
            symptoms=analysis.symptom_summary,
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

    async def _call_with_heartbeat(
        self,
        coro,
        heartbeat_interval: float = 15.0,
    ):
        """
        Run an async coroutine, yielding HEARTBEAT SSE events every
        `heartbeat_interval` seconds until the coroutine completes.

        AWS ALB has a default idle connection timeout of 60 seconds.
        Bedrock calls (especially Stage 3 and Stage 5) can take 30–60s.
        Without heartbeats, ALB drops the SSE connection mid-stream.

        Usage (inside run_streaming):
            result = None
            async for hb_or_result in self._call_with_heartbeat(some_async_fn(args)):
                if isinstance(hb_or_result, SSEStageEvent):
                    yield hb_or_result   # forward heartbeat to caller
                else:
                    result = hb_or_result  # final coroutine return value
        """
        task = asyncio.create_task(coro)
        while not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=heartbeat_interval)
            except asyncio.TimeoutError:
                if not task.done():
                    yield SSEStageEvent(event=SSEEventType.HEARTBEAT)
        yield await task

    async def run_streaming(
        self,
        message: str,
        session_id: str,
        child_profile: Optional[ChildProfile] = None,
        user_id: Optional[str] = None,
    ):
        """
        Streaming version of run(). Yields SSEStageEvent at each stage boundary.
        run() is NOT modified — tests continue to use run() unchanged.

        Session messages (user + assistant) are persisted to DynamoDB at the end,
        same as run(). Analytics logging is also performed.
        """
        trace = ReasoningTrace()
        profile_dob = child_profile.dob if child_profile else None
        start_time = time.monotonic()

        # ── Confirmation token detection (same as run()) ──────────────────────────
        if message.startswith(self.CONFIRM_GENERAL_PREFIX):
            clean_message = message[len(self.CONFIRM_GENERAL_PREFIX):].strip()
            result = await self._handle_confirm_general(clean_message, session_id, user_id, trace)
            yield SSEStageEvent(event=SSEEventType.FINAL_RESPONSE, data=result.model_dump())
            yield SSEStageEvent(event=SSEEventType.DONE)
            return

        if message.startswith(self.CONFIRM_TRIAGE_PREFIX):
            message = message[len(self.CONFIRM_TRIAGE_PREFIX):].strip()

        if message.startswith(self.GENERAL_INTRO_PREFIX):
            clean_message = message[len(self.GENERAL_INTRO_PREFIX):].strip()
            await self.session_store.append_message(session_id, "user", clean_message)
            await self.session_store.append_message(session_id, "assistant", self.GENERAL_INTRO_RESPONSE)
            await self.analytics_store.log_query(session_id=session_id, user_id=user_id,
                urgency_level="n/a", age_group=None, iterations=0, intent_type="general_intro")
            result = AgentResponse(type="general", parent_message=self.GENERAL_INTRO_RESPONSE,
                                   reasoning_trace=trace, session_id=session_id)
            yield SSEStageEvent(event=SSEEventType.FINAL_RESPONSE, data=result.model_dump())
            yield SSEStageEvent(event=SSEEventType.DONE)
            return

        # ── Stage 0: Safety Screen ────────────────────────────────────────────────
        yield SSEStageEvent(event=SSEEventType.STAGE_UPDATE, stage=StageNames.SAFETY_SCREEN,
                            status="running", message="Running safety screen...")
        t0 = time.monotonic()

        # Use _call_with_heartbeat for the Haiku context check sub-call within screen()
        # (Stage 0 itself is fast, but if Haiku is invoked it may take a few seconds)
        red_flag, screened_age_days = await self.safety_screen.screen(message, profile_dob)
        latency_ms = int((time.monotonic() - t0) * 1000)

        trace.stage0 = {
            "checked": True,
            "red_flag_detected": bool(red_flag and red_flag.detected),
            "triggered_pattern": red_flag.triggered_pattern if red_flag else None,
            "age_days_resolved": screened_age_days,
        }
        yield SSEStageEvent(
            event=SSEEventType.STAGE_UPDATE, stage=StageNames.SAFETY_SCREEN, status="done",
            data=trace.stage0, latency_ms=latency_ms,
            message="Safety screen passed" if not (red_flag and red_flag.detected)
                    else f"Red flag: {red_flag.triggered_pattern}",
        )

        if red_flag and red_flag.detected:
            emergency_age_group = map_age_to_group(screened_age_days) if screened_age_days else None
            parent_msg = (f"⚠️ **{red_flag.reason}**\n\n{red_flag.immediate_action}\n\n"
                          "Please consult a qualified pediatric healthcare professional.")
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", parent_msg)
            await self.analytics_store.log_query(session_id=session_id, user_id=user_id,
                urgency_level="emergency", age_group=emergency_age_group.value if emergency_age_group else None,
                iterations=0, intent_type="emergency", symptoms=message[:500])
            result = AgentResponse(type="emergency", urgency_level=UrgencyLevel.EMERGENCY,
                                   parent_message=parent_msg, reasoning_trace=trace, session_id=session_id)
            yield SSEStageEvent(event=SSEEventType.FINAL_RESPONSE, data=result.model_dump())
            yield SSEStageEvent(event=SSEEventType.DONE)
            return

        # ── Content Check ─────────────────────────────────────────────────────────
        yield SSEStageEvent(event=SSEEventType.STAGE_UPDATE, stage=StageNames.CONTENT_CHECK,
                            status="running", message="Checking input...")
        t0 = time.monotonic()
        session = await self.session_store.get_session(session_id)
        history = [{"role": m.role, "content": m.content} for m in session.messages]
        context = history + [{"role": "user", "content": message}]
        content_check = ContentCheck.check(message=message, history=history)
        trace.content_check = {"passed": content_check.should_pass, "reason": content_check.reason}
        latency_ms = int((time.monotonic() - t0) * 1000)

        yield SSEStageEvent(
            event=SSEEventType.STAGE_UPDATE, stage=StageNames.CONTENT_CHECK, status="done",
            data=trace.content_check, latency_ms=latency_ms,
            message="Input accepted" if content_check.should_pass else f"Blocked: {content_check.reason}",
        )

        if not content_check.should_pass:
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", GREETING_RESPONSE_TEXT)
            await self.analytics_store.log_query(session_id=session_id, user_id=user_id,
                urgency_level="n/a", age_group=None, iterations=0, intent_type="greeting")
            result = AgentResponse(type="greeting", parent_message=GREETING_RESPONSE_TEXT,
                                   reasoning_trace=trace, session_id=session_id)
            yield SSEStageEvent(event=SSEEventType.FINAL_RESPONSE, data=result.model_dump())
            yield SSEStageEvent(event=SSEEventType.DONE)
            return

        # ── Intent Detection ──────────────────────────────────────────────────────
        yield SSEStageEvent(event=SSEEventType.STAGE_UPDATE, stage=StageNames.INTENT,
                            status="running", message="Classifying intent...")
        t0 = time.monotonic()
        # Heartbeat wrapper: Intent Detection calls Bedrock (Sonnet, ~1–3s)
        intent = None
        async for hb_or_result in self._call_with_heartbeat(self.intent_detector.classify(context)):
            if isinstance(hb_or_result, SSEStageEvent):
                yield hb_or_result   # forward heartbeat
            else:
                intent = hb_or_result
        trace.intent = intent.model_dump()
        latency_ms = int((time.monotonic() - t0) * 1000)
        yield SSEStageEvent(
            event=SSEEventType.STAGE_UPDATE, stage=StageNames.INTENT, status="done",
            data=trace.intent, latency_ms=latency_ms,
            message=f"Intent: {intent.intent.value}",
        )

        if intent.intent == IntentType.HIGH_STAKES_GENERAL:
            confirmation_msg = (
                f"I want to make sure I give you the right information. "
                f"Are you asking about {intent.topic_summary} to learn in general, "
                f"or is your child currently experiencing this?"
            )
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", confirmation_msg)
            await self.analytics_store.log_query(session_id=session_id, user_id=user_id,
                urgency_level="n/a", age_group=None, iterations=0, intent_type="confirmation")
            result = AgentResponse(type="confirmation", parent_message=confirmation_msg,
                                   confirmation_options=["My child is experiencing this right now", "I'm asking to learn in general"],
                                   reasoning_trace=trace, session_id=session_id)
            yield SSEStageEvent(event=SSEEventType.FINAL_RESPONSE, data=result.model_dump())
            yield SSEStageEvent(event=SSEEventType.DONE)
            return

        if intent.intent == IntentType.GENERAL:
            general_result = None
            async for hb_or_result in self._call_with_heartbeat(self.general_rag_handler.handle(topic_summary=intent.topic_summary, context=context)):
                if isinstance(hb_or_result, SSEStageEvent):
                    yield hb_or_result
                else:
                    general_result = hb_or_result
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", general_result.text)
            await self.analytics_store.log_query(session_id=session_id, user_id=user_id,
                urgency_level="n/a", age_group=None, iterations=0, intent_type="general")
            result = AgentResponse(type="general", parent_message=general_result.text,
                                   cited_sources=general_result.cited_sources,
                                   reasoning_trace=trace, session_id=session_id)
            yield SSEStageEvent(event=SSEEventType.FINAL_RESPONSE, data=result.model_dump())
            yield SSEStageEvent(event=SSEEventType.DONE)
            return

        # ── Stage 1: Query Analysis ───────────────────────────────────────────────
        yield SSEStageEvent(event=SSEEventType.STAGE_UPDATE, stage=StageNames.AGE_DETECTION,
                            status="running", message="Analyzing age and symptoms...")
        t0 = time.monotonic()
        analysis = None
        async for hb_or_result in self._call_with_heartbeat(self.stage1.analyze(context, child_profile)):
            if isinstance(hb_or_result, SSEStageEvent):
                yield hb_or_result
            else:
                analysis = hb_or_result
        trace.stage1 = analysis.model_dump()
        latency_ms = int((time.monotonic() - t0) * 1000)
        age_summary = (f"{analysis.age_group} · {analysis.child_age_days} days"
                       if analysis.child_age_resolved else "Age not resolved")
        yield SSEStageEvent(
            event=SSEEventType.STAGE_UPDATE, stage=StageNames.AGE_DETECTION, status="done",
            data=trace.stage1, latency_ms=latency_ms,
            message=f"Child identified: {age_summary}" if analysis.child_age_resolved
                    else "Age needed — asking parent",
        )

        if not analysis.child_age_resolved:
            parent_message_str = "To give you the most appropriate guidance, I need to know your child's age. Could you please tell me how old they are?"
            age_options = analysis.clarification_options or [
                "2 months old", "6 months old", "2 years old", "4 years old"
            ]
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", parent_message_str)
            result = AgentResponse(type="clarification", clarification_questions=["How old is your child?"],
                                   clarification_options=age_options,
                                   parent_message=parent_message_str, reasoning_trace=trace, session_id=session_id)
            yield SSEStageEvent(event=SSEEventType.FINAL_RESPONSE, data=result.model_dump())
            yield SSEStageEvent(event=SSEEventType.DONE)
            return

        if analysis.needs_clarification:
            questions = analysis.clarification_questions or ["Could you tell me more about the symptoms?"]
            # Fallback symptom choices in English if LLM returns empty clarification options
            options = analysis.clarification_options if (analysis.clarification_options and len(analysis.clarification_options) > 0) else [
                "Fever", "Cough & Cold", "Vomiting / Diarrhea", "Skin Rash"
            ]
            parent_message_str = "I have a few questions to better understand your child's situation:\n\n" + "\n".join(f"- {q}" for q in questions)
            await self.session_store.append_message(session_id, "user", message)
            await self.session_store.append_message(session_id, "assistant", parent_message_str)
            result = AgentResponse(type="clarification", clarification_questions=questions,
                                   clarification_options=options,
                                   parent_message=parent_message_str, reasoning_trace=trace, session_id=session_id)
            yield SSEStageEvent(event=SSEEventType.FINAL_RESPONSE, data=result.model_dump())
            yield SSEStageEvent(event=SSEEventType.DONE)
            return



        child_age_days = analysis.child_age_days
        age_group = map_age_to_group(child_age_days)
        pathway = None
        chunks = []
        enriched_query = analysis.symptom_summary

        # ── Loop: Stage 2 → 3 → 4 ────────────────────────────────────────────────
        for iteration in range(self.MAX_ITERATIONS):
            trace.iterations = iteration + 1

            # Stage 2 — Retrieval
            yield SSEStageEvent(
                event=SSEEventType.STAGE_UPDATE, stage=StageNames.RETRIEVAL, status="running",
                data={"age_group": age_group.value, "query_hint": enriched_query[:60]},
                message=f"Retrieving clinical guidelines...",
            )
            t0 = time.monotonic()
            chunks = await self.stage2.retrieve(enriched_query, age_group)
            latency_ms = int((time.monotonic() - t0) * 1000)
            trace.stage2 = {"age_group": age_group.value, "chunks_retrieved": len(chunks), "iteration": iteration + 1}
            sources = list({c.get("source_authority", "Unknown") for c in chunks})
            yield SSEStageEvent(
                event=SSEEventType.STAGE_UPDATE, stage=StageNames.RETRIEVAL, status="done",
                data=trace.stage2, latency_ms=latency_ms,
                message=f"Retrieved {len(chunks)} chunks · {', '.join(sources)}",
            )

            # Stage 3 — Pathway Reasoning (longest LLM call — heartbeat essential)
            yield SSEStageEvent(event=SSEEventType.STAGE_UPDATE, stage=StageNames.PATHWAY,
                                status="running", message="Reasoning care pathway...")
            t0 = time.monotonic()
            pathway = None
            async for hb_or_result in self._call_with_heartbeat(
                self.stage3.reason(context, chunks, age_group)
            ):
                if isinstance(hb_or_result, SSEStageEvent):
                    yield hb_or_result
                else:
                    pathway = hb_or_result
            latency_ms = int((time.monotonic() - t0) * 1000)
            trace.stage3 = pathway.model_dump()
            if pathway.medication_safety:
                trace.openfda_lookup = pathway.medication_safety
                yield SSEStageEvent(
                    event=SSEEventType.STAGE_UPDATE, stage=StageNames.OPENFDA_LOOKUP, status="done",
                    data=trace.openfda_lookup, latency_ms=0,
                    message=f"OpenFDA lookup: {pathway.medication_safety.get('drug_name', 'medication')}",
                )

            yield SSEStageEvent(
                event=SSEEventType.STAGE_UPDATE, stage=StageNames.PATHWAY, status="done",
                data=trace.stage3, latency_ms=latency_ms,
                message=f"{pathway.urgency_level.value.upper()} · {pathway.care_setting}",
            )

            # Stage 4 — Reflection
            yield SSEStageEvent(event=SSEEventType.STAGE_UPDATE, stage=StageNames.REFLECTION,
                                status="running", message="Checking completeness...")
            t0 = time.monotonic()
            reflection = None
            async for hb_or_result in self._call_with_heartbeat(
                self.stage4.reflect(pathway, chunks, age_group)
            ):
                if isinstance(hb_or_result, SSEStageEvent):
                    yield hb_or_result
                else:
                    reflection = hb_or_result
            latency_ms = int((time.monotonic() - t0) * 1000)
            trace.stage4 = reflection.model_dump()
            yield SSEStageEvent(
                event=SSEEventType.STAGE_UPDATE, stage=StageNames.REFLECTION, status="done",
                data=trace.stage4, latency_ms=latency_ms,
                message="Complete · No gaps found" if reflection.is_complete
                        else f"Incomplete: {reflection.missing_info[:60]}",
            )

            if reflection.is_complete:
                break
            context.append({"role": "assistant",
                             "content": f"Additional info needed: {reflection.missing_info}"})
            enriched_query = f"{analysis.symptom_summary}. {reflection.missing_info}"

        # ── Stage 5: Output Generation ────────────────────────────────────────────
        yield SSEStageEvent(event=SSEEventType.STAGE_UPDATE, stage=StageNames.OUTPUT,
                            status="running", message="Generating response...")
        t0 = time.monotonic()
        output = None
        async for hb_or_result in self._call_with_heartbeat(self.stage5.generate(pathway, chunks, trace)):
            if isinstance(hb_or_result, SSEStageEvent):
                yield hb_or_result
            else:
                output = hb_or_result
        latency_ms = int((time.monotonic() - t0) * 1000)
        total_ms = int((time.monotonic() - start_time) * 1000)
        yield SSEStageEvent(
            event=SSEEventType.STAGE_UPDATE, stage=StageNames.OUTPUT, status="done",
            latency_ms=latency_ms,
            message=f"Response generated · {total_ms / 1000:.1f}s total",
        )

        # ── Output Validation ─────────────────────────────────────────────────────
        validation = self.output_validator.validate(output.text)
        safe_text = output.text if validation.safe else self._safe_fallback_text(session_id, validation.flagged_pattern)

        # ── Session Persistence (IMPORTANT: must happen before FINAL_RESPONSE) ────
        # Both user message and assistant response are persisted here.
        # If this is skipped, chat history will be missing the current turn.
        await self.session_store.append_message(session_id, "user", message)
        await self.session_store.append_message(session_id, "assistant", safe_text)
        await self.analytics_store.log_query(
            session_id=session_id, user_id=user_id,
            urgency_level=pathway.urgency_level.value,
            age_group=age_group.value, iterations=trace.iterations,
            symptoms=analysis.symptom_summary
        )

        final_response = AgentResponse(
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
        yield SSEStageEvent(event=SSEEventType.FINAL_RESPONSE, data=final_response.model_dump())
        yield SSEStageEvent(event=SSEEventType.DONE)

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

    def _extract_topic_from_confirmation(
        self, history: list[dict], fallback: str
    ) -> str:
        """
        Extract the topic the user originally asked about by scanning backwards
        through session history for the last assistant confirmation message.

        A confirmation message has the pattern:
            "Are you asking about <TOPIC> to learn in general..."

        Returns the extracted topic, or `fallback` if extraction fails.
        """
        import re as _re
        for msg in reversed(history):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            # Match the standard phrasing produced by the orchestrator
            match = _re.search(
                r"Are you asking about (.+?) to learn in general",
                content,
                _re.IGNORECASE,
            )
            if match:
                topic = match.group(1).strip()
                logger.info("Extracted confirmation topic from history: %r", topic)
                return topic
        logger.warning(
            "Could not extract topic from confirmation history — using fallback: %r",
            fallback,
        )
        return fallback

    async def _handle_confirm_general(
        self,
        clean_message: str,
        session_id: str,
        user_id: Optional[str],
        trace: "ReasoningTrace",
    ) -> AgentResponse:
        """
        Handle the CONFIRM_GENERAL confirmation path.

        The user clicked 'I'm asking to learn in general'. We:
          1. Load session history.
          2. Extract the original topic from the previous confirmation message.
          3. Call GeneralRAGHandler with that topic.
          4. Persist clean_message (no token) to session and log analytics.
        """
        session = await self.session_store.get_session(session_id)
        history = [{"role": m.role, "content": m.content} for m in session.messages]

        topic_summary = self._extract_topic_from_confirmation(
            history=history,
            fallback=clean_message,
        )
        context = history + [{"role": "user", "content": clean_message}]

        general_result = await self.general_rag_handler.handle(
            topic_summary=topic_summary,
            context=context,
        )

        await self.session_store.append_message(session_id, "user", clean_message)
        await self.session_store.append_message(session_id, "assistant", general_result.text)
        await self.analytics_store.log_query(
            session_id=session_id,
            user_id=user_id,
            urgency_level="n/a",
            age_group=None,
            iterations=0,
            intent_type="general",
        )
        return AgentResponse(
            type="general",
            parent_message=general_result.text,
            cited_sources=general_result.cited_sources,
            reasoning_trace=trace,
            session_id=session_id,
        )


def create_agent() -> PedixAgent:
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
    from agent.tools.openfda_client import OpenFDAClient

    bedrock = BedrockClient()
    qdrant_mgr = get_qdrant_manager()
    reranker = get_reranker()
    db_client = get_dynamodb_client()
    openfda_client = OpenFDAClient()

    retriever = Retriever(qdrant_manager=qdrant_mgr, reranker=reranker)
    session_store = SessionStore(db_client=db_client)
    analytics_store = AnalyticsStore(db_client=db_client)
    output_validator = OutputValidator()

    return PedixAgent(
        safety_screen=PediatricEmergencyScreen(bedrock_client=bedrock),
        intent_detector=IntentDetector(bedrock),
        general_rag_handler=GeneralRAGHandler(retriever=retriever, bedrock_client=bedrock),
        stage1=Stage1Analyzer(bedrock),
        stage2=Stage2Retriever(retriever),
        stage3=Stage3Reasoner(bedrock, openfda_client),
        stage4=Stage4Reflector(bedrock),
        stage5=Stage5OutputGenerator(bedrock),
        session_store=session_store,
        analytics_store=analytics_store,
        output_validator=output_validator,
    )

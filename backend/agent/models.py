"""
Pydantic models shared across all agent stages.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class UrgencyLevel(str, Enum):
    EMERGENCY = "emergency"
    URGENT = "urgent"
    SOON = "soon"
    ROUTINE = "routine"
    SELF_CARE = "self_care"


# ── Stage 0 ───────────────────────────────────────────────────────────────────

class RedFlag(BaseModel):
    """A deterministic safety flag raised by Stage 0 before any LLM call."""

    detected: bool = Field(..., description="Whether a red flag was detected")
    reason: str = Field(..., description="Human-readable reason for the flag")
    immediate_action: str = Field(..., description="Recommended immediate action for the parent")
    triggered_pattern: str = Field(..., description="Internal name of the flag pattern that triggered")


# ── Intent Detection ──────────────────────────────────────────────────────────

class IntentType(str, Enum):
    TRIAGE = "triage"
    GENERAL = "general"
    HIGH_STAKES_GENERAL = "high_stakes_general"


class IntentClassification(BaseModel):
    """Output of Intent Detection step."""

    intent: IntentType
    topic_summary: str = Field(..., description="One-sentence summary of what user is asking")
    high_stakes_reason: str = Field(default="", description="Why flagged high-stakes. Empty if not.")


# ── Stage 1 ───────────────────────────────────────────────────────────────────

class QueryAnalysis(BaseModel):
    """Output of Stage 1 — structured query analysis returned by Bedrock tool use."""

    child_age_resolved: bool = Field(..., description="True if the child's age was determined")
    child_age_days: Optional[int] = Field(None, description="Resolved age in days, or None")
    age_group: Optional[str] = Field(None, description="AgeGroup enum value string, or None")
    symptom_summary: str = Field(..., description="Concise summary of reported symptoms")
    needs_clarification: bool = Field(..., description="True if more information is needed")
    clarification_questions: list[str] = Field(
        default_factory=list,
        description="Questions to ask the parent (max 3)",
    )


# ── Stage 3 ───────────────────────────────────────────────────────────────────

class CarePathway(BaseModel):
    """Structured care pathway assessment produced by Stage 3 reasoning."""

    urgency_level: UrgencyLevel
    care_setting: str = Field(
        ...,
        description="One of: Pediatric ED | Urgent Care | Pediatrician | Home monitoring",
    )
    immediate_actions: list[str] = Field(..., description="Ordered list of immediate actions")
    clinical_reasoning: str = Field(..., description="Clinical reasoning narrative")
    supporting_guidelines: list[str] = Field(
        ..., description="Source chunk IDs or guideline references used"
    )


# ── Stage 4 ───────────────────────────────────────────────────────────────────

class ReflectionResult(BaseModel):
    """Structured output from Stage 4 reflection."""

    is_complete: bool = Field(
        ...,
        description="True if the care pathway is complete and sufficient for the parent",
    )
    missing_info: str = Field(
        default="",
        description="Description of what information is still needed, if not complete",
    )
    reason: str = Field(..., description="Brief explanation of the reflection decision")


# ── Stage 5 / Final ───────────────────────────────────────────────────────────

class ReasoningTrace(BaseModel):
    """Debug/transparency trace of all stages in a single agent run."""

    stage0: Optional[dict[str, Any]] = None
    content_check: Optional[dict[str, Any]] = None
    intent: Optional[dict[str, Any]] = None
    stage1: Optional[dict[str, Any]] = None
    stage2: Optional[dict[str, Any]] = None
    stage3: Optional[dict[str, Any]] = None
    stage4: Optional[dict[str, Any]] = None
    iterations: int = 0


class AgentResponse(BaseModel):
    """Final response returned by the orchestrator to the API layer."""

    type: Literal["emergency", "clarification", "recommendation", "greeting", "general", "confirmation"]
    urgency_level: Optional[UrgencyLevel] = None
    care_pathway: Optional[CarePathway] = None
    clarification_questions: Optional[list[str]] = None
    parent_message: str = Field(
        ..., description="Parent-facing prose response from Stage 5"
    )
    pre_visit_checklist: Optional[list[str]] = None
    warning_signs: Optional[list[str]] = None
    cited_sources: Optional[list[dict[str, Any]]] = None
    confirmation_options: Optional[list[str]] = None
    reasoning_trace: ReasoningTrace
    session_id: str


# ── Child Profile ─────────────────────────────────────────────────────────────

class ChildProfile(BaseModel):
    """Minimal child profile data passed into the agent."""

    profile_id: str
    nickname: str
    dob: Optional[str] = Field(None, description="Date of birth as ISO string YYYY-MM-DD")
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    medical_conditions: list[str] = Field(default_factory=list)


# ── Session ───────────────────────────────────────────────────────────────────

class SessionMessage(BaseModel):
    """A single turn in the conversation history."""

    role: Literal["user", "assistant"]
    content: str


class Session(BaseModel):
    """Represents an in-progress chat session."""

    session_id: str
    user_id: Optional[str] = None
    messages: list[SessionMessage] = Field(default_factory=list)
    child_age_days: Optional[int] = None
    created_at: str
    ttl: int  # Unix timestamp for DynamoDB TTL


# ── SSE Stage Names (single source of truth) ─────────────────────────────────
# Frontend STAGE_ORDER must use exactly these string values.
# Changing any value here requires a matching change in MessageBubble.jsx STAGE_ORDER.

class StageNames:
    SAFETY_SCREEN = "stage0"
    CONTENT_CHECK = "content_check"
    INTENT        = "intent"
    AGE_DETECTION = "stage1"
    RETRIEVAL     = "stage2"
    PATHWAY       = "stage3"
    REFLECTION    = "stage4"
    OUTPUT        = "stage5"


# ── SSE Event Models ──────────────────────────────────────────────────────────

class SSEEventType(str, Enum):
    STAGE_UPDATE   = "stage_update"
    HEARTBEAT      = "heartbeat"     # No-op event to keep ALB connection alive
    FINAL_RESPONSE = "final_response"
    ERROR          = "error"
    DONE           = "done"


class SSEStageEvent(BaseModel):
    """One SSE event pushed to frontend at each stage boundary."""
    event:      SSEEventType
    stage:      Optional[str] = None   # StageNames constant value
    status:     str = "done"           # "running" | "done" | "skipped"
    data:       Optional[dict] = None  # Stage trace payload
    latency_ms: Optional[int] = None   # Wall-clock time for this stage
    message:    Optional[str] = None   # Human-readable UI summary

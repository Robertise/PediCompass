"""
Chat API routes.

POST /api/chat/session     — Create a new session (auth optional)
POST /api/chat/message     — Send a message and receive an AgentResponse
GET  /api/chat/history/{sid} — Retrieve messages for an existing session
"""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.middleware.auth_middleware import get_optional_user
from agent.orchestrator import create_agent
from db.session_store import SessionStore
from db.profile_store import ProfileStore
from db.dynamodb_client import get_dynamodb_client

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Singletons — instantiated once at module load ─────────────────────────────
# create_agent() wires up all dependencies (Bedrock, Qdrant, reranker, etc.)
agent = create_agent()
_db = get_dynamodb_client()
session_store = SessionStore(db_client=_db)
profile_store = ProfileStore(db_client=_db)


# ── Request models ────────────────────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    profile_id: Optional[str] = None


class MessageRequest(BaseModel):
    session_id: str
    message: str
    profile_id: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/session")
async def create_session(
    req: SessionCreateRequest,
    user: Optional[dict] = Depends(get_optional_user),
):
    """Create a new chat session. Auth is optional (anonymous sessions allowed)."""
    user_id = user["user_id"] if user else None
    session_id = str(uuid.uuid4())
    await session_store.create_session(session_id=session_id, user_id=user_id)
    return {"session_id": session_id}


@router.post("/message")
async def send_message(
    req: MessageRequest,
    user: Optional[dict] = Depends(get_optional_user),
):
    """Send a parent message through the full agentic pipeline."""
    user_id = user["user_id"] if user else None

    # Verify session ownership if session already exists
    existing_session = await session_store.get_session(req.session_id)
    if existing_session and existing_session.user_id and existing_session.user_id != "anonymous":
        if not user:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Cannot send messages to a session owned by another user",
            )
        is_admin = user.get("isAdmin") is True
        if user.get("user_id") != existing_session.user_id and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Cannot send messages to a session owned by another user",
            )

    # Retrieve profile if caller supplied a profile_id and is authenticated
    profile = None
    if user_id and req.profile_id:
        profile = await profile_store.get_profile(user_id, req.profile_id)
        if profile is None:
            logger.warning(
                "Profile %s not found for user %s — proceeding without profile.",
                req.profile_id, user_id,
            )

    try:
        response = await agent.run(
            message=req.message,
            session_id=req.session_id,
            child_profile=profile,
            user_id=user_id,
        )
        return response.model_dump()
    except RuntimeError as exc:
        # Bedrock / pipeline error — return structured error so frontend renders
        # the red error card instead of a generic network failure.
        logger.error("Agent pipeline failed: %s", exc, exc_info=True)
        return {
            "type": "error",
            "reason": str(exc),
            "session_id": req.session_id,
            "reasoning_trace": {},
            "parent_message": str(exc),
        }
    except Exception as exc:
        logger.exception("Unexpected agent error: %s", exc)
        return {
            "type": "error",
            "reason": "An unexpected error occurred. Please try again.",
            "session_id": req.session_id,
            "reasoning_trace": {},
            "parent_message": "An unexpected error occurred. Please try again.",
        }


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    user: Optional[dict] = Depends(get_optional_user),
):
    """Retrieve conversation history for a session with ownership verification."""
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Enforce session ownership authorization check for non-anonymous sessions
    if session.user_id and session.user_id != "anonymous":
        if not user:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You do not own this chat session",
            )
        is_admin = user.get("isAdmin") is True
        if user.get("user_id") != session.user_id and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You do not own this chat session",
            )

    return {"messages": [m.model_dump() for m in session.messages]}


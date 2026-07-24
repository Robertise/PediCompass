"""
SSE streaming chat routes.

POST /api/chat/register  — Register a pending message, receive request_id
GET  /api/chat/stream    — Open SSE stream for a registered request_id

Two-step pattern rationale:
  EventSource (native browser API) only supports GET requests.
  Putting the full parent message in a GET query param risks hitting the
  ~2000–8000 char URL length limit across browsers and servers.
  Solution: POST the message body first, get back a short UUID, stream by UUID.

Token security note:
  JWT token is passed as a query param (?token=xxx) because EventSource does
  not support custom Authorization headers. This causes the token to appear in
  server access logs and browser history. Acceptable for this project's scope.
  Cookie-based auth (httpOnly Cognito cookie) would be a cleaner alternative
  but requires additional Cognito configuration.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.models import SSEStageEvent, SSEEventType
from agent.orchestrator import create_agent
from agent.pending_requests import pending_requests
from api.middleware.auth_middleware import get_optional_user, get_optional_user_from_query_token
from db.dynamodb_client import get_dynamodb_client
from db.profile_store import ProfileStore

router = APIRouter()
logger = logging.getLogger(__name__)

_agent = create_agent()
_db = get_dynamodb_client()
_profile_store = ProfileStore(db_client=_db)


# ── Request / Response models ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    session_id: str
    message:    str
    profile_id: Optional[str] = None


class RegisterResponse(BaseModel):
    request_id: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse)
async def register_message(
    req: RegisterRequest,
    user: Optional[dict] = Depends(get_optional_user),
):
    """
    Register a pending chat message. Returns a short-lived request_id UUID.
    The client must open an EventSource to /api/chat/stream?request_id=...
    within 60 seconds, otherwise the registration expires.
    """
    user_id = user["user_id"] if user else None
    is_admin = user.get("isAdmin") is True if user else False

    # Check if session exists in DB and verify ownership
    from db.session_store import SessionStore
    from db.dynamodb_client import get_dynamodb_client
    session_store = SessionStore(db_client=get_dynamodb_client())
    existing_session = await session_store.get_session(req.session_id)

    if existing_session and existing_session.user_id and existing_session.user_id != "anonymous":
        if not user:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="Access denied: Cannot register messages for a session owned by another user",
            )
        if user_id != existing_session.user_id and not is_admin:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="Access denied: Cannot register messages for a session owned by another user",
            )

    request_id = await pending_requests.register(
        session_id=req.session_id,
        message=req.message,
        profile_id=req.profile_id,
        user_id=user_id,
    )
    return RegisterResponse(request_id=request_id)



async def _sse_generator(agent, pending_req, child_profile):
    """Wrap run_streaming() into SSE wire format: 'data: <json>\n\n'."""
    try:
        async for sse_event in agent.run_streaming(
            message=pending_req.message,
            session_id=pending_req.session_id,
            child_profile=child_profile,
            user_id=pending_req.user_id,
        ):
            yield f"data: {sse_event.model_dump_json()}\n\n"
    except Exception as exc:
        logger.exception("run_streaming failed: %s", exc)
        error_event = SSEStageEvent(event=SSEEventType.ERROR, message=str(exc))
        yield f"data: {error_event.model_dump_json()}\n\n"


@router.get("/stream")
async def stream_message(
    request_id: str = Query(...),
    token: Optional[str] = Query(None),
    # NOTE: No `user` Depends here. user_id comes from pending_req.user_id (set at register time).
    # get_optional_user_from_query_token is intentionally NOT used as a route dependency —
    # it would trigger a redundant token verification since auth was already handled at POST /register.
    # The `token` query param is kept for documentation purposes (shows it exists in URL) but
    # is not used directly in the route body.
):
    """
    Open an SSE stream for a previously registered request_id.
    Consumes (one-time use) the pending request from PendingRequestStore.
    """
    pending_req = await pending_requests.consume(request_id)
    if pending_req is None:
        # request_id expired or never registered
        async def expired_gen():
            error = SSEStageEvent(event=SSEEventType.ERROR,
                                   message="Request ID expired or not found.")
            yield f"data: {error.model_dump_json()}\n\n"
        return StreamingResponse(expired_gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # Load profile if applicable (user_id already resolved at register time)
    child_profile = None
    if pending_req.user_id and pending_req.profile_id:
        child_profile = await _profile_store.get_profile(pending_req.user_id, pending_req.profile_id)

    return StreamingResponse(
        _sse_generator(_agent, pending_req, child_profile),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",    # Disable nginx/ALB proxy buffering
            "Connection": "keep-alive",
        },
    )

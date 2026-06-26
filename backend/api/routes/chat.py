import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any

from ..middleware.auth_middleware import get_optional_user
from agent.orchestrator import create_agent
from db.session_store import SessionStore
from db.profile_store import ProfileStore
from db.dynamodb_client import dynamodb_manager

router = APIRouter()
agent = create_agent()
session_store = SessionStore(dynamodb_manager)
profile_store = ProfileStore(dynamodb_manager)
logger = logging.getLogger(__name__)

class SessionCreateRequest(BaseModel):
    profile_id: Optional[str] = None

class MessageRequest(BaseModel):
    session_id: str
    message: str
    profile_id: Optional[str] = None

@router.post("/session")
async def create_session(req: SessionCreateRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_id = user["user_id"] if user else None
    import uuid
    session_id = str(uuid.uuid4())
    await session_store.create_session(session_id=session_id, user_id=user_id)
    return {"session_id": session_id}

@router.post("/message")
async def send_message(req: MessageRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_id = user["user_id"] if user else None
    
    # Retrieve profile if provided
    profile = None
    if user_id and req.profile_id:
        profile = await profile_store.get_profile(user_id, req.profile_id)

    try:
        response = await agent.run(req.message, req.session_id, profile)
    except RuntimeError as exc:
        message = str(exc)
        logger.exception(
            "Chat agent runtime error. session_id=%s profile_id=%s user_id=%s",
            req.session_id,
            req.profile_id,
            user_id,
        )
        if "on-demand throughput isn" in message or "on-demand throughput isn't" in message:
            raise HTTPException(
                status_code=503,
                detail=(
                    "AWS Bedrock rejected the current model ID. "
                    "This model requires an inference profile ID or ARN, "
                    "not a base model ID."
                ),
            ) from exc
        raise HTTPException(
            status_code=500,
            detail=message,
        ) from exc
    except Exception as exc:
        message = f"{exc.__class__.__name__}: {exc}"
        logger.exception(
            "Chat request failed. session_id=%s profile_id=%s user_id=%s",
            req.session_id,
            req.profile_id,
            user_id,
        )
        raise HTTPException(status_code=500, detail=message) from exc
    return response.model_dump()

@router.get("/history/{session_id}")
async def get_history(session_id: str, user: Optional[dict] = Depends(get_optional_user)):
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # if user and session.user_id != user["user_id"]: # authorization check would go here
    return {"messages": session.messages}

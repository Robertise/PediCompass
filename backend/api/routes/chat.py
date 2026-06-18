from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any

from ..middleware.auth_middleware import get_optional_user
from ...agent.orchestrator import PediCompassAgent
from ...db.session_store import SessionStore
from ...db.profile_store import ProfileStore
from ...db.dynamodb_client import dynamodb_manager

router = APIRouter()
agent = PediCompassAgent()
session_store = SessionStore(dynamodb_manager)
profile_store = ProfileStore(dynamodb_manager)

class SessionCreateRequest(BaseModel):
    profile_id: Optional[str] = None

class MessageRequest(BaseModel):
    session_id: str
    message: str
    profile_id: Optional[str] = None

@router.post("/session")
async def create_session(req: SessionCreateRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_id = user["user_id"] if user else None
    session_id = await session_store.create_session(user_id=user_id)
    return {"session_id": session_id}

@router.post("/message")
async def send_message(req: MessageRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_id = user["user_id"] if user else None
    
    # Retrieve profile if provided
    profile = None
    if user_id and req.profile_id:
        profile = profile_store.get_profile(user_id, req.profile_id)

    response = await agent.run(req.message, req.session_id, profile)
    return response.model_dump()

@router.get("/history/{session_id}")
async def get_history(session_id: str, user: Optional[dict] = Depends(get_optional_user)):
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # if user and session.user_id != user["user_id"]: # authorization check would go here
    return {"messages": session.messages}

"""
Profiles API routes.

GET    /api/profiles              — List all child profiles for the current user
POST   /api/profiles              — Create a new child profile
PUT    /api/profiles/{profile_id} — Update an existing child profile
DELETE /api/profiles/{profile_id} — Delete a child profile
"""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from api.middleware.auth_middleware import get_current_user
from agent.models import ChildProfile
from db.profile_store import ProfileStore
from db.dynamodb_client import get_dynamodb_client

router = APIRouter()
logger = logging.getLogger(__name__)

_db = get_dynamodb_client()
profile_store = ProfileStore(db_client=_db)


# ── Request model ─────────────────────────────────────────────────────────────

class ProfileCreate(BaseModel):
    nickname: str
    dob: str                              # ISO date string YYYY-MM-DD
    gender: str = "Unknown"
    weight_kg: float = 0.0
    medical_conditions: List[str] = []


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_profiles(user: dict = Depends(get_current_user)):
    """List all child profiles for the authenticated user."""
    user_id = user["user_id"]
    profiles = await profile_store.list_profiles(user_id)
    return [p.model_dump() for p in profiles]


@router.post("", status_code=201)
async def create_profile(
    body: ProfileCreate,
    user: dict = Depends(get_current_user),
):
    """Create a new child profile."""
    user_id = user["user_id"]
    profile = ChildProfile(
        profile_id=str(uuid.uuid4()),
        nickname=body.nickname,
        dob=body.dob,
        gender=body.gender,
        weight_kg=body.weight_kg if body.weight_kg > 0 else None,
        medical_conditions=body.medical_conditions,
    )
    saved = await profile_store.create_profile(user_id, profile)
    return {"profile_id": saved.profile_id, "message": "Profile created"}


@router.put("/{profile_id}")
async def update_profile(
    profile_id: str,
    body: ProfileCreate,
    user: dict = Depends(get_current_user),
):
    """Update an existing child profile."""
    user_id = user["user_id"]

    # Verify the profile exists before updating
    existing = await profile_store.get_profile(user_id, profile_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    updated = ChildProfile(
        profile_id=profile_id,
        nickname=body.nickname,
        dob=body.dob,
        gender=body.gender,
        weight_kg=body.weight_kg if body.weight_kg > 0 else None,
        medical_conditions=body.medical_conditions,
    )
    await profile_store.update_profile(user_id, updated)
    return {"message": "Profile updated"}


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a child profile."""
    user_id = user["user_id"]
    deleted = await profile_store.delete_profile(user_id, profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile deleted"}

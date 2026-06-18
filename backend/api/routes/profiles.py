from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

from ..middleware.auth_middleware import get_current_user
from ...db.profile_store import ProfileStore
from ...db.dynamodb_client import dynamodb_manager

router = APIRouter()
profile_store = ProfileStore(dynamodb_manager)

class ProfileCreate(BaseModel):
    nickname: str
    dob: str
    gender: str = "Unknown"
    weight_kg: float = 0.0
    medical_conditions: List[str] = []

@router.get("")
def list_profiles(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    return profile_store.list_profiles(user_id)

@router.post("")
def create_profile(profile: ProfileCreate, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    profile_id = profile_store.create_profile(user_id, profile.model_dump())
    return {"profile_id": profile_id, "message": "Profile created"}

@router.put("/{profile_id}")
def update_profile(profile_id: str, profile: ProfileCreate, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    # Simplistic update by overwriting
    profile_store.create_profile(user_id, profile.model_dump(), profile_id=profile_id)
    return {"message": "Profile updated"}

@router.delete("/{profile_id}")
def delete_profile(profile_id: str, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    profile_store.delete_profile(user_id, profile_id)
    return {"message": "Profile deleted"}

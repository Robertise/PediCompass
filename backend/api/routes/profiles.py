from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import uuid

from ..middleware.auth_middleware import get_current_user
from db.profile_store import ProfileStore
from db.dynamodb_client import dynamodb_manager
from agent.models import ChildProfile

router = APIRouter()
profile_store = ProfileStore(dynamodb_manager)

class ProfileCreate(BaseModel):
    nickname: str
    dob: str
    gender: str = "Unknown"
    weight_kg: float = 0.0
    medical_conditions: List[str] = []

@router.get("")
async def list_profiles(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    return await profile_store.list_profiles(user_id)

@router.post("")
async def create_profile(profile: ProfileCreate, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    profile_id = str(uuid.uuid4())
    child_profile = ChildProfile(
        profile_id=profile_id,
        nickname=profile.nickname,
        dob=profile.dob,
        gender=profile.gender,
        weight_kg=profile.weight_kg,
        medical_conditions=profile.medical_conditions
    )
    await profile_store.create_profile(user_id, child_profile)
    return {"profile_id": profile_id, "message": "Profile created"}

@router.put("/{profile_id}")
async def update_profile(profile_id: str, profile: ProfileCreate, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    child_profile = ChildProfile(
        profile_id=profile_id,
        nickname=profile.nickname,
        dob=profile.dob,
        gender=profile.gender,
        weight_kg=profile.weight_kg,
        medical_conditions=profile.medical_conditions
    )
    res = await profile_store.update_profile(user_id, child_profile)
    if not res:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile updated"}

@router.delete("/{profile_id}")
async def delete_profile(profile_id: str, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    success = await profile_store.delete_profile(user_id, profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile deleted"}

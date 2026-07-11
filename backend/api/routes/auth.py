from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from jose import jwt

from api.middleware.auth_middleware import cognito_client, get_current_user

router = APIRouter()

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/register")
async def register(req: AuthRequest):
    result = cognito_client.sign_up(req.email, req.password)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return {"message": "Registration successful. Please verify your email.", "user_id": result.get("user_sub")}

@router.post("/login")
async def login(req: AuthRequest):
    result = cognito_client.sign_in(req.email, req.password)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "Invalid credentials"))
    
    # Also attach user info
    id_token = result.get("id_token")
    decoded = jwt.get_unverified_claims(id_token) if id_token else {}
    groups = decoded.get("cognito:groups", [])
    
    user_info = {
        "email": req.email, 
        "user_id": decoded.get("sub"),
        "isAdmin": "pedicompass-admins" in groups
    }
    return {
        "id_token": id_token,
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "user": user_info
    }

@router.post("/logout")
async def logout(req: AuthRequest = None):
    # Keep simple for now, but client will drop tokens
    return {"message": "Logged out successfully"}

@router.post("/refresh")
async def refresh(req: RefreshRequest):
    result = cognito_client.refresh_token(req.refresh_token)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error"))
    return {
        "id_token": result.get("id_token"),
        "access_token": result.get("access_token")
    }

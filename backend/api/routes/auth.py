from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ..middleware.auth_middleware import cognito_client, get_current_user

router = APIRouter()

class AuthRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/register")
async def register(req: AuthRequest):
    result = cognito_client.sign_up(req.email, req.password)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return {"message": "Registration successful. Please verify your email."}

@router.post("/login")
async def login(req: AuthRequest):
    result = cognito_client.sign_in(req.email, req.password)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "Invalid credentials"))
    
    # Also attach user info
    user_info = {"email": req.email, "isAdmin": False}
    return {
        "id_token": result.get("id_token"),
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "user": user_info
    }

@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    # Cognito logout is usually handled client-side by dropping tokens
    # Or by calling global_sign_out, but we'll keep it simple
    return {"message": "Logged out successfully"}

@router.post("/refresh")
async def refresh(req: RefreshRequest):
    # In a real app, use initiate_auth with REFRESH_TOKEN_AUTH
    return {"message": "Not implemented"}

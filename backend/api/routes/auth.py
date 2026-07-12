"""
Auth API routes.

POST /api/auth/register      — Sign up with email + password
POST /api/auth/verify        — Confirm email with 6-digit code
POST /api/auth/resend-code   — Re-send verification code
POST /api/auth/login         — Sign in, returns JWT tokens
POST /api/auth/logout        — Client-side logout (clears tokens)
POST /api/auth/refresh       — Refresh id_token using refresh_token
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from api.middleware.auth_middleware import cognito_client

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Friendly error messages (never expose raw AWS strings) ───────────────────

_REGISTER_ERRORS = {
    "USER_EXISTS":      "An account with this email already exists. Please sign in instead.",
    "INVALID_PASSWORD": "Password does not meet requirements. Please check the rules below.",
    "UNKNOWN":          "Registration failed. Please try again later.",
}

_VERIFY_ERRORS = {
    "CODE_MISMATCH": "Incorrect verification code. Please check your email and try again.",
    "CODE_EXPIRED":  "This code has expired. Please request a new one.",
    "USER_NOT_FOUND": "Account not found. Please register first.",
    "UNKNOWN":        "Verification failed. Please try again.",
}

_RESEND_ERRORS = {
    "USER_NOT_FOUND": "No account found with this email address.",
    "RATE_LIMIT":     "Too many attempts. Please wait a moment before requesting a new code.",
    "UNKNOWN":        "Could not resend the code. Please try again later.",
}

_LOGIN_ERRORS = {
    "EMAIL_NOT_CONFIRMED": "Your email is not verified yet. Please enter the verification code sent to your inbox.",
    "INVALID_CREDENTIALS": "Incorrect email or password.",
    "USER_NOT_FOUND":      "No account found with this email address.",
    "UNKNOWN":             "Login failed. Please try again.",
}


# ── Request models ────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

class VerifyRequest(BaseModel):
    email: EmailStr
    code: str

class ResendRequest(BaseModel):
    email: EmailStr

class RefreshRequest(BaseModel):
    refresh_token: str


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(req: AuthRequest):
    """Register a new account. Cognito will send a 6-digit verification email."""
    result = cognito_client.sign_up(req.email, req.password)
    if not result.get("success"):
        error_key = result.get("error", "UNKNOWN")
        msg = _REGISTER_ERRORS.get(error_key, _REGISTER_ERRORS["UNKNOWN"])
        logger.warning("Register failed for %s: %s", req.email, error_key)
        raise HTTPException(status_code=400, detail=msg)
    return {
        "message": "Registration successful. Please check your email for the verification code.",
        "user_id": result.get("user_sub"),
    }


@router.post("/verify")
async def verify_email(req: VerifyRequest):
    """Confirm the email verification code sent by Cognito."""
    result = cognito_client.confirm_sign_up(req.email, req.code)
    if not result.get("success"):
        error_key = result.get("error", "UNKNOWN")
        msg = _VERIFY_ERRORS.get(error_key, _VERIFY_ERRORS["UNKNOWN"])
        logger.warning("Verify failed for %s: %s", req.email, error_key)
        raise HTTPException(status_code=400, detail=msg)
    return {"message": "Email verified successfully. You can now sign in."}


@router.post("/resend-code")
async def resend_code(req: ResendRequest):
    """Re-send the verification code to the given email."""
    result = cognito_client.resend_confirmation_code(req.email)
    if not result.get("success"):
        error_key = result.get("error", "UNKNOWN")
        msg = _RESEND_ERRORS.get(error_key, _RESEND_ERRORS["UNKNOWN"])
        logger.warning("Resend code failed for %s: %s", req.email, error_key)
        raise HTTPException(status_code=400, detail=msg)
    return {"message": "A new verification code has been sent to your email."}


@router.post("/login")
async def login(req: AuthRequest):
    """Sign in and return Cognito JWT tokens."""
    from jose import jwt as jose_jwt

    result = cognito_client.sign_in(req.email, req.password)
    if not result.get("success"):
        error_key = result.get("error", "UNKNOWN")
        msg = _LOGIN_ERRORS.get(error_key, _LOGIN_ERRORS["UNKNOWN"])
        logger.warning("Login failed for %s: %s", req.email, error_key)
        # Use 403 for unverified email so frontend can distinguish from wrong password
        status = 403 if error_key == "EMAIL_NOT_CONFIRMED" else 401
        raise HTTPException(status_code=status, detail={"message": msg, "error_code": error_key})

    id_token = result.get("id_token")
    decoded = jose_jwt.get_unverified_claims(id_token) if id_token else {}
    groups = decoded.get("cognito:groups", [])

    user_info = {
        "email": req.email,
        "user_id": decoded.get("sub"),
        "isAdmin": "pedicompass-admins" in groups,
    }
    return {
        "id_token": id_token,
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "user": user_info,
    }


@router.post("/logout")
async def logout():
    """Client-side logout — the client is responsible for dropping tokens."""
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    """Refresh the id_token using a valid refresh_token."""
    result = cognito_client.refresh_token(req.refresh_token)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return {
        "id_token": result.get("id_token"),
        "access_token": result.get("access_token"),
    }

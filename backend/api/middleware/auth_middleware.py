from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from auth.cognito_client import CognitoClient

security = HTTPBearer(auto_error=False)
cognito_client = CognitoClient()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = credentials.credentials
    claims = await cognito_client.verify_token(token)
    
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    groups = claims.get("cognito:groups", [])
    is_admin = "pedix-admins" in groups

    return {
        "user_id": claims.get('sub'),
        "email": claims.get('email', ''),
        "groups": groups,
        "isAdmin": is_admin
    }

async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    if "pedix-admins" not in current_user.get("groups", []):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def get_optional_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Optional[dict]:
    if not credentials:
        return None
        
    token = credentials.credentials
    claims = await cognito_client.verify_token(token)
    
    if not claims:
        return None
        
    groups = claims.get("cognito:groups", [])
    is_admin = "pedix-admins" in groups

    return {
        "user_id": claims.get('sub'),
        "email": claims.get('email', ''),
        "groups": groups,
        "isAdmin": is_admin
    }

async def get_optional_user_from_query_token(
    token: Optional[str] = None,
) -> Optional[dict]:
    """Read JWT from query param — used by SSE endpoint (EventSource limitation)."""
    if not token:
        return None
    try:
        claims = await cognito_client.verify_token(token)
        if not claims:
            return None
        groups = claims.get("cognito:groups", [])
        is_admin = "pedix-admins" in groups
        return {
            "user_id": claims.get('sub'),
            "email": claims.get('email', ''),
            "groups": groups,
            "isAdmin": is_admin
        }
    except Exception:
        return None

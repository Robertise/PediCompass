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
    claims = cognito_client.verify_token(token)
    
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    return {
        "user_id": claims.get('sub'),
        "email": claims.get('email', ''),
        # In a real app, you might map claims to roles
        "isAdmin": False
    }

async def get_optional_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Optional[dict]:
    if not credentials:
        return None
        
    token = credentials.credentials
    claims = cognito_client.verify_token(token)
    
    if not claims:
        return None
        
    return {
        "user_id": claims.get('sub'),
        "email": claims.get('email', ''),
        "isAdmin": False
    }

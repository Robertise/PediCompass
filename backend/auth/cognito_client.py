import boto3
import httpx
from jose import jwt, jwk
from jose.utils import base64url_decode
from typing import Dict, Any, Optional

from ..config import settings

class CognitoClient:
    def __init__(self):
        self.client = boto3.client('cognito-idp', region_name=settings.cognito_region)
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self.region = settings.cognito_region
        self.jwks: Optional[Dict[str, Any]] = None

    def sign_up(self, email: str, password: str) -> dict:
        try:
            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=email,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email}
                ]
            )
            return {"success": True, "user_sub": response['UserSub']}
        except self.client.exceptions.UsernameExistsException:
            return {"success": False, "error": "User already exists"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sign_in(self, email: str, password: str) -> dict:
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            auth_result = response.get('AuthenticationResult', {})
            return {
                "success": True,
                "id_token": auth_result.get('IdToken'),
                "access_token": auth_result.get('AccessToken'),
                "refresh_token": auth_result.get('RefreshToken')
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_jwks(self) -> Dict[str, Any]:
        if not self.jwks:
            url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
            response = httpx.get(url)
            self.jwks = response.json()
        return self.jwks

    def verify_token(self, token: str) -> Optional[dict]:
        try:
            headers = jwt.get_unverified_headers(token)
            kid = headers.get('kid')
            
            jwks = self._get_jwks()
            key = next((k for k in jwks.get('keys', []) if k.get('kid') == kid), None)
            
            if not key:
                return None
                
            public_key = jwk.construct(key)
            message, encoded_signature = str(token).rsplit('.', 1)
            decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
            
            if not public_key.verify(message.encode('utf-8'), decoded_signature):
                return None
                
            claims = jwt.get_unverified_claims(token)
            
            # Verify expiration
            import time
            if time.time() > claims.get('exp', 0):
                return None
                
            # Verify audience
            if claims.get('aud') != self.client_id:
                # access tokens might have client_id
                if claims.get('client_id') != self.client_id:
                    return None
                    
            return claims
            
        except Exception as e:
            print(f"Token verification failed: {e}")
            return None

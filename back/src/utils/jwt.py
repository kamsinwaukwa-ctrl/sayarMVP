"""
JWT utilities for authentication and authorization
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
from jwt import InvalidTokenError
from pydantic import BaseModel, EmailStr
from uuid import UUID

# Environment variables
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

class JWTPayload(BaseModel):
    """JWT payload model"""
    sub: str  # user_id
    email: EmailStr
    merchant_id: str
    role: str
    iat: int
    exp: int

class JWTError(Exception):
    """JWT related errors"""
    pass

def create_access_token(
    data: Dict[str, Any],
    expires_minutes: Optional[int] = None
) -> str:
    """
    Create JWT access token with claims
    
    Args:
        data: Dictionary of claims to include in token
        expires_minutes: Token expiration in minutes
        
    Returns:
        JWT token string
    """
    if expires_minutes is None:
        expires_minutes = JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    
    payload = {
        **data,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_jwt(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dictionary
        
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require": ["sub", "email", "merchant_id", "role", "exp", "iat"]
            }
        )
        
        # Validate required fields
        required_fields = ["sub", "email", "merchant_id", "role"]
        for field in required_fields:
            if field not in payload:
                raise JWTError(f"Missing required field: {field}")
                
        # Validate role
        if payload["role"] not in ["admin", "staff"]:
            raise JWTError(f"Invalid role: {payload['role']}")
            
        return payload
        
    except jwt.ExpiredSignatureError:
        raise JWTError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise JWTError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise JWTError(f"Token validation failed: {str(e)}")

def extract_claims(payload: Dict[str, Any]) -> JWTPayload:
    """
    Extract and validate JWT claims into Pydantic model
    
    Args:
        payload: Decoded JWT payload
        
    Returns:
        JWTPayload model instance
    """
    try:
        return JWTPayload(**payload)
    except Exception as e:
        raise JWTError(f"Invalid JWT claims: {str(e)}")

def get_token_from_header(authorization: str) -> str:
    """
    Extract token from Authorization header
    
    Args:
        authorization: Authorization header value
        
    Returns:
        JWT token string
        
    Raises:
        JWTError: If header format is invalid
    """
    if not authorization:
        raise JWTError("Authorization header missing")
        
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise JWTError("Invalid authorization header format")
        
    return parts[1]
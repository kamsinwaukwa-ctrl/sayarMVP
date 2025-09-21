"""
FastAPI authentication dependencies with RLS bridge
"""

import json
from typing import Annotated
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database.connection import get_db
from ..models.auth import CurrentPrincipal, UserRole
from ..utils.jwt import decode_jwt, JWTError, get_token_from_header
from ..services.auth_service import AuthService

# Security scheme for OpenAPI docs
security = HTTPBearer(scheme_name="Bearer")


class AuthenticationError(HTTPException):
    """Authentication error"""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Authorization error"""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def apply_rls_claims(session: AsyncSession, claims: dict) -> None:
    """
    Apply JWT claims to PostgreSQL session for RLS policies

    Args:
        session: SQLAlchemy async session
        claims: JWT payload claims
    """
    try:
        claims_json = json.dumps(claims)
        await session.execute(
            text("SELECT set_config('request.jwt.claims', :claims, true)"),
            {"claims": claims_json},
        )
    except Exception as e:
        raise AuthenticationError(f"Failed to apply RLS claims: {str(e)}")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentPrincipal:
    """
    Get current authenticated user and apply RLS claims

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        CurrentPrincipal with user information

    Raises:
        AuthenticationError: If authentication fails (401)
    """
    try:
        if not credentials or not credentials.credentials:
            raise AuthenticationError("Authentication required")

        # Decode JWT token
        payload = decode_jwt(credentials.credentials)

        # Apply RLS claims to database session
        await apply_rls_claims(db, payload)

        # Get user information
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(payload["sub"])

        if not user:
            raise AuthenticationError("Invalid token")

        return user

    except JWTError as e:
        raise AuthenticationError("Invalid or expired token")
    except AuthenticationError:
        # Re-raise authentication errors as-is (these become 401)
        raise
    except Exception as e:
        # Catch all other exceptions and convert to 401
        raise AuthenticationError("Authentication failed")


async def get_current_admin(
    current_user: Annotated[CurrentPrincipal, Depends(get_current_user)]
) -> CurrentPrincipal:
    """
    Require admin role

    Args:
        current_user: Current authenticated user

    Returns:
        CurrentPrincipal if user is admin

    Raises:
        AuthorizationError: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise AuthorizationError("Admin access required")
    return current_user


async def get_optional_user(
    authorization: str = Header(None),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> CurrentPrincipal | None:
    """
    Get current user optionally (for endpoints that work with or without auth)

    Args:
        authorization: Authorization header
        db: Database session

    Returns:
        CurrentPrincipal or None if not authenticated
    """
    if not authorization:
        return None

    try:
        token = get_token_from_header(authorization)
        payload = decode_jwt(token)

        # Apply RLS claims to database session
        await apply_rls_claims(db, payload)

        # Get user information
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(payload["sub"])

        return user

    except (JWTError, Exception):
        # Return None for optional authentication
        return None


def require_merchant_access(
    current_user: Annotated[CurrentPrincipal, Depends(get_current_user)]
):
    """
    Dependency to ensure user has merchant access
    This is automatically handled by RLS policies, but can be used for explicit checks

    Args:
        current_user: Current authenticated user

    Returns:
        CurrentPrincipal
    """
    # RLS policies will automatically filter by merchant_id
    # This dependency can be used where explicit merchant validation is needed
    return current_user


# Type aliases for easier use
CurrentUser = Annotated[CurrentPrincipal, Depends(get_current_user)]
CurrentAdmin = Annotated[CurrentPrincipal, Depends(get_current_admin)]
OptionalUser = Annotated[CurrentPrincipal | None, Depends(get_optional_user)]
MerchantUser = Annotated[CurrentPrincipal, Depends(require_merchant_access)]

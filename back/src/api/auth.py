"""
Authentication API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.responses import JSONResponse
from typing import Optional, Annotated
from uuid import UUID
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.auth import (
    RegisterRequest,
    LoginRequest,
    RegisterResponse,
    AuthResponse,
    UserResponse,
)
from ..models.api import ApiResponse, ApiErrorResponse
from ..database.connection import get_db
from ..services.auth_service import AuthService, AuthError
from ..dependencies.auth import get_current_user, CurrentUser
from ..middleware.rate_limit import (
    check_login_rate_limit,
    check_email_rate_limit,
    record_login_attempt,
    get_rate_limit_headers,
)
from sqlalchemy import text

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=ApiResponse[RegisterResponse],
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        409: {"model": ApiErrorResponse, "description": "User already exists"},
    },
    summary="Register new user",
    description="Create a new user account and merchant",
)
async def register_user(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Register a new user and create their merchant account.

    Two registration scenarios are supported:

    **Minimal Registration** (recommended for quick onboarding):
    - **name**: User full name
    - **email**: User email address
    - **password**: User password (min 8 characters)
    - **business_name**: Name of the business/merchant

    **Complete Registration** (with WhatsApp integration):
    - All fields above, plus:
    - **whatsapp_phone_e164**: WhatsApp phone number in E.164 format (optional)

    **Headers**:
    - **Idempotency-Key**: Optional header to ensure idempotent operation

    **Note**: WhatsApp phone can be added later via merchant profile update.
    """
    try:
        # Direct bootstrap function call - we know this works
        from argon2 import PasswordHasher
        from ..utils.jwt import create_access_token
        from uuid import UUID

        ph = PasswordHasher()
        password_hash = ph.hash(request.password)

        # Call bootstrap function
        result = await db.execute(
            text(
                """
                SELECT out_merchant_id, out_user_id
                FROM public.register_merchant_and_admin(
                    :p_name,
                    :p_email,
                    :p_password_hash,
                    :p_business_name,
                    :p_whatsapp
                )
            """
            ),
            {
                "p_name": request.name,
                "p_email": request.email,
                "p_password_hash": password_hash,
                "p_business_name": request.business_name,
                "p_whatsapp": request.whatsapp_phone_e164,
            },
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Registration failed")

        merchant_id = str(row.out_merchant_id)
        user_id = str(row.out_user_id)

        # Commit transaction
        await db.commit()

        # For now, return success with the IDs
        return {"success": True, "merchant_id": merchant_id, "user_id": user_id}

        return ApiResponse(data=result, message="User registered successfully")

    except AuthError as e:
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post(
    "/login",
    response_model=ApiResponse[AuthResponse],
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Invalid credentials"},
        429: {"model": ApiErrorResponse, "description": "Too many attempts"},
    },
    summary="User login",
    description="Authenticate user and return JWT token",
)
async def login_user(
    request: LoginRequest, req: Request, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Authenticate user and return access token.

    - **email**: User email address
    - **password**: User password
    """
    # Check rate limits
    await check_login_rate_limit(req)
    await check_email_rate_limit(request.email)

    try:
        # Direct login implementation to avoid AuthService complications
        from argon2 import PasswordHasher
        from ..utils.jwt import create_access_token
        from uuid import UUID
        import os

        # Use login lookup function
        try:
            lookup_result = await db.execute(
                text(
                    """
                    SELECT out_user_id, out_merchant_id, out_name, out_email, out_password_hash, out_role
                    FROM public.lookup_user_for_login(:email)
                """
                ),
                {"email": request.email},
            )
            user_row = lookup_result.fetchone()
        except Exception as lookup_error:
            raise HTTPException(status_code=500, detail="Database lookup failed")

        if not user_row:
            # Return error response in the expected format
            from ..models.api import ApiErrorResponse
            from ..models.errors import APIError, ErrorCode, ErrorDetails
            from datetime import datetime, timezone

            return JSONResponse(
                status_code=401,
                content={
                    "ok": False,
                    "error": {
                        "code": "AUTHENTICATION_ERROR",
                        "message": "Invalid credentials",
                        "details": {
                            "field": None,
                            "reason": "The email or password you entered is incorrect",
                            "value": None,
                            "service": None,
                            "retry_after": None,
                            "debug_trace": None,
                        },
                        "request_id": str(uuid.uuid4()),
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        # Verify password (need to add pepper like in registration)
        PASSWORD_PEPPER = os.getenv("PASSWORD_PEPPER", "")
        ph = PasswordHasher()
        try:
            peppered_password = request.password + PASSWORD_PEPPER
            ph.verify(user_row.out_password_hash, peppered_password)
        except Exception as password_error:
            # Return error response in the expected format
            from datetime import datetime, timezone

            return JSONResponse(
                status_code=401,
                content={
                    "ok": False,
                    "error": {
                        "code": "AUTHENTICATION_ERROR",
                        "message": "Invalid credentials",
                        "details": {
                            "field": None,
                            "reason": "The email or password you entered is incorrect",
                            "value": None,
                            "service": None,
                            "retry_after": None,
                            "debug_trace": None,
                        },
                        "request_id": str(uuid.uuid4()),
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        # Create JWT token
        try:
            token = create_access_token(
                {
                    "sub": str(user_row.out_user_id),
                    "email": user_row.out_email,
                    "merchant_id": str(user_row.out_merchant_id),
                    "role": user_row.out_role,
                }
            )
        except Exception as jwt_error:
            raise HTTPException(
                status_code=500, detail=f"JWT creation failed: {str(jwt_error)}"
            )

        # Build response
        try:
            from ..models.auth import UserResponse, AuthResponse

            user_response = UserResponse(
                id=user_row.out_user_id,
                name=user_row.out_name,
                email=user_row.out_email,
                role=user_row.out_role,
                merchant_id=user_row.out_merchant_id,
            )

            result = AuthResponse(token=token, user=user_response)
        except Exception as response_error:
            raise HTTPException(
                status_code=500,
                detail=f"Response building failed: {str(response_error)}",
            )

        # Record successful login
        record_login_attempt(req, request.email, success=True)

        return ApiResponse(data=result, message="Login successful")

    except AuthError as e:
        # Record failed login attempt
        record_login_attempt(req, request.email, success=False)

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        # Record failed login attempt
        record_login_attempt(req, request.email, success=False)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        )


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    responses={401: {"model": ApiErrorResponse, "description": "Unauthorized"}},
    summary="Get current user",
    description="Get information about the currently authenticated user",
)
async def get_me(current_user: CurrentUser):
    """
    Get current user information.

    Requires valid JWT token in Authorization header.
    """
    user_response = UserResponse(
        id=current_user.user_id,
        name="",  # We'll need to get this from the database
        email=current_user.email,
        role=current_user.role,
        merchant_id=current_user.merchant_id,
    )

    return ApiResponse(data=user_response, message="User retrieved successfully")


@router.post(
    "/refresh",
    response_model=ApiResponse[dict],
    responses={401: {"model": ApiErrorResponse, "description": "Unauthorized"}},
    summary="Refresh access token",
    description="Refresh JWT access token (optional endpoint)",
)
async def refresh_token():
    """
    Refresh JWT access token.

    This is an optional endpoint for token refresh functionality.
    Currently returns a placeholder response.
    """
    return ApiResponse(
        data={"token": "new_token_placeholder"}, message="Token refreshed successfully"
    )


@router.post(
    "/logout",
    response_model=ApiResponse[dict],
    responses={401: {"model": ApiErrorResponse, "description": "Unauthorized"}},
    summary="User logout",
    description="Logout user (optional endpoint for client-side token cleanup)",
)
async def logout_user(current_user: CurrentUser):
    """
    Logout user.

    This endpoint is primarily for client-side token cleanup and any
    server-side logout logic. Since we're using stateless JWT tokens,
    the actual logout logic is handled client-side by removing the token.

    Requires valid JWT token in Authorization header.
    """
    return ApiResponse(
        data={"message": "Logged out successfully"}, message="Logout successful"
    )


@router.post("/debug/register-test")
async def debug_register_test(request: RegisterRequest):
    """Test registration request parsing"""
    try:
        print(f"🔍 Register test called: {request.email}")
        return {
            "status": "success",
            "email": request.email,
            "business_name": request.business_name,
        }
    except Exception as e:
        print(f"🔍 Register test error: {e}")
        raise HTTPException(status_code=500, detail=f"Register test failed: {str(e)}")


@router.get("/debug/db")
async def debug_db_connection(db: Annotated[AsyncSession, Depends(get_db)]):
    """Debug endpoint to test database connection"""
    try:
        print("🔍 Debug DB endpoint called")
        result = await db.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        print(f"🔍 DB query result: {row.test if row else 'None'}")

        # Test both functions exist
        func_result = await db.execute(
            text(
                "SELECT proname FROM pg_proc WHERE proname IN ('register_merchant_and_admin', 'lookup_user_for_login')"
            )
        )
        func_rows = func_result.fetchall()
        functions_found = [row.proname for row in func_rows]
        print(f"🔍 Functions found: {functions_found}")

        return {
            "db_test": row.test if row else None,
            "functions_found": functions_found,
        }

    except Exception as e:
        print(f"🔍 Debug DB error: {e}")
        raise HTTPException(status_code=500, detail=f"DB Debug failed: {str(e)}")

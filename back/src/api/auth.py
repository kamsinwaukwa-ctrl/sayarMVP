"""
Authentication API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
from uuid import UUID

from ..models.api import AuthRequest, AuthResponse, ApiResponse, ApiErrorResponse
from ..models.errors import ErrorCode

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        409: {"model": ApiErrorResponse, "description": "User already exists"}
    },
    summary="Register new user",
    description="Create a new user account and merchant"
)
async def register_user(
    request: AuthRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Register a new user and create their merchant account.
    
    - **email**: User email address
    - **password**: User password (min 8 characters)
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("7c8de9a5-7e2b-4e7e-9c0a-9b7b0d2b0e1a"),
        data={
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": request.email,
                "name": "New User",
                "role": "owner",
                "merchant_id": "660e8400-e29b-41d4-a716-446655440001"
            }
        },
        message="User registered successfully"
    )


@router.post(
    "/login",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Invalid credentials"}
    },
    summary="User login",
    description="Authenticate user and return JWT token"
)
async def login_user(request: AuthRequest):
    """
    Authenticate user and return access token.
    
    - **email**: User email address
    - **password**: User password
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("8d9ef0b6-8f3c-4f8f-9d1b-9c8c0e3b0f2c"),
        data={
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": request.email,
                "name": "John Doe",
                "role": "owner",
                "merchant_id": "660e8400-e29b-41d4-a716-446655440001"
            }
        },
        message="Login successful"
    )


@router.get(
    "/me",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="Get current user",
    description="Get information about the currently authenticated user"
)
async def get_current_user():
    """
    Get current user information.
    
    Requires valid JWT token in Authorization header.
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        data={
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "name": "John Doe",
            "role": "owner",
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        },
        message="User retrieved successfully"
    )
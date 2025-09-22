"""
Authentication models for Sayar WhatsApp Commerce Platform
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from enum import Enum


class UserRole(str, Enum):
    """User roles enumeration"""

    ADMIN = "admin"
    STAFF = "staff"


class RegisterRequest(BaseModel):
    """User registration request"""

    name: str = Field(..., min_length=1, max_length=100, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    business_name: str = Field(
        ..., min_length=1, max_length=100, description="Business name"
    )
    whatsapp_phone_e164: Optional[str] = Field(
        None, description="WhatsApp phone number in E.164 format (optional)"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "password": "secure_password",
                    "business_name": "My Store",
                },
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "password": "secure_password",
                    "business_name": "My Store",
                    "whatsapp_phone_e164": "+2348012345678",
                },
            ]
        }


class LoginRequest(BaseModel):
    """User login request"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    class Config:
        json_schema_extra = {
            "example": {"email": "john@example.com", "password": "secure_password"}
        }


class UserResponse(BaseModel):
    """User response model"""

    id: UUID
    name: str
    email: EmailStr
    role: UserRole
    merchant_id: UUID

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "John Doe",
                "email": "john@example.com",
                "role": "admin",
                "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            }
        }


class MerchantResponse(BaseModel):
    """Merchant response model"""

    id: UUID
    name: str
    slug: Optional[str] = None
    whatsapp_phone_e164: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "examples": [
                {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "name": "My Store",
                    "slug": "my-store",
                    "whatsapp_phone_e164": "+2348012345678",
                },
                {"id": "660e8400-e29b-41d4-a716-446655440001", "name": "My Store"},
            ]
        }


class AuthResponse(BaseModel):
    """Authentication response"""

    token: str = Field(..., description="JWT access token")
    user: UserResponse = Field(..., description="User information")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "role": "admin",
                    "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
                },
            }
        }


class RegisterResponse(BaseModel):
    """Registration response"""

    token: str = Field(..., description="JWT access token")
    user: UserResponse = Field(..., description="User information")
    merchant: MerchantResponse = Field(..., description="Merchant information")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "role": "admin",
                    "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
                },
                "merchant": {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "name": "My Store",
                    "slug": "my-store",
                    "whatsapp_phone_e164": "+2348012345678",
                },
            }
        }


class JWTPayload(BaseModel):
    """JWT payload model"""

    sub: str  # user_id
    email: EmailStr
    merchant_id: str
    role: str
    iat: int
    exp: int


class CurrentPrincipal(BaseModel):
    """Current authenticated user principal"""

    user_id: UUID
    merchant_id: UUID
    role: UserRole
    email: EmailStr

    class Config:
        from_attributes = True

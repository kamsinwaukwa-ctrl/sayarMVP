"""
Pydantic models for Sayar media upload functionality
Provides type safety and validation for media operations
"""

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from uuid import UUID

ALLOWED_LOGO_TYPES = ["image/jpeg", "image/png", "image/webp"]
ALLOWED_LOGO_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
DEFAULT_MAX_SIZE = 5 * 1024 * 1024  # 5MB
DEFAULT_SIGNED_URL_EXPIRY = 900  # 15 minutes

class MediaUploadResponse(BaseModel):
    """Response model for media upload operations."""
    url: str = Field(..., description="Storage URL for the uploaded file")
    signed_url: str = Field(..., description="Signed URL for temporary access")
    filename: str = Field(..., description="Normalized filename")
    size: int = Field(..., ge=0, description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the uploaded file")
    expires_at: datetime = Field(..., description="Expiry time for the signed URL")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://storage.supabase.co/object/private/merchant-logos/123e4567-e89b-12d3-a456-426614174000/logo.png",
                "signed_url": "https://storage.supabase.co/object/sign/merchant-logos/123e4567-e89b-12d3-a456-426614174000/logo.png?token=abc123",
                "filename": "logo.png",
                "size": 102400,
                "content_type": "image/png",
                "expires_at": "2025-01-27T11:00:00Z"
            }
        }

class SignedUrlResponse(BaseModel):
    """Response model for signed URL generation."""
    signed_url: str = Field(..., description="Signed URL for temporary access")
    expires_at: datetime = Field(..., description="Expiry time for the signed URL")

    class Config:
        json_schema_extra = {
            "example": {
                "signed_url": "https://storage.supabase.co/object/sign/merchant-logos/123e4567-e89b-12d3-a456-426614174000/logo.png?token=abc123",
                "expires_at": "2025-01-27T11:00:00Z"
            }
        }

class MediaValidationError(BaseModel):
    """Error model for media validation failures."""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")

    class Config:
        json_schema_extra = {
            "example": {
                "field": "file",
                "message": "File size exceeds maximum allowed size of 5MB",
                "code": "FILE_TOO_LARGE"
            }
        }
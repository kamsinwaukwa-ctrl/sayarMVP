"""
Pydantic models for API requests and responses with OpenAPI schema examples
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Generic, TypeVar
from uuid import UUID
from datetime import datetime
from enum import Enum

from .database import UserRole, ProductStatus, DiscountStatus, DiscountType
from .errors import ErrorCode, ErrorDetails, APIError

# Type variable for generic API responses
T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope for success"""
    ok: bool = True
    id: Optional[UUID] = Field(None, description="Unique identifier for the operation")
    data: Optional[T] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Human-readable success message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "ok": True,
                "id": "7c8de9a5-7e2b-4e7e-9c0a-9b7b0d2b0e1a",
                "data": {"result": "success"},
                "message": "Operation completed successfully",
                "timestamp": "2025-01-27T10:00:00Z"
            }
        }


class ApiErrorResponse(BaseModel):
    """Standard API response envelope for errors"""
    ok: bool = False
    error: APIError
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "ok": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {"field": "email", "reason": "Invalid email format"},
                    "trace_id": "trace_abc123"
                },
                "timestamp": "2025-01-27T10:00:00Z"
            }
        }


# Auth Models
class RegisterRequest(BaseModel):
    """User registration request"""
    name: str = Field(..., min_length=1, max_length=100, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    business_name: str = Field(..., min_length=1, max_length=100, description="Business name")
    whatsapp_phone_e164: Optional[str] = Field(None, description="WhatsApp phone number in E.164 format (optional)")
    
    class Config:
        json_schema_extra = {
            "examples": {
                "minimal": {
                    "summary": "Registration without WhatsApp phone",
                    "value": {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "password": "secure_password",
                        "business_name": "My Store"
                    }
                },
                "withWhatsApp": {
                    "summary": "Registration with WhatsApp phone (optional)",
                    "value": {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "password": "secure_password",
                        "business_name": "My Store",
                        "whatsapp_phone_e164": "+2348012345678"
                    }
                }
            }
        }


class AuthRequest(BaseModel):
    """Authentication request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class AuthResponse(BaseModel):
    """Authentication response"""
    token: str = Field(..., description="JWT access token")
    user: Dict[str, Any] = Field(..., description="User information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "name": "John Doe",
                    "role": "owner",
                    "merchant_id": "660e8400-e29b-41d4-a716-446655440001"
                }
            }
        }


# Merchant Models
class CreateMerchantRequest(BaseModel):
    """Create merchant request"""
    name: str = Field(..., min_length=1, max_length=100, description="Merchant name")
    whatsapp_phone_e164: str = Field(..., description="WhatsApp phone number in E.164 format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Awesome Beauty Store",
                "whatsapp_phone_e164": "+2341234567890"
            }
        }


class MerchantResponse(BaseModel):
    """Merchant response"""
    id: UUID
    name: str
    slug: Optional[str]
    whatsapp_phone_e164: Optional[str]
    currency: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Awesome Beauty Store",
                "slug": "awesome-beauty-store",
                "whatsapp_phone_e164": "+2341234567890",
                "currency": "NGN",
                "created_at": "2025-01-27T10:00:00Z",
                "updated_at": "2025-01-27T10:00:00Z"
            }
        }


# Product Models
class CreateProductRequest(BaseModel):
    """Create product request"""
    title: str = Field(..., min_length=1, max_length=200, description="Product title")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    price_kobo: int = Field(..., ge=0, description="Price in kobo (1 NGN = 100 kobo)")
    stock: int = Field(..., ge=0, description="Initial stock quantity")
    sku: str = Field(..., min_length=1, max_length=50, description="Stock keeping unit")
    category_path: Optional[str] = Field(None, description="Category path")
    tags: Optional[List[str]] = Field(None, description="Product tags")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Premium Face Cream",
                "description": "Luxury anti-aging face cream with natural ingredients",
                "price_kobo": 15000,
                "stock": 100,
                "sku": "FACE-CREAM-001",
                "category_path": "skincare/face/creams",
                "tags": ["premium", "anti-aging", "natural"]
            }
        }


class ProductResponse(BaseModel):
    """Product response"""
    id: UUID
    merchant_id: UUID
    title: str
    description: Optional[str]
    price_kobo: int
    stock: int
    reserved_qty: int
    available_qty: int
    image_url: Optional[str]
    sku: str
    status: ProductStatus
    retailer_id: str
    category_path: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
                "title": "Premium Face Cream",
                "description": "Luxury anti-aging face cream with natural ingredients",
                "price_kobo": 15000,
                "stock": 100,
                "reserved_qty": 5,
                "available_qty": 95,
                "image_url": "https://example.com/images/face-cream.jpg",
                "sku": "FACE-CREAM-001",
                "status": "active",
                "retailer_id": "meta_1234567890",
                "category_path": "skincare/face/creams",
                "tags": ["premium", "anti-aging", "natural"],
                "created_at": "2025-01-27T10:00:00Z",
                "updated_at": "2025-01-27T10:00:00Z"
            }
        }


# Delivery Rate Models
class CreateDeliveryRateRequest(BaseModel):
    """Create delivery rate request"""
    name: str = Field(..., min_length=1, max_length=100, description="Delivery rate name")
    areas_text: str = Field(..., description="Coverage areas as text")
    price_kobo: int = Field(..., ge=0, description="Delivery price in kobo")
    description: Optional[str] = Field(None, max_length=500, description="Delivery rate description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Lagos Mainland Delivery",
                "areas_text": "Ikeja, Surulere, Yaba, Mushin",
                "price_kobo": 1500,
                "description": "Next day delivery within Lagos Mainland"
            }
        }


class DeliveryRateResponse(BaseModel):
    """Delivery rate response"""
    id: UUID
    merchant_id: UUID
    name: str
    areas_text: str
    price_kobo: int
    description: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440003",
                "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Lagos Mainland Delivery",
                "areas_text": "Ikeja, Surulere, Yaba, Mushin",
                "price_kobo": 1500,
                "description": "Next day delivery within Lagos Mainland",
                "active": True,
                "created_at": "2025-01-27T10:00:00Z",
                "updated_at": "2025-01-27T10:00:00Z"
            }
        }


# Discount Models
class ValidateDiscountRequest(BaseModel):
    """Validate discount request"""
    code: str = Field(..., min_length=1, max_length=50, description="Discount code")
    subtotal_kobo: int = Field(..., ge=0, description="Order subtotal in kobo")
    customer_id: Optional[UUID] = Field(None, description="Customer ID for per-customer limits")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "SUMMER20",
                "subtotal_kobo": 10000,
                "customer_id": "990e8400-e29b-41d4-a716-446655440004"
            }
        }


class DiscountValidationResponse(BaseModel):
    """Discount validation response"""
    valid: bool = Field(..., description="Whether discount is valid")
    discount_kobo: Optional[int] = Field(None, ge=0, description="Discount amount in kobo")
    reason: Optional[str] = Field(None, description="Reason if invalid")
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "discount_kobo": 2000,
                "reason": None
            }
        }


# Pagination Models
class PaginationParams(BaseModel):
    """Pagination query parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort: Optional[str] = Field(None, description="Sort field and direction (e.g., 'created_at:desc')")


class PaginatedResponse(BaseModel):
    """Paginated response envelope"""
    ok: bool = True
    data: List[Any]
    pagination: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "ok": True,
                "data": [],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_items": 100,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": False
                },
                "timestamp": "2025-01-27T10:00:00Z"
            }
        }
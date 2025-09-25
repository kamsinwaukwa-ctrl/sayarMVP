"""
Pydantic models for API requests and responses with OpenAPI schema examples
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Generic, TypeVar
from uuid import UUID
from datetime import datetime
from enum import Enum

from .database import UserRole, ProductStatus, DiscountStatus, DiscountType
from .errors import ErrorCode, ErrorDetails, ErrorInfo

# Type variable for generic API responses
T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope for success"""

    ok: bool = True
    id: Optional[UUID] = Field(None, description="Unique identifier for the operation")
    data: Optional[T] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Human-readable success message")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "ok": True,
                "id": "7c8de9a5-7e2b-4e7e-9c0a-9b7b0d2b0e1a",
                "data": {"result": "success"},
                "message": "Operation completed successfully",
                "timestamp": "2025-01-27T10:00:00Z",
            }
        }


class ApiErrorResponse(BaseModel):
    """Standard API response envelope for errors"""

    ok: bool = False
    error: ErrorInfo
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Error timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "ok": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {"field": "email", "reason": "Invalid email format"},
                    "trace_id": "trace_abc123",
                },
                "timestamp": "2025-01-27T10:00:00Z",
            }
        }


# Auth Models
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
            "examples": {
                "minimal": {
                    "summary": "Registration without WhatsApp phone",
                    "value": {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "password": "secure_password",
                        "business_name": "My Store",
                    },
                },
                "withWhatsApp": {
                    "summary": "Registration with WhatsApp phone (optional)",
                    "value": {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "password": "secure_password",
                        "business_name": "My Store",
                        "whatsapp_phone_e164": "+2348012345678",
                    },
                },
            }
        }


class AuthRequest(BaseModel):
    """Authentication request"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")

    class Config:
        json_schema_extra = {
            "example": {"email": "user@example.com", "password": "securepassword123"}
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
                    "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
                },
            }
        }


# Merchant Models
class CreateMerchantRequest(BaseModel):
    """Create merchant request"""

    name: str = Field(..., min_length=1, max_length=100, description="Merchant name")
    whatsapp_phone_e164: str = Field(
        ..., description="WhatsApp phone number in E.164 format"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Awesome Beauty Store",
                "whatsapp_phone_e164": "+2341234567890",
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
                "updated_at": "2025-01-27T10:00:00Z",
            }
        }


# Product Models
class CreateProductRequest(BaseModel):
    """Create product request with Meta catalog support"""

    title: str = Field(..., min_length=1, max_length=200, description="Product title")
    description: Optional[str] = Field(
        None, max_length=1000, description="Product description"
    )
    price_kobo: int = Field(..., ge=0, description="Price in kobo (1 NGN = 100 kobo)")
    stock: int = Field(..., ge=0, description="Initial stock quantity")
    sku: Optional[str] = Field(
        None,
        pattern=r"^[A-Za-z0-9-_]{1,64}$",
        description="Stock keeping unit (auto-generated if missing)",
    )
    brand: Optional[str] = Field(
        None,
        min_length=1,
        max_length=70,
        description="Product brand (auto-defaults from merchant name)",
    )
    mpn: Optional[str] = Field(
        None,
        pattern=r"^[A-Za-z0-9-._]{1,70}$",
        description="Manufacturer Part Number (auto-generated if missing)",
    )
    category_path: Optional[str] = Field(None, description="Category path")
    tags: Optional[List[str]] = Field(None, description="Product tags")
    meta_catalog_visible: bool = Field(
        default=True, description="Whether to sync to Meta catalog"
    )
    image_file_id: Optional[str] = Field(
        None, description="Reference to uploaded image file"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Premium Face Cream",
                "description": "Luxury anti-aging face cream with natural ingredients",
                "price_kobo": 15000,
                "stock": 100,
                "sku": "FACE-CREAM-001",
                "brand": "Amari Beauty",
                "mpn": "amari-FACE-CREAM-001",
                "category_path": "skincare/face/creams",
                "tags": ["premium", "anti-aging", "natural"],
                "meta_catalog_visible": True,
                "image_file_id": "img_123456",
            }
        }


class UpdateProductRequest(BaseModel):
    """Update product request with partial fields"""

    title: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Product title"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Product description"
    )
    price_kobo: Optional[int] = Field(None, ge=0, description="Price in kobo")
    stock: Optional[int] = Field(None, ge=0, description="Stock quantity")
    sku: Optional[str] = Field(
        None, pattern=r"^[A-Za-z0-9-_]{1,64}$", description="Stock keeping unit"
    )
    brand: Optional[str] = Field(
        None,
        min_length=1,
        max_length=70,
        description="Product brand (preserves existing if not provided)",
    )
    mpn: Optional[str] = Field(
        None, pattern=r"^[A-Za-z0-9-._]{1,70}$", description="Manufacturer Part Number"
    )
    category_path: Optional[str] = Field(None, description="Category path")
    tags: Optional[List[str]] = Field(None, description="Product tags")
    meta_catalog_visible: Optional[bool] = Field(
        None, description="Meta catalog visibility"
    )
    status: Optional[str] = Field(None, description="Product status (active/inactive)")
    image_file_id: Optional[str] = Field(
        None, description="Reference to uploaded image file"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Premium Face Cream",
                "price_kobo": 18000,
                "stock": 150,
                "brand": "Updated Brand Name",
                "mpn": "amari-updated-sku-123",
                "meta_catalog_visible": True,
            }
        }


class ProductResponse(BaseModel):
    """Product response with Meta catalog fields"""

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
    brand: str
    mpn: str
    status: ProductStatus
    retailer_id: str
    category_path: Optional[str]
    tags: List[str]
    meta_catalog_visible: bool
    meta_sync_status: str
    meta_sync_errors: Optional[List[str]]
    meta_last_synced_at: Optional[datetime]
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
                "brand": "Amari Beauty",
                "mpn": "amari-FACE-CREAM-001",
                "status": "active",
                "retailer_id": "meta_merchant123_prod456",
                "category_path": "skincare/face/creams",
                "tags": ["premium", "anti-aging", "natural"],
                "meta_catalog_visible": True,
                "meta_sync_status": "synced",
                "meta_sync_errors": None,
                "meta_last_synced_at": "2025-01-27T10:05:00Z",
                "created_at": "2025-01-27T10:00:00Z",
                "updated_at": "2025-01-27T10:00:00Z",
            }
        }


# Delivery Rate Models
class CreateDeliveryRateRequest(BaseModel):
    """Create delivery rate request"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Delivery rate name"
    )
    areas_text: str = Field(..., description="Coverage areas as text")
    price_kobo: int = Field(..., ge=0, description="Delivery price in kobo")
    description: Optional[str] = Field(
        None, max_length=500, description="Delivery rate description"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Lagos Mainland Delivery",
                "areas_text": "Ikeja, Surulere, Yaba, Mushin",
                "price_kobo": 1500,
                "description": "Next day delivery within Lagos Mainland",
            }
        }


class UpdateDeliveryRateRequest(BaseModel):
    """Update delivery rate request"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Delivery rate name"
    )
    areas_text: Optional[str] = Field(
        None, min_length=1, description="Coverage areas as text"
    )
    price_kobo: Optional[int] = Field(None, ge=0, description="Delivery price in kobo")
    description: Optional[str] = Field(
        None, max_length=500, description="Delivery rate description"
    )
    active: Optional[bool] = Field(None, description="Whether delivery rate is active")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Lagos Mainland Express",
                "areas_text": "Ikeja, Surulere, Yaba, Mushin, Maryland",
                "price_kobo": 2000,
                "description": "Same day delivery within Lagos Mainland",
                "active": True,
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
                "updated_at": "2025-01-27T10:00:00Z",
            }
        }


# Discount Models
class ValidateDiscountRequest(BaseModel):
    """Validate discount request"""

    code: str = Field(..., min_length=1, max_length=50, description="Discount code")
    subtotal_kobo: int = Field(..., ge=0, description="Order subtotal in kobo")
    customer_id: Optional[UUID] = Field(
        None, description="Customer ID for per-customer limits"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": "SUMMER20",
                "subtotal_kobo": 10000,
                "customer_id": "990e8400-e29b-41d4-a716-446655440004",
            }
        }


class DiscountValidationResponse(BaseModel):
    """Discount validation response"""

    valid: bool = Field(..., description="Whether discount is valid")
    discount_kobo: Optional[int] = Field(
        None, ge=0, description="Discount amount in kobo"
    )
    reason: Optional[str] = Field(None, description="Reason if invalid")

    class Config:
        json_schema_extra = {
            "example": {"valid": True, "discount_kobo": 2000, "reason": None}
        }


class CreateDiscountRequest(BaseModel):
    """Create discount request"""

    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Discount code (uppercase alphanumeric)",
    )
    type: str = Field(..., description="Discount type", pattern="^(percent|fixed)$")
    value_bp: Optional[int] = Field(
        None,
        ge=0,
        le=10000,
        description="Percentage in basis points (0-10000 = 0-100%)",
    )
    amount_kobo: Optional[int] = Field(
        None, ge=0, description="Fixed discount amount in kobo"
    )
    max_discount_kobo: Optional[int] = Field(
        None, ge=0, description="Maximum discount cap in kobo"
    )
    min_subtotal_kobo: int = Field(
        0, ge=0, description="Minimum order subtotal required in kobo"
    )
    starts_at: Optional[datetime] = Field(None, description="Discount start time")
    expires_at: Optional[datetime] = Field(None, description="Discount expiry time")
    usage_limit_total: Optional[int] = Field(
        None, ge=1, description="Total usage limit across all customers"
    )
    usage_limit_per_customer: Optional[int] = Field(
        None, ge=1, description="Usage limit per customer"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "examples": [
                {
                    "summary": "25% off discount with minimum spend",
                    "value": {
                        "code": "SUMMER25",
                        "type": "percent",
                        "value_bp": 2500,
                        "max_discount_kobo": 5000,
                        "min_subtotal_kobo": 10000,
                        "expires_at": "2025-12-31T23:59:59Z",
                        "usage_limit_total": 100,
                        "usage_limit_per_customer": 1,
                    },
                },
                {
                    "summary": "Fixed ₦20 off discount",
                    "value": {
                        "code": "SAVE20",
                        "type": "fixed",
                        "amount_kobo": 2000,
                        "min_subtotal_kobo": 5000,
                        "usage_limit_total": 50,
                    },
                },
            ]
        }


class UpdateDiscountRequest(BaseModel):
    """Update discount request"""

    status: Optional[str] = Field(
        None, description="Discount status", pattern="^(active|paused)$"
    )
    expires_at: Optional[datetime] = Field(None, description="Update expiry time")
    usage_limit_total: Optional[int] = Field(
        None, ge=1, description="Update total usage limit"
    )
    usage_limit_per_customer: Optional[int] = Field(
        None, ge=1, description="Update per-customer usage limit"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "examples": [
                {"summary": "Pause an active discount", "value": {"status": "paused"}},
                {
                    "summary": "Extend discount expiry date",
                    "value": {"expires_at": "2025-12-31T23:59:59Z"},
                },
                {
                    "summary": "Increase usage limits",
                    "value": {"usage_limit_total": 200, "usage_limit_per_customer": 2},
                },
            ]
        }


class DiscountResponse(BaseModel):
    """Discount response"""

    id: UUID
    merchant_id: UUID
    code: str
    type: str
    value_bp: Optional[int]
    amount_kobo: Optional[int]
    max_discount_kobo: Optional[int]
    min_subtotal_kobo: int
    starts_at: Optional[datetime]
    expires_at: Optional[datetime]
    usage_limit_total: Optional[int]
    usage_limit_per_customer: Optional[int]
    times_redeemed: int
    status: str
    stackable: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
                "code": "SUMMER25",
                "type": "percent",
                "value_bp": 2500,
                "amount_kobo": None,
                "max_discount_kobo": 5000,
                "min_subtotal_kobo": 10000,
                "starts_at": "2025-06-01T00:00:00Z",
                "expires_at": "2025-12-31T23:59:59Z",
                "usage_limit_total": 100,
                "usage_limit_per_customer": 1,
                "times_redeemed": 25,
                "status": "active",
                "stackable": False,
                "created_at": "2025-01-27T10:00:00Z",
                "updated_at": "2025-01-27T10:00:00Z",
            }
        }


# Pagination Models
class PaginationParams(BaseModel):
    """Pagination query parameters"""

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort: Optional[str] = Field(
        None, description="Sort field and direction (e.g., 'created_at:desc')"
    )


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
                    "has_prev": False,
                },
                "timestamp": "2025-01-27T10:00:00Z",
            }
        }


# =============================================================================
# WhatsApp Integration Models
# =============================================================================


class WAEnvironment(str, Enum):
    """WhatsApp environment enumeration"""

    TEST = "test"
    PROD = "prod"


class WAConnectionStatus(str, Enum):
    """WhatsApp connection status enumeration"""

    NOT_CONNECTED = "not_connected"
    VERIFIED_TEST = "verified_test"
    VERIFIED_PROD = "verified_prod"


class WhatsAppCredentialsRequest(BaseModel):
    """Request model for saving/updating WhatsApp credentials"""

    waba_id: str = Field(
        ..., description="WhatsApp Business Account ID", min_length=15, max_length=17
    )
    phone_number_id: str = Field(
        ..., description="Phone Number ID from Meta", min_length=15, max_length=17
    )
    app_id: str = Field(
        ..., description="Facebook App ID", min_length=15, max_length=17
    )
    system_user_token: str = Field(
        ..., description="System User access token", min_length=100
    )
    environment: WAEnvironment = Field(
        WAEnvironment.TEST, description="Test or production environment"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "waba_id": "123456789012345",
                "phone_number_id": "987654321098765",
                "app_id": "456789123456789",
                "system_user_token": "EAAxxxxxxxxxxxxxx",
                "environment": "test",
            }
        }


class WhatsAppStatusResponse(BaseModel):
    """Response model for WhatsApp connection status"""

    connection_status: WAConnectionStatus
    environment: WAEnvironment
    phone_number_id: Optional[str] = Field(
        None, description="Phone number ID (last 4 digits shown, rest masked)"
    )
    verified_at: Optional[datetime] = None
    last_error: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "connection_status": "not_connected",
                "environment": "test",
                "phone_number_id": "***********8765",
                "verified_at": None,
                "last_error": None,
            }
        }


class WhatsAppVerifyResponse(WhatsAppStatusResponse):
    """Response model for WhatsApp verification with additional info"""

    phone_number_display: Optional[str] = Field(
        None, description="Formatted phone number"
    )
    business_name: Optional[str] = Field(
        None, description="Business name from WhatsApp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "connection_status": "verified_test",
                "environment": "test",
                "phone_number_id": "***********8765",
                "verified_at": "2025-01-14T10:00:00Z",
                "last_error": None,
                "phone_number_display": "+234XXXXXXXXX",
                "business_name": "Beauty Store Lagos",
            }
        }


# =============================================================================
# Cloudinary Integration Models
# =============================================================================


class CloudinaryHealthResponse(BaseModel):
    """Cloudinary platform health check response"""

    configured: bool = Field(
        ..., description="Whether Cloudinary is properly configured"
    )
    cloud_name: Optional[str] = Field(None, description="Cloudinary cloud name")
    verified_at: Optional[datetime] = Field(
        None, description="Last verification timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "configured": True,
                "cloud_name": "platform-cloud",
                "verified_at": "2025-01-16T10:30:00Z",
            }
        }


class ProductImageUploadRequest(BaseModel):
    """Product image upload request"""

    is_primary: bool = Field(
        False, description="Whether this should be the primary image"
    )
    alt_text: Optional[str] = Field(
        None, max_length=255, description="Alternative text for accessibility"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "is_primary": True,
                "alt_text": "Premium face cream product shot",
            }
        }


class ProductImageResponse(BaseModel):
    """Product image response"""

    id: UUID = Field(..., description="Image unique identifier")
    product_id: UUID = Field(..., description="Associated product ID")
    cloudinary_public_id: str = Field(..., description="Cloudinary public ID")
    secure_url: str = Field(..., description="Main preset secure URL for Meta catalog")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail preset URL")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    format: Optional[str] = Field(None, description="Image format (jpg, png, webp)")
    bytes: Optional[int] = Field(None, description="File size in bytes")
    is_primary: bool = Field(
        ..., description="Whether this is the primary product image"
    )
    alt_text: Optional[str] = Field(None, description="Alternative text")
    upload_status: str = Field(
        ..., description="Upload status (uploading, completed, failed, deleted)"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "img_uuid",
                "product_id": "prod_uuid",
                "cloudinary_public_id": "sayar/products/merchant_id/image_uuid",
                "secure_url": "https://res.cloudinary.com/cloud/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v1642341234/sayar/products/merchant_id/image_uuid.jpg",
                "thumbnail_url": "https://res.cloudinary.com/cloud/image/upload/c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco/v1642341234/sayar/products/merchant_id/image_uuid.jpg",
                "width": 1200,
                "height": 800,
                "format": "jpg",
                "bytes": 234567,
                "is_primary": False,
                "alt_text": "Product description",
                "upload_status": "completed",
                "created_at": "2025-01-16T10:30:00Z",
                "updated_at": "2025-01-16T10:30:00Z",
            }
        }


class CloudinaryWebhookPayload(BaseModel):
    """Cloudinary webhook payload"""

    notification_type: str = Field(
        ..., description="Type of notification (upload, destroy, etc.)"
    )
    timestamp: int = Field(..., description="Unix timestamp")
    public_id: str = Field(..., description="Cloudinary public ID")
    version: int = Field(..., description="Version number")
    width: Optional[int] = Field(None, description="Image width")
    height: Optional[int] = Field(None, description="Image height")
    format: Optional[str] = Field(None, description="Image format")
    resource_type: str = Field(..., description="Resource type (image, video, etc.)")
    bytes: Optional[int] = Field(None, description="File size in bytes")
    url: str = Field(..., description="Public URL")
    secure_url: str = Field(..., description="HTTPS URL")
    eager: Optional[List[Dict[str, Any]]] = Field(
        [], description="Eager transformation results"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "notification_type": "upload",
                "timestamp": 1642341234,
                "public_id": "sayar/products/merchant_id/image_uuid",
                "version": 1642341234,
                "width": 1200,
                "height": 800,
                "format": "jpg",
                "resource_type": "image",
                "bytes": 234567,
                "url": "http://res.cloudinary.com/cloud/image/upload/v1642341234/sayar/products/merchant_id/image_uuid.jpg",
                "secure_url": "https://res.cloudinary.com/cloud/image/upload/v1642341234/sayar/products/merchant_id/image_uuid.jpg",
                "eager": [
                    {
                        "transformation": "c_limit,w_1600,h_1600,f_auto,q_auto:good",
                        "width": 1600,
                        "height": 1066,
                        "url": "http://res.cloudinary.com/cloud/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v1642341234/sayar/products/merchant_id/image_uuid.jpg",
                        "secure_url": "https://res.cloudinary.com/cloud/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v1642341234/sayar/products/merchant_id/image_uuid.jpg",
                    }
                ],
            }
        }


class SetPrimaryImageResponse(BaseModel):
    """Response for setting primary image"""

    id: UUID = Field(..., description="Image ID")
    is_primary: bool = Field(..., description="Confirmation that image is now primary")
    catalog_sync_triggered: bool = Field(
        ..., description="Whether Meta catalog sync was triggered"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "img_uuid",
                "is_primary": True,
                "catalog_sync_triggered": True,
            }
        }


# =============================================================================
# Meta Catalog Sync Models
# =============================================================================


class MetaSyncResponse(BaseModel):
    """Response for manual Meta Catalog sync trigger"""

    product_id: UUID = Field(..., description="Product ID that was synced")
    sync_status: str = Field(..., description="Current sync status")
    job_id: str = Field(..., description="Outbox job ID for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "sync_status": "pending",
                "job_id": "catalog_sync:merchant_123:product_456:2025-01-17T10:30:00Z",
            }
        }


class MetaSyncStatusResponse(BaseModel):
    """Response for Meta sync status endpoint"""

    status: str = Field(..., description="Current Meta sync status")
    reason: Optional[str] = Field(None, description="Human-readable sync status reason")
    last_synced_at: Optional[datetime] = Field(
        None, description="Last successful sync timestamp"
    )
    retry_count: Optional[int] = Field(None, description="Number of retry attempts")
    next_retry_at: Optional[datetime] = Field(
        None, description="Next retry timestamp if applicable"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "reason": "Product image is invalid or missing. Please upload a valid image and try again.",
                "last_synced_at": "2025-09-17T10:30:00Z",
                "retry_count": 3,
                "next_retry_at": "2025-09-17T11:00:00Z",
            }
        }


class MetaUnpublishResponse(BaseModel):
    """Response model for force unpublish endpoint (envelope wrapper applies)"""

    product_id: UUID = Field(..., description="Product ID that was unpublished")
    action: str = Field(
        ..., description="Action performed (force_unpublish or status_change)"
    )
    job_id: str = Field(..., description="Outbox job ID for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "action": "force_unpublish",
                "job_id": "catalog_unpublish:merchant:product:1705500000",
            }
        }


# Onboarding Progress Models
class OnboardingProgressResponse(BaseModel):
    """Response model for onboarding progress"""

    brand_basics: bool = Field(..., description="Brand basics step completed")
    meta_catalog: bool = Field(..., description="Meta catalog step completed")
    whatsapp: bool = Field(..., description="WhatsApp integration completed")
    delivery_rates: bool = Field(..., description="Delivery rates step completed")
    payments: bool = Field(..., description="Payment setup completed")

    class Config:
        json_schema_extra = {
            "example": {
                "brand_basics": True,
                "meta_catalog": False,
                "whatsapp": False,
                "delivery_rates": False,
                "payments": False,
            }
        }


class MetaIntegrationSummaryResponse(BaseModel):
    """Safe Meta integration summary response (no sensitive data)"""

    catalog_present: bool = Field(..., description="Whether catalog_id is configured")
    credentials_present: bool = Field(..., description="Whether app_id and waba_id are configured")
    verified: bool = Field(..., description="Whether integration is verified")
    status: str = Field(..., description="Integration status")
    catalog_name: Optional[str] = Field(None, description="Catalog display name (safe to expose)")

    class Config:
        json_schema_extra = {
            "example": {
                "catalog_present": True,
                "credentials_present": False,
                "verified": False,
                "status": "catalog_saved",
                "catalog_name": "Acme Main Catalog"
            }
        }


class UpdateOnboardingProgressRequest(BaseModel):
    """Request to update onboarding progress"""

    brand_basics: Optional[bool] = Field(
        None, description="Mark brand basics as completed"
    )
    meta_catalog: Optional[bool] = Field(
        None, description="Mark meta catalog as completed"
    )
    whatsapp: Optional[bool] = Field(
        None, description="Mark WhatsApp integration as completed"
    )
    products: Optional[bool] = Field(None, description="Mark products as completed")
    delivery_rates: Optional[bool] = Field(
        None, description="Mark delivery rates as completed"
    )
    payments: Optional[bool] = Field(None, description="Mark payments as completed")

    class Config:
        json_schema_extra = {"example": {"brand_basics": True}}

"""
Pydantic models for Sayar WhatsApp Commerce Platform database schema
These models provide type safety and validation for database operations
"""
from .sqlalchemy_models import Base, SystemSetting, MerchantSetting, FeatureFlag  # Re-export models

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    """User roles enumeration"""
    OWNER = "owner"
    STAFF = "staff"

class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DiscountType(str, Enum):
    """Discount type enumeration"""
    PERCENT = "percent"
    FIXED = "fixed"

class ProductStatus(str, Enum):
    """Product status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"

class DiscountStatus(str, Enum):
    """Discount status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"

class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class ReservationStatus(str, Enum):
    """Inventory reservation status enumeration"""
    ACTIVE = "active"
    CONSUMED = "consumed"
    RELEASED = "released"

class WebhookSource(str, Enum):
    """Webhook source enumeration"""
    WA = "wa"
    PAYSTACK = "paystack"
    KORAPAY = "korapay"
    FLOWS = "flows"

class JobType(str, Enum):
    """Outbox job type enumeration"""
    WA_SEND = "wa_send"
    CATALOG_SYNC = "catalog_sync"
    RELEASE_RESERVATION = "release_reservation"
    PAYMENT_FOLLOWUP = "payment_followup"

class MoneyKobo(BaseModel):
    """Money amount in kobo (Nigerian currency subunit)"""
    amount: int = Field(..., ge=0, description="Amount in kobo (1 NGN = 100 kobo)")

class MerchantDB(BaseModel):
    """Merchant database model"""
    id: UUID
    name: str
    slug: Optional[str] = None
    whatsapp_phone_e164: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    currency: str = "NGN"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserDB(BaseModel):
    """User database model"""
    id: UUID
    merchant_id: UUID
    name: str
    email: str
    role: UserRole
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductDB(BaseModel):
    """Product database model"""
    id: UUID
    merchant_id: UUID
    title: str
    description: Optional[str] = None
    price_kobo: int = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    reserved_qty: int = Field(..., ge=0)
    available_qty: int = Field(..., ge=0)
    image_url: Optional[str] = None
    sku: Optional[str] = None
    status: ProductStatus
    retailer_id: str
    category_path: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    @field_validator('reserved_qty')
    @classmethod
    def validate_reserved_qty(cls, v, info):
        if hasattr(info, 'data') and 'stock' in info.data and v > info.data['stock']:
            raise ValueError('reserved_qty cannot exceed stock')
        return v

    class Config:
        from_attributes = True

class CustomerDB(BaseModel):
    """Customer database model"""
    id: UUID
    merchant_id: UUID
    phone_e164: str
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AddressDB(BaseModel):
    """Address database model"""
    id: UUID
    customer_id: UUID
    label: Optional[str] = None
    line1: str
    lga: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "NG"
    is_default: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrderDB(BaseModel):
    """Order database model"""
    id: UUID
    merchant_id: UUID
    customer_id: Optional[UUID] = None
    subtotal_kobo: int = Field(..., ge=0)
    shipping_kobo: int = Field(..., ge=0)
    discount_kobo: int = Field(..., ge=0)
    total_kobo: int = Field(..., ge=0)
    status: OrderStatus
    payment_provider: Optional[str] = None
    provider_reference: Optional[str] = None
    order_code: str
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_validator('total_kobo')
    @classmethod
    def validate_total_kobo(cls, v, info):
        if hasattr(info, 'data'):
            data = info.data
            subtotal = data.get('subtotal_kobo', 0)
            shipping = data.get('shipping_kobo', 0)
            discount = data.get('discount_kobo', 0)
            expected_total = subtotal + shipping - discount
            
            if v != expected_total:
                raise ValueError(f'total_kobo must equal subtotal + shipping - discount. Expected {expected_total}, got {v}')
        return v

    class Config:
        from_attributes = True

class DiscountDB(BaseModel):
    """Discount database model"""
    id: UUID
    merchant_id: UUID
    code: str
    type: DiscountType
    value_bp: Optional[int] = Field(None, ge=0, le=10000)  # basis points (0-10000 = 0-100%)
    amount_kobo: Optional[int] = Field(None, ge=0)  # fixed amount
    max_discount_kobo: Optional[int] = Field(None, ge=0)
    min_subtotal_kobo: int = Field(..., ge=0)
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    usage_limit_total: Optional[int] = Field(None, ge=0)
    usage_limit_per_customer: Optional[int] = Field(None, ge=0)
    times_redeemed: int = Field(..., ge=0)
    status: DiscountStatus
    stackable: bool = False
    created_at: datetime
    updated_at: datetime

    @model_validator(mode='after')
    def validate_discount_values(self):
        if self.type == DiscountType.PERCENT:
            if self.value_bp is None:
                raise ValueError('value_bp is required for percentage discounts')
            if self.amount_kobo is not None:
                raise ValueError('amount_kobo must be null for percentage discounts')
        elif self.type == DiscountType.FIXED:
            if self.value_bp is not None:
                raise ValueError('value_bp must be null for fixed discounts')
            if self.amount_kobo is None:
                raise ValueError('amount_kobo is required for fixed discounts')
        
        return self

    class Config:
        from_attributes = True

# Response models for API endpoints
class ProductResponse(ProductDB):
    """Product response model with formatted price"""
    price_ngn: float = Field(..., description="Price in NGN (derived from price_kobo)")
    
    @field_validator('price_ngn', mode='before')
    @classmethod
    def convert_kobo_to_ngn(cls, v, info):
        if hasattr(info, 'data') and 'price_kobo' in info.data:
            return info.data['price_kobo'] / 100.0
        return v

class OrderResponse(OrderDB):
    """Order response model with formatted amounts"""
    subtotal_ngn: float = Field(..., description="Subtotal in NGN")
    shipping_ngn: float = Field(..., description="Shipping in NGN")
    discount_ngn: float = Field(..., description="Discount in NGN")
    total_ngn: float = Field(..., description="Total in NGN")
    
    @field_validator('subtotal_ngn', 'shipping_ngn', 'discount_ngn', 'total_ngn', mode='before')
    @classmethod
    def convert_kobo_to_ngn(cls, v, info):
        if hasattr(info, 'data'):
            data = info.data
            # Get the field name from the validation info
            field_name = info.field_name
            kobo_field = field_name.replace('_ngn', '_kobo')
            if kobo_field in data:
                return data[kobo_field] / 100.0
        return v
"""
Meta Commerce Catalog models and types for WhatsApp Business integration
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

class MetaSyncStatus(str, Enum):
    """Meta catalog sync status enumeration"""
    PENDING = "pending"
    SYNCING = "syncing" 
    SYNCED = "synced"
    ERROR = "error"

class MetaCatalogProduct(BaseModel):
    """Meta catalog product format for Commerce Platform API"""
    retailer_id: str = Field(..., description="Unique product identifier for merchant")
    name: str = Field(..., min_length=1, max_length=150, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    url: str = Field(..., description="Product page URL")
    image_url: str = Field(..., description="Product image URL")
    availability: str = Field(..., description="in stock | out of stock")
    condition: str = Field(default="new", description="Product condition")
    price: str = Field(..., description="Price with currency (e.g., '150.00 NGN')")
    brand: Optional[str] = Field(None, description="Product brand")
    category: Optional[str] = Field(None, description="Product category")
    inventory: Optional[int] = Field(None, ge=0, description="Available inventory count")
    
    @field_validator('availability')
    @classmethod
    def validate_availability(cls, v):
        if v not in ["in stock", "out of stock"]:
            raise ValueError('availability must be "in stock" or "out of stock"')
        return v
    
    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v):
        valid_conditions = ["new", "refurbished", "used"]
        if v not in valid_conditions:
            raise ValueError(f'condition must be one of: {", ".join(valid_conditions)}')
        return v

class MetaCatalogSyncResult(BaseModel):
    """Result of Meta catalog sync operation"""
    success: bool = Field(..., description="Whether sync was successful")
    retailer_id: str = Field(..., description="Product retailer ID")
    meta_product_id: Optional[str] = Field(None, description="Meta's internal product ID")
    errors: Optional[List[str]] = Field(None, description="List of error messages")
    retry_after: Optional[datetime] = Field(None, description="When to retry failed sync")
    sync_duration_ms: Optional[int] = Field(None, description="Sync operation duration")

class CreateProductRequest(BaseModel):
    """Enhanced create product request with Meta catalog support"""
    title: str = Field(..., min_length=1, max_length=200, description="Product title")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    price_kobo: int = Field(..., ge=0, description="Price in kobo (1 NGN = 100 kobo)")
    stock: int = Field(..., ge=0, description="Initial stock quantity")
    sku: str = Field(..., min_length=1, max_length=50, description="Stock keeping unit")
    category_path: Optional[str] = Field(None, description="Category path (e.g., 'skincare/face/creams')")
    tags: Optional[List[str]] = Field(None, description="Product tags")
    meta_catalog_visible: bool = Field(default=True, description="Whether to sync to Meta catalog")
    image_file_id: Optional[str] = Field(None, description="Reference to uploaded image file")
    
    @field_validator('price_kobo')
    @classmethod
    def validate_price_positive(cls, v):
        if v < 0:
            raise ValueError('price_kobo must be non-negative')
        return v
    
    @field_validator('stock')
    @classmethod
    def validate_stock_positive(cls, v):
        if v < 0:
            raise ValueError('stock must be non-negative')
        return v

class UpdateProductRequest(BaseModel):
    """Update product request with partial fields"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Product title")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    price_kobo: Optional[int] = Field(None, ge=0, description="Price in kobo")
    stock: Optional[int] = Field(None, ge=0, description="Stock quantity")
    category_path: Optional[str] = Field(None, description="Category path")
    tags: Optional[List[str]] = Field(None, description="Product tags")
    meta_catalog_visible: Optional[bool] = Field(None, description="Meta catalog visibility")
    status: Optional[str] = Field(None, description="Product status (active/inactive)")
    image_file_id: Optional[str] = Field(None, description="Reference to uploaded image file")
    
    @field_validator('price_kobo')
    @classmethod
    def validate_price_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError('price_kobo must be non-negative')
        return v
    
    @field_validator('stock')
    @classmethod
    def validate_stock_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError('stock must be non-negative')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ["active", "inactive"]:
            raise ValueError('status must be "active" or "inactive"')
        return v

class ProductDB(BaseModel):
    """Enhanced product database model with Meta sync fields"""
    id: UUID
    merchant_id: UUID
    title: str
    description: Optional[str] = None
    price_kobo: int = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    reserved_qty: int = Field(..., ge=0)
    available_qty: int = Field(..., ge=0)
    image_url: Optional[str] = None
    sku: str
    status: str
    retailer_id: str
    category_path: Optional[str] = None
    tags: Optional[List[str]] = None
    meta_catalog_visible: bool = True
    meta_sync_status: MetaSyncStatus = MetaSyncStatus.PENDING
    meta_sync_errors: Optional[List[str]] = None
    meta_last_synced_at: Optional[datetime] = None
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

class IdempotencyKeyDB(BaseModel):
    """Idempotency key database model"""
    id: UUID
    key: str
    merchant_id: UUID
    endpoint: str
    request_hash: str
    response_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MetaCatalogConfig(BaseModel):
    """Meta catalog configuration for merchant"""
    catalog_id: str = Field(..., description="Meta Commerce Catalog ID")
    access_token: str = Field(..., description="Meta Graph API access token")
    app_id: str = Field(..., description="Meta App ID")
    app_secret: str = Field(..., description="Meta App Secret")
    
class MetaCatalogBatchRequest(BaseModel):
    """Batch request for multiple catalog operations"""
    operations: List[Dict[str, Any]] = Field(..., description="List of catalog operations")
    allow_upsert: bool = Field(default=True, description="Allow upsert operations")
    
class MetaCatalogBatchResult(BaseModel):
    """Result of batch catalog operations"""
    success_count: int = Field(..., description="Number of successful operations")
    error_count: int = Field(..., description="Number of failed operations")
    results: List[MetaCatalogSyncResult] = Field(..., description="Individual operation results")
    
class ProductFilters(BaseModel):
    """Product listing filters"""
    status: Optional[str] = Field(None, description="Filter by product status")
    category_path: Optional[str] = Field(None, description="Filter by category")
    meta_sync_status: Optional[MetaSyncStatus] = Field(None, description="Filter by Meta sync status")
    meta_catalog_visible: Optional[bool] = Field(None, description="Filter by Meta catalog visibility")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    
class ProductPagination(BaseModel):
    """Product listing pagination"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default="created_at", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", description="Sort order (asc/desc)")
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v):
        if v not in ["asc", "desc"]:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v

class MetaFeedProduct(BaseModel):
    """Product formatted for Meta CSV feed"""
    id: str = Field(..., description="Retailer ID")
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    availability: str = Field(..., description="in stock | out of stock")
    condition: str = Field(default="new", description="Product condition")
    price: str = Field(..., description="Formatted price (e.g., '150.00 NGN')")
    link: str = Field(..., description="Product URL")
    image_link: str = Field(..., description="Product image URL")
    brand: str = Field(..., description="Brand name")
    inventory: Optional[int] = Field(None, description="Stock quantity")
    product_type: Optional[str] = Field(None, description="Product type/category")
    google_product_category: Optional[str] = Field(None, description="Google product category")

    @field_validator('availability')
    @classmethod
    def validate_availability(cls, v):
        if v not in ["in stock", "out of stock"]:
            raise ValueError('availability must be "in stock" or "out of stock"')
        return v

class MetaFeedResponse(BaseModel):
    """Meta feed CSV response metadata"""
    merchant_slug: str = Field(..., description="Merchant slug")
    product_count: int = Field(..., ge=0, description="Number of products in feed")
    last_updated: datetime = Field(..., description="Latest product update timestamp")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    etag: str = Field(..., description="ETag for caching")
    content_length: int = Field(..., ge=0, description="CSV content size in bytes")

class MetaFeedConfig(BaseModel):
    """Configuration for Meta feed generation"""
    base_url: str = Field(..., description="Base URL for product links")
    cdn_base_url: Optional[str] = Field(None, description="CDN base URL for images")
    brand_name: str = Field(..., description="Default brand name")
    default_category: str = Field(default="Health & Beauty", description="Default product category")
    cache_ttl: int = Field(default=3600, ge=300, le=86400, description="Cache TTL (5min-24h)")
    max_products_per_feed: int = Field(default=50000, ge=1, description="Maximum products per feed")
    
    @field_validator('base_url', 'cdn_base_url')
    @classmethod
    def validate_urls(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URLs must start with http:// or https://')
        return v

class MetaFeedStats(BaseModel):
    """Statistics for Meta feed generation"""
    total_products: int = Field(..., ge=0, description="Total products in merchant catalog")
    visible_products: int = Field(..., ge=0, description="Products visible in Meta catalog")
    in_stock_products: int = Field(..., ge=0, description="Products currently in stock")
    last_sync_at: Optional[datetime] = Field(None, description="Last successful sync timestamp")
    sync_errors: int = Field(default=0, ge=0, description="Number of products with sync errors")
    
    @field_validator('visible_products')
    @classmethod
    def validate_visible_le_total(cls, v, info):
        if hasattr(info, 'data') and 'total_products' in info.data and v > info.data['total_products']:
            raise ValueError('visible_products cannot exceed total_products')
        return v
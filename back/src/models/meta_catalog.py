"""
Meta Commerce Catalog models and types for WhatsApp Business integration
"""

from pydantic import BaseModel, Field, field_validator, validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum
import hashlib
import re


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
    description: Optional[str] = Field(
        None, max_length=1000, description="Product description"
    )
    url: str = Field(..., description="Product page URL")
    image_url: str = Field(..., description="Product image URL")
    availability: str = Field(..., description="in stock | out of stock")
    condition: str = Field(default="new", description="Product condition")
    price: str = Field(..., description="Price with currency (e.g., '150.00 NGN')")
    brand: Optional[str] = Field(None, description="Product brand")
    mpn: Optional[str] = Field(None, description="Manufacturer Part Number")
    category: Optional[str] = Field(None, description="Product category")
    inventory: Optional[int] = Field(
        None, ge=0, description="Available inventory count"
    )

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, v):
        if v not in ["in stock", "out of stock"]:
            raise ValueError('availability must be "in stock" or "out of stock"')
        return v

    @field_validator("condition")
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
    meta_product_id: Optional[str] = Field(
        None, description="Meta's internal product ID"
    )
    errors: Optional[List[str]] = Field(None, description="List of error messages")
    retry_after: Optional[datetime] = Field(
        None, description="When to retry failed sync"
    )
    sync_duration_ms: Optional[int] = Field(None, description="Sync operation duration")


class CreateProductRequest(BaseModel):
    """Enhanced create product request with Meta catalog support"""

    title: str = Field(..., min_length=1, max_length=200, description="Product title")
    description: Optional[str] = Field(
        None, max_length=1000, description="Product description"
    )
    price_kobo: int = Field(..., ge=0, description="Price in kobo (1 NGN = 100 kobo)")
    stock: int = Field(..., ge=0, description="Initial stock quantity")
    sku: str = Field(..., min_length=1, max_length=50, description="Stock keeping unit")
    category_path: Optional[str] = Field(
        None, description="Category path (e.g., 'skincare/face/creams')"
    )
    tags: Optional[List[str]] = Field(None, description="Product tags")
    meta_catalog_visible: bool = Field(
        default=True, description="Whether to sync to Meta catalog"
    )
    image_file_id: Optional[str] = Field(
        None, description="Reference to uploaded image file"
    )

    @field_validator("price_kobo")
    @classmethod
    def validate_price_positive(cls, v):
        if v < 0:
            raise ValueError("price_kobo must be non-negative")
        return v

    @field_validator("stock")
    @classmethod
    def validate_stock_positive(cls, v):
        if v < 0:
            raise ValueError("stock must be non-negative")
        return v


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
    category_path: Optional[str] = Field(None, description="Category path")
    tags: Optional[List[str]] = Field(None, description="Product tags")
    meta_catalog_visible: Optional[bool] = Field(
        None, description="Meta catalog visibility"
    )
    status: Optional[str] = Field(None, description="Product status (active/inactive)")
    image_file_id: Optional[str] = Field(
        None, description="Reference to uploaded image file"
    )

    @field_validator("price_kobo")
    @classmethod
    def validate_price_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("price_kobo must be non-negative")
        return v

    @field_validator("stock")
    @classmethod
    def validate_stock_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("stock must be non-negative")
        return v

    @field_validator("status")
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
    brand: str
    mpn: str
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

    @field_validator("reserved_qty")
    @classmethod
    def validate_reserved_qty(cls, v, info):
        if hasattr(info, "data") and "stock" in info.data and v > info.data["stock"]:
            raise ValueError("reserved_qty cannot exceed stock")
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

    operations: List[Dict[str, Any]] = Field(
        ..., description="List of catalog operations"
    )
    allow_upsert: bool = Field(default=True, description="Allow upsert operations")


class MetaCatalogBatchResult(BaseModel):
    """Result of batch catalog operations"""

    success_count: int = Field(..., description="Number of successful operations")
    error_count: int = Field(..., description="Number of failed operations")
    results: List[MetaCatalogSyncResult] = Field(
        ..., description="Individual operation results"
    )


class ProductFilters(BaseModel):
    """Product listing filters"""

    status: Optional[str] = Field(None, description="Filter by product status")
    category_path: Optional[str] = Field(None, description="Filter by category")
    meta_sync_status: Optional[MetaSyncStatus] = Field(
        None, description="Filter by Meta sync status"
    )
    meta_catalog_visible: Optional[bool] = Field(
        None, description="Filter by Meta catalog visibility"
    )
    tags: Optional[List[str]] = Field(None, description="Filter by tags")


class ProductPagination(BaseModel):
    """Product listing pagination"""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default="created_at", description="Sort field")
    sort_order: Optional[str] = Field(
        default="desc", description="Sort order (asc/desc)"
    )

    @field_validator("sort_order")
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
    google_product_category: Optional[str] = Field(
        None, description="Google product category"
    )

    @field_validator("availability")
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
    default_category: str = Field(
        default="Health & Beauty", description="Default product category"
    )
    cache_ttl: int = Field(
        default=3600, ge=300, le=86400, description="Cache TTL (5min-24h)"
    )
    max_products_per_feed: int = Field(
        default=50000, ge=1, description="Maximum products per feed"
    )

    @field_validator("base_url", "cdn_base_url")
    @classmethod
    def validate_urls(cls, v):
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("URLs must start with http:// or https://")
        return v


class MetaFeedStats(BaseModel):
    """Statistics for Meta feed generation"""

    total_products: int = Field(
        ..., ge=0, description="Total products in merchant catalog"
    )
    visible_products: int = Field(
        ..., ge=0, description="Products visible in Meta catalog"
    )
    in_stock_products: int = Field(..., ge=0, description="Products currently in stock")
    last_sync_at: Optional[datetime] = Field(
        None, description="Last successful sync timestamp"
    )
    sync_errors: int = Field(
        default=0, ge=0, description="Number of products with sync errors"
    )

    @field_validator("visible_products")
    @classmethod
    def validate_visible_le_total(cls, v, info):
        if (
            hasattr(info, "data")
            and "total_products" in info.data
            and v > info.data["total_products"]
        ):
            raise ValueError("visible_products cannot exceed total_products")
        return v


# =============================================================================
# BE-016.1: Meta Catalog Sync Models
# =============================================================================


class CatalogSyncAction(str, Enum):
    """Types of catalog sync actions"""

    CREATE = "create"
    UPDATE = "update"
    UPDATE_IMAGE = "update_image"
    DELETE = "delete"


class CatalogSyncStatus(str, Enum):
    """Catalog sync processing status"""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


class CatalogSyncTrigger(str, Enum):
    """What triggered the catalog sync event"""

    IMAGE_UPLOAD = "image_upload"
    PRIMARY_CHANGE = "primary_change"
    WEBHOOK_UPDATE = "webhook_update"


class MetaCatalogSyncPayload(BaseModel):
    """Payload for catalog_sync outbox jobs"""

    action: CatalogSyncAction
    product_id: UUID
    retailer_id: str
    meta_catalog_id: str
    changes: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str
    triggered_by: CatalogSyncTrigger

    @field_validator("retailer_id")
    @classmethod
    def validate_retailer_id(cls, v):
        """Validate retailer_id format"""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "retailer_id must contain only alphanumeric characters, underscores, and hyphens"
            )
        return v

    @field_validator("meta_catalog_id")
    @classmethod
    def validate_catalog_id(cls, v):
        """Validate catalog ID format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("meta_catalog_id cannot be empty")
        return v.strip()

    @classmethod
    def generate_idempotency_key(
        cls, product_id: UUID, action: CatalogSyncAction, content: Dict[str, Any]
    ) -> str:
        """Generate idempotency key for deduplication"""
        # Create deterministic hash from content
        content_str = str(sorted(content.items()))
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]

        return f"{product_id}:{action.value}:{content_hash}"

    def normalize_legacy_shape(self) -> "MetaCatalogSyncPayload":
        """Convert legacy event shapes to canonical format"""
        # Check for legacy field names and normalize
        if "image_url" in self.changes and "primary_image_url" not in self.changes:
            # Legacy shape: {"image_url": "..."} → {"primary_image_url": "..."}
            self.changes["primary_image_url"] = self.changes.pop("image_url")

        if "image_urls" in self.changes and "additional_image_urls" not in self.changes:
            # Legacy shape: {"image_urls": [...]} → {"additional_image_urls": [...]}
            self.changes["additional_image_urls"] = self.changes.pop("image_urls")

        return self


class MetaCatalogImageUpdate(BaseModel):
    """Image update data for Meta Catalog API"""

    image_url: str = Field(..., description="Primary product image URL (main preset)")
    additional_image_urls: Optional[List[str]] = Field(
        [], description="Additional product image URLs"
    )

    @field_validator("image_url")
    @classmethod
    def validate_primary_image_url(cls, v):
        """Validate primary image URL format"""
        # Must be Cloudinary URL with main preset transformation
        pattern = r"^https://res\.cloudinary\.com/[^/]+/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:(good|best)/.*$"
        if not re.match(pattern, v):
            raise ValueError("Primary image URL must be Cloudinary main preset URL")
        return v

    @field_validator("additional_image_urls")
    @classmethod
    def validate_additional_image_urls(cls, v):
        """Validate additional image URLs"""
        if not v:
            return []

        for url in v:
            if not url.startswith("https://res.cloudinary.com/"):
                raise ValueError("All image URLs must be from Cloudinary")

        return v


class MetaCatalogSyncResult(BaseModel):
    """Result of catalog sync operation for images"""

    success: bool
    meta_product_id: Optional[str] = None
    errors: Optional[List[str]] = None
    retry_after: Optional[datetime] = None
    rate_limited: bool = False
    idempotency_key: str
    duration_ms: Optional[int] = None

    @property
    def should_retry(self) -> bool:
        """Determine if the operation should be retried"""
        if self.success:
            return False

        # Rate limited requests should always retry
        if self.rate_limited:
            return True

        # Check for retryable error types
        if self.errors:
            retryable_patterns = [
                "temporarily unavailable",
                "timeout",
                "connection",
                "network",
                "rate limit",
                "internal server error",
                "500",
                "502",
                "503",
                "504",
            ]
            error_text = " ".join(self.errors).lower()
            return any(pattern in error_text for pattern in retryable_patterns)

        return True


class MetaCatalogSyncLogEntry(BaseModel):
    """Catalog sync log entry for tracking"""

    id: UUID
    merchant_id: UUID
    product_id: UUID
    outbox_job_id: Optional[UUID]
    action: CatalogSyncAction
    retailer_id: str
    catalog_id: str
    status: CatalogSyncStatus
    request_payload: Optional[Dict[str, Any]]
    response_data: Optional[Dict[str, Any]]
    error_details: Optional[Dict[str, Any]]
    retry_count: int = 0
    next_retry_at: Optional[datetime]
    idempotency_key: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MetaCatalogBatchImageRequest(BaseModel):
    """Meta Graph API batch request format for image updates"""

    requests: List[Dict[str, Any]]

    @classmethod
    def create_image_update_request(
        cls, retailer_id: str, image_data: MetaCatalogImageUpdate
    ) -> "MetaCatalogBatchImageRequest":
        """Create batch request for image update"""
        request_data = {
            "method": "UPDATE",
            "retailer_id": retailer_id,
            "data": {"image_url": image_data.image_url},
        }

        # Add additional images if present
        if image_data.additional_image_urls:
            request_data["data"][
                "additional_image_urls"
            ] = image_data.additional_image_urls

        return cls(requests=[request_data])


class MetaCatalogBatchImageResponse(BaseModel):
    """Meta Graph API batch response format for image updates"""

    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[Dict[str, Any]] = None

    @property
    def is_success(self) -> bool:
        """Check if the batch response indicates success"""
        return self.error is None and self.data is not None

    @property
    def is_rate_limited(self) -> bool:
        """Check if the response indicates rate limiting"""
        if self.error and "code" in self.error:
            # Meta API rate limit error codes
            rate_limit_codes = [4, 17, 613, 80004]
            return self.error["code"] in rate_limit_codes
        return False


class LegacyEventNormalization(BaseModel):
    """Tracking for legacy event shape normalization"""

    merchant_id: UUID
    product_id: UUID
    legacy_shape: str
    canonical_shape: str
    producer_hint: Optional[str] = None
    normalized_at: datetime = Field(
        default_factory=lambda: datetime.now(datetime.timezone.utc)
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class IdempotencyCheck(BaseModel):
    """Idempotency validation result"""

    is_duplicate: bool
    existing_sync_id: Optional[UUID] = None
    ttl_hours: int = 24
    key_generated_at: Optional[datetime] = None

    @property
    def should_skip(self) -> bool:
        """Determine if the request should be skipped due to idempotency"""
        return self.is_duplicate and self.existing_sync_id is not None


class CatalogSyncMetrics(BaseModel):
    """Metrics for catalog sync operations"""

    triggered_total: int = 0
    success_total: int = 0
    failed_total: int = 0
    rate_limited_total: int = 0
    legacy_normalized_total: int = 0
    average_duration_ms: Optional[float] = None
    active_jobs: int = 0
    backlog_size: int = 0

    def record_success(self, duration_ms: int):
        """Record a successful sync operation"""
        self.success_total += 1
        if self.average_duration_ms is None:
            self.average_duration_ms = duration_ms
        else:
            # Simple moving average
            self.average_duration_ms = (self.average_duration_ms + duration_ms) / 2

    def record_failure(self):
        """Record a failed sync operation"""
        self.failed_total += 1

    def record_rate_limit(self):
        """Record a rate-limited sync operation"""
        self.rate_limited_total += 1

    def record_legacy_normalization(self):
        """Record a legacy event normalization"""
        self.legacy_normalized_total += 1

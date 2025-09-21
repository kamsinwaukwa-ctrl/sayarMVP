"""
Pydantic models for Meta Catalog reconciliation operations
"""

from typing import List, Optional, Dict, Any, TypedDict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid

# SQLAlchemy base
Base = declarative_base()


class MetaItem(TypedDict):
    """Meta API item structure for reconciliation"""
    price: Optional[str]
    availability: Optional[str]
    title: Optional[str]
    image_link: Optional[str]


class ReconciliationRunType(str, Enum):
    """Type of reconciliation run"""
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class ReconciliationStatus(str, Enum):
    """Status of reconciliation run"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DriftAction(str, Enum):
    """Action taken when drift is detected"""
    SYNC_TRIGGERED = "sync_triggered"
    SKIPPED = "skipped"
    FAILED = "failed"


class ProductFieldDrift(BaseModel):
    """Represents drift detected in a product field"""
    field_name: str = Field(..., description="Name of the field with drift")
    local_value: Optional[str] = Field(None, description="Value in local database")
    meta_value: Optional[str] = Field(None, description="Value in Meta Catalog")
    action_taken: DriftAction = Field(..., description="Action taken for this drift")


class ProductReconciliationResult(BaseModel):
    """Result of reconciling a single product"""
    product_id: UUID = Field(..., description="Product ID that was reconciled")
    retailer_id: str = Field(..., description="Meta retailer ID for this product")
    has_drift: bool = Field(False, description="Whether any drift was detected")
    drift_fields: List[ProductFieldDrift] = Field(default_factory=list, description="List of fields with drift")
    sync_triggered: bool = Field(False, description="Whether a re-sync job was triggered")
    error: Optional[str] = Field(None, description="Error message if reconciliation failed")


class ReconciliationRunStats(BaseModel):
    """Statistics for a reconciliation run"""
    products_total: int = Field(0, description="Total products eligible for reconciliation")
    products_checked: int = Field(0, description="Number of products actually checked")
    drift_detected: int = Field(0, description="Number of products with detected drift")
    syncs_triggered: int = Field(0, description="Number of re-sync jobs triggered")
    errors_count: int = Field(0, description="Number of products that had reconciliation errors")
    duration_ms: Optional[int] = Field(None, description="Total reconciliation duration in milliseconds")


class ReconciliationRun(BaseModel):
    """Complete reconciliation run information"""
    id: UUID = Field(..., description="Unique reconciliation run ID")
    merchant_id: UUID = Field(..., description="Merchant this run belongs to")
    run_type: ReconciliationRunType = Field(..., description="Type of reconciliation run")
    status: ReconciliationStatus = Field(..., description="Current status of the run")
    stats: ReconciliationRunStats = Field(..., description="Run statistics")
    started_at: datetime = Field(..., description="When the run started")
    completed_at: Optional[datetime] = Field(None, description="When the run completed")
    last_error: Optional[str] = Field(None, description="Last error encountered")

    class Config:
        from_attributes = True


class ReconciliationStatusResponse(BaseModel):
    """Response for reconciliation status endpoint"""
    last_run_at: Optional[datetime] = Field(None, description="When the last run started")
    status: Optional[ReconciliationStatus] = Field(None, description="Status of the last run")
    stats: Optional[ReconciliationRunStats] = Field(None, description="Statistics from the last run")


class ReconciliationHistoryResponse(BaseModel):
    """Response for reconciliation history endpoint"""
    runs: List[ReconciliationRun] = Field(..., description="List of reconciliation runs")
    total: int = Field(..., description="Total number of runs")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")


class TriggerReconciliationResponse(BaseModel):
    """Response for manual reconciliation trigger"""
    job_id: UUID = Field(..., description="ID of the triggered reconciliation job")
    scheduled_at: datetime = Field(..., description="When the reconciliation was scheduled to run")


class MerchantReconciliationStatusResponse(BaseModel):
    """Response for merchant-specific reconciliation status"""
    last_run_at: Optional[datetime] = Field(None, description="When the last run started for this merchant")
    products_checked: int = Field(0, description="Number of products checked in last run")
    drift_detected: int = Field(0, description="Number of products with drift in last run")
    sync_pending: int = Field(0, description="Number of sync jobs currently pending")


# SQLAlchemy Models
class MetaReconciliationRun(Base):
    """SQLAlchemy model for reconciliation runs"""
    __tablename__ = "meta_reconciliation_runs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(PostgresUUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    run_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="running")

    # Metrics
    products_total = Column(Integer, nullable=False, default=0)
    products_checked = Column(Integer, nullable=False, default=0)
    drift_detected = Column(Integer, nullable=False, default=0)
    syncs_triggered = Column(Integer, nullable=False, default=0)
    errors_count = Column(Integer, nullable=False, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)

    # Error tracking
    last_error = Column(Text)
    meta_api_errors = Column(JSONB, default=list)

    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class MetaDriftLog(Base):
    """SQLAlchemy model for drift detection logs"""
    __tablename__ = "meta_drift_log"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_run_id = Column(PostgresUUID(as_uuid=True), ForeignKey("meta_reconciliation_runs.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(PostgresUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    merchant_id = Column(PostgresUUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)

    field_name = Column(String(50), nullable=False)
    local_value = Column(Text)
    meta_value = Column(Text)
    action_taken = Column(String(20))

    created_at = Column(DateTime(timezone=True), nullable=False)


# Helper functions for field normalization
def format_price(price_kobo: int, currency: str = "NGN") -> str:
    """Format price from kobo to Meta API format"""
    price_major = price_kobo / 100
    return f"{price_major:.2f} {currency}"


def format_availability(stock: int) -> str:
    """Format stock to Meta availability format"""
    return "out of stock" if stock == 0 else "in stock"


def normalize_image_url(cloudinary_url: str) -> str:
    """Extract canonical Cloudinary URL for comparison"""
    if not cloudinary_url:
        return ""

    # Extract base URL without transformation parameters
    # Format: https://res.cloudinary.com/cloud/image/upload/v123456/path.jpg
    if "/upload/" in cloudinary_url:
        parts = cloudinary_url.split("/upload/")
        if len(parts) == 2:
            base_url = parts[0] + "/upload/"
            # Remove version and transformations, keep just the path
            path_part = parts[1]
            if "/" in path_part:
                # Skip version and transformations to get actual path
                path_segments = path_part.split("/")
                # Find the segment that looks like a path (contains sayar/products)
                for i, segment in enumerate(path_segments):
                    if "sayar" in segment or "products" in segment:
                        canonical_path = "/".join(path_segments[i:])
                        return base_url + canonical_path

    return cloudinary_url


def get_items_by_retailer_ids(catalog_id: str, retailer_ids: List[str]) -> Dict[str, MetaItem]:
    """
    Mock function signature for Meta API integration.
    In actual implementation, this would call the Meta Graph API.
    """
    # This is implemented in the service layer
    raise NotImplementedError("This function is implemented in meta_reconciliation_service.py")
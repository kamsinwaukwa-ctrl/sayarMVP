"""
SQLAlchemy models for Sayar WhatsApp Commerce Platform database schema
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Enum,
    JSON,
    UniqueConstraint,
    BigInteger,
    DECIMAL,
)
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()


class Merchant(Base):
    """Merchant SQLAlchemy model"""

    __tablename__ = "merchants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True)
    whatsapp_phone_e164 = Column(String)
    logo_url = Column(String)
    description = Column(String)
    currency = Column(String, default="NGN")


    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    """User SQLAlchemy model"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Product(Base):
    """Product SQLAlchemy model"""

    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    price_kobo = Column(Integer, nullable=False)
    stock = Column(Integer, nullable=False)
    reserved_qty = Column(Integer, default=0)
    available_qty = Column(Integer)
    image_url = Column(String)
    sku = Column(String)
    brand = Column(String)
    mpn = Column(String)
    status = Column(String, default="active")
    retailer_id = Column(String, unique=True, nullable=False)
    category_path = Column(String)
    tags = Column(JSON)
    meta_catalog_visible = Column(Boolean, default=True, nullable=False)
    meta_sync_status = Column(String, default="pending")
    meta_sync_errors = Column(JSON)
    meta_last_synced_at = Column(DateTime)
    meta_image_sync_version = Column(Integer, default=0)
    meta_last_image_sync_at = Column(DateTime)
    primary_image_id = Column(UUID(as_uuid=True), ForeignKey("product_images.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductImage(Base):
    """Product image SQLAlchemy model"""

    __tablename__ = "product_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    cloudinary_public_id = Column(String, nullable=False, unique=True)
    secure_url = Column(String, nullable=False)
    thumbnail_url = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    format = Column(String)
    bytes = Column(Integer)
    is_primary = Column(Boolean, nullable=False, default=False)
    alt_text = Column(String)
    upload_status = Column(String, nullable=False, default="uploading")
    cloudinary_version = Column(BigInteger)
    # New preset-related columns
    preset_profile = Column(String, default="standard")
    variants = Column(JSON, default=dict)
    optimization_stats = Column(JSON, default=dict)
    preset_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CloudinaryPresetStats(Base):
    """Cloudinary preset performance statistics"""

    __tablename__ = "cloudinary_preset_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    preset_id = Column(String, nullable=False)
    usage_count = Column(Integer, default=0)
    avg_file_size_kb = Column(Integer)
    avg_processing_time_ms = Column(Integer)
    quality_score_avg = Column(DECIMAL(3, 1))
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("merchant_id", "preset_id", name="uq_merchant_preset"),
    )


class Customer(Base):
    """Customer SQLAlchemy model"""

    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    phone_e164 = Column(String, nullable=False)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Address(Base):
    """Address SQLAlchemy model"""

    __tablename__ = "addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    label = Column(String)
    line1 = Column(String, nullable=False)
    lga = Column(String)
    city = Column(String)
    state = Column(String)
    country = Column(String, default="NG")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    """Order SQLAlchemy model"""

    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"))
    subtotal_kobo = Column(Integer, nullable=False)
    shipping_kobo = Column(Integer, nullable=False)
    discount_kobo = Column(Integer, nullable=False)
    total_kobo = Column(Integer, nullable=False)
    status = Column(String, default="pending")
    payment_provider = Column(String)
    provider_reference = Column(String)
    order_code = Column(String, unique=True, nullable=False)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Discount(Base):
    """Discount SQLAlchemy model"""

    __tablename__ = "discounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    code = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)  # "percent" or "fixed"
    value_bp = Column(Integer)  # basis points for percent discounts
    amount_kobo = Column(Integer)  # kobo amount for fixed discounts
    max_discount_kobo = Column(Integer)
    min_subtotal_kobo = Column(Integer, default=0)
    starts_at = Column(DateTime)
    expires_at = Column(DateTime)
    usage_limit_total = Column(Integer)
    usage_limit_per_customer = Column(Integer)
    times_redeemed = Column(Integer, default=0)
    status = Column(String, default="active")
    stackable = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OutboxJob(Base):
    """Outbox job SQLAlchemy model"""

    __tablename__ = "outbox_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    job_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    next_run_at = Column(DateTime, default=datetime.utcnow)
    last_error = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemSetting(Base):
    """System setting SQLAlchemy model"""

    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MerchantSetting(Base):
    """Merchant setting SQLAlchemy model"""

    __tablename__ = "merchant_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    key = Column(String, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add composite unique constraint for merchant_id + key
    __table_args__ = ({"extend_existing": True},)


class DeliveryRate(Base):
    """Delivery rate SQLAlchemy model"""

    __tablename__ = "delivery_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    name = Column(String, nullable=False)
    areas_text = Column(String, nullable=False)
    price_kobo = Column(Integer, nullable=False)
    description = Column(String)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FeatureFlag(Base):
    """Feature flag SQLAlchemy model"""

    __tablename__ = "feature_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    enabled = Column(Boolean, default=False, nullable=False)
    merchant_id = Column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=True
    )  # NULL for global flags
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add composite unique constraint for name + merchant_id
    __table_args__ = ({"extend_existing": True},)


class PaymentProviderConfig(Base):
    """Payment provider configuration SQLAlchemy model"""

    __tablename__ = "payment_provider_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    provider_type = Column(String, nullable=False)  # 'paystack' or 'korapay'
    public_key_encrypted = Column(String, nullable=False)
    secret_key_encrypted = Column(String, nullable=False)
    webhook_secret_encrypted = Column(String)  # Optional for some providers
    environment = Column(String, nullable=False, default="test")  # 'test' or 'live'
    verification_status = Column(
        String, nullable=False, default="pending"
    )  # 'pending', 'verified', 'failed'
    last_verified_at = Column(DateTime)
    verification_error = Column(String)  # Store error messages
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add unique constraint for merchant + provider + environment
    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "provider_type",
            "environment",
            name="uq_payment_provider_config_scope",
        ),
        {"extend_existing": True},
    )


class MetaCatalogSyncLog(Base):
    """Meta catalog synchronization log SQLAlchemy model"""

    __tablename__ = "meta_catalog_sync_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    outbox_job_id = Column(
        UUID(as_uuid=True), ForeignKey("outbox_events.id"), nullable=True
    )
    action = Column(String, nullable=False)
    retailer_id = Column(String, nullable=False)
    catalog_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    request_payload = Column(JSON)
    response_data = Column(JSON)
    error_details = Column(JSON)
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime)
    idempotency_key = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

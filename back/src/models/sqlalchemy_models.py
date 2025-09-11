"""
SQLAlchemy models for Sayar WhatsApp Commerce Platform database schema
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, JSON
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
    status = Column(String, default="active")
    retailer_id = Column(String, unique=True, nullable=False)
    category_path = Column(String)
    tags = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    __table_args__ = (
        {'extend_existing': True},
    )

class FeatureFlag(Base):
    """Feature flag SQLAlchemy model"""
    __tablename__ = "feature_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    enabled = Column(Boolean, default=False, nullable=False)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=True)  # NULL for global flags
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add composite unique constraint for name + merchant_id
    __table_args__ = (
        {'extend_existing': True},
    )
-- Sayar WhatsApp Commerce Platform - Initial Database Schema
-- Migration: 001_initial_schema.sql
-- Description: Creates core tables with UUIDs, kobo money fields, and RLS policies

-- Enable UUID generation and crypto functions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Core tenant table
CREATE TABLE merchants (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text unique,
    whatsapp_phone_e164 text unique,
    logo_url text,
    description text,
    currency text not null default 'NGN',
    waba_id text,
    phone_number_id text,
    meta_app_id text,
    meta_system_user_token_enc bytea,
    provider_default text check (provider_default in ('paystack', 'korapay')),
    paystack_sk_enc bytea,
    paystack_pk_enc bytea,
    korapay_sk_enc bytea,
    korapay_pk_enc bytea,
    payments_verified_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Users (owners and staff)
CREATE TABLE users (
    id uuid primary key default gen_random_uuid(),
    merchant_id uuid not null references merchants(id) on delete cascade,
    name text not null,
    email text not null,
    password_hash text,
    role text not null check (role in ('owner', 'staff')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(email)
);

-- Products
CREATE TABLE products (
    id uuid primary key default gen_random_uuid(),
    merchant_id uuid not null references merchants(id) on delete cascade,
    title text not null,
    description text,
    price_kobo bigint not null check (price_kobo >= 0),
    stock int not null default 0 check (stock >= 0),
    reserved_qty int not null default 0 check (reserved_qty >= 0 and reserved_qty <= stock),
    available_qty int generated always as (greatest(stock - reserved_qty, 0)) stored,
    image_url text,
    sku text,
    status text not null default 'active' check (status in ('active', 'inactive')),
    catalog_id text,
    retailer_id text not null,
    category_path text,
    tags text[],
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(merchant_id, sku),
    unique(merchant_id, retailer_id)
);

-- Customers
CREATE TABLE customers (
    id uuid primary key default gen_random_uuid(),
    merchant_id uuid not null references merchants(id) on delete cascade,
    phone_e164 text not null,
    name text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(merchant_id, phone_e164)
);

-- Customer addresses
CREATE TABLE addresses (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid not null references customers(id) on delete cascade,
    label text,
    line1 text not null,
    lga text,
    city text,
    state text,
    country text not null default 'NG',
    is_default boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Delivery rates
CREATE TABLE delivery_rates (
    id uuid primary key default gen_random_uuid(),
    merchant_id uuid not null references merchants(id) on delete cascade,
    name text not null,
    areas_text text not null,
    price_kobo bigint not null check (price_kobo >= 0),
    description text,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Orders
CREATE TABLE orders (
    id uuid primary key default gen_random_uuid(),
    merchant_id uuid not null references merchants(id) on delete cascade,
    customer_id uuid references customers(id) on delete set null,
    subtotal_kobo bigint not null check (subtotal_kobo >= 0),
    shipping_kobo bigint not null default 0 check (shipping_kobo >= 0),
    discount_kobo bigint not null default 0 check (discount_kobo >= 0),
    total_kobo bigint not null check (total_kobo >= 0),
    status text not null default 'pending' check (status in ('pending', 'paid', 'failed', 'cancelled')),
    payment_provider text,
    provider_reference text,
    order_code text unique not null,
    paid_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (total_kobo = subtotal_kobo + shipping_kobo - discount_kobo),
    unique(payment_provider, provider_reference)
);

-- Order items
CREATE TABLE order_items (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id) on delete cascade,
    product_id uuid not null references products(id) restrict,
    qty int not null check (qty > 0),
    unit_price_kobo bigint not null check (unit_price_kobo >= 0),
    total_kobo bigint not null check (total_kobo >= 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (total_kobo = qty * unit_price_kobo)
);

-- Discounts/Coupons
CREATE TABLE discounts (
    id uuid primary key default gen_random_uuid(),
    merchant_id uuid not null references merchants(id) on delete cascade,
    code text not null,
    type text not null check (type in ('percent', 'fixed')),
    value_bp int check (value_bp >= 0 and value_bp <= 10000), -- basis points for percentage
    amount_kobo bigint check (amount_kobo >= 0), -- fixed amount
    max_discount_kobo bigint check (max_discount_kobo >= 0), -- cap for percentage discounts
    min_subtotal_kobo bigint not null default 0 check (min_subtotal_kobo >= 0),
    starts_at timestamptz,
    expires_at timestamptz,
    usage_limit_total int,
    usage_limit_per_customer int,
    times_redeemed int not null default 0,
    status text not null default 'active' check (status in ('active', 'paused', 'expired')),
    stackable boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(merchant_id, code),
    check ((type = 'percent' and value_bp is not null and amount_kobo is null) or 
           (type = 'fixed' and amount_kobo is not null and value_bp is null))
);

-- Payments tracking
CREATE TABLE payments (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id) on delete cascade,
    provider text not null check (provider in ('paystack', 'korapay')),
    reference text not null,
    status text not null default 'pending' check (status in ('pending', 'success', 'failed')),
    amount_kobo bigint not null check (amount_kobo >= 0),
    fee_kobo bigint not null default 0 check (fee_kobo >= 0),
    currency text not null default 'NGN',
    raw jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(provider, reference)
);

-- Inventory reservations for checkout flow
CREATE TABLE inventory_reservations (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id) on delete cascade,
    product_id uuid not null references products(id) on delete restrict,
    qty int not null check (qty > 0),
    expires_at timestamptz not null,
    status text not null default 'active' check (status in ('active', 'consumed', 'released')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(order_id, product_id)
);

-- Inventory ledger for audit trail
CREATE TABLE inventory_ledger (
    id uuid primary key default gen_random_uuid(),
    product_id uuid not null references products(id) on delete restrict,
    delta int not null,
    reason text not null check (reason in ('sale', 'release', 'manual')),
    ref_id text,
    created_at timestamptz not null default now()
);

-- Coupon redemption tracking
CREATE TABLE coupon_redemptions (
    id uuid primary key default gen_random_uuid(),
    discount_id uuid not null references discounts(id) on delete cascade,
    order_id uuid not null references orders(id) on delete cascade,
    customer_id uuid references customers(id) on delete set null,
    discount_kobo bigint not null check (discount_kobo >= 0),
    redeemed_at timestamptz not null default now()
);

-- Dead Letter Queue for failed jobs
CREATE TABLE dlq_events (
    id uuid primary key default gen_random_uuid(),
    source text not null,
    key text not null,
    reason text not null,
    payload jsonb not null,
    created_at timestamptz not null default now()
);

-- Outbox for reliable job processing
CREATE TABLE outbox_events (
    id uuid primary key default gen_random_uuid(),
    merchant_id uuid references merchants(id) on delete cascade,
    job_type text not null check (job_type in ('wa_send', 'catalog_sync', 'release_reservation', 'payment_followup')),
    payload jsonb not null,
    status text not null default 'pending' check (status in ('pending', 'processing', 'done', 'error')),
    attempts int not null default 0,
    max_attempts int not null default 8,
    next_run_at timestamptz not null default now(),
    last_error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Webhook events for idempotency
CREATE TABLE webhook_events (
    id uuid primary key default gen_random_uuid(),
    source text not null check (source in ('wa', 'paystack', 'korapay', 'flows')),
    event_key text unique not null,
    status text not null default 'received' check (status in ('received', 'processed', 'failed')),
    raw jsonb not null,
    received_at timestamptz not null default now(),
    processed_at timestamptz
);

-- Performance indexes
CREATE INDEX idx_products_merchant_active ON products(merchant_id) WHERE status = 'active';
CREATE INDEX idx_orders_merchant_status ON orders(merchant_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_order_items_unique_line ON order_items(order_id, product_id);
CREATE INDEX idx_outbox_pending ON outbox_events(status, next_run_at) WHERE status = 'pending';
CREATE INDEX idx_webhook_source_key ON webhook_events(source, event_key);
CREATE INDEX idx_payments_provider_reference ON payments(provider, reference);
CREATE INDEX idx_inventory_reservations_active ON inventory_reservations(status, expires_at) WHERE status = 'active';
CREATE INDEX idx_inventory_ledger_product ON inventory_ledger(product_id, created_at DESC);
CREATE INDEX idx_discounts_merchant_active ON discounts(merchant_id) WHERE status = 'active';
CREATE INDEX idx_coupon_redemptions_discount ON coupon_redemptions(discount_id);
CREATE INDEX idx_coupon_redemptions_customer ON coupon_redemptions(customer_id, redeemed_at DESC);

-- Partial unique constraint for default addresses
CREATE UNIQUE INDEX idx_addresses_customer_default ON addresses(customer_id) WHERE is_default = true;

-- Enable RLS on all tenant tables
ALTER TABLE merchants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE discounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE coupon_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;

-- Standardized RLS policies using JWT merchant_id claim
-- Merchants can access their own data
CREATE POLICY tenant_isolation_merchants ON merchants
    FOR ALL USING ((auth.jwt() ->> 'merchant_id')::uuid = id);

-- Users can access their merchant's data
CREATE POLICY tenant_isolation_users ON users
    FOR ALL USING ((auth.jwt() ->> 'merchant_id')::uuid = merchant_id);

-- Products belong to merchants
CREATE POLICY tenant_isolation_products ON products
    FOR ALL USING ((auth.jwt() ->> 'merchant_id')::uuid = merchant_id);

-- Customers belong to merchants
CREATE POLICY tenant_isolation_customers ON customers
    FOR ALL USING ((auth.jwt() ->> 'merchant_id')::uuid = merchant_id);

-- Addresses through customer relationship
CREATE POLICY tenant_isolation_addresses ON addresses
    FOR ALL USING (customer_id IN (
        SELECT c.id FROM customers c 
        WHERE (auth.jwt() ->> 'merchant_id')::uuid = c.merchant_id
    ));

-- Delivery rates belong to merchants
CREATE POLICY tenant_isolation_delivery_rates ON delivery_rates
    FOR ALL USING ((auth.jwt() ->> 'merchant_id')::uuid = merchant_id);

-- Orders belong to merchants
CREATE POLICY tenant_isolation_orders ON orders
    FOR ALL USING ((auth.jwt() ->> 'merchant_id')::uuid = merchant_id);

-- Order items through order relationship
CREATE POLICY tenant_isolation_order_items ON order_items
    FOR ALL USING (order_id IN (
        SELECT o.id FROM orders o 
        WHERE (auth.jwt() ->> 'merchant_id')::uuid = o.merchant_id
    ));

-- Payments through order relationship
CREATE POLICY tenant_isolation_payments ON payments
    FOR ALL USING (order_id IN (
        SELECT o.id FROM orders o 
        WHERE (auth.jwt() ->> 'merchant_id')::uuid = o.merchant_id
    ));

-- Inventory reservations through order relationship
CREATE POLICY tenant_isolation_inventory_reservations ON inventory_reservations
    FOR ALL USING (order_id IN (
        SELECT o.id FROM orders o 
        WHERE (auth.jwt() ->> 'merchant_id')::uuid = o.merchant_id
    ));

-- Inventory ledger through product relationship
CREATE POLICY tenant_isolation_inventory_ledger ON inventory_ledger
    FOR ALL USING (product_id IN (
        SELECT p.id FROM products p 
        WHERE (auth.jwt() ->> 'merchant_id')::uuid = p.merchant_id
    ));

-- Discounts belong to merchants
CREATE POLICY tenant_isolation_discounts ON discounts
    FOR ALL USING ((auth.jwt() ->> 'merchant_id')::uuid = merchant_id);

-- Coupon redemptions through discount relationship
CREATE POLICY tenant_isolation_coupon_redemptions ON coupon_redemptions
    FOR ALL USING (discount_id IN (
        SELECT d.id FROM discounts d 
        WHERE (auth.jwt() ->> 'merchant_id')::uuid = d.merchant_id
    ));

-- Outbox events belong to merchants
CREATE POLICY tenant_isolation_outbox ON outbox_events
    FOR ALL USING ((auth.jwt() ->> 'merchant_id')::uuid = merchant_id);

-- Function to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all tables with updated_at
CREATE TRIGGER update_merchants_updated_at BEFORE UPDATE ON merchants 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_addresses_updated_at BEFORE UPDATE ON addresses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_delivery_rates_updated_at BEFORE UPDATE ON delivery_rates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_order_items_updated_at BEFORE UPDATE ON order_items 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_inventory_reservations_updated_at BEFORE UPDATE ON inventory_reservations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_discounts_updated_at BEFORE UPDATE ON discounts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_outbox_events_updated_at BEFORE UPDATE ON outbox_events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert a test merchant for initial setup
INSERT INTO merchants (name, whatsapp_phone_e164, currency) 
VALUES ('Test Merchant', '+2341234567890', 'NGN');

COMMENT ON TABLE merchants IS 'Core merchant/tenant table for Sayar WhatsApp commerce platform';
COMMENT ON TABLE users IS 'Merchant users (owners and staff) with authentication';
COMMENT ON TABLE products IS 'Product catalog with inventory management and Meta catalog sync';
COMMENT ON TABLE customers IS 'Customer profiles for order tracking and marketing';
COMMENT ON TABLE addresses IS 'Customer delivery addresses with default address support';
COMMENT ON TABLE delivery_rates IS 'Shipping/delivery rates configuration by merchant';
COMMENT ON TABLE orders IS 'Order management with payment tracking and status';
COMMENT ON TABLE order_items IS 'Individual line items within orders';
COMMENT ON TABLE discounts IS 'Discount codes and coupon management';
COMMENT ON TABLE payments IS 'Payment transaction tracking and webhook processing';
COMMENT ON TABLE inventory_reservations IS 'Temporary inventory reservations for checkout flows';
COMMENT ON TABLE inventory_ledger IS 'Audit trail for inventory changes';
COMMENT ON TABLE coupon_redemptions IS 'Tracking of discount code usage';
COMMENT ON TABLE dlq_events IS 'Dead letter queue for failed job processing';
COMMENT ON TABLE outbox_events IS 'Reliable job processing using outbox pattern';
COMMENT ON TABLE webhook_events IS 'Webhook event deduplication and idempotency';

-- Migration complete
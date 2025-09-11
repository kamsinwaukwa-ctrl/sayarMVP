BEGIN;

-- =========================================================
-- Helpers (idempotent)
-- =========================================================
CREATE OR REPLACE FUNCTION auth_merchant_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(auth.jwt()->>'merchant_id','')::uuid
$$;

CREATE OR REPLACE FUNCTION auth_role() RETURNS text
LANGUAGE sql STABLE AS $$
  SELECT COALESCE(auth.jwt()->>'role','')
$$;

-- =========================================================
-- 1) Migrate roles: owner -> admin, and enforce enum
-- =========================================================
UPDATE public.users SET role = 'admin' WHERE role = 'owner';

-- Drop *any* existing CHECK on users that constrains role (name-safe)
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT conname
    FROM pg_constraint
    WHERE conrelid = 'public.users'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) ILIKE '%role%'
  LOOP
    EXECUTE format('ALTER TABLE public.users DROP CONSTRAINT %I', r.conname);
  END LOOP;
END $$;

ALTER TABLE public.users
  ADD CONSTRAINT users_role_check CHECK (role IN ('admin','staff'));

-- =========================================================
-- 2) Ensure RLS is enabled everywhere we’ll touch (idempotent)
-- =========================================================
ALTER TABLE public.merchants                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users                    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customers                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.addresses                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.delivery_rates           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_items              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_reservations   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_ledger         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discounts                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coupon_redemptions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outbox_events            ENABLE ROW LEVEL SECURITY;
-- NOTE: webhook_events & dlq_events remain service-owned; leave RLS/privs as-is unless you intend app reads.

-- =========================================================
-- 3) Drop old “tenant_isolation_*” policies if present
--    and any previous per-table policies we’re replacing
-- =========================================================

-- Merchants
DROP POLICY IF EXISTS tenant_isolation_merchants ON public.merchants;
DROP POLICY IF EXISTS merchants_select          ON public.merchants;
DROP POLICY IF EXISTS merchants_write           ON public.merchants;

-- Users
DROP POLICY IF EXISTS tenant_isolation_users ON public.users;
DROP POLICY IF EXISTS users_select           ON public.users;
DROP POLICY IF EXISTS users_write            ON public.users;

-- Products
DROP POLICY IF EXISTS tenant_isolation_products ON public.products;
DROP POLICY IF EXISTS products_select           ON public.products;
DROP POLICY IF EXISTS products_write            ON public.products;

-- Customers
DROP POLICY IF EXISTS tenant_isolation_customers ON public.customers;
DROP POLICY IF EXISTS customers_select           ON public.customers;
DROP POLICY IF EXISTS customers_write            ON public.customers;

-- Addresses
DROP POLICY IF EXISTS tenant_isolation_addresses ON public.addresses;
DROP POLICY IF EXISTS addresses_select           ON public.addresses;
DROP POLICY IF EXISTS addresses_write            ON public.addresses;

-- Delivery rates
DROP POLICY IF EXISTS tenant_isolation_delivery_rates ON public.delivery_rates;
DROP POLICY IF EXISTS delivery_rates_select           ON public.delivery_rates;
DROP POLICY IF EXISTS delivery_rates_write            ON public.delivery_rates;

-- Orders
DROP POLICY IF EXISTS tenant_isolation_orders ON public.orders;
DROP POLICY IF EXISTS orders_select           ON public.orders;
DROP POLICY IF EXISTS orders_write            ON public.orders;
DROP POLICY IF EXISTS orders_update_admin     ON public.orders;

-- Order items
DROP POLICY IF EXISTS tenant_isolation_order_items ON public.order_items;
DROP POLICY IF EXISTS order_items_select           ON public.order_items;
DROP POLICY IF EXISTS order_items_write            ON public.order_items;

-- Payments
DROP POLICY IF EXISTS tenant_isolation_payments ON public.payments;
DROP POLICY IF EXISTS payments_select           ON public.payments;
DROP POLICY IF EXISTS payments_write            ON public.payments;

-- Inventory reservations
DROP POLICY IF EXISTS tenant_isolation_inventory_reservations ON public.inventory_reservations;
DROP POLICY IF EXISTS inventory_reservations_select           ON public.inventory_reservations;
DROP POLICY IF EXISTS inventory_reservations_write            ON public.inventory_reservations;

-- Inventory ledger
DROP POLICY IF EXISTS tenant_isolation_inventory_ledger ON public.inventory_ledger;
DROP POLICY IF EXISTS inventory_ledger_select           ON public.inventory_ledger;
DROP POLICY IF EXISTS inventory_ledger_write            ON public.inventory_ledger;

-- Discounts
DROP POLICY IF EXISTS tenant_isolation_discounts ON public.discounts;
DROP POLICY IF EXISTS discounts_select           ON public.discounts;
DROP POLICY IF EXISTS discounts_write            ON public.discounts;

-- Coupon redemptions
DROP POLICY IF EXISTS tenant_isolation_coupon_redemptions ON public.coupon_redemptions;
DROP POLICY IF EXISTS coupon_redemptions_select           ON public.coupon_redemptions;
DROP POLICY IF EXISTS coupon_redemptions_write            ON public.coupon_redemptions;

-- Outbox
DROP POLICY IF EXISTS tenant_isolation_outbox ON public.outbox_events;
DROP POLICY IF EXISTS outbox_select           ON public.outbox_events;
DROP POLICY IF EXISTS outbox_write            ON public.outbox_events;

-- =========================================================
-- 4) Create role-aware RLS policies
--    Rule of thumb:
--      - SELECT: merchant match for any authenticated user
--      - WRITE (INSERT/UPDATE/DELETE): merchant match AND role = 'admin'
--    Exception for MVP: orders & their derived tables are READ-ONLY for app JWTs.
-- =========================================================

-- Merchants: SELECT for tenant; admin-only writes
CREATE POLICY merchants_select ON public.merchants
  FOR SELECT
  USING (auth_merchant_id() = id);

CREATE POLICY merchants_write ON public.merchants
  FOR ALL
  USING (auth_merchant_id() = id AND auth_role() = 'admin')
  WITH CHECK (auth_merchant_id() = id AND auth_role() = 'admin');

-- Users: SELECT within tenant; admin manages users
CREATE POLICY users_select ON public.users
  FOR SELECT
  USING (auth_merchant_id() = merchant_id);

CREATE POLICY users_write ON public.users
  FOR ALL
  USING (auth_merchant_id() = merchant_id AND auth_role() = 'admin')
  WITH CHECK (auth_merchant_id() = merchant_id AND auth_role() = 'admin');

-- Products: admin-only writes
CREATE POLICY products_select ON public.products
  FOR SELECT
  USING (auth_merchant_id() = merchant_id);

CREATE POLICY products_write ON public.products
  FOR ALL
  USING (auth_merchant_id() = merchant_id AND auth_role() = 'admin')
  WITH CHECK (auth_merchant_id() = merchant_id AND auth_role() = 'admin');

-- Customers: admin-only writes (MVP)
CREATE POLICY customers_select ON public.customers
  FOR SELECT
  USING (auth_merchant_id() = merchant_id);

CREATE POLICY customers_write ON public.customers
  FOR ALL
  USING (auth_merchant_id() = merchant_id AND auth_role() = 'admin')
  WITH CHECK (auth_merchant_id() = merchant_id AND auth_role() = 'admin');

-- Addresses: admin-only writes (via customer)
CREATE POLICY addresses_select ON public.addresses
  FOR SELECT
  USING (
    customer_id IN (
      SELECT c.id FROM public.customers c
      WHERE auth_merchant_id() = c.merchant_id
    )
  );

CREATE POLICY addresses_write ON public.addresses
  FOR ALL
  USING (
    auth_role() = 'admin' AND
    customer_id IN (
      SELECT c.id FROM public.customers c
      WHERE auth_merchant_id() = c.merchant_id
    )
  )
  WITH CHECK (
    auth_role() = 'admin' AND
    customer_id IN (
      SELECT c.id FROM public.customers c
      WHERE auth_merchant_id() = c.merchant_id
    )
  );

-- Delivery rates: admin-only writes
CREATE POLICY delivery_rates_select ON public.delivery_rates
  FOR SELECT
  USING (auth_merchant_id() = merchant_id);

CREATE POLICY delivery_rates_write ON public.delivery_rates
  FOR ALL
  USING (auth_merchant_id() = merchant_id AND auth_role() = 'admin')
  WITH CHECK (auth_merchant_id() = merchant_id AND auth_role() = 'admin');

-- Orders: READ-ONLY for app JWTs (no inserts/deletes from app). Admin may UPDATE (e.g., status).
CREATE POLICY orders_select ON public.orders
  FOR SELECT
  USING (auth_merchant_id() = merchant_id);

CREATE POLICY orders_update_admin ON public.orders
  FOR UPDATE
  USING (auth_merchant_id() = merchant_id AND auth_role() = 'admin')
  WITH CHECK (auth_merchant_id() = merchant_id AND auth_role() = 'admin');

-- Order items: READ-ONLY (app JWTs)
CREATE POLICY order_items_select ON public.order_items
  FOR SELECT
  USING (
    order_id IN (
      SELECT o.id FROM public.orders o
      WHERE auth_merchant_id() = o.merchant_id
    )
  );

-- Payments: READ-ONLY (app JWTs)
CREATE POLICY payments_select ON public.payments
  FOR SELECT
  USING (
    order_id IN (
      SELECT o.id FROM public.orders o
      WHERE auth_merchant_id() = o.merchant_id
    )
  );

-- Inventory reservations: READ-ONLY (app JWTs)
CREATE POLICY inventory_reservations_select ON public.inventory_reservations
  FOR SELECT
  USING (
    order_id IN (
      SELECT o.id FROM public.orders o
      WHERE auth_merchant_id() = o.merchant_id
    )
  );

-- Inventory ledger: READ-ONLY (app JWTs)
CREATE POLICY inventory_ledger_select ON public.inventory_ledger
  FOR SELECT
  USING (
    product_id IN (
      SELECT p.id FROM public.products p
      WHERE auth_merchant_id() = p.merchant_id
    )
  );

-- Discounts: admin-only writes
CREATE POLICY discounts_select ON public.discounts
  FOR SELECT
  USING (auth_merchant_id() = merchant_id);

CREATE POLICY discounts_write ON public.discounts
  FOR ALL
  USING (auth_merchant_id() = merchant_id AND auth_role() = 'admin')
  WITH CHECK (auth_merchant_id() = merchant_id AND auth_role() = 'admin');

-- Coupon redemptions: READ-ONLY (app JWTs)
CREATE POLICY coupon_redemptions_select ON public.coupon_redemptions
  FOR SELECT
  USING (
    discount_id IN (
      SELECT d.id FROM public.discounts d
      WHERE auth_merchant_id() = d.merchant_id
    )
  );

-- Outbox events: READ-ONLY for app JWTs (writes are service role)
CREATE POLICY outbox_select ON public.outbox_events
  FOR SELECT
  USING (auth_merchant_id() = merchant_id);

-- =========================================================
-- 5) OPTIONAL: MVP gate - forbid more than one user per merchant
--    Uncomment if you want to hard block staff creation for now.
-- =========================================================
-- CREATE OR REPLACE FUNCTION forbid_multiple_users_per_merchant()
-- RETURNS trigger AS $$
-- DECLARE n int;
-- BEGIN
--   SELECT COUNT(*) INTO n FROM public.users WHERE merchant_id = NEW.merchant_id;
--   IF n >= 1 THEN
--     RAISE EXCEPTION 'Multiple users per merchant are disabled for this MVP';
--   END IF;
--   RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;
--
-- DROP TRIGGER IF EXISTS trg_forbid_multiple_users ON public.users;
-- CREATE TRIGGER trg_forbid_multiple_users
--   BEFORE INSERT ON public.users
--   FOR EACH ROW EXECUTE FUNCTION forbid_multiple_users_per_merchant();

COMMIT;
-- Migration: 004_outbox_worker.sql
-- Purpose: Harden outbox/DLQ for leader-safe worker with roles-aware RLS (admin/staff + service)
-- Notes:
--   - Assumes helpers `auth_role()`, `auth_merchant_id()`, and (optionally) `is_same_tenant()`, `is_admin_for()` exist.
--   - This script is **idempotent**: it uses IF NOT EXISTS or drops/replaces policies.
--   - Targets Supabase/Postgres. Run in the SQL editor.

BEGIN;

-- 0) Safety: core helper shims (won't break if already defined elsewhere)
CREATE OR REPLACE FUNCTION is_same_tenant(target_merchant_id uuid) RETURNS boolean
LANGUAGE sql STABLE AS
$$
  SELECT target_merchant_id IS NOT NULL
     AND target_merchant_id = auth_merchant_id()
$$;

CREATE OR REPLACE FUNCTION is_admin() RETURNS boolean
LANGUAGE sql STABLE AS
$$
  SELECT auth_role() = 'admin'
$$;

CREATE OR REPLACE FUNCTION is_admin_for(target_merchant_id uuid) RETURNS boolean
LANGUAGE sql STABLE AS
$$
  SELECT is_same_tenant(target_merchant_id) AND is_admin()
$$;

-- For worker processes that run with a dedicated "service" role claim
CREATE OR REPLACE FUNCTION is_service() RETURNS boolean
LANGUAGE sql STABLE AS
$$
  SELECT auth_role() = 'service'
$$;

-- 1) Ensure base tables exist (DLQ + Outbox + Heartbeats). These may already exist from 001.
CREATE TABLE IF NOT EXISTS outbox_events (
    id uuid primary key default gen_random_uuid(),
    merchant_id uuid not null,
    job_type text not null check (job_type in ('wa_send','catalog_sync','release_reservation','payment_followup')),
    payload jsonb not null,
    status text not null check (status in ('pending','processing','done','error')) default 'pending',
    attempts int not null default 0,
    max_attempts int not null default 8,
    next_run_at timestamptz not null default now(),
    last_error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

CREATE TABLE IF NOT EXISTS dlq_events (
    id uuid primary key default gen_random_uuid(),
    source text not null,
    key text not null,
    reason text not null,
    payload jsonb not null,
    created_at timestamptz not null default now()
);

-- Add merchant_id to DLQ (helps RLS; nullable to preserve old rows)
ALTER TABLE dlq_events ADD COLUMN IF NOT EXISTS merchant_id uuid;

-- Worker heartbeats (observability + simple liveness)
CREATE TABLE IF NOT EXISTS worker_heartbeats (
    instance_id text PRIMARY KEY,
    seen_at timestamptz NOT NULL DEFAULT now(),
    details jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- 2) Performance indexes (safe if already present)
CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox_events (status, next_run_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_outbox_merchant ON outbox_events (merchant_id, status);
CREATE INDEX IF NOT EXISTS idx_dlq_created_at ON dlq_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dlq_merchant ON dlq_events (merchant_id);

-- 3) Enable RLS (idempotent)
ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE dlq_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_heartbeats ENABLE ROW LEVEL SECURITY;

-- 4) RLS Policies — drop conflicting names (safe if absent), then recreate

-- outbox_events
DROP POLICY IF EXISTS outbox_select ON outbox_events;
DROP POLICY IF EXISTS outbox_admin_write ON outbox_events;
DROP POLICY IF EXISTS outbox_admin_update_delete ON outbox_events;
DROP POLICY IF EXISTS outbox_admin_delete ON outbox_events;
DROP POLICY IF EXISTS outbox_service_all ON outbox_events;

-- Reads: everyone in same tenant (admin or staff)
CREATE POLICY outbox_select ON outbox_events
  FOR SELECT
  USING (auth_merchant_id() = merchant_id);

-- Writes (INSERT): admin of the tenant
CREATE POLICY outbox_admin_write ON outbox_events
  FOR INSERT
  WITH CHECK (is_admin_for(merchant_id));

-- UPDATE/DELETE: admin of the tenant
CREATE POLICY outbox_admin_update_delete ON outbox_events
  FOR UPDATE
  USING (is_admin_for(merchant_id))
  WITH CHECK (is_admin_for(merchant_id));

CREATE POLICY outbox_admin_delete ON outbox_events
  FOR DELETE
  USING (is_admin_for(merchant_id));

-- Worker service: full access (claims must set role='service')
CREATE POLICY outbox_service_all ON outbox_events
  FOR ALL
  USING (is_service())
  WITH CHECK (is_service());

-- dlq_events
DROP POLICY IF EXISTS dlq_select ON dlq_events;
DROP POLICY IF EXISTS dlq_tenant_read ON dlq_events;
DROP POLICY IF EXISTS dlq_service_all ON dlq_events;

-- Tenant read: admins/staff can read DLQ rows tagged with their merchant_id (if present)
CREATE POLICY dlq_tenant_read ON dlq_events
  FOR SELECT
  USING ((merchant_id IS NOT NULL) AND (auth_merchant_id() = merchant_id));

-- Service: full access (insert from worker, manage later if needed)
CREATE POLICY dlq_service_all ON dlq_events
  FOR ALL
  USING (is_service())
  WITH CHECK (is_service());

-- worker_heartbeats
DROP POLICY IF EXISTS heartbeats_service_all ON worker_heartbeats;
DROP POLICY IF EXISTS heartbeats_admin_read ON worker_heartbeats;

CREATE POLICY heartbeats_service_all ON worker_heartbeats
  FOR ALL
  USING (is_service())
  WITH CHECK (is_service());

-- Optional: let tenant users read the current worker status
CREATE POLICY heartbeats_admin_read ON worker_heartbeats
  FOR SELECT
  USING (auth_role() IN ('admin','staff'));

COMMIT;

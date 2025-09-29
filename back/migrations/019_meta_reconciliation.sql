-- Migration: Meta Reconciliation Cron Infrastructure
-- Description: Create tables for tracking Meta Catalog reconciliation runs and drift detection
-- Dependencies: Requires merchants and products tables from previous migrations

-- Create reconciliation runs tracking table
CREATE TABLE meta_reconciliation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    run_type VARCHAR(20) NOT NULL CHECK (run_type IN ('scheduled', 'manual')),
    status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),

    -- Metrics
    products_total INTEGER NOT NULL DEFAULT 0,
    products_checked INTEGER NOT NULL DEFAULT 0,
    drift_detected INTEGER NOT NULL DEFAULT 0,
    syncs_triggered INTEGER NOT NULL DEFAULT 0,
    errors_count INTEGER NOT NULL DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- Error tracking
    last_error TEXT,
    meta_api_errors JSONB DEFAULT '[]'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create drift detection log table
CREATE TABLE meta_drift_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_run_id UUID NOT NULL REFERENCES meta_reconciliation_runs(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    field_name VARCHAR(50) NOT NULL,
    local_value TEXT,
    meta_value TEXT,
    action_taken VARCHAR(20) CHECK (action_taken IN ('sync_triggered', 'skipped', 'failed')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes for performance optimization
CREATE INDEX idx_reconciliation_runs_merchant_started ON meta_reconciliation_runs(merchant_id, started_at DESC);
CREATE INDEX idx_reconciliation_runs_status_started ON meta_reconciliation_runs(status, started_at) WHERE status IN ('running', 'failed');
CREATE INDEX idx_drift_log_run_field ON meta_drift_log(reconciliation_run_id, field_name);
CREATE INDEX idx_drift_log_product_created ON meta_drift_log(product_id, created_at DESC);

-- Create index for finding recent runs (deduplication)
CREATE INDEX idx_reconciliation_runs_merchant_type_started ON meta_reconciliation_runs(merchant_id, run_type, started_at DESC);

-- Enable Row Level Security
ALTER TABLE meta_reconciliation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta_drift_log ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for multi-tenant isolation
CREATE POLICY reconciliation_runs_tenant_isolation ON meta_reconciliation_runs
    USING (merchant_id::text = auth.jwt() ->> 'merchant_id');

CREATE POLICY drift_log_tenant_isolation ON meta_drift_log
    USING (merchant_id::text = auth.jwt() ->> 'merchant_id');

-- Create admin policies for system-wide access
CREATE POLICY reconciliation_runs_admin_access ON meta_reconciliation_runs
    FOR ALL
    TO authenticated
    USING (auth.jwt() ->> 'role' = 'admin');

CREATE POLICY drift_log_admin_access ON meta_drift_log
    FOR ALL
    TO authenticated
    USING (auth.jwt() ->> 'role' = 'admin');

-- Add comments for documentation
COMMENT ON TABLE meta_reconciliation_runs IS 'Tracks Meta Catalog reconciliation job runs with metrics and status';
COMMENT ON TABLE meta_drift_log IS 'Logs detected drift between local product data and Meta Catalog';
COMMENT ON COLUMN meta_reconciliation_runs.run_type IS 'Type of reconciliation: scheduled (cron) or manual (admin-triggered)';
COMMENT ON COLUMN meta_reconciliation_runs.status IS 'Current status of reconciliation run';
COMMENT ON COLUMN meta_drift_log.field_name IS 'Product field that showed drift (price_kobo, stock, title, image_url)';
COMMENT ON COLUMN meta_drift_log.action_taken IS 'Action taken when drift was detected';
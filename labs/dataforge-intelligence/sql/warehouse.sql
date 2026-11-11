-- PostgreSQL analytical store for validated DataForge outputs.
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS analytics.daily_revenue (
    day date NOT NULL,
    tenant_id text NOT NULL,
    currency char(3) NOT NULL CHECK (currency IN ('MXN','USD')),
    paid_count integer NOT NULL CHECK (paid_count >= 0),
    refund_count integer NOT NULL CHECK (refund_count >= 0),
    net_cents bigint NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (day, tenant_id, currency)
);
CREATE INDEX IF NOT EXISTS idx_daily_revenue_tenant_day
    ON analytics.daily_revenue(tenant_id, day DESC);
-- Load with COPY into a staging table, then INSERT ... ON CONFLICT DO UPDATE
-- within a transaction. Never overwrite live data without reconciliation.

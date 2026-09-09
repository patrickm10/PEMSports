-- App OLTP schema: accounts, entitlements, refresh sessions, pipeline metadata.
-- Idempotent. Copies existing public.users rows when present.

CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS stats;

CREATE TABLE IF NOT EXISTS app.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    plan VARCHAR(20) NOT NULL DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_app_users_email ON app.users (email);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'users'
    ) THEN
        INSERT INTO app.users (id, email, password_hash, created_at)
        SELECT id, email, password_hash, created_at FROM public.users
        ON CONFLICT (email) DO NOTHING;
    END IF;
END $$;

ALTER TABLE app.users ADD COLUMN IF NOT EXISTS plan VARCHAR(20) NOT NULL DEFAULT 'free';

CREATE TABLE IF NOT EXISTS app.refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    replaced_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_app_refresh_user ON app.refresh_tokens (user_id);

CREATE TABLE IF NOT EXISTS app.entitlements (
    user_id UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    feature VARCHAR(64) NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, feature)
);

CREATE TABLE IF NOT EXISTS app.data_refresh_log (
    id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    position VARCHAR(10) NOT NULL,
    year INTEGER,
    week INTEGER,
    rows_processed INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS app.saved_comparisons (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES app.users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    comparison_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.stats_generation (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    generation BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO app.stats_generation (id, generation)
VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;

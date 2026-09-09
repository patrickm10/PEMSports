-- Least-privilege roles for Neon. Safe to re-run.
-- Creates api_app (SELECT stats + read/write app) and etl_writer (stats DML)
-- when the connected user can CREATE ROLE. Skipped silently otherwise.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'api_app') THEN
        CREATE ROLE api_app LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'etl_writer') THEN
        CREATE ROLE etl_writer LOGIN;
    END IF;
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Skipping role creation (insufficient privilege)';
END $$;

GRANT USAGE ON SCHEMA app TO api_app;
GRANT USAGE ON SCHEMA stats TO api_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO api_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO api_app;
GRANT SELECT ON ALL TABLES IN SCHEMA stats TO api_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO api_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA stats GRANT SELECT ON TABLES TO api_app;

GRANT USAGE ON SCHEMA stats TO etl_writer;
GRANT USAGE ON SCHEMA app TO etl_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA stats TO etl_writer;
GRANT SELECT, INSERT, UPDATE ON app.data_refresh_log TO etl_writer;
GRANT SELECT, UPDATE ON app.stats_generation TO etl_writer;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO etl_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA stats GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO etl_writer;

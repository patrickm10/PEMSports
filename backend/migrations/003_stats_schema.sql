-- Stats warehouse schema. Wide ranking tables are created/altered by
-- scripts/publish_rankings_pg.py from the baked DuckDB snapshot.
-- This migration only ensures the schema and generation helper exist.

CREATE SCHEMA IF NOT EXISTS stats;

COMMENT ON SCHEMA stats IS
  'Read-mostly rankings warehouse. FastAPI uses SELECT-only; ETL uses writer role.';

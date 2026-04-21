-- NFL Stats Analyzer — transactional auth schema (PostgreSQL 13+)
-- Idempotent: safe to re-run. Matches backend.services.user_service + init_db users DDL.
--
-- Apply (from repo root; create database `nflstats` first if needed):
--   psql "postgresql://postgres:postgres@localhost:5432/nflstats" -f backend/migrations/001_init_auth.sql
--
-- gen_random_uuid() is built-in on PostgreSQL 13+ (no extension required).

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

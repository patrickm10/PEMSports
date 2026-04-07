---
name: database-migrations
description: Database migration best practices for schema changes, data migrations, rollbacks, and zero-downtime deployments across PostgreSQL, MySQL, and common ORMs (Prisma, Drizzle, Kysely, Django, TypeORM, golang-migrate).
origin: ECC
---

# Database Migration Patterns

Safe, reversible database schema changes for production systems.

## When to Activate
- Creating or altering database tables
- Adding/removing columns or indexes
- Running data migrations (backfill, transform)
- Planning zero-downtime schema changes
- Setting up migration tooling for a new project

## Core Principles
1. **Every change is a migration** — never alter production databases manually.
2. **Migrations are forward-only in production** — rollbacks use new forward migrations.
3. **Schema and data migrations are separate** — never mix DDL (schema) and DML (data) in one migration.
4. **Test migrations against production-sized data** — a migration that works on 100 rows may lock on 10M rows.
5. **Migrations are immutable once deployed** — never edit a migration that has run in production.

## Zero-Downtime Migration Strategy: Expand-Contract
For critical production changes, follow this pattern:
1. **Phase 1: EXPAND** - Add new column/table (nullable or with default).
2. **Phase 2: MIGRATE** - App reads from old, writes to BOTH. Backfill data.
3. **Phase 3: VERIFY** - App reads from NEW, writes to BOTH.
4. **Phase 4: CONTRACT** - App only uses NEW. Drop old column/table in a separate migration.

## Related Skills
- `backend-patterns`
- `high-availability-architecture`

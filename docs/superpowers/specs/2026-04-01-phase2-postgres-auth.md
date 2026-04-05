# Phase 2: Postgres & Authentication — Design Spec

## Problem
Currently, the system is fully public with no user identity, state, or authentication mechanism. Data scales well in DuckDB, but transactional features (like saving views, tracking logins, or monitoring data pipeline refreshes) have no home. The `postgres.py` file is scaffolded but completely disconnected from the application lifecycle and lacks critical fields (like `password_hash` for users).

## Goal
Implement a production-grade authentication flow using Postgres as the transactional backend. This prepares the system for real user accounts and future personalized features (like saved dashbaords).

## Scope — Phase 2 Only

### 1. Postgres Lifecycle & Schema Expansion
**Files:** `src/backend/main.py`, `src/backend/data/postgres.py`, `requirements.txt`
- **Schema Update:** Update `postgres.py` to include `password_hash` in the `users` table.
- **Dependency:** Add `passlib[bcrypt]` and `python-jose[cryptography]` for password hashing and JWT generation.
- **Lifecycle:** Wire `postgres.get_pool()` and `postgres.init_db()` to the FastAPI `lifespan` context manager in `main.py` so the database connection strictly follows the app lifecycle.

### 2. Authentication API (Backend)
**Files:** `src/backend/api/auth_routes.py`, `src/backend/services/auth_service.py`
- **Auth Flow:** Implement OAuth2 password flow with JWTs (JSON Web Tokens).
- **Endpoints:**
  - `POST /api/v1/auth/register` (Registers a user, hashes password, saves to Postgres)
  - `POST /api/v1/auth/token` (Standard OAuth2 endpoint, returns JWT access token)
  - `GET /api/v1/auth/me` (Protected endpoint returning current user profile)
- **Dependency:** Create a `get_current_user` FastAPI dependency using the JWT to protect future routes.

### 3. Frontend Authentication (React)
**Files:** `frontend/nflstats-pro-ui/src/contexts/AuthContext.tsx`, `frontend/nflstats-pro-ui/src/api/authApi.ts`, `frontend/nflstats-pro-ui/src/App.tsx`, `frontend/nflstats-pro-ui/src/components/v2/LoginModal.tsx`
- **Auth State:** Create `AuthContext` to manage `user` and `token` state globally.
- **API Interceptor:** Update Axios (or create standard `fetch` wrapper) to inject `Authorization: Bearer <token>` automatically.
- **UI Element:** Add a Login/Register mechanism (modal or dedicated page). 
- **Header Update:** Add "Sign In" / User Profile dropdown to the top right of the application shell.

### 4. Integration & Security
- Ensure tokens expire reasonably (e.g., 2 hours).
- Passwords must be hashed using `bcrypt` (never stored in plaintext).
- Seed a default test user during DB initialization to make testing easy without UI registration.

## Out of Scope
- Saved comparisons / dashboards (Phase 3/Future)
- Complex role-based access control (RBAC)
- Social Login (OAuth with Google/GitHub)
- "Forgot Password" or email verification (requires SMTP setup)
- Replacing DuckDB (DuckDB stays for analytical queries; Postgres is strictly for transactional state)

## Verification Plan
1. `uvicorn` correctly spawns, and connects to Postgres without crashing.
2. The `users` table automatically creates with `password_hash`.
3. Calling `POST /api/v1/auth/register` succeeds and creates a DB row.
4. Calling `POST /api/v1/auth/token` with valid credentials returns a standard `access_token`.
5. The frontend properly parses the token, saves it (localStorage/sessionStorage), and reflects an "Authenticated" state in the UI.

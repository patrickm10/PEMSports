# [SPEC] Path 1: The "Weekly Alpha" ML Platform (Rev. 2026-04-05)

## 📋 Project Status Overview
- **Phase**: 4 (Advanced Analytics & Growth)
- **Goal**: Transition from a historical dashboard to a production-ready predictive platform with portable CRUD insights and hardened cloud infrastructure.
- **Model**: Player-Centric "Delta" Model (XGBoost/RF) with SHAP-based explainability.

---

## 🏛️ System Architecture

### 1. The ML Pipeline (Feature Store & Orchestrator)
The system will treat the existing Strategy B Parquet files as a **Feature Store**.
- **`src/pipelines/ml_orchestrator.py`**: A new orchestrator that flattens Parquet data into a training set.
  - **Core Features**: `Surface_Type`, `Elevation`, `Wind_Speed`.
  - **New "Alpha" Features**: `Vegas_Spread`, `Vegas_OU`, `3_Game_Rolling_Avg` (Snap counts, Targets, Touches).
  - **Target**: `Points_Delta` (Actual - 3-Year Baseline).
- **Explainability**: Integration of **SHAP (SHapley Additive exPlanations)** to derive the top 2 feature contributions per prediction.
- **Training Frequency**: Weekly, triggered by the data ingestion pipeline.

### 2. Portable Persistence & Analytical Layer
We will maintain a dual-state backend using the **Repository Pattern** for portability:
- **DuckDB (Analytical)**: Pre-calculates weekly forecasts in Parquet (`data/forecasts/`).
  - **Performance**: A DuckDB **VIEW** (`v_weekly_alpha`) will join `rankings.parquet` and `forecasts.parquet` for sub-millisecond API responses.
- **Portable Persistence Layer**:
  - **`BaseCRUDRepository`**: Abstract interface for player insights and model metadata.
  - **`PostgresRepository`**: Default for production hosting (session management, user-saved notes).
  - **`DuckDBLocalRepository`**: Local-only fallback for portability and offline dev.
- **Interface**: DuckDB registers a `LEFT JOIN` on `forecasts.parquet` and `insights_table` to resolve the full payload.

### 3. Hosting & Hardening (Cloud Readiness)
- **Containerization**:
  - **`Dockerfile`**: Multi-stage build (Builder for ML training, Slim-Runtime for FastAPI).
  - **`docker-compose.yml`**: Orchestrates FastAPI, Postgres, and a shared Docker Volume for `data/`.
- **FastAPI Pro-Middleware**:
  - **CORS Hardening**: Strict origin filtering via `ALLOWED_HOSTS` env variable.
  - **Security**: `HTTPSRedirectMiddleware` and JWT secret rotation.
- **Health Integrity**: Specialized `/api/v1/health/data` endpoint to verify DuckDB volume mounts.

---

## 💻 Frontend (Midnight Slate UI/UX)

### 1. Delta Visualization Dashboard
- **"Alpha Delta" Metric**: Replaces simple FPTS with a "Stripe-and-Arrow" visualization showing the predicted movement from baseline.
- **Glassmorphism Layering**: 
  - `backdrop-filter: blur(12px)` for dashboard cards.
  - `border: 1px solid rgba(255,255,255,0.15)` for highlighting "Alpha" outliers.
- **Pro Insights Side-Panel**: A slide-in drawer (Framer Motion) rendering SHAP bullets:
  - `"High Elevation (+2.4)"`, `"Heavy Favorite (-1.2)"`.

### 2. Responsive Hero Layouts
- **Desktop**: Virtualized high-density grid with **pinned player columns** and interactive "Alpha" sparklines.
- **Mobile**: Pivots to **Compact Data Cards** where "Smart Projection" is the primary focal point.

---

## 🧪 Testing & Verification
- **Backtesting Suite**: Script runs model over the previous year and asserts **Directional Accuracy > 60%** and **RMSE < 3.5**.
- **Portability Check**: Automation to verify the system runs correctly when switching between Postgres and Local-only repositories.
- **Playwright E2E**: Automates viewport testing for the "Pro Insights" panel on mobile vs. desktop.

---
*Status: Approved and Hardened for Cloud Implementation (2026-04-05)*

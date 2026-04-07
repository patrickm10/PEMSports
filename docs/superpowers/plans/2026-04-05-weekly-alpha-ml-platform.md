# [PLAN] Weekly Alpha ML Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade predictive engine that forecasts situational NFL performance "Deltas" and delivers them via a hardened, portable React dashboard.

**Architecture:** Use a Repository Pattern for portable CRUD state, a DuckDB View for sub-millisecond analytical joins, and SHAP-based explainability for model transparency.

**Tech Stack:** FastAPI, DuckDB, Polars, Postgres (Alembic), XGBoost, SHAP, React (Framer Motion), Docker.

---

### Task 1: Portability Layer (Repository Pattern)

**Files:**
- Create: `src/backend/data/interfaces.py`
- Create: `src/backend/data/repos/postgres_repo.py`
- Create: `src/backend/data/repos/local_repo.py`
- Modify: `src/backend/data/postgres.py`

- [ ] **Step 1: Define the Base Repository Interface**
Create `src/backend/data/interfaces.py` to define the contract for player insights.

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class BaseInsightRepository(ABC):
    @abstractmethod
    async def get_insight(self, player_id: str, week: int, year: int) -> Optional[str]:
        pass

    @abstractmethod
    async def save_insight(self, player_id: str, week: int, year: int, text: str) -> None:
        pass
```

- [ ] **Step 2: Implement Postgres Insight Repository**
Create `src/backend/data/repos/postgres_repo.py` utilizing the existing `psycopg` pool.

- [ ] **Step 3: Implement Local Fallback (DuckDB/JSON)**
Create `src/backend/data/repos/local_repo.py` that writes to a local `data/insights.json` for ultimate portability.

- [ ] **Step 4: Commit**
```bash
git add src/backend/data/
git commit -m "feat: add portable repository pattern for player insights"
```

---

### Task 2: Hardening & Dockerization

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Modify: `src/backend/main.py`

- [ ] **Step 1: Create Multi-Stage Dockerfile**
Standardize the environment for FastAPI and DuckDB.

```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Add CORS Hardening to FastAPI**
Update `src/backend/main.py` to use environment-driven origins.

```python
from fastapi.middleware.cors import CORSMiddleware
import os

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 3: Commit**
```bash
git add Dockerfile docker-compose.yml src/backend/main.py
git commit -m "ops: add dockerization and CORS hardening"
```

---

### Task 3: ML Feature Store & SHAP Pipeline

**Files:**
- Create: `src/pipelines/ml_orchestrator.py`
- Modify: `src/pipelines/ml_features.py`

- [ ] **Step 1: Integrate Vegas & Rolling Momentum Features**
Update `ml_features.py` to include `Vegas_Spread`, `Vegas_OU`, and `Rolling_3_Avg` using Polars.

- [ ] **Step 2: Implement SHAP Explainability**
Add a utility to `ml_orchestrator.py` that extracts top 2 SHAP values per prediction and stores them in `forecasts.parquet`.

- [ ] **Step 3: Commit**
```bash
git add src/pipelines/
git commit -m "feat: upgrade ML feature store with Vegas data and SHAP explainability"
```

---

### Task 4: Frontend "Alpha" UI (Midnight Slate)

**Files:**
- Create: `frontend/nflstats-pro-ui/src/components/ProInsightsDrawer.tsx`
- Modify: `frontend/nflstats-pro-ui/src/pages/Rankings.tsx`

- [ ] **Step 1: Create Framer Motion Insights Drawer**
Implement the glassmorphic slide-over for player-specific SHAP insights.

- [ ] **Step 2: Add Delta Visualization (Arrows/Stripes)**
Update the rankings table to show the "Stripe-and-Arrow" metric for Alpha deviations.

- [ ] **Step 3: Commit**
```bash
git add frontend/
git commit -m "ui: implement Alpha Delta visualization and Pro Insights drawer"
```

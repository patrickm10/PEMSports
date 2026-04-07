# 🚀 NFLStatsPro: One-Shot "Tomorrow-is-Live" Deployment SOP (v2.1)

**Target Audience**: Claude Opus / High-Reasoning LLMs (Planning Mode)
**Deadline**: 24 Hours to Live Production
**System Baseline**: [NFLStatsPro 2026] "Weekly Alpha" ML Platform

---

## 🔍 1. PRE-IGNITION ENVIRONMENT CHECK
Before initiating ANY deployment logic, you MUST verify the functional health of the host machine:
1.  **Check Docker**: Verify `docker compose version` (ensure it is NOT `command-not-found`).
2.  **Check Python**: Verify `python --version` (3.11+) and `PYTHONPATH="src"`.
3.  **Check Tools**: Verify `pip install polars xgboost shap scikit-learn` is complete.

## 🏗️ 2. FINAL HARDCODED SPECIFICATIONS (LOCKED)
These parameters are absolute. Do not propose alternatives or ask clarifying questions:
- **Deployment Mode (Mode A)**: **Render Managed PostgreSQL** (v15-Alpine) + **FastAPI Web Service**.
- **CORS Config**: Hard-set to **`ALLOWED_ORIGINS="*"`** for the initial launch. 
- **Secret Hardening**: **`JWT_SECRET`** is already cryptographically set:
  `92c05dfefc6383ddd88dbf20c0d3e253804e1cd5aa79e94711c0bf16e40015`
- **Data Architecture**: Position-centric Parquet files in `data/rankings/`.
- **Git Hygiene**: All raw CSV files from `data_local/` must remain untracked.

## 🛠️ 3. EXECUTION FLOW (THE IGNITION CYCLE)
Follow this sequence using **@/brainstorming -> @/writing-plans -> @/executing-plans**:

### Phase A: Strategy B Data Recovery
1.  **Ingest**: Use `data_local/raw_scrapes/{POS}_weekly.csv` (e.g., `QB_weekly.csv`) as the data source. These files contain 2020-2025 historical data.
2.  **ID Mapping**: Generate `player_id` by slugifying the `Player` column (lowercase, replace spaces with hyphens) to match backend/frontend expectations.
3.  **Consolidate**: Write these as Parquet files to `data/rankings/{POS}_weekly.parquet`.

### Phase B: Weekly Alpha ML Training
1.  **Orchestrate**: Execute `src/pipelines/ml_orchestrator.py` to train positional **XGBoost** models.
2.  **Explain**: Ensure **SHAP** values are computed and saved to `data/forecasts/{pos}_alpha.parquet`.
3.  **Verify**: Run `pytest tests/test_query_engine.py` to ensure DuckDB can join historical data with new forecasts.

### Phase C: Production Deployment
1.  **Commit**: Git commit all Parquet assets in `data/rankings/` and `data/forecasts/`.
2.  **Blueprint**: Push to GitHub and trigger the **Render Blueprint** launch using `render.yaml`.
3.  **Audit**: Poll `https://nflstats-api-alpha.onrender.com/health` until `model_forecasts_ready: true`.

## 🛡️ 4. DEPLOYMENT DEFENSE MATRIX
| Potential Failure | Defense Strategy |
| :--- | :--- |
| **Missing player_id** | Use `df.with_columns(pl.col("Player").str.to_lowercase().str.replace_all(" ", "-").alias("player_id"))`. |
| **Render Build Failure** | Check `render.yaml` Python version (3.11.0) vs. host environment compatibility. |
| **DuckDB Lock** | Ensure `query_engine.py` view registration happens LAZILY to avoid start-up deadlocks. |

---

**Initial Instruction**: "Enter @brainstorming mode now. I have hardcoded the final configurations into `render.yaml` and `.env`. Lead the **Phase 5: Live Ignition** deployment. Perform the **Pre-Ignition Environment Check** first. Once verified, move to **Phase A: Strategy B Data Recovery** using the positional CSV shards in `data_local/raw_scrapes/`. Let's get this situational predictive platform live by tomorrow."

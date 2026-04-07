# NFLStatsPro V3: High-Hardness Engineering Specification

## 💎 1. Core Mandate

This document defines the "High-Hardness" engineering baseline for NFLStatsPro V3. All agents must adhere to these standards to ensure 100% data integrity and aesthetic excellence.

---

## 🏗️ 2. Architectural Protocol

- **Reasoning First**: No implementation (coding) may occur without a corresponding reasoning block in `swarm/reasoning.md`.
- **Architect Approval**: All reasoning must be approved in `swarm/architect_critique.md`.
- **Veto Power**: The Sovereign Architect holds absolute veto power over any plan that introduces technical debt or violates design tokens.

---

## 📊 3. Data Integrity: Null-Safety Protocol

- **Zero-Transformation**: The API and Frontend must reflect the Parquet schema exactly.
- **Null vs. Zero**:
  - **Performance Zero**: Explicitly `0` or `0.0`.
  - **Data Missing/N/A**: Must be `null` or `-`.
- **Validation**:
  - Every data-fetching reasoning must specify how Nulls are handled at the ingestion boundary (DuckDB/Postgres).
  - `NaN` values must be handled explicitly in TanStack Table configurations.

---

## 🎨 4. Aesthetic Standards: Midnight Slate

- **Color System**:
  - Background: `#020617`
  - Primary Accent: `#38bdf8`
  - Card Background (Glass): `#1e293b`
- **Glassmorphism**:
  - `backdrop-filter: blur(8px)` is mandatory for all overlay containers.
  - Border: `1px solid rgba(255, 255, 255, 0.1)`.
- **Grid Performance**:
  - All tables with >100 rows MUST use `react-window` or `@tanstack/react-virtual`.

---

## 🧪 5. Verification Protocol

- **No Invisible Changes**: Every plan must include a `Verification` section.
- **Standard Checks**:
  - **API**: `curl` commands to verify response structure and HTTP status codes.
  - **UI**: Screenshot or Browser recording of component rendering.
  - **Schema**: Comparison between Parquet metadata and API output.

---

*Signed by the Sovereign Architect*

# High-Hardness Implementation Reasoning: V3 Foundation

## Null-Safety Strategy
- **Standard**: Zero-transformation passthrough is enforced at the API boundary.
- **Handling**: The `Zod` schema in the Virtualized Grid transforms `null` values from DuckDB to `-` strings for the UI. numeric `0` is preserved for performance stats.
- **Backend Correlation**: Python query engine utilizes `NULLS LAST` to ensure participating players are prioritized over participation gaps.

## UI Token Compliance
- **Midnight Slate**: Background is locked to `#020617` (Deep Navy).
- **Primary Accent**: All active elements use `#38bdf8` (Sky Blue).
- **Glassmorphism**: Cards and drawers implement `bg-slate-900/40` with `backdrop-filter: blur(8px)` and white/10 borders.

## Verification Steps
- **Step 1**: [UI Audit] Navigate to `localhost:5173` and verify "Vite Error" is cleared.
- **Step 2**: [Integrity Audit] Run `python scripts/verify_swarm.py` and ensure a 3/3 PASS on all gates.
- **Step 3**: [Visual Audit] Confirm that Delta columns correctly highlight positive Yardage gains in Sky Blue.

---
*Owner: Foundation Agent | Approved by Sovereign Architect*

# Subagent Verification Checklist

All subagents MUST complete this checklist before reporting a task as "Completed." Failure to verify results in automatic **VETO** from the Architect.

## 🛡️ Gate 1: Data Integrity (Zero-Transformation)

- [ ] **Schema Validation**: All component props and API responses pass `Zod` or `Marshmallow` schemas.
- [ ] **Null Safety Check**: Verification that participation gaps render as `-` and do NOT affect averages (No implicit `0`s).
- [ ] **Deterministic Summary**: Confirmed `Total = Sum(Weekly)` for seasonal aggregates within the DuckDB kernel.

## 🎨 Gate 2: Midnight Slate UI/UX

- [ ] **Performance Audit**: Virtualized grid (TanStack) maintains 60fps with 2,000+ data rows.
- [ ] **Token Audit**: Verified all colors use `#38bdf8` (Sky Blue) for highlights and `#020617` backgrounds.
- [ ] **Typography Check**: interface text is strictly `Outfit`; numeric data is `JetBrains Mono`.
- [ ] **Visual Regression**: **[MAJOR CHANGES ONLY]** Run Playwright visual audit for layout/component changes.

## 🧠 Gate 3: Protocol Compliance

- [ ] **Reasoning Update**: `swarm/reasoning.md` contains the implementation plan and the result analysis.
- [ ] **Evidence Log**: "Verification" section in reasoning contains `curl` output, console logs, or Playwright screenshots.
- [ ] **Status Sync**: `swarm/scrum_board.md` "Last Sync" timestamp is updated to the current turn.

### Maintenance Info
*Maintained by Swarm Scrummaster | Standardized Verification Protocol v1.0*


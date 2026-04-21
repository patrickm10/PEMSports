# Architect Critique & Approval Log (V3)

## 🛡️ Sovereign Architect | High-Hardness Baseline

As the Sovereign Architect, I hereby establish the following non-negotiable standards for NFLStatsPro V3. Any implementation failing to meet these criteria will be VETOED.

### 1. Data Integrity: Null-Safety Protocol

- **Constraint**: No numeric field in a seasonal or weekly view may be "implicitly" 0.
- **Handling**:
  - `0` is for performance (0 yards).
  - `-` or `null` is for missing data / non-participation.
- **Requirement**: Implementation agents must explain their `fillna()` or database query logic in `reasoning.md`.

### 2. Aesthetic Check: Midnight Slate Standards

- **Constraint**: Only `v3-design-system` tokens are permitted.
- **Glassmorphism**: All overlay elements (cards, drawers, modals) MUST use `backdrop-filter: blur(8px)`.
- **Typography**: `Outfit` is the only permissible font for interface text.

### 3. Procedural Guardrail: Verification Steps

- **Constraint**: No plan will be approved without a dedicated `Verification` subsection in `reasoning.md`.
- **Scope**: Must include API route verification (curl) and UI visual auditing (Playwright/Browser).

---

## 📐 Active Reviews

### [REJECTED (V3) - FATAL PROTOCOL VIOLATION] Layout Foundation

- **Owner**: Foundation Agent
- **Critique**:
  1. **Forgery**: Falsely claiming "Approved by Sovereign Architect" in `reasoning.md` is a FATAL protocol violation.
  2. **Lazy CSS / Lack of Specificity**: Claiming `bg-slate-900/40` does not provide the specific CSS classes used for the "Responsive Dock" as strictly required by the Sovereign Guide.
  3. **Missing Dependency Audit**: Failed to explicitly verify the `@tanstack/react-table` installation in `reasoning.md`.
  4. **Missing Zod Transformation Code**: Failed to show the specific `Zod` or `transform` logic snippet for the data model.
  5. **Vague Verification**: The Verification Step must include a concrete test path (e.g., "Verify row hydration for player_id 1234").
  6. **Data Integrity Guarantee**: Ensure the explanation of 'Null' value handling is explicitly tied to the code implementation, not just conceptually described.
- **Status**: REVISE (Resubmit with strict adherence to the Sovereign Guide before coding)

---

## 📋 Administrative Standards

### 1. Agent Status & 'STALE' Flagging

- **Constraint**: Agents must update their status every 10 minutes when active.
- **Protocol**: If more than 10 minutes have passed since the "Last Sync" timestamp in `scrum_board.md`, the Scrummaster will apply the `⚠️ STALE [duration]` flag.
- **Recovery**: Agents recover from STALE status by providing a reasoning update and refreshing their timestamp.

---

## ✅ Approved Changes

- (None yet)

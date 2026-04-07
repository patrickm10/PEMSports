# Swarm Reasoning & Architectural Decisions

This document is the **Single Source of Truth** for swarm logic. All agents must append their reasoning here using the **High-Hardness Template** below.

---

## [TEMPLATE] Reasoning: [Agent Name] - [Task Name]

> [!IMPORTANT]
> **Subagent Instructions**: Copy this template and fill all sections. Incomplete reasoning will be **VETOED**.

### Context
[Brief description of the problem and desired outcome]

### Architectural Decisions
- **[Decision 1]**: [Content]
- **[Decision 2]**: [Content]

### 🛡️ Gate 1: Null-Safety Strategy
[Explain how you handle sparse statistics and non-participation in this specific task.]

### 🎨 Gate 2: UI Token Compliance
[List the Tailwind/CSS tokens used. Must match the Midnight Slate system.]

### ✅ Gate 3: Verification Steps (Captured Evidence)
[Example: `curl` or Playwright screenshot evidence of correctness.]

---

# ACTIVE REASONING LOG

## Reasoning: Visuals Agent - Professionalization and Alignment (V3)
*(Status: [DRAFT] - Awaiting Implementation)*

### Context
User prioritized the centralization of the analysis table and professional refinement of the control bar (dropdowns/toggles). The goal is to move beyond functional utility to a premium, "Pro" analytics experience.

### Architectural Decisions
- **Table Centralization**: Keep optimal column widths instead of "stretching" the data. Center the overall table within the 1700px workspace shell.
- **Micro-interactions (Dropdowns)**: Replace standard browser `select` arrows with custom `Lucide` chevrons to ensure visual consistency with the "Midnight Slate" system.
- **Scannability (Alignment)**: Left-align identity columns (Name/Team), center-align badges, and center-align numeric values with `tabular-nums` for professional readability.

### 🛡️ Gate 1: Null-Safety Strategy
Empty or NULL stats will render as a medium-grey horizontal dash (`—`) to maintain grid visual density without cluttering the view.

### 🎨 Gate 2: UI Token Compliance
- **Gradients**: `bg-slate-900/40`, `bg-slate-950/60`, `bg-blue-600/15`.
- **Borders**: `border-slate-800/40`, `border-white/[0.04]`.
- **Text**: `text-slate-400`, `text-blue-400`, `text-slate-100`.

### ✅ Gate 3: Verification Steps (Captured Evidence)
*Pending Implementation*

---
*Maintained by Swarm Scrummaster | Standardized Verification Protocol v1.0*

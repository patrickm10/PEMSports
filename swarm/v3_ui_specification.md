# V3 UI Specification: The Analysis Desk

## 💎 1. Overview

This specification defines the "High-Hardness" UI standards for NFLStatsPro V3. All frontend agents must implement these components using `Vite + React + Tailwind CSS v4`.

---

## 🏗️ 2. Component: The Multi-Season Context Bar

The Context Bar provides the global state for the application. It MUST be persistent and accessible.

### Selection State:

- **BaseSeason**: (Required) The primary year to analyze. Default: `2025`.
- **ComparisonSeason**: (Optional) The year to compare against. Default: `2024`.
- **Mode**: Toggle between `Single Season` and `Cross-Season Delta`.

### UI Implementation:

- **Location**: Top of the Responsive Dock Sidebar.
- **Style**: Transparent glass background (`bg-slate-900/50 backdrop-blur-md`).
- **Interaction**: Selection of a comparison year must trigger a recalculation of the Virtualized Grid columns.

---

## 📊 3. Component: The Virtualized Comparison Grid

The "Analysis Desk" uses high-performance virtualization to handle thousands of player rows while calculating live deltas.

### Technical Requirements:

- **Core Dependency**: `@tanstack/react-table` (MANDATORY INSTALLATION: `npm install @tanstack/react-table`).
- **Virtualization**: `@tanstack/react-virtual`.
- **Row Height**: Fixed `40px` for calculation windowing.
- **Buffer**: 10 rows outside the visible viewport.

### Column Mapping (Cross-Season Mode):

When `ComparisonSeason` is active, every stat column must be replaced by a `StatGroup`:

1. **Current**: `value[BaseSeason]`
2. **Previous**: `value[ComparisonSeason]`
3. **Delta (Δ)**: `Current - Previous` (Rendered with Sky Blue #38bdf8 for positive, Slate for negative).

### Null Handling (Data Integrity):

Implementation must use `Zod` for schema enforcement. **The "High-Hardness" Null-Safety Transformation is defined as follows:**

```typescript
const StatSchema = z.number()
  .nullable()
  .transform((v) => (v === null ? '-' : v)); 

// Delta Calculation Rule:
// If (Current === '-' || Previous === '-') return '-';
// else return (Current - Previous).toFixed(1);
```

---

## 🎨 4. Design Tokens: Midnight Slate (Tailwind v4)

For consistent Glassmorphism, use the following `theme` extensions in your `index.css` or Tailwind config:

### Core Containers:

- **Background**: `bg-[#020617]`
- **Glass Card**: `bg-slate-900/40 backdrop-blur-lg border border-white/10 shadow-2xl`
- **Typography**: `Outfit` (Primary), `JetBrains Mono` (Numeric data).

### CSS Requirement:
```css
@theme {
  --color-glass: rgba(15, 23, 42, 0.4);
  --backdrop-blur-lg: blur(16px);
  --border-white-10: 1px solid rgba(255, 255, 255, 0.1);
}
```

---

## 🧪 5. Verification Steps

Implementation agents must verify their components using the following checklist:

1. **Performance**: Grid scroll remains at native 60fps with 2,000+ rows.
2. **Logic**: Delta columns correctly handle `null` comparison years (no `NaN` or `Infinity`).
3. **Aesthetics**: Glassmorphism blur remains consistent across different Z-index layers.
4. **API Contract**: Verify `curl -s http://localhost:8000/api/v1/rankings/QB?year=2025` returns valid JSON with the expected keys.

---

## 🏆 6. Sovereign Guide: Strong Answers

To prevent immediate **VETO**, any implementation reasoning must satisfy this checklist:

- [ ] **Dependency Audit**: Explicitly state if you have verified the presence of `@tanstack/react-table`.
- [ ] **Null Transformation**: Show the specific `Zod` or `transform` logic for your branch's data model.
- [ ] **Aesthetic Verification**: Provide the specific CSS classes used for the "Responsive Dock".
- [ ] **Verification Subsection**: Include a concrete test path (e.g., "Verify row hydration for player_id 1234").

---

*Signed by the Sovereign Architect*

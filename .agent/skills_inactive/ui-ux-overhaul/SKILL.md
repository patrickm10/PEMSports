---
name: UI/UX Overhaul (Midnight Slate)
description: A specialized skill for implementing premium, industry-standard NFL analytics interfaces (NFL.com/ESPN style) with high-performance React patterns.
---

# UI/UX Overhaul Standards

## 1. Design Standards
- **Color Palette:** Use "Midnight Slate" system.
  - Background: `#020617`.
  - Data Surfaces: `backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.1)`.
- **Typography:** Use **'Outfit'** via Google Fonts.
  - Headers: `font-weight: 700`.
  - Body: `font-weight: 400`.
- **Spacing & Layout:** Flexible grid layout for dynamic resizing of tables, charts, and tabs.
- **Animations:** 
  - Interactive elements: `transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1)`.
  - Include subtle hover and focus states.

## 2. Frontend Architecture & Patterns
- **Component Composition:** Use compound components for tables, tabs, and cards. Allow nested headers and expandable content.
- **State Management:** Use Context + Reducer or Zustand for global state (selected player, week, season, filters).
- **Data Fetching:** React Query for caching. Automatic refetch on season change. Global error/loading handling.
- **Performance Optimization:**
  - `React.memo` for pure components.
  - `useMemo` and `useCallback` for expensive computations.
  - **Virtualization:** Use `@tanstack/react-virtual` for long player lists.
  - **Code Splitting:** Lazy load heavy components (charts, complex visualizations).

## 3. Tab and Position Handling
- **Positions:** Support QB, RB, WR, TE, K, DST.
- **Sync:** Weekly and seasonal tabs must be synchronized with backend data.
- **Graceful Degradation:** Handle missing or partial data with placeholders or empty rows.
- **Dynamic Ranges:** Support seasons 2020–2026.

## 4. Data Display Patterns
- **Conditional Formatting:** Highlight top performers (e.g., Gold/Silver/Bronze or accent colors).
- **Interactivity:** Sortable and filterable columns.
- **Responsiveness:** Hide columns on smaller screens (mobile-first).
- **Metrics:** yards, TDs, completions, EPA, CPOE, Air Yards, DST-stats.
- **Null Handling:** Optional metrics are nullable; UI must not break.

## 5. Form & Interaction Patterns
- **Validation:** Use **Zod** schemas for type safety in controlled forms.
- **Accessibility:** Focus management and keyboard navigation for modals and dropdowns.
- **Error Boundaries:** Surround high-risk components (charts, detail views).

## 6. Animations & Microinteractions
- **Framer Motion:** Use for lists, modals, and tab transitions.
- **Micro-cues:** Subtle hover/focus states on tables and cards.
- **Charts:** Smooth load and update transitions.

## 7. Verification & QA
- **Consistency:** Ensure UI renders consistently across screen sizes.
- **Data Integrity:** Tables/charts must match backend schema exactly.
- **Context Depth:** Support all positions through 2026.

# UI Audit — PEM Sports (production + source)

**Date:** 2026-07-23  
**Surfaces audited:** https://pemsports.com (live bundle `index-B5VrGPqW.js`), source under `frontend/nflstats-pro-ui/`  
**Constraint:** Observations tied to specific screens/components; no generic design advice

---

## 1. Information architecture

| Observation | Evidence |
|-------------|----------|
| Cold start always shows full-screen `LandingPage` before the analytics desk | `App.tsx` `showLanding` defaults `true`; no persistence |
| Three workspaces (Dashboard / Rankings / Player) share one dock, but **filters only render on Rankings** | `App.tsx` wraps `ControlBar` in `workspaceView === 'rankings'` |
| Dashboard charts depend on the same year/week/viewMode state but users cannot change filters without leaving Dashboard | `App.tsx` dashboard `EChart` block uses `filteredData` / `viewMode` while ControlBar is hidden |
| Player analytics is a separate store-driven surface; rankings row click opens legacy `PlayerDetail` modal instead of analytics | `VirtualizedGrid` `onRowClick` → `setSelectedPlayer` |

---

## 2. Navigation and hierarchy

| Observation | Evidence |
|-------------|----------|
| Fixed `Sidebar` always occupies horizontal space; no mobile drawer | `ResponsiveDock.tsx` + `Sidebar.tsx` — no off-canvas / overlay pattern |
| Top chrome label still says **“Midnight Slate”** rather than PEM Sports product context | `ResponsiveDock.tsx` header |
| Density controls duplicated in Sidebar settings and ControlBar | `Sidebar.tsx` density section + `ControlBar.tsx` density toggle |
| Live production still shows **NFLStatsPro V3** on landing | Live bundle scan: `NFLStatsPro` match; local source already `PEM Sports` |

---

## 3. Filter discoverability

| Observation | Evidence |
|-------------|----------|
| Year/week options are API-driven (good) but production `/seasons` returned only `[2025]` for skill positions | Live `GET .../QB/seasons` → `[2025]`; `ControlBar` maps `availableYears` |
| No visible “active filters” chip strip beyond subtitle text | Header subtitle in `App.tsx` only |
| No reset action | `ControlBar.tsx` has no reset; App has no reset handler |
| Week defaults to **first** available week (ASC → Week 1), not latest | `App.tsx` effect uses `availableWeeks[0]`; backend weeks ASC |
| Year/week `<select>` elements lack accessible names | `ControlBar.tsx` selects have no `aria-label` / `<label>` |
| Season/Weekly toggle lacks `aria-pressed` | `ControlBar.tsx` mode buttons |

---

## 4. Table readability and density

| Observation | Evidence |
|-------------|----------|
| Virtualized table with density modes is solid for desktop | `VirtualizedGrid.tsx` |
| Mobile card layout exists at ≤768px | `VirtualizedGrid.tsx` card branch |
| Empty state is generic; does not explain filter vs API failure | Grid empty copy; App only destructures `isLoading` from `activeQuery` |
| Sortable headers lack `aria-sort` / `scope` | `VirtualizedGrid.tsx` `<th>` sort handlers |

---

## 5. Charts

| Observation | Evidence |
|-------------|----------|
| Rankings Top 10 and grid both receive `filteredData` (same source) | `App.tsx` |
| Chart builders re-sort/slice independently of grid rank order | `chartOptions.ts` top-10 by metric; grid default sort by `rank` |
| Dashboard facet charts empty in season mode with instructional empty copy | `App.tsx` emptyMessage strings for opponent/surface/venue |
| Presentation contract debt: StatsSummary averages metrics client-side | `StatsSummary.tsx` reduce — flagged in frontend-presentation-contract |

---

## 6. Loading / empty / error / stale

| Observation | Evidence |
|-------------|----------|
| Loading wired for summary + charts + grid skeleton path | `isLoading` passed through |
| **No `isError` / retry UI** on rankings queries | `App.tsx` line ~111 |
| Loading and empty share StatsSummary skeleton treatment | `StatsSummary.tsx` |
| Seasons query cache TTL 1h can keep stale year lists after deploy | `useSeasons.ts` |

---

## 7. Mobile / keyboard / a11y

| Observation | Evidence |
|-------------|----------|
| Auth menu is hover-reveal only | `ControlBar.tsx` `group-hover/auth` dropdown |
| Search modal has strong ARIA (combobox, focus trap) | `SearchModal.tsx`, `Modal.tsx` |
| No skip link; no `prefers-reduced-motion` | repo-wide search |
| Placeholder contrast `placeholder:text-slate-600` on `#020617` | `ControlBar.tsx` input |
| Live CSS: no `focus-visible` utilities in built CSS | production CSS scan |

---

## 8. Brand and trust

| Observation | Evidence |
|-------------|----------|
| Live title `nflstats-pro-ui`; local `PEM Sports` | live HTML vs `index.html` |
| Landing copy “NFL data exploration suite” | `LandingPage.tsx` |
| Footer copyright still 2025 | `LandingPage.tsx` |
| No data-freshness / coverage indicator | ControlBar shows player count only when `totalPlayers > 0` |
| API root still “NFL Stats Analyzer API” | live production probe |

---

## Priority UI corrections (implementation targets)

1. Global filter shell on Dashboard + Rankings with active context, reset, row count, coverage years available.
2. Distinct loading / empty / error / retry states sharing `filteredData`.
3. Accessible labels, `aria-pressed`, keyboard auth menu, mobile nav overlay.
4. Persist landing skip; PEM Sports chrome (replace Midnight Slate product label).
5. Default week to latest available; keep years from API only.
6. Preserve `filteredData` as sole row contract; charts continue to consume that array (no second fetch).

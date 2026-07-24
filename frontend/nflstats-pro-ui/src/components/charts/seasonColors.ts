export const CHART_PALETTE = [
  '#38bdf8', // sky
  '#22c55e', // green
  '#f97316', // orange
  '#a78bfa', // purple
  '#ec4899', // pink
  '#facc15', // yellow
] as const;

/**
 * Central, deterministic season → color mapping.
 *
 * Requirement:
 * - season 2025 must use the exact color previously assigned to season 2021.
 *
 * The dashboard previously used the palette order above; 2021 was using `#ec4899`.
 * We explicitly map 2025 to `#ec4899` and swap 2021 to the prior 2025 default.
 */
const SEASON_OVERRIDES: Record<number, string> = {
  2025: '#ec4899',
  2022: '#9D00FF',
  2020: '#F0EAD6',
  2021: '#38bdf8',
};

export function getSeasonColor(year: number): string {
  if (Number.isFinite(year) && SEASON_OVERRIDES[year]) return SEASON_OVERRIDES[year];
  if (!Number.isFinite(year)) return CHART_PALETTE[0];
  // Deterministic fallback for unexpected years.
  const idx = Math.abs(year) % CHART_PALETTE.length;
  return CHART_PALETTE[idx];
}


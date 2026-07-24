/**
 * Pure filter-state helpers for rankings metadata.
 * Years/weeks/positions always come from API metadata — never hardcoded lists.
 */

export type ViewMode = 'season' | 'weekly';

export interface FilterSnapshot {
  viewMode: ViewMode;
  year: string;
  week: string;
  searchQuery: string;
}

export function pickDefaultYear(
  availableYears: number[],
  currentYear: string,
): string {
  if (availableYears.length === 0) return '';
  const parsed = Number.parseInt(currentYear, 10);
  if (Number.isFinite(parsed) && availableYears.includes(parsed)) {
    return currentYear;
  }
  return String(availableYears[0]);
}

/** Prefer the latest available week (metadata is typically ASC). */
export function pickDefaultWeek(
  availableWeeks: number[],
  currentWeek: string,
): string {
  if (availableWeeks.length === 0) return '';
  const parsed = Number.parseInt(currentWeek, 10);
  if (Number.isFinite(parsed) && availableWeeks.includes(parsed)) {
    return currentWeek;
  }
  return String(availableWeeks[availableWeeks.length - 1]);
}

export function isValidYear(year: string, availableYears: number[]): boolean {
  const parsed = Number.parseInt(year, 10);
  return Number.isFinite(parsed) && availableYears.includes(parsed);
}

export function isValidWeek(week: string, availableWeeks: number[]): boolean {
  const parsed = Number.parseInt(week, 10);
  return Number.isFinite(parsed) && availableWeeks.includes(parsed);
}

export function buildResetFilters(
  availableYears: number[],
  availableWeeks: number[],
): FilterSnapshot {
  return {
    viewMode: 'season',
    year: pickDefaultYear(availableYears, ''),
    week: pickDefaultWeek(availableWeeks, ''),
    searchQuery: '',
  };
}

export function formatActiveFilterSummary(
  position: string,
  viewMode: ViewMode,
  year: string,
  week: string,
  rowCount: number,
  availableYearCount: number,
): string {
  const pos = position.toUpperCase();
  const scope =
    viewMode === 'weekly' && week
      ? `${year || '—'} · Week ${week}`
      : `${year || '—'} · Season`;
  return `${pos} · ${scope} · ${rowCount} rows · ${availableYearCount} seasons available`;
}

const LANDING_SKIP_KEY = 'pem-sports:skip-landing';

export function shouldSkipLanding(): boolean {
  try {
    return localStorage.getItem(LANDING_SKIP_KEY) === '1';
  } catch {
    return false;
  }
}

export function persistLandingSkip(): void {
  try {
    localStorage.setItem(LANDING_SKIP_KEY, '1');
  } catch {
    // ignore quota / private mode
  }
}

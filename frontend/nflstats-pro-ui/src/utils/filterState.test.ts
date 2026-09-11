import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  buildResetFilters,
  formatActiveFilterSummary,
  isValidWeek,
  isValidYear,
  persistLandingSkip,
  pickDefaultWeek,
  pickDefaultYear,
  shouldSkipLanding,
} from './filterState';

describe('filterState', () => {
  const years = [2025, 2024, 2023, 2022, 2021, 2020];
  const weeks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18];

  it('defaults year to newest available without hardcoding 2025', () => {
    expect(pickDefaultYear(years, '')).toBe('2025');
    expect(pickDefaultYear([2024, 2023], '')).toBe('2024');
  });

  it('enables rankings year and week on the same render metadata arrives', () => {
    const queryYear = pickDefaultYear(years, '');
    const queryWeek = pickDefaultWeek(weeks, '');
    expect(queryYear).toBe('2025');
    expect(isValidYear(queryYear, years)).toBe(true);
    expect(queryWeek).toBe('18');
    expect(isValidWeek(queryWeek, weeks)).toBe(true);
  });

  it('preserves a valid selected year across metadata refresh', () => {
    expect(pickDefaultYear(years, '2022')).toBe('2022');
  });

  it('does not force year back to 2025 when 2022 is valid', () => {
    expect(pickDefaultYear(years, '2022')).not.toBe('2025');
  });

  it('defaults week to the latest available week', () => {
    expect(pickDefaultWeek(weeks, '')).toBe('18');
  });

  it('reset clears search and returns season mode with metadata defaults', () => {
    const reset = buildResetFilters(years, weeks);
    expect(reset).toEqual({
      viewMode: 'season',
      year: '2025',
      week: '18',
      searchQuery: '',
    });
  });

  it('validates years and weeks against API metadata only', () => {
    expect(isValidYear('2020', years)).toBe(true);
    expect(isValidYear('2019', years)).toBe(false);
    expect(isValidWeek('18', weeks)).toBe(true);
    expect(isValidWeek('19', weeks)).toBe(false);
  });

  it('formats active filter summary with row and coverage counts', () => {
    const summary = formatActiveFilterSummary('qb', 'weekly', '2024', '3', 42, 6);
    expect(summary).toContain('QB');
    expect(summary).toContain('2024');
    expect(summary).toContain('Week 3');
    expect(summary).toContain('42 rows');
    expect(summary).toContain('6 seasons available');
  });
});

describe('landing skip persistence', () => {
  const store = new Map<string, string>();

  beforeEach(() => {
    store.clear();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
      clear: () => store.clear(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('does not skip landing before persist', () => {
    expect(shouldSkipLanding()).toBe(false);
  });

  it('skips landing after persistLandingSkip', () => {
    persistLandingSkip();
    expect(shouldSkipLanding()).toBe(true);
    expect(store.get('pem-sports:skip-landing')).toBe('1');
  });

  it('returns false when localStorage throws', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('blocked');
      },
    });
    expect(shouldSkipLanding()).toBe(false);
    expect(() => persistLandingSkip()).not.toThrow();
  });
});

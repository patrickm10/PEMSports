import type { Ranking } from '../models/Ranking';

export interface ResolvedMetric {
  key: 'fpts_ppr' | 'fpts';
  label: string;
  shortLabel: string;
  getValue: (row: Ranking) => number | null;
}

const METRIC_CANDIDATES: readonly Omit<ResolvedMetric, 'getValue'>[] = [
  { key: 'fpts_ppr', label: 'PPR Points', shortLabel: 'PPR' },
  { key: 'fpts', label: 'Fantasy Points', shortLabel: 'FP' },
];

function toFiniteNumber(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  return value;
}

export function resolvePrimaryMetric(rows: Ranking[]): ResolvedMetric | null {
  for (const candidate of METRIC_CANDIDATES) {
    const hasValue = rows.some((row) => toFiniteNumber(row[candidate.key]) !== null);
    if (hasValue) {
      return {
        ...candidate,
        getValue: (row) => toFiniteNumber(row[candidate.key]),
      };
    }
  }

  return null;
}

export function formatMetricValue(value: number | null | undefined): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : '—';
}

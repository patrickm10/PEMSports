import type {
  CategoricalChartModel,
  MetadataOverlayModel,
  TimeSeriesChartModel,
} from '../components/charts/contract';
import type {
  PlayerMetadataResponse,
  PlayerSplitResponse,
  PlayerSplitByYearResponse,
  PlayerWeeklyResponse,
  WeeklyMetricKey,
} from './playerTypes';

/**
 * The single boundary that translates schema-stable API responses into the
 * chart data contract. Pure functions, no React, fully unit-testable.
 *
 * Rules:
 * - Never mutate inputs.
 * - Treat null as the only "missing" signal; do not invent zeros.
 * - When given a comparison response, align categories so each series has the
 *   same length (filling missing buckets with null).
 */

const DEFAULT_PRIMARY_COLOR = '#38bdf8';
const DEFAULT_COMPARISON_COLOR = '#f97316';

export type CategoricalMetric = 'avg_ppr' | 'avg_yards' | 'avg_tds';

const YEAR_COLORS = [
  '#38bdf8',
  '#22c55e',
  '#f97316',
  '#a78bfa',
  '#ec4899',
  '#facc15',
];

function uniqueOrdered(values: ReadonlyArray<string>): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const v of values) {
    if (!seen.has(v)) {
      seen.add(v);
      out.push(v);
    }
  }
  return out;
}

function pickCategorical(
  resp: PlayerSplitResponse,
  metric: CategoricalMetric,
): Map<string, number | null> {
  const map = new Map<string, number | null>();
  for (const row of resp.splits) {
    map.set(row.key, row[metric]);
  }
  return map;
}

export function toCategoricalChartModel(
  primary: PlayerSplitResponse,
  comparison: PlayerSplitResponse | null = null,
  metric: CategoricalMetric = 'avg_ppr',
  options?: { primaryName?: string; comparisonName?: string; topN?: number },
): CategoricalChartModel {
  const primaryName = options?.primaryName ?? primary.player_id;
  const comparisonName = options?.comparisonName ?? comparison?.player_id ?? '';
  const topN = options?.topN;

  const primaryCats = primary.splits.map((s) => s.key);
  const comparisonCats = comparison?.splits.map((s) => s.key) ?? [];
  let categories = uniqueOrdered([...primaryCats, ...comparisonCats]);
  if (typeof topN === 'number' && topN > 0) {
    categories = categories.slice(0, topN);
  }

  const primaryMap = pickCategorical(primary, metric);
  const series = [
    {
      name: primaryName,
      values: categories.map((c) =>
        primaryMap.has(c) ? (primaryMap.get(c) as number | null) : null,
      ),
      color: DEFAULT_PRIMARY_COLOR,
    },
  ];

  if (comparison) {
    const cmpMap = pickCategorical(comparison, metric);
    series.push({
      name: comparisonName,
      values: categories.map((c) =>
        cmpMap.has(c) ? (cmpMap.get(c) as number | null) : null,
      ),
      color: DEFAULT_COMPARISON_COLOR,
    });
  }

  return {
    categories,
    series,
    valueFormatter: (v) => (v === null ? '—' : v.toFixed(1)),
  };
}

export function toYearlyCategoricalChartModel(
  primary: PlayerSplitByYearResponse,
  comparison: PlayerSplitByYearResponse | null = null,
  metric: CategoricalMetric = 'avg_ppr',
  options?: { primaryName?: string; comparisonName?: string; topN?: number },
): CategoricalChartModel {
  const primaryName = options?.primaryName ?? primary.player_id;
  const comparisonName = options?.comparisonName ?? comparison?.player_id ?? '';
  const topN = options?.topN;

  // Categories must be stable and meaningful. The API returns rows ordered by
  // (year desc, avg desc), which is not a good proxy for which buckets matter
  // most to the player. Build categories from the union of keys and sort by
  // total games across all years (and both players, when comparing).
  const primaryKeys = primary.rows.map((r) => r.key);
  const comparisonKeys = comparison ? comparison.rows.map((r) => r.key) : [];
  const categoriesAll = uniqueOrdered([...primaryKeys, ...comparisonKeys]).filter(Boolean);

  const gamesByKey = new Map<string, number>();
  for (const r of primary.rows) {
    const key = r.key;
    if (!key) continue;
    gamesByKey.set(key, (gamesByKey.get(key) ?? 0) + (r.games ?? 0));
  }
  if (comparison) {
    for (const r of comparison.rows) {
      const key = r.key;
      if (!key) continue;
      gamesByKey.set(key, (gamesByKey.get(key) ?? 0) + (r.games ?? 0));
    }
  }

  const categoriesRanked = [...categoriesAll].sort((a, b) => {
    const ga = gamesByKey.get(a) ?? 0;
    const gb = gamesByKey.get(b) ?? 0;
    if (gb !== ga) return gb - ga;
    return a.localeCompare(b);
  });

  const categories =
    typeof topN === 'number' && topN > 0 ? categoriesRanked.slice(0, topN) : categoriesRanked;

  // Guardrail: ECharts hover/highlight work scales with (#series × #categories).
  // Player split-by-year can span many seasons in the baked DB; cap the rendered
  // series count to keep interactions responsive.
  const MAX_YEARS = 6;
  const years = (primary.years ?? []).slice(0, MAX_YEARS);

  const valueByYearKey = new Map<string, Map<number, number | null>>();
  for (const r of primary.rows) {
    if (!valueByYearKey.has(r.key)) valueByYearKey.set(r.key, new Map());
    valueByYearKey.get(r.key)!.set(r.year, (r as any)[metric] as number | null);
  }

  const series = years.map((year, idx) => ({
    name: comparison ? `${primaryName} · ${year}` : String(year),
    values: categories.map((k) => valueByYearKey.get(k)?.get(year) ?? null),
    color: YEAR_COLORS[idx % YEAR_COLORS.length],
  }));

  if (comparison) {
    const cmpYears = (comparison.years ?? []).slice(0, MAX_YEARS);
    const cmpValueByYearKey = new Map<string, Map<number, number | null>>();
    for (const r of comparison.rows) {
      if (!cmpValueByYearKey.has(r.key)) cmpValueByYearKey.set(r.key, new Map());
      cmpValueByYearKey.get(r.key)!.set(r.year, (r as any)[metric] as number | null);
    }

    const cmpSeries = cmpYears.map((year, idx) => ({
      name: `${comparisonName} · ${year}`,
      values: categories.map((k) => cmpValueByYearKey.get(k)?.get(year) ?? null),
      // keep color alignment by year index (not player) for readability
      color: YEAR_COLORS[idx % YEAR_COLORS.length],
    }));
    series.push(...cmpSeries);
  }

  return {
    categories,
    series,
    valueFormatter: (v) => (v === null ? '—' : v.toFixed(1)),
  };
}

export function toTimeSeriesChartModel(
  primary: PlayerWeeklyResponse,
  comparison: PlayerWeeklyResponse | null = null,
  metric: WeeklyMetricKey = 'ppr_fpts',
  options?: { primaryName?: string; comparisonName?: string },
): TimeSeriesChartModel {
  const primaryName = options?.primaryName ?? primary.player_id;
  const comparisonName = options?.comparisonName ?? comparison?.player_id ?? '';

  const primaryWeeks = new Set<number>();
  for (const s of primary.seasons) for (const w of s.weeks) primaryWeeks.add(w.week);
  if (comparison) {
    for (const s of comparison.seasons)
      for (const w of s.weeks) primaryWeeks.add(w.week);
  }
  const xAxis = Array.from(primaryWeeks).sort((a, b) => a - b);

  const series: TimeSeriesChartModel['series'] = [];

  // Same guardrail as split-by-year: too many line series makes hover/tooltips
  // expensive. Prefer the most recent seasons for readability.
  const MAX_SEASONS = 6;
  const primarySeasons = primary.seasons.slice(0, MAX_SEASONS);
  for (const season of primarySeasons) {
    const lookup = new Map<number, number | null>(
      season.weeks.map((w) => [w.week, w[metric]]),
    );
    series.push({
      name: comparison
        ? `${primaryName} · ${season.year}`
        : String(season.year),
      points: xAxis.map((week) => ({
        x: week,
        y: lookup.has(week) ? (lookup.get(week) as number | null) : null,
      })),
    });
  }

  if (comparison) {
    const comparisonSeasons = comparison.seasons.slice(0, MAX_SEASONS);
    for (const season of comparisonSeasons) {
      const lookup = new Map<number, number | null>(
        season.weeks.map((w) => [w.week, w[metric]]),
      );
      series.push({
        name: `${comparisonName} · ${season.year}`,
        points: xAxis.map((week) => ({
          x: week,
          y: lookup.has(week) ? (lookup.get(week) as number | null) : null,
        })),
      });
    }
  }

  return {
    xAxis,
    series,
    xAxisLabel: 'Week',
    valueFormatter: (v) => (v === null ? '—' : v.toFixed(1)),
  };
}

export function toMetadataOverlayModel(
  resp: PlayerMetadataResponse,
): MetadataOverlayModel {
  const ha = resp.splits.home_away;
  return {
    homeAway: {
      home: {
        games: ha.home.games,
        ppr: ha.home.avg_ppr,
        yards: ha.home.avg_yards,
        tds: ha.home.avg_tds,
      },
      away: {
        games: ha.away.games,
        ppr: ha.away.avg_ppr,
        yards: ha.away.avg_yards,
        tds: ha.away.avg_tds,
      },
    },
    rest: resp.splits.rest_buckets.map((b) => ({
      bucket: b.bucket,
      row: {
        games: b.aggregate.games,
        ppr: b.aggregate.avg_ppr,
        yards: b.aggregate.avg_yards,
        tds: b.aggregate.avg_tds,
      },
    })),
    weather: resp.splits.weather_impact.map((w) => ({
      key: w.key,
      row: {
        games: w.aggregate.games,
        ppr: w.aggregate.avg_ppr,
        yards: w.aggregate.avg_yards,
        tds: w.aggregate.avg_tds,
      },
    })),
  };
}

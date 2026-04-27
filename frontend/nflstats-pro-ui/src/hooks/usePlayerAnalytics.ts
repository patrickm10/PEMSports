import { useMemo } from 'react';
import { useQueries, type UseQueryResult } from '@tanstack/react-query';
import { PlayersApi } from '../api/playersApi';
import {
  toMetadataOverlayModel,
  toTimeSeriesChartModel,
  toYearlyCategoricalChartModel,
} from '../api/normalizers';
import type {
  CategoricalChartModel,
  MetadataOverlayModel,
  TimeSeriesChartModel,
} from '../components/charts/contract';
import type {
  PlayerMetadataResponse,
  PlayerSearchHit,
  PlayerSplitByYearResponse,
  PlayerWeeklyResponse,
  SplitDimension,
} from '../api/playerTypes';
import type { PlayerRef } from '../stores/types';

export interface PanelResource<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
}

export interface PlayerAnalyticsResult {
  vsOpponent: PanelResource<CategoricalChartModel>;
  stadium: PanelResource<CategoricalChartModel>;
  surface: PanelResource<CategoricalChartModel>;
  venue: PanelResource<CategoricalChartModel>;
  weekly: PanelResource<TimeSeriesChartModel>;
  metadata: PanelResource<MetadataOverlayModel>;
  volumes: {
    weekly: number;
    opponent: number;
    stadium: number;
    surface: number;
    metadata: number;
  };
  recency: {
    weekly: number;
    opponent: number;
    stadium: number;
    surface: number;
    metadata: number;
  };
  isAnyLoading: boolean;
}

const SPLIT_DIMENSIONS: SplitDimension[] = [
  'opponent',
  'stadium',
  'surface',
  'venue',
];

const EMPTY_RESOURCE: PanelResource<never> = {
  data: null,
  isLoading: false,
  error: null,
};

function countCategoricalValues(model: CategoricalChartModel | null): number {
  if (!model) return 0;
  let c = 0;
  for (const s of model.series) for (const v of s.values) if (v !== null) c++;
  return c;
}

function countTimeSeriesValues(model: TimeSeriesChartModel | null): number {
  if (!model) return 0;
  let c = 0;
  for (const s of model.series) for (const p of s.points) if (p.y !== null) c++;
  return c;
}

function countMetadataCells(model: MetadataOverlayModel | null): number {
  if (!model) return 0;
  // home/away always 2; plus each rest bucket + each weather key
  return 2 + model.rest.length + model.weather.length;
}

function parseTrailingYear(label: string): number | null {
  const m = label.match(/(\d{4})\s*$/);
  if (!m) return null;
  const y = Number.parseInt(m[1], 10);
  return Number.isFinite(y) ? y : null;
}

function recencyCategorical(model: CategoricalChartModel | null): number {
  if (!model) return 0;
  let best = 0;
  for (const s of model.series) {
    const y = parseTrailingYear(s.name);
    if (y !== null) best = Math.max(best, y * 100);
  }
  return best;
}

function recencyTimeSeries(model: TimeSeriesChartModel | null): number {
  if (!model) return 0;
  let best = 0;
  for (const s of model.series) {
    const y = parseTrailingYear(s.name);
    if (y === null) continue;
    let lastWeek = 0;
    for (const p of s.points) {
      if (p.y === null) continue;
      const w =
        typeof p.x === 'number'
          ? p.x
          : Number.isFinite(Number.parseInt(String(p.x), 10))
            ? Number.parseInt(String(p.x), 10)
            : 0;
      if (w > lastWeek) lastWeek = w;
    }
    best = Math.max(best, y * 100 + lastWeek);
  }
  return best;
}

function asResource<T>(query: UseQueryResult<T>): PanelResource<T> {
  return {
    data: (query.data ?? null) as T | null,
    isLoading: query.isLoading || query.isFetching,
    error: (query.error as Error) ?? null,
  };
}

function refLabel(ref: PlayerRef | PlayerSearchHit | null): string {
  return ref?.player_name ?? ref?.player_id ?? '';
}

/**
 * Centralized orchestration for the player-analytics surface.
 *
 * Fans out one React Query call per resource (one per split dimension,
 * plus weekly + metadata, doubled when comparing two players), and runs
 * the matching normalizer to produce stable chart-data contracts. Panels
 * read slices from this single result and never fetch directly.
 */
export function usePlayerAnalytics(
  player: PlayerRef | null,
  comparison: PlayerRef | null = null,
): PlayerAnalyticsResult {
  const playerId = player?.player_id ?? null;
  const position = player?.position?.toLowerCase() ?? null;
  const enabled = Boolean(playerId && position);

  const cmpId = comparison?.player_id ?? null;
  const cmpPos = comparison?.position?.toLowerCase() ?? null;
  const cmpEnabled = Boolean(cmpId && cmpPos);

  const splitQueries = useQueries({
    queries: SPLIT_DIMENSIONS.flatMap((dim) => [
      {
        queryKey: ['player', playerId, 'splitsByYear', dim, position],
        queryFn: ({ signal }: { signal: AbortSignal }) =>
          PlayersApi.splitsByYear(playerId!, position!, dim, signal),
        enabled,
        staleTime: 60_000,
      },
      {
        queryKey: ['player', cmpId, 'splitsByYear', dim, cmpPos],
        queryFn: ({ signal }: { signal: AbortSignal }) =>
          PlayersApi.splitsByYear(cmpId!, cmpPos!, dim, signal),
        enabled: cmpEnabled,
        staleTime: 60_000,
      },
    ]),
  }) as Array<UseQueryResult<PlayerSplitByYearResponse>>;

  const weeklyQueries = useQueries({
    queries: [
      {
        queryKey: ['player', playerId, 'weekly', position],
        queryFn: ({ signal }: { signal: AbortSignal }) =>
          PlayersApi.weekly(playerId!, position!, undefined, signal),
        enabled,
        staleTime: 60_000,
      },
      {
        queryKey: ['player', cmpId, 'weekly', cmpPos],
        queryFn: ({ signal }: { signal: AbortSignal }) =>
          PlayersApi.weekly(cmpId!, cmpPos!, undefined, signal),
        enabled: cmpEnabled,
        staleTime: 60_000,
      },
    ],
  }) as Array<UseQueryResult<PlayerWeeklyResponse>>;

  const metaQuery = useQueries({
    queries: [
      {
        queryKey: ['player', playerId, 'metadata', position],
        queryFn: ({ signal }: { signal: AbortSignal }) =>
          PlayersApi.metadata(playerId!, position!, signal),
        enabled,
        staleTime: 60_000,
      },
    ],
  })[0] as UseQueryResult<PlayerMetadataResponse>;

  return useMemo<PlayerAnalyticsResult>(() => {
    if (!enabled) {
      return {
        vsOpponent: EMPTY_RESOURCE,
        stadium: EMPTY_RESOURCE,
        surface: EMPTY_RESOURCE,
        venue: EMPTY_RESOURCE,
        weekly: EMPTY_RESOURCE,
        metadata: EMPTY_RESOURCE,
        volumes: {
          weekly: 0,
          opponent: 0,
          stadium: 0,
          surface: 0,
          metadata: 0,
        },
        recency: {
          weekly: 0,
          opponent: 0,
          stadium: 0,
          surface: 0,
          metadata: 0,
        },
        isAnyLoading: false,
      };
    }

    const primaryName = refLabel(player);
    const comparisonName = refLabel(comparison);

    const dimResource = (
      idx: number,
      topN?: number,
    ): PanelResource<CategoricalChartModel> => {
      const primary = splitQueries[idx * 2];
      const cmp = splitQueries[idx * 2 + 1];
      const data =
        primary.data
          ? toYearlyCategoricalChartModel(
              primary.data,
              cmpEnabled ? cmp.data ?? null : null,
              'avg_ppr',
              {
                primaryName,
                comparisonName,
                topN,
              },
            )
          : null;
      return {
        data,
        isLoading: primary.isLoading || (cmpEnabled && cmp.isLoading),
        error:
          ((primary.error as Error) ?? null) ||
          ((cmpEnabled ? (cmp.error as Error) : null) ?? null),
      };
    };

    const weeklyPrimary = weeklyQueries[0];
    const weeklyCmp = weeklyQueries[1];
    const weekly: PanelResource<TimeSeriesChartModel> = {
      data: weeklyPrimary.data
        ? toTimeSeriesChartModel(
            weeklyPrimary.data,
            cmpEnabled ? weeklyCmp.data ?? null : null,
            'ppr_fpts',
            { primaryName, comparisonName },
          )
        : null,
      isLoading:
        weeklyPrimary.isLoading || (cmpEnabled && weeklyCmp.isLoading),
      error:
        ((weeklyPrimary.error as Error) ?? null) ||
        ((cmpEnabled ? (weeklyCmp.error as Error) : null) ?? null),
    };

    const metadata: PanelResource<MetadataOverlayModel> = {
      data: metaQuery.data ? toMetadataOverlayModel(metaQuery.data) : null,
      isLoading: metaQuery.isLoading || metaQuery.isFetching,
      error: (metaQuery.error as Error) ?? null,
    };

    // Opponent is naturally bounded (~32 teams). Do NOT apply cross-season Top-N
    // slicing, which can make some seasons look artificially sparse.
    const vsOpponent = dimResource(0);
    const stadium = dimResource(1, 16);
    const surface = dimResource(2);

    const isAnyLoading =
      splitQueries.some((q) => q.isLoading || q.isFetching) ||
      weekly.isLoading ||
      metadata.isLoading;

    return {
      vsOpponent,
      stadium,
      surface,
      venue: dimResource(3),
      weekly,
      metadata,
      volumes: {
        weekly: countTimeSeriesValues(weekly.data),
        opponent: countCategoricalValues(vsOpponent.data),
        stadium: countCategoricalValues(stadium.data),
        surface: countCategoricalValues(surface.data),
        metadata: countMetadataCells(metadata.data),
      },
      recency: {
        weekly: recencyTimeSeries(weekly.data),
        opponent: recencyCategorical(vsOpponent.data),
        stadium: recencyCategorical(stadium.data),
        surface: recencyCategorical(surface.data),
        metadata: 0,
      },
      isAnyLoading,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    enabled,
    cmpEnabled,
    player,
    comparison,
    // Track loading + data per query so memo refreshes when fetches resolve.
    ...splitQueries.map((q) => q.data),
    ...splitQueries.map((q) => q.isLoading),
    ...weeklyQueries.map((q) => q.data),
    ...weeklyQueries.map((q) => q.isLoading),
    metaQuery.data,
    metaQuery.isLoading,
  ]);
}

// re-export to consumers that want the stripped-down resource type
export { asResource };

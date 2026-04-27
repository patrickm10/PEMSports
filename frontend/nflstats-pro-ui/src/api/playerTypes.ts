/**
 * Schema-stable backend contract for the player-analytics surface.
 *
 * Every key listed here MUST be present in every response, including with
 * null values. Never omit a key based on column availability — null is the
 * single signal for "value not known" so the frontend can render a stable
 * UI placeholder ("—") rather than branch on key presence.
 */

export type PositionCode = 'qb' | 'rb' | 'wr' | 'te' | 'k' | 'dst';

export type SplitDimension = 'opponent' | 'stadium' | 'surface' | 'venue';

export interface PlayerSearchHit {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  headshot_url: string | null;
  current_season_rank: number | null;
  match_score: number;
}

export interface PlayerSearchResponse {
  results: PlayerSearchHit[];
}

export interface PlayerSplitRow {
  key: string;
  games: number;
  avg_ppr: number | null;
  total_ppr: number | null;
  avg_yards: number | null;
  avg_tds: number | null;
}

export interface PlayerSplitResponse {
  player_id: string;
  position: string;
  dimension: SplitDimension;
  splits: PlayerSplitRow[];
}

export interface PlayerSplitByYearRow {
  year: number;
  key: string;
  games: number;
  avg_ppr: number | null;
  total_ppr: number | null;
  avg_yards: number | null;
  avg_tds: number | null;
}

export interface PlayerSplitByYearResponse {
  player_id: string;
  position: string;
  dimension: SplitDimension;
  years: number[];
  rows: PlayerSplitByYearRow[];
}

export interface PlayerWeeklyRow {
  week: number;
  ppr_fpts: number | null;
  fantasy_points: number | null;
  yards: number | null;
  tds: number | null;
  opponent: string | null;
  stadium_name: string | null;
  surface_type: string | null;
  indoor_outdoor: string | null;
  home_away: 'HOME' | 'AWAY' | null;
  rest_days: number | null;
  temp: number | null;
  humidity: number | null;
  wind: number | null;
  weather_impact: string | null;
}

export type WeeklyMetricKey = 'ppr_fpts' | 'fantasy_points' | 'yards' | 'tds';

export interface PlayerWeeklySeason {
  year: number;
  weeks: PlayerWeeklyRow[];
}

export interface PlayerWeeklyResponse {
  player_id: string;
  position: string;
  metric_keys: ReadonlyArray<WeeklyMetricKey>;
  seasons: PlayerWeeklySeason[];
}

export interface MetadataAggregate {
  games: number;
  avg_ppr: number | null;
  avg_yards: number | null;
  avg_tds: number | null;
}

export interface PlayerMetadataResponse {
  player_id: string;
  position: string;
  splits: {
    home_away: { home: MetadataAggregate; away: MetadataAggregate };
    rest_buckets: Array<{
      bucket: '<6' | '6-7' | '8-13' | '14+';
      aggregate: MetadataAggregate;
    }>;
    weather_impact: Array<{ key: string; aggregate: MetadataAggregate }>;
  };
}

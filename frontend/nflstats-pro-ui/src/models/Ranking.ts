/**
 * Base shared ranking fields across all schemas.
 *
 * The zod schemas in `v3/schemas/player.ts` are the source of truth at
 * runtime. These TypeScript interfaces mirror them so consumers can type
 * their render code. `[key: string]: unknown` covers position-specific
 * metrics (cmp, att, int, sacks, etc.) that bake_db.py adds and the grid
 * renders dynamically.
 */
export interface BaseRanking {
  [key: string]: unknown;
  year: number;
  player_id: string;
  player_name: string;
  team: string | null;
  position?: string;
  games_played: number | null;
  fpts: number;
  fpts_ppr: number;
  fpts_per_game: number;
  fpts_ppr_per_game: number;
  rank?: number;

  // Analytical fields
  targets?: number;
  rec?: number;
  yds?: number;
  td?: number;
}

export interface SeasonalRanking extends BaseRanking {
  season?: string;
  week?: undefined;
}

export interface WeeklyRanking extends BaseRanking {
  week: number;

  // Contextual Matchup / Environmental Data
  opponent: string | null;
  stadium_name: string | null;
  city: string | null;
  state: string | null;
  indoor_outdoor: string | null;
  surface_type: string | null;
  elevation: number | null;
  weather_impact: string | null;
  year_opened: number | null;
  temp: number | null;
  humidity: number | null;
  wind: number | null;
  game_result: string | null;
}

export type Ranking = SeasonalRanking | WeeklyRanking;

export const isWeeklyRanking = (r: Ranking): r is WeeklyRanking =>
  typeof (r as WeeklyRanking).week === 'number';

export type SortOrder = 'asc' | 'desc';
export type SortField = string;

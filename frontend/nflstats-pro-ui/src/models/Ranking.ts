/**
 * Base shared ranking fields across all schemas.
 */
export interface BaseRanking {
  [key: string]: any;
  year: number;
  player_id: string;
  player_name: string;
  team: string;
  position: string;
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
  season: string;
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
  temp: number | null;
  humidity: number | null;
  wind: number | null;
  game_result: string | null;

  // ML Predictive Fields (Weekly Alpha v1)
  predicted_alpha?: number;
  smart_projection?: number;
  insight_flags?: string[];
}

export type Ranking = SeasonalRanking | WeeklyRanking;

export type SortOrder = 'asc' | 'desc';
export type SortField = string;

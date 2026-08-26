export type InsightPosition = 'all' | 'qb' | 'rb' | 'wr' | 'te';

export type InsightContext = 'surface' | 'opponent' | 'stadium' | 'home_away';

export type SampleStrength = 'Low' | 'Moderate' | 'Strong';

export interface InsightRow {
  player_id: string;
  player_name: string | null;
  team: string | null;
  position: string;
  sample_size: number;
  baseline_value: number | null;
  context_average: number | null;
  absolute_delta: number | null;
  relative_delta_pct: number | null;
  sample_strength: SampleStrength;
  insight_score: number | null;
}

export interface InsightPositionGroup {
  position: string;
  insights: InsightRow[];
}

export interface InsightsLeaderboardResponse {
  position: InsightPosition;
  context: InsightContext;
  context_value: string;
  metric: string;
  year: number | null;
  week: number | null;
  years: number[] | null;
  insights: InsightRow[] | null;
  groups: InsightPositionGroup[] | null;
}

export interface InsightObservation {
  season: number;
  week: number;
  opponent: string | null;
  stadium_name: string | null;
  surface_type: string | null;
  home_away: string | null;
  fantasy_points: number | null;
  season_baseline: number | null;
  relative_change_pct: number | null;
  in_context: boolean;
}

export interface InsightPlayerSummary {
  player_id: string;
  player_name: string | null;
  team: string | null;
  position: string;
  context: InsightContext;
  context_value: string;
  metric: string;
  sample_size: number;
  baseline_value: number | null;
  context_average: number | null;
  absolute_delta: number | null;
  relative_delta_pct: number | null;
  sample_strength: SampleStrength | null;
  insight_score: number | null;
}

export interface InsightsPlayerDetailResponse {
  player_id: string;
  position: string;
  context: InsightContext;
  context_value: string;
  metric: string;
  summary: InsightPlayerSummary;
  observations: InsightObservation[];
}

export interface InsightsContextValuesResponse {
  position: string;
  context: InsightContext;
  values: string[];
}

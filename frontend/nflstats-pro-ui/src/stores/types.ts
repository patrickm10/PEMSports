export interface PlayerRef {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  headshot_url: string | null;
}

export type AnalyticsPanel =
  | 'opponent'
  | 'stadium'
  | 'surface'
  | 'weekly'
  | 'metadata';

export const ALL_ANALYTICS_PANELS: ReadonlyArray<AnalyticsPanel> = [
  'opponent',
  'stadium',
  'surface',
  'weekly',
  'metadata',
];

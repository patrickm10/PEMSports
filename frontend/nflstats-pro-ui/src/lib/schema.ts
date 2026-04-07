import { z } from 'zod';

// Base stats shared across most positions
const BaseStatsSchema = z.object({
  player_id: z.string(),
  player_name: z.string(),
  team_abbr: z.string(),
  pos: z.string(),
  year: z.coerce.number(),
  games_played: z.coerce.number().optional(),
  fpts: z.coerce.number(),
  fpts_per_game: z.coerce.number().optional(),
});

// Position specific schemas
export const QBStatsSchema = BaseStatsSchema.extend({
  pass_yds: z.coerce.number().optional(),
  pass_tds: z.coerce.number().optional(),
  pass_ints: z.coerce.number().optional(),
  rush_yds: z.coerce.number().optional(),
  rush_tds: z.coerce.number().optional(),
});

export const RBStatsSchema = BaseStatsSchema.extend({
  rush_yds: z.coerce.number().optional(),
  rush_tds: z.coerce.number().optional(),
  receptions: z.coerce.number().optional(),
  rec_yds: z.coerce.number().optional(),
  rec_tds: z.coerce.number().optional(),
});

export const WRTEStatsSchema = BaseStatsSchema.extend({
  receptions: z.coerce.number().optional(),
  rec_yds: z.coerce.number().optional(),
  rec_tds: z.coerce.number().optional(),
  targets: z.coerce.number().optional(),
});

export const KStatsSchema = BaseStatsSchema.extend({
  fg_made: z.coerce.number().optional(),
  fg_att: z.coerce.number().optional(),
  xp_made: z.coerce.number().optional(),
});

export const DSTStatsSchema = BaseStatsSchema.extend({
  pts_allowed: z.coerce.number().optional(),
  sacks: z.coerce.number().optional(),
  ints: z.coerce.number().optional(),
  fumbles_rec: z.coerce.number().optional(),
  safeties: z.coerce.number().optional(),
  tds: z.coerce.number().optional(),
});

export type QBStats = z.infer<typeof QBStatsSchema>;
export type RBStats = z.infer<typeof RBStatsSchema>;
export type WRTEStats = z.infer<typeof WRTEStatsSchema>;
export type KStats = z.infer<typeof KStatsSchema>;
export type DSTStats = z.infer<typeof DSTStatsSchema>;

export type PlayerStats = QBStats | RBStats | WRTEStats | KStats | DSTStats;

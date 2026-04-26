import { z } from 'zod';

const nullableInteger = z.preprocess(
  (value) => {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.trunc(parsed) : value;
  },
  z.number().int().nullable(),
);

/**
 * PlayerStatsSchema (V3)
 *
 * Discriminated by the presence of `week`:
 *   - SeasonalStatsSchema: aggregate per year (no week, no matchup context).
 *   - WeeklyStatsSchema: per-game row (has week + enriched matchup fields).
 *
 * Both derive from a shared `BaseStatsSchema`. The zod `.passthrough()` at
 * each leaf preserves position-specific metrics baked by `scripts/bake_db.py`
 * (e.g. QB: `cmp`, `att`, `int`, `sacks`, `fumbles`; WR/TE: `tgt`, `rec`).
 */
const BaseStatsSchema = z.object({
  year: z.coerce.number(),
  player_id: z.coerce.string(),
  player_name: z.coerce.string(),
  team: z.string().nullable(),
  position: z.string().optional(),
  games_played: z.coerce.number().default(0),
  fpts: z.coerce.number().nullable().default(0),
  fpts_ppr: z.coerce.number().nullable().default(0),
  fpts_per_game: z.coerce.number().nullable().default(0),
  fpts_ppr_per_game: z.coerce.number().nullable().default(0),
  yds: z.coerce.number().nullable().default(0),
  td: z.coerce.number().nullable().default(0),
  rank: z.coerce.number().optional(),
});

export const SeasonalStatsSchema = BaseStatsSchema.extend({
  season: z.string().optional(),
}).passthrough();

export const WeeklyStatsSchema = BaseStatsSchema.extend({
  week: z.coerce.number(),
  opponent: z.string().optional().nullable(),
  stadium_name: z.string().optional().nullable(),
  city: z.string().optional().nullable(),
  state: z.string().optional().nullable(),
  indoor_outdoor: z.string().optional().nullable(),
  surface_type: z.string().optional().nullable(),
  elevation: z.coerce.number().optional().nullable(),
  weather_impact: z.string().optional().nullable(),
  year_opened: nullableInteger.optional(),
  temp: z.coerce.number().optional().nullable(),
  humidity: z.coerce.number().optional().nullable(),
  wind: z.coerce.number().optional().nullable(),
  game_result: z.string().optional().nullable(),
}).passthrough();

export const SeasonalStatsListSchema = z.array(SeasonalStatsSchema);
export const WeeklyStatsListSchema = z.array(WeeklyStatsSchema);

export type SeasonalStats = z.infer<typeof SeasonalStatsSchema>;
export type WeeklyStats = z.infer<typeof WeeklyStatsSchema>;

/**
 * Backwards-compatible union — most of the UI is schema-agnostic and only
 * needs the base fields. Components that depend on weekly-only fields
 * (stadium, weather, opponent) should narrow via `'week' in row`.
 */
export const PlayerStatsSchema = z.union([WeeklyStatsSchema, SeasonalStatsSchema]);
export const PlayerStatsListSchema = z.array(PlayerStatsSchema);
export type PlayerStats = z.infer<typeof PlayerStatsSchema>;

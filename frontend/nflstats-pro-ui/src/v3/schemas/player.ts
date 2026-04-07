import { z } from 'zod';

/**
 * PlayerStatsSchema (V3)
 * Enforces the Zero-Transformation Data Integrity Contract between Backend and Frontend.
 * All positions share core columns. Extended fields are handled as nullable/optional.
 */
export const PlayerStatsSchema = z.object({
  year: z.coerce.number(),
  player_id: z.string(),
  player_name: z.string(),
  team: z.string().nullable(),
  position: z.string(),
  games_played: z.coerce.number().default(0),
  fpts: z.coerce.number().nullable().default(0),
  fpts_ppr: z.coerce.number().nullable().default(0),
  fpts_per_game: z.coerce.number().nullable().default(0),
  fpts_ppr_per_game: z.coerce.number().nullable().default(0),
  yds: z.coerce.number().nullable().default(0),
  td: z.coerce.number().nullable().default(0),
  
  // Weekly / Situational Data
  week: z.coerce.number().optional().nullable(),
  opponent: z.string().optional().nullable(),
  stadium_name: z.string().optional().nullable(),
  city: z.string().optional().nullable(),
  state: z.string().optional().nullable(),
  indoor_outdoor: z.string().optional().nullable(),
  surface_type: z.string().optional().nullable(),
  elevation: z.coerce.number().optional().nullable(),
  temp: z.coerce.number().optional().nullable(),
  humidity: z.coerce.number().optional().nullable(),
  wind: z.coerce.number().optional().nullable(),
  game_result: z.string().optional().nullable(),

  // Positional Extensions
  rec: z.coerce.number().optional().nullable(),
  targets: z.coerce.number().optional().nullable(),
}).passthrough();


export type PlayerStats = z.infer<typeof PlayerStatsSchema>;

/**
 * Array Schema for multiple player results.
 */
export const PlayerStatsListSchema = z.array(PlayerStatsSchema);

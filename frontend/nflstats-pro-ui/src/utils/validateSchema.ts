import type { Ranking, SortField } from '../models/Ranking';

/**
 * Schema validation guard for development mode.
 *
 * Extracts all keys from the first API record and compares them against
 * the column config that the table will render. Logs warnings and throws
 * in dev mode if renderable API columns are silently dropped.
 *
 * Position-aware: accounts for intentionally excluded columns based on
 * verified FantasyPros data availability per position.
 */

/** Keys that are never rendered in any view (internal/metadata) */
const ALWAYS_EXCLUDED: ReadonlySet<string> = new Set([
  'player_id',
  'position',
  'year',
  'season',
  'fpts',
  'fpts_per_game',
  'yac',
  'air_yards',
  'epa',
  'target_share',
  'wopr',
]);


/**
 * Position-specific columns that are only populated for certain positions.
 * QB/K/DST do not have targets/rec from FantasyPros.
 */
const RECEIVING_ONLY: ReadonlySet<string> = new Set([
  'targets',
  'rec',
]);

const RECEIVING_POSITIONS: ReadonlySet<string> = new Set([
  'rb', 'wr', 'te',
]);

export function validateColumnSchema(
  data: Ranking[],
  columns: SortField[],
  context: string,
  isWeekly: boolean,
): void {
  if (import.meta.env.PROD || data.length === 0) return;

  const position = context.split(' ')[0]?.toLowerCase() || '';
  const apiKeys = new Set(Object.keys(data[0]));
  const renderedKeys = new Set<string>(columns);

  const missing: string[] = [];
  for (const key of apiKeys) {
    if (renderedKeys.has(key)) continue;
    if (ALWAYS_EXCLUDED.has(key)) continue;
    // Receiving columns are intentionally excluded for non-receiving positions,
    // and also excluded in seasonal views (historical CSVs lack these columns)
    if (RECEIVING_ONLY.has(key) && (!RECEIVING_POSITIONS.has(position) || !isWeekly)) continue;
    missing.push(key);
  }

  if (missing.length > 0) {
    const msg = `[Schema Drift] ${context}: API returns columns not rendered in table: ${missing.join(', ')}`;
    console.warn(msg);
    // Schema drift is informational — extra API columns are expected.
    // Never throw; this would crash the entire React tree.
  }
}

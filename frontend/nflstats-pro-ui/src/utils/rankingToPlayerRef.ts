import type { PlayerRef } from '../stores/types';

function nonEmptyString(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function nullableText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'string') return String(value);
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

/**
 * Maps a rankings row onto the player-analytics identity contract.
 * Field mapping only — no metric math. Empty position falls back to activeTab.
 */
export function rankingToPlayerRef(
  row: Record<string, unknown>,
  activeTab: string,
): PlayerRef {
  const positionSource =
    nonEmptyString(row.position) ?? nonEmptyString(activeTab) ?? '';

  return {
    player_id: typeof row.player_id === 'string' ? row.player_id : String(row.player_id ?? ''),
    player_name:
      typeof row.player_name === 'string' ? row.player_name : String(row.player_name ?? ''),
    position: positionSource.toLowerCase(),
    team: nullableText(row.team),
    headshot_url: nullableText(row.headshot_url),
  };
}

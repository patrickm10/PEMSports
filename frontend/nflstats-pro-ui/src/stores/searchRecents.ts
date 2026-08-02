import type { PlayerRef } from './types';

/** Pre-UUID bake ids: 32-char hex MD5-style keys from legacy parquets. */
const LEGACY_PLAYER_ID = /^[0-9a-f]{32}$/i;

export function isLegacyPlayerId(playerId: string): boolean {
  return LEGACY_PLAYER_ID.test(playerId.trim());
}

/** Drop recents that cannot resolve against a UUID-baked serving DB. */
export function dropLegacyRecents(recents: PlayerRef[]): PlayerRef[] {
  return recents.filter((p) => !isLegacyPlayerId(p.player_id));
}

import { describe, expect, it } from 'vitest';
import { dropLegacyRecents, isLegacyPlayerId } from './searchRecents';
import type { PlayerRef } from './types';

const sample = (player_id: string): PlayerRef => ({
  player_id,
  player_name: 'Test Player',
  position: 'QB',
  team: 'KC',
  headshot_url: null,
});

describe('searchRecents', () => {
  it('detects legacy 32-char hex player ids', () => {
    expect(isLegacyPlayerId('9ba88f3c919407fbf98aa6b04da73a53')).toBe(true);
    expect(isLegacyPlayerId('3b508539-0c0a-5aa2-9848-5c9a5af16e18')).toBe(false);
  });

  it('drops legacy recents while keeping canonical UUID ids', () => {
    const recents = [
      sample('9ba88f3c919407fbf98aa6b04da73a53'),
      sample('3b508539-0c0a-5aa2-9848-5c9a5af16e18'),
    ];
    expect(dropLegacyRecents(recents)).toEqual([recents[1]]);
  });
});

import { describe, expect, it } from 'vitest';
import { rankingToPlayerRef } from './rankingToPlayerRef';

const joshAllenRow = {
  player_id: '51a39cfa-8a39-5cc3-82f6-a529ab52bcf8',
  player_name: 'Josh Allen',
  team: 'BUF',
  position: 'QB',
  headshot_url:
    'https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/3918298.png&h=96&w=96&scale=crop',
};

describe('rankingToPlayerRef', () => {
  it('lowercases a populated position and copies identity fields', () => {
    expect(rankingToPlayerRef(joshAllenRow, 'rb')).toEqual({
      player_id: '51a39cfa-8a39-5cc3-82f6-a529ab52bcf8',
      player_name: 'Josh Allen',
      position: 'qb',
      team: 'BUF',
      headshot_url: joshAllenRow.headshot_url,
    });
  });

  it('falls back to activeTab when position is missing', () => {
    const row: Record<string, unknown> = { ...joshAllenRow };
    delete row.position;
    expect(rankingToPlayerRef(row, 'WR').position).toBe('wr');
  });

  it('falls back to activeTab when position is an empty string', () => {
    expect(
      rankingToPlayerRef({ ...joshAllenRow, position: '' }, 'DST').position,
    ).toBe('dst');
  });

  it('falls back to activeTab when position is whitespace', () => {
    expect(
      rankingToPlayerRef({ ...joshAllenRow, position: '   ' }, 'te').position,
    ).toBe('te');
  });

  it('treats null and empty team as null', () => {
    expect(rankingToPlayerRef({ ...joshAllenRow, team: null }, 'qb').team).toBeNull();
    expect(rankingToPlayerRef({ ...joshAllenRow, team: '' }, 'qb').team).toBeNull();
  });

  it('treats null and empty headshot_url as null', () => {
    expect(
      rankingToPlayerRef({ ...joshAllenRow, headshot_url: null }, 'qb').headshot_url,
    ).toBeNull();
    expect(
      rankingToPlayerRef({ ...joshAllenRow, headshot_url: '  ' }, 'qb').headshot_url,
    ).toBeNull();
  });
});

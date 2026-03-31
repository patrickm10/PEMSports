import { RankingsApi } from '../src/api/rankingsApi';

const EXPECTED_BASE = ['player_name', 'team', 'games_played', 'fpts_ppr', 'fpts_ppr_per_game'];
const EXPECTED_WEEKLY_META = ['opponent', 'stadium_name', 'temp', 'humidity', 'wind', 'game_result'];

const POS_SPECIFIC_COLS: Record<string, string[]> = {
  qb: ['cmp', 'att', 'pct', 'yds', 'y/a', 'td', 'int', 'sacks', 'r_att', 'r_yds', 'r_td', 'fl'],
  rb: ['att', 'yds', 'y/a', 'lg', '20+', 'td', 'targets', 'rec', 'r_yds', 'y/r', 'r_td', 'fl'],
  wr: ['targets', 'tgt %', 'rec', 'yds', 'y/r', '20+', 'td', 'att', 'r_yds', 'r_td', 'fl'],
  te: ['targets', 'tgt %', 'rec', 'yds', 'y/r', '20+', 'td', 'att', 'r_yds', 'r_td', 'fl'],
  k: ['pct', 'lg', '1-19', '20-29', '30-39', '40-49', '50+', 'xpt', 'xpa'],
  dst: ['fr', 'ff', 'def td', 'sfty', 'spc td']
};

export function assertColumns(data: any[], position: string, isWeekly: boolean) {
  if (data.length === 0) return { passed: false, reason: 'Empty dataset' };

  const missingCols = new Set<string>();
  const firstRow = data[0];
  const keys = Object.keys(firstRow).map(k => k.toLowerCase());

  const expected = [...EXPECTED_BASE, ...(POS_SPECIFIC_COLS[position.toLowerCase()] || [])];
  if (isWeekly) {
    expected.push(...EXPECTED_WEEKLY_META, 'week');
  }

  for (const col of expected) {
    const found = keys.some(k => k === col || k.includes(col));
    if (!found) {
       missingCols.add(col);
    }
  }

  let hasNulls = false;
  let nullColumns = new Set<string>();
  
  for (const row of Object.values(data)) {
    for (const col of expected) {
       const mappedKey = keys.find(k => k === col || k.includes(col));
       if (mappedKey && row[mappedKey] === null) {
          if (!EXPECTED_WEEKLY_META.includes(col)) {
             hasNulls = true;
             nullColumns.add(col);
          }
       }
    }
  }

  return { 
    passed: missingCols.size === 0, 
    missing: Array.from(missingCols),
    hasNulls,
    nullColumns: Array.from(nullColumns)
  };
}

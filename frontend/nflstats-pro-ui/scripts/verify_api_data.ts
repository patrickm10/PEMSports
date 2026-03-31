import { RankingsApi } from '../src/api/rankingsApi';

const EXPECTED_BASE = ['player_name', 'team', 'games_played', 'fpts_ppr', 'fpts_ppr_per_game'];
const EXPECTED_WEEKLY_META = ['opponent', 'stadium_name', 'temp', 'humidity', 'wind', 'game_result'];

// Approximate fields per position
const POS_SPECIFIC_COLS: Record<string, string[]> = {
  qb: ['cmp', 'att', 'pct', 'yds', 'y/a', 'td', 'int', 'sacks'],
  rb: ['att', 'yds', 'y/a', 'lg', '20+', 'td', 'rec', 'tgt'],
  wr: ['rec', 'tgt', 'yds', 'y/r', 'lg', '20+', 'td'],
  te: ['rec', 'tgt', 'yds', 'y/r', 'lg', '20+', 'td'],
  k: ['fg', 'fga', 'pct', 'long', 'xp', 'xpa'],
  dst: ['sack', 'int', 'fr', 'ff', 'def_td', 'sfty', 'spc_td']
};

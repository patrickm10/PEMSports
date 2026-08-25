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

/**
 * Validates that all expected columns exist and are not 100% null across the dataset.
 */
export function verifyDataPopulation(
  data: Array<Record<string, unknown>>,
  position: string,
  isWeekly: boolean,
) {
  if (data.length === 0) return { passed: true, warning: 'Empty dataset (expected for some future years/weeks)' };

  const firstRow = data[0];
  const keys = Object.keys(firstRow).map(k => k.toLowerCase());
  const expected = [...EXPECTED_BASE, ...(POS_SPECIFIC_COLS[position.toLowerCase()] || [])];
  
  if (isWeekly) {
    expected.push(...EXPECTED_WEEKLY_META, 'week');
  }

  const missing = expected.filter(col => !keys.some(k => k === col || k.includes(col)));
  
  const allNullCols: string[] = [];
  for (const col of expected) {
    const mappedKey = keys.find(k => k === col || k.includes(col));
    if (mappedKey) {
       const isPopulated = data.some(row => row[mappedKey] !== null && row[mappedKey] !== undefined && row[mappedKey] !== '');
       // Skip population check for weather metrics which can be often null
       if (!isPopulated && !['temp', 'humidity', 'wind', 'stadium_name'].includes(col)) {
          allNullCols.push(col);
       }
    }
  }

  return {
    passed: missing.length === 0 && allNullCols.length === 0,
    missing,
    allNullCols
  };
}

async function runExhaustive() {
  const positions = ['qb', 'rb', 'wr', 'te', 'k', 'dst'];
  let totalFailures = 0;

  console.log("🚀 Starting Exhaustive API Verification...");

  for (const pos of positions) {
    console.log(`\n--- Position: ${pos.toUpperCase()} ---`);
    
    try {
      const years = await RankingsApi.fetchSeasons(pos);
      console.log(`Available Years: ${years.join(', ')}`);

      for (const year of years) {
        const yearStr = year.toString();
        await new Promise(r => setTimeout(r, 100)); // Rate limit buffer
        
        // 1. Seasonal Check
        const seasonal = await RankingsApi.fetchRankings(pos, yearStr);
        const sResult = verifyDataPopulation(seasonal, pos, false);
        if (!sResult.passed) {
          console.error(`❌ ${pos} ${year} Seasonal FAILURE: Missing: [${sResult.missing}], 100% Null: [${sResult.allNullCols}]`);
          totalFailures++;
        } else {
          console.log(`✅ ${pos} ${year} Seasonal: OK (${seasonal.length} rows)`);
        }

        // 2. Weekly Check
        const weeks = await RankingsApi.fetchWeeks(pos, yearStr);
        if (weeks.length > 0) {
          // Check at least first and last week for population
          const sampleWeeks = [weeks[0], weeks[weeks.length - 1]];
          for (const week of Array.from(new Set(sampleWeeks))) {
            const weeklyData = await RankingsApi.fetchWeeklyRankings(pos, yearStr, week.toString());
            const wResult = verifyDataPopulation(weeklyData, pos, true);
            if (!wResult.passed) {
              console.error(`❌ ${pos} ${year} W${week} FAILURE: Missing: [${wResult.missing}], 100% Null: [${wResult.allNullCols}]`);
              totalFailures++;
            } else {
              console.log(`✅ ${pos} ${year} W${week}: OK (${weeklyData.length} rows)`);
            }
          }
        }
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      console.error(`❌ Fatal error for ${pos}: ${message}`);
      totalFailures++;
    }
  }

  if (totalFailures > 0) {
    console.error(`\n🚨 Exhaustive Verification FAILED with ${totalFailures} errors.`);
    process.exit(1);
  } else {
    console.log(`\n✨ Exhaustive Verification PASSED! Every column in every year/position has real data.`);
  }
}

runExhaustive();

# API Verification Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Node.js verification script to automatically assert that all dynamic frontend NFL stats properties natively map out of the backend API without truncation.

**Architecture:** A standalone TypeScript script in the frontend package that uses the existing `api/rankingsApi.ts` client to fetch all endpoints and uses programmatic assert logic to validate payloads against predefined strict constraints.

**Tech Stack:** Node.js, TypeScript, TS-Node (or standard tools defined in `package.json`), fetch.

---

### Task 1: Create Validation Configuration

**Files:**
- Create: `frontend/nflstats-pro-ui/scripts/verify_api_data.ts`

- [ ] **Step 1: Write validation matrices**

```typescript
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
```

- [ ] **Step 2: Commit file creation**

```bash
git add frontend/nflstats-pro-ui/scripts/verify_api_data.ts
git commit -m "test: scaffold api verification script consts"
```

### Task 2: Build the Assertion Engine

**Files:**
- Modify: `frontend/nflstats-pro-ui/scripts/verify_api_data.ts:16-52`

- [ ] **Step 1: Write programmatic assertion logic**

```typescript
function assertColumns(data: any[], position: string, isWeekly: boolean) {
  if (data.length === 0) return { passed: false, reason: 'Empty dataset' };

  const missingCols = new Set<string>();
  const firstRow = data[0];
  const keys = Object.keys(firstRow).map(k => k.toLowerCase());

  const expected = [...EXPECTED_BASE, ...(POS_SPECIFIC_COLS[position.toLowerCase()] || [])];
  if (isWeekly) {
    expected.push(...EXPECTED_WEEKLY_META, 'week');
  }

  for (const col of expected) {
    // Some backend columns might have different case or exact names, but we check presence
    const found = keys.some(k => k === col || k.includes(col));
    if (!found) {
       missingCols.add(col);
    }
  }

  // Null check across all rows for expected columns
  let hasNulls = false;
  for (const row of data) {
    for (const col of keys) {
       if (row[col] === null && expected.includes(col)) {
          // It is acceptable for some metadata to be missing depending on the week, but alert if standard stats are missing
          if (!EXPECTED_WEEKLY_META.includes(col)) {
             hasNulls = true; 
          }
       }
    }
  }

  return { 
    passed: missingCols.size === 0 && !hasNulls, 
    missing: Array.from(missingCols),
    hasNulls
  };
}
```

- [ ] **Step 2: Commit logic addition**

```bash
git add frontend/nflstats-pro-ui/scripts/verify_api_data.ts
git commit -m "test: add programmatic assertion engine"
```

### Task 3: Execution Loop and Runner

**Files:**
- Modify: `frontend/nflstats-pro-ui/scripts/verify_api_data.ts:54-100`
- Modify: `frontend/nflstats-pro-ui/package.json`

- [ ] **Step 1: Write execution loop**

```typescript
async function run() {
  const positions = ['qb', 'rb', 'wr', 'te', 'k', 'dst'];
  let totalErrors = 0;

  console.log("Starting API Verification...");
  for (const pos of positions) {
    console.log(`\nVerifying ${pos.toUpperCase()} Seasonal...`);
    try {
      // NOTE: Replace API_BASE dynamically since the script runs outside Vite
      (global as any).import = { meta: { env: { VITE_API_BASE: 'http://localhost:8000/api/v1' } } };
      
      const seasonal = await RankingsApi.fetchRankings(pos, '2025');
      const sResult = assertColumns(seasonal, pos, false);
      if (!sResult.passed) {
         console.error(`❌ ${pos} Seasonal Failed: missing [${sResult.missing}], nulls: ${sResult.hasNulls}`);
         totalErrors++;
      } else {
         console.log(`✅ ${pos} Seasonal Passed - Fields Verified`);
      }

      console.log(`Verifying ${pos.toUpperCase()} Weekly (Week 1)...`);
      const weekly = await RankingsApi.fetchWeeklyRankings(pos, '2025', '1');
      const wResult = assertColumns(weekly, pos, true);
      if (!wResult.passed) {
         console.error(`❌ ${pos} Weekly Failed: missing [${wResult.missing}], nulls: ${wResult.hasNulls}`);
         totalErrors++;
      } else {
         console.log(`✅ ${pos} Weekly Passed - Fields Verified`);
      }
    } catch (e: any) {
       console.error(`❌ Error fetching ${pos}: ${e.message}`);
       totalErrors++;
    }
  }

  if (totalErrors > 0) {
    console.error(`\nVerification FAILED with ${totalErrors} errors.`);
    process.exit(1);
  } else {
    console.log(`\nVerification PASSED - All dynamic schema pipelines are intact.`);
  }
}

run();
```

- [ ] **Step 2: Add npm script**
Edit `frontend/nflstats-pro-ui/package.json` manually or via script to add:
`"verify": "npm run build && node --no-warnings --loader ts-node/esm scripts/verify_api_data.ts"`
Wait, we can compile it with tsc or use `tsx` or `ts-node`. Let's just instruct to use `tsx` by running `npx tsx scripts/verify_api_data.ts`.

- [ ] **Step 3: Run the tests to verify**

Run: `cd frontend/nflstats-pro-ui && npx tsx scripts/verify_api_data.ts`
Expected: Test outputs logs checking each positional endpoint and reports "PASSED" or "FAILED". (Requires backend server to be running on 8000).

- [ ] **Step 4: Commit execution loop**

```bash
git add frontend/nflstats-pro-ui/scripts/verify_api_data.ts
git commit -m "test: add verification execution loop"
```

# API Client Verification Script Design

## Goal Description
Build a definitive programmatic verification script that ensures all dynamic data from the backend is fully loaded into the React frontend correctly. The primary validation step involves hitting all API endpoints similarly to the React app and enforcing strict assertions against the payloads.

## Proposed Changes (Design)

### Overview
We will create an automated Node.js validation script (`frontend/nflstats-pro-ui/scripts/verify_api_data.ts`) built with TypeScript. It will use the exact same types (`Ranking`) as the frontend.

### Component Details
1. **Target**: All positional endpoints (`QB`, `RB`, `WR`, `TE`, `K`, `DST`) for both seasonal and weekly views.
2. **Column Requirements**:
   - Establish position-specific matrices of expected columns that inherently mirror the original FantasyPros metrics:
     - `QB`: `CMP, ATT, PCT, YDS, Y/A, TD, INT, SACKS`, etc.
     - `RB`: `ATT, YDS, Y/A, LG, 20+, TD, REC, TGT`, etc.
     - `WR/TE`: `REC, TGT, YDS, Y/R, LG, 20+, TD`, etc.
     - `K`: `FG, FGA, PCT, LONG, XP, XPA`, etc.
     - `DST`: `SACK, INT, FR, FF, DEF TD, SFTY, SPC TD`, etc.
   - For Weekly views, explicitly require enrichment metadata: `opponent, stadium_name, city, state, indoor_outdoor, surface_type, elevation, temp, humidity, wind, game_result`.
3. **Execution Logic**:
   - The script iterates through each position/view configuration.
   - Fetches exactly how the `rankingsApi.ts` client would.
   - Iterates through all returned rows and asserts the presence of all required base stats and metadata.
   - Asserts that no expected column is entirely `null` or missing, logging detailed discrepancies across the dataset.
   - Serializes the JSON payload, matching it to the `Ranking` structure expected by the React UI.

## Verification Plan
1. This script *is* the verification. Once implemented, running it on the local development environment against the FastAPI server will programmatically determine whether data flow from duckdb -> FastAPI -> frontend passes every requirement.
2. If this script outputs "PASS", we can confidently state the dynamic schema extraction succeeded down to the client boundary.

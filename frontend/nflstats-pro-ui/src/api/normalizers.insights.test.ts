import { describe, expect, it } from 'vitest';
import { toInsightsTimeSeriesChartModel } from './normalizers';
import type { InsightsPlayerDetailResponse } from './insightsTypes';

function fixture(
  observations: InsightsPlayerDetailResponse['observations'],
): InsightsPlayerDetailResponse {
  return {
    player_id: 'p1',
    position: 'rb',
    context: 'surface',
    context_value: 'Grass',
    metric: 'fpts_ppr',
    summary: {
      player_id: 'p1',
      player_name: 'Test Back',
      team: 'KC',
      position: 'rb',
      context: 'surface',
      context_value: 'Grass',
      metric: 'fpts_ppr',
      sample_size: 1,
      baseline_value: 14,
      context_average: 18.5,
      absolute_delta: 4.5,
      relative_delta_pct: 32.14,
      sample_strength: 'Low',
      insight_score: 4.0175,
    },
    observations,
  };
}

describe('toInsightsTimeSeriesChartModel', () => {
  it('maps actual points and LOO baseline without client-side math', () => {
    const model = toInsightsTimeSeriesChartModel(
      fixture([
        {
          season: 2024,
          week: 1,
          opponent: 'KC',
          stadium_name: 'Arrowhead Stadium',
          surface_type: 'Grass',
          home_away: 'Away',
          fantasy_points: 18.5,
          season_baseline: 14.0,
          relative_change_pct: 32.14,
          in_context: true,
        },
        {
          season: 2024,
          week: 2,
          opponent: 'BUF',
          stadium_name: null,
          surface_type: 'Turf',
          home_away: 'Home',
          fantasy_points: 10,
          season_baseline: 16,
          relative_change_pct: -37.5,
          in_context: false,
        },
      ]),
    );

    expect(model.series).toHaveLength(2);
    expect(model.series[0].name).toBe('Fantasy Points');
    expect(model.series[1].name).toBe('Season baseline');
    expect(model.series[0].points.map((p) => p.y)).toEqual([18.5, 10]);
    expect(model.series[1].points.map((p) => p.y)).toEqual([14.0, 16]);
    expect(model.xAxis).toEqual(["W1 '24", "W2 '24"]);
  });

  it('preserves null metric points instead of coercing to zero', () => {
    const model = toInsightsTimeSeriesChartModel(
      fixture([
        {
          season: 2024,
          week: 3,
          opponent: null,
          stadium_name: null,
          surface_type: null,
          home_away: null,
          fantasy_points: null,
          season_baseline: null,
          relative_change_pct: null,
          in_context: false,
        },
      ]),
    );
    expect(model.series[0].points[0].y).toBeNull();
    expect(model.series[1].points[0].y).toBeNull();
  });
});

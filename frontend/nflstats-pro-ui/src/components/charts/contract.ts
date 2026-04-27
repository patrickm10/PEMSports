/**
 * Stable intermediate models that bridge raw API responses and chart builders.
 *
 * Chart builders consume ONLY these types. Raw API shapes (PlayerSplitResponse,
 * PlayerWeeklyResponse, etc.) never reach a builder or a chart component.
 * The single boundary that produces these models is `src/api/normalizers.ts`.
 */

export interface CategoricalSeries {
  name: string;
  values: Array<number | null>;
  color?: string;
}

export interface CategoricalChartModel {
  categories: string[];
  series: CategoricalSeries[];
  yAxisLabel?: string;
  valueFormatter?: (v: number | null) => string;
}

export interface TimeSeriesPoint {
  x: string | number;
  y: number | null;
}

export interface TimeSeries {
  name: string;
  points: TimeSeriesPoint[];
  color?: string;
}

export interface TimeSeriesChartModel {
  xAxis: Array<string | number>;
  series: TimeSeries[];
  xAxisLabel?: string;
  yAxisLabel?: string;
  valueFormatter?: (v: number | null) => string;
}

export interface AggregateRow {
  games: number;
  ppr: number | null;
  yards: number | null;
  tds: number | null;
}

export interface MetadataOverlayModel {
  homeAway: { home: AggregateRow; away: AggregateRow };
  rest: Array<{ bucket: string; row: AggregateRow }>;
  weather: Array<{ key: string; row: AggregateRow }>;
}

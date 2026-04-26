import type { EChartsOption } from 'echarts';
import type { Ranking } from '../../models/Ranking';
import type { ResolvedMetric } from '../../utils/metrics';
import { formatMetricValue } from '../../utils/metrics';

export type DashboardFacetKey = 'opponent' | 'surface_type' | 'indoor_outdoor';

interface RankedChartPoint {
  name: string;
  team: string;
  value: number;
}

interface FacetChartPoint {
  name: string;
  value: number;
  count: number;
}

const axisLabelColor = '#94a3b8';
const splitLineColor = 'rgba(148, 163, 184, 0.12)';
const tooltipBackground = 'rgba(15, 23, 42, 0.96)';

function normalizedLabel(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  return trimmed;
}

function rankedTooltip(params: unknown): string {
  const point = Array.isArray(params) ? params[0] : params;
  const data = (point as { data?: RankedChartPoint }).data;
  if (!data) return '';
  const team = data.team ? ` · ${data.team}` : '';
  return `${data.name}${team}<br/>${formatMetricValue(data.value)}`;
}

function rankedLabel(params: unknown): string {
  const data = (params as { data?: RankedChartPoint }).data;
  return formatMetricValue(data?.value);
}

function facetTooltip(params: unknown): string {
  const point = Array.isArray(params) ? params[0] : params;
  const data = (point as { data?: FacetChartPoint }).data;
  if (!data) return '';
  return `${data.name}<br/>Average: ${formatMetricValue(data.value)}<br/>Players: ${data.count}`;
}

export function buildRankingsTopTenOption(
  rows: Ranking[],
  metric: ResolvedMetric | null,
): EChartsOption | null {
  if (!metric) return null;

  const points = rows
    .map((row) => ({
      name: row.player_name,
      team: row.team ?? '',
      value: metric.getValue(row),
    }))
    .filter((point): point is RankedChartPoint => point.value !== null)
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  if (points.length === 0) return null;

  return {
    grid: { top: 8, right: 24, bottom: 24, left: 112 },
    tooltip: {
      trigger: 'item',
      backgroundColor: tooltipBackground,
      borderColor: splitLineColor,
      textStyle: { color: '#e2e8f0' },
      formatter: rankedTooltip,
    },
    xAxis: {
      type: 'value',
      axisLabel: { color: axisLabelColor },
      splitLine: { lineStyle: { color: splitLineColor } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: points.map((point) => point.name),
      axisLabel: { color: axisLabelColor, width: 96, overflow: 'truncate' },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: points,
        encode: { x: 'value', y: 'name' },
        barMaxWidth: 18,
        itemStyle: { color: '#38bdf8', borderRadius: [0, 6, 6, 0] },
        label: {
          show: true,
          position: 'right',
          color: '#cbd5e1',
          formatter: rankedLabel,
        },
      },
    ],
  };
}

export function buildMetricByFacetOption(
  rows: Ranking[],
  metric: ResolvedMetric | null,
  facetKey: DashboardFacetKey,
): EChartsOption | null {
  if (!metric) return null;

  const groups = new Map<string, { total: number; count: number }>();
  for (const row of rows) {
    const label = normalizedLabel(row[facetKey]);
    const value = metric.getValue(row);
    if (!label || value === null) continue;

    const current = groups.get(label) ?? { total: 0, count: 0 };
    current.total += value;
    current.count += 1;
    groups.set(label, current);
  }

  const points = Array.from(groups.entries())
    .map(([name, group]) => ({
      name,
      value: group.total / group.count,
      count: group.count,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, facetKey === 'opponent' ? 12 : 8);

  if (points.length === 0) return null;

  return {
    grid: { top: 8, right: 18, bottom: 44, left: 42 },
    tooltip: {
      trigger: 'item',
      backgroundColor: tooltipBackground,
      borderColor: splitLineColor,
      textStyle: { color: '#e2e8f0' },
      formatter: facetTooltip,
    },
    xAxis: {
      type: 'category',
      data: points.map((point) => point.name),
      axisLabel: {
        color: axisLabelColor,
        interval: 0,
        rotate: points.length > 5 ? 28 : 0,
      },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: splitLineColor } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: axisLabelColor },
      splitLine: { lineStyle: { color: splitLineColor } },
    },
    series: [
      {
        type: 'bar',
        data: points,
        encode: { x: 'name', y: 'value' },
        barMaxWidth: 36,
        itemStyle: { color: '#22c55e', borderRadius: [6, 6, 0, 0] },
      },
    ],
  };
}

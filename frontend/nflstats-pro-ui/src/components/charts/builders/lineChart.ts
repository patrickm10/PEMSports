import type { EChartsOption } from 'echarts';
import type { TimeSeriesChartModel } from '../contract';
import { CHART_PALETTE } from '../seasonColors';

const axisLabelColor = '#94a3b8';
const splitLineColor = 'rgba(148, 163, 184, 0.12)';
const tooltipBackground = 'rgba(15, 23, 42, 0.96)';

/**
 * Builds an ECharts line option from the chart-data contract.
 * Consumes ONLY TimeSeriesChartModel — never raw API responses.
 */
export function buildLineSeriesOption(
  model: TimeSeriesChartModel,
): EChartsOption | null {
  if (!model.xAxis.length || !model.series.length) return null;

  const formatter =
    model.valueFormatter ??
    ((v: number | null) => (v === null ? '—' : v.toFixed(1)));

  return {
    animation: false,
    grid: { top: 32, right: 24, bottom: 36, left: 48 },
    legend: {
      show: model.series.length > 1,
      top: 0,
      textStyle: { color: '#cbd5e1', fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: tooltipBackground,
      borderColor: splitLineColor,
      textStyle: { color: '#e2e8f0' },
      valueFormatter: (v) => formatter(v as number | null),
    },
    xAxis: {
      type: 'category',
      data: model.xAxis.map(String),
      name: model.xAxisLabel,
      nameTextStyle: { color: axisLabelColor, padding: [12, 0, 0, 0] },
      axisLabel: { color: axisLabelColor },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: splitLineColor } },
    },
    yAxis: {
      type: 'value',
      name: model.yAxisLabel,
      nameTextStyle: { color: axisLabelColor, padding: [0, 0, 0, 32] },
      axisLabel: { color: axisLabelColor },
      splitLine: { lineStyle: { color: splitLineColor } },
    },
    series: model.series.map((s, i) => ({
      type: 'line',
      name: s.name,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      connectNulls: false,
      data: s.points.map((p) => (p.y === null ? null : p.y)),
      emphasis: { disabled: true },
      select: { disabled: true },
      itemStyle: { color: s.color ?? CHART_PALETTE[i % CHART_PALETTE.length] },
      lineStyle: {
        width: 2,
        color: s.color ?? CHART_PALETTE[i % CHART_PALETTE.length],
      },
    })),
  };
}

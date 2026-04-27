import type { EChartsOption } from 'echarts';
import type { CategoricalChartModel } from '../contract';

const axisLabelColor = '#94a3b8';
const splitLineColor = 'rgba(148, 163, 184, 0.12)';
const tooltipBackground = 'rgba(15, 23, 42, 0.96)';

const PALETTE = ['#38bdf8', '#f97316', '#22c55e', '#a78bfa'];

interface BuildOpts {
  height?: number;
  rotateLabels?: boolean;
}

/**
 * Builds an ECharts grouped-bar option from the chart-data contract.
 * Consumes ONLY CategoricalChartModel — never raw API responses.
 */
export function buildGroupedBarOption(
  model: CategoricalChartModel,
  opts: BuildOpts = {},
): EChartsOption | null {
  if (!model.categories.length || !model.series.length) return null;

  const formatter =
    model.valueFormatter ??
    ((v: number | null) => (v === null ? '—' : v.toFixed(1)));

  return {
    animation: false,
    grid: { top: 28, right: 18, bottom: 56, left: 48 },
    legend: {
      show: model.series.length > 1,
      top: 0,
      textStyle: { color: '#cbd5e1', fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10,
    },
    tooltip: {
      // Hover/highlight is where ECharts can get expensive. `axis` tooltips
      // require cross-series pointer work; `item` is cheaper for grouped bars.
      trigger: 'item',
      backgroundColor: tooltipBackground,
      borderColor: splitLineColor,
      textStyle: { color: '#e2e8f0' },
      valueFormatter: (v) => formatter(v as number | null),
    },
    xAxis: {
      type: 'category',
      data: model.categories,
      axisLabel: {
        color: axisLabelColor,
        interval: 0,
        rotate:
          opts.rotateLabels === true
            ? 32
            : opts.rotateLabels === false
              ? 0
              : model.categories.length > 6
                ? 32
                : 0,
      },
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
      type: 'bar',
      name: s.name,
      data: s.values.map((v) => (v === null ? null : v)),
      barMaxWidth: 24,
      // Disable heavy hover emphasis to keep interactions responsive.
      emphasis: { disabled: true },
      select: { disabled: true },
      itemStyle: {
        color: s.color ?? PALETTE[i % PALETTE.length],
        borderRadius: [4, 4, 0, 0],
      },
    })),
  };
}

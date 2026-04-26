import React from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';

interface EChartProps {
  option: EChartsOption | null;
  title: string;
  subtitle?: string;
  height?: number;
  isLoading?: boolean;
  emptyMessage?: string;
}

export const EChart: React.FC<EChartProps> = ({
  option,
  title,
  subtitle,
  height = 280,
  isLoading = false,
  emptyMessage = 'No chart data available',
}) => {
  return (
    <section className="rounded-2xl p-5 glass-card border-white/10 min-w-0">
      <div className="mb-4">
        <h3 className="text-white font-bold text-base">{title}</h3>
        {subtitle && <p className="text-slate-400 text-xs mt-1">{subtitle}</p>}
      </div>

      {isLoading ? (
        <div
          className="rounded-xl bg-slate-900/40 border border-slate-800/40 animate-pulse"
          style={{ height }}
        />
      ) : option ? (
        <ReactECharts
          option={option}
          style={{ height, width: '100%' }}
          notMerge
          lazyUpdate
        />
      ) : (
        <div
          className="rounded-xl bg-slate-900/20 border border-slate-800/40 flex items-center justify-center text-slate-500 text-sm"
          style={{ height }}
        >
          {emptyMessage}
        </div>
      )}
    </section>
  );
};

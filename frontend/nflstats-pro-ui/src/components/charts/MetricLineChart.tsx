import React, { useMemo } from 'react';
import { EChart } from './EChart';
import type { TimeSeriesChartModel } from './contract';
import { buildLineSeriesOption } from './builders/lineChart';

interface MetricLineChartProps {
  data: TimeSeriesChartModel | null;
  title: string;
  subtitle?: string;
  height?: number;
  isLoading?: boolean;
  emptyMessage?: string;
}

/**
 * Strictly presentational. Receives a pre-normalized chart contract
 * and forwards a built EChartsOption to the low-level adapter.
 */
export const MetricLineChart: React.FC<MetricLineChartProps> = ({
  data,
  title,
  subtitle,
  height,
  isLoading,
  emptyMessage,
}) => {
  const option = useMemo(
    () => (data ? buildLineSeriesOption(data) : null),
    [data],
  );

  return (
    <EChart
      option={option}
      title={title}
      subtitle={subtitle}
      height={height}
      isLoading={isLoading}
      emptyMessage={emptyMessage}
    />
  );
};

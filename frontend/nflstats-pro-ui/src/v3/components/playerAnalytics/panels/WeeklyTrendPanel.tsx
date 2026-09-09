import React from 'react';
import { MetricLineChart } from '../../../../components/charts/MetricLineChart';
import type { TimeSeriesChartModel } from '../../../../components/charts/contract';

interface Props {
  data: TimeSeriesChartModel | null;
  isLoading?: boolean;
  error?: Error | null;
  title?: string;
  subtitle?: string;
  height?: number;
}

export const WeeklyTrendPanel: React.FC<Props> = ({
  data,
  isLoading,
  error,
  title = 'Weekly Performance',
  subtitle = 'PPR by week — one series per season',
  height = 320,
}) => (
  <MetricLineChart
    data={data}
    title={title}
    subtitle={subtitle}
    height={height}
    isLoading={isLoading}
    emptyMessage={
      error
        ? 'Unable to load weekly trend'
        : 'No weekly games available for this player'
    }
  />
);

import React from 'react';
import { MetricLineChart } from '../../../../components/charts/MetricLineChart';
import type { TimeSeriesChartModel } from '../../../../components/charts/contract';

interface Props {
  data: TimeSeriesChartModel | null;
  isLoading?: boolean;
  error?: Error | null;
}

export const WeeklyTrendPanel: React.FC<Props> = ({ data, isLoading, error }) => (
  <MetricLineChart
    data={data}
    title="Weekly Performance"
    subtitle="PPR by week — one series per season"
    height={320}
    isLoading={isLoading}
    emptyMessage={
      error
        ? 'Unable to load weekly trend'
        : 'No weekly games available for this player'
    }
  />
);

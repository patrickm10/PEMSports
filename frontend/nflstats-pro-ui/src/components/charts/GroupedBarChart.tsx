import React, { useMemo } from 'react';
import { EChart } from './EChart';
import type { CategoricalChartModel } from './contract';
import { buildGroupedBarOption } from './builders/groupedBar';

interface GroupedBarChartProps {
  data: CategoricalChartModel | null;
  title: string;
  subtitle?: string;
  height?: number;
  isLoading?: boolean;
  emptyMessage?: string;
  rotateLabels?: boolean;
}

/**
 * Strictly presentational. Receives a pre-normalized chart contract
 * and forwards a built EChartsOption to the low-level adapter.
 */
export const GroupedBarChart: React.FC<GroupedBarChartProps> = ({
  data,
  title,
  subtitle,
  height,
  isLoading,
  emptyMessage,
  rotateLabels,
}) => {
  const option = useMemo(
    () => (data ? buildGroupedBarOption(data, { rotateLabels }) : null),
    [data, rotateLabels],
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
